"""Deterministic synthetic world — the research feed (SYNTHETIC, seeded).

Exercises the full pipeline with zero network, zero capital, zero Wintermute
API. When W1 delivers real quotes, a real feed class implements the same
surface (``funding_obs``, ``spot_quotes``, ``forward_quote``) and the strategy
code does not change.

World model:
- one underlying (default "SYN") with a spot price following a GBM;
- a CEX perp whose funding APR follows an OU process around a drifting mean;
  funding settles every 8h and prints with observation noise;
- an OTC desk that quotes spot and dated forwards off a SLOW EWMA of the
  observed funding history (its own pricing model) plus quote noise — the
  synthetic stand-in for "the desk's implied carry lags realized funding".

Everything is driven by ``advance_day()``; the RNG is seeded, so runs are
reproducible bit-for-bit.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..models.market_data import (FundingObservation, Instrument, Price,
                                  PriceSource, RFQQuote)

DAY_MS = 86_400_000
H8_MS = 8 * 3_600_000


@dataclass
class MockRFQFeedParams:
    symbol: str = "SYN"
    spot0: float = 100.0
    spot_vol_annual: float = 0.45
    apr_mean: float = 0.09
    apr_vol_annual: float = 0.03          # OU vol of the funding APR
    ou_half_life_days: float = 12.0
    apr_drift_per_day: float = 0.0        # regime drift applied via drift_fn
    obs_noise_per_8h: float = 0.6e-4      # per-settlement print noise (rate units)
    desk_slow_half_life_h: float = 720.0  # desk pricing lags ~30 days
    desk_quote_noise_apr: float = 0.003   # σ of desk's implied-APR noise
    desk_spot_half_spread_bps: float = 3.0
    desk_fwd_half_spread_bps: float = 6.0
    quote_ttl_ms: int = 30_000


@dataclass
class MockRFQFeed:
    """Seeded synthetic CEX+desk world. Call ``advance_day()`` once per day."""

    seed: int = 7
    params: MockRFQFeedParams = field(default_factory=MockRFQFeedParams)
    mean_fn: Optional[object] = None     # callable(day_index) -> target funding APR mean

    def __post_init__(self) -> None:
        p = self.params
        self._rng = random.Random(self.seed)
        self._day = 0
        self._t0 = 1_767_225_600_000      # 2026-01-01T00:00:00Z (fixed epoch)
        self._now = self._t0
        self._apr = p.apr_mean
        self._spot = p.spot0
        self._obs: List[FundingObservation] = []
        self._quote_seq = 0

    # ------------------------------------------------------------------ world

    def advance_day(self) -> None:
        p = self.params
        self._day += 1
        self._now = self._t0 + self._day * DAY_MS
        target_mean = self.mean_fn(self._day) if callable(self.mean_fn) else p.apr_mean
        ou_pull = -(math.log(2.0) / p.ou_half_life_days) * (self._apr - target_mean)
        shock = p.apr_vol_annual / math.sqrt(365.0) * self._rng.gauss(0.0, 1.0)
        self._apr = self._apr + ou_pull + shock
        daily_spot_vol = p.spot_vol_annual / math.sqrt(365.0)
        self._spot *= math.exp(-0.5 * daily_spot_vol ** 2 + daily_spot_vol * self._rng.gauss(0.0, 1.0))
        # three 8h funding settlements per day, observed with print noise
        for k in range(3):
            ts = self._now - DAY_MS + (k + 1) * H8_MS
            rate = self._apr / (3.0 * 365.0) + self._rng.gauss(0.0, p.obs_noise_per_8h)
            self._obs.append(FundingObservation(
                venue="SYNTH_CEX", symbol=f"{p.symbol}-PERP",
                rate_interval=rate, interval_h=8.0, ts=ts))

    @property
    def day(self) -> int:
        return self._day

    @property
    def now_ms(self) -> int:
        return self._now

    @property
    def spot(self) -> float:
        return self._spot

    @property
    def true_apr(self) -> float:
        return self._apr

    @property
    def funding_obs(self) -> List[FundingObservation]:
        return list(self._obs)

    def realized_funding_apr_between(self, day_from: int, day_to: int) -> float:
        """Mean true APR over a day window (research comparison only)."""
        lo, hi = self._t0 + day_from * DAY_MS, self._t0 + day_to * DAY_MS
        pts = [(o.ts, o.rate_interval / o.interval_h) for o in self._obs if lo <= o.ts <= hi]
        if not pts:
            return float("nan")
        return sum(r for _, r in pts) / len(pts) * 24.0 * 365.0

    # ------------------------------------------------------------------ desk

    def _ref_mid(self) -> Price:
        return Price(value=self._spot, source=PriceSource.SYNTHETIC_MOCK, ts=self._now)

    def _next_quote_id(self) -> str:
        self._quote_seq += 1
        return f"MQ-{self._day:04d}-{self._quote_seq:04d}"

    def _desk_slow_apr(self) -> float:
        """The desk prices forwards off a slow EWMA of *observed* funding."""
        p = self.params
        if not self._obs:
            return p.apr_mean
        ref = self._obs[-1].ts
        wsum, rsum = 0.0, 0.0
        for o in self._obs:
            age_h = max(0.0, (ref - o.ts) / 3.6e6)
            w = 0.5 ** (age_h / p.desk_slow_half_life_h)
            wsum += w
            rsum += w * o.rate_hourly
        return (rsum / wsum) * 24.0 * 365.0

    def spot_instrument(self) -> Instrument:
        p = self.params
        return Instrument(symbol=p.symbol, kind="spot", venue="SYNTH_DESK", base=p.symbol,
                          qty_precision=4)

    def forward_instrument(self, tenor_days: int) -> Instrument:
        p = self.params
        return Instrument(symbol=f"{p.symbol}-FWD-{tenor_days}D", kind="forward",
                          venue="SYNTH_DESK", base=p.symbol, qty_precision=4,
                          expiry_ts=self._now + tenor_days * DAY_MS)

    def spot_quotes(self) -> Tuple[RFQQuote, RFQQuote]:
        """Desk spot (bid, ask) around the composite mid."""
        p = self.params
        mid = self._ref_mid()
        half = p.desk_spot_half_spread_bps / 1e4
        bid_px = Price(value=self._spot * (1.0 - half), source=PriceSource.SYNTHETIC_MOCK, ts=self._now)
        ask_px = Price(value=self._spot * (1.0 + half), source=PriceSource.SYNTHETIC_MOCK, ts=self._now)
        inst = self.spot_instrument()
        return (
            RFQQuote(quote_id=self._next_quote_id(), instrument=inst, side="bid",
                     px=bid_px, size_quote=1_000.0, ref_mid=mid, ttl_ms=p.quote_ttl_ms),
            RFQQuote(quote_id=self._next_quote_id(), instrument=inst, side="ask",
                     px=ask_px, size_quote=1_000.0, ref_mid=mid, ttl_ms=p.quote_ttl_ms),
        )

    def forward_quotes(self, tenor_days: int) -> Tuple[RFQQuote, RFQQuote]:
        """Desk dated-forward (bid, ask).

        The desk's implied APR = its slow funding estimate + quote noise; the
        premium is then (1 + implied·tenor/365) on the current spot.
        """
        p = self.params
        mid = self._ref_mid()
        implied = self._desk_slow_apr() + self._rng.gauss(0.0, p.desk_quote_noise_apr)
        fwd_mid = self._spot * (1.0 + implied * tenor_days / 365.0)
        half = p.desk_fwd_half_spread_bps / 1e4
        bid_px = Price(value=fwd_mid * (1.0 - half), source=PriceSource.SYNTHETIC_MOCK, ts=self._now)
        ask_px = Price(value=fwd_mid * (1.0 + half), source=PriceSource.SYNTHETIC_MOCK, ts=self._now)
        inst = self.forward_instrument(tenor_days)
        return (
            RFQQuote(quote_id=self._next_quote_id(), instrument=inst, side="bid",
                     px=bid_px, size_quote=1_000.0, ref_mid=mid, ttl_ms=p.quote_ttl_ms),
            RFQQuote(quote_id=self._next_quote_id(), instrument=inst, side="ask",
                     px=ask_px, size_quote=1_000.0, ref_mid=mid, ttl_ms=p.quote_ttl_ms),
        )

    def settlement_print(self) -> Price:
        """Forward settlement fixing = spot at expiry (cash settlement)."""
        return Price(value=self._spot, source=PriceSource.SETTLEMENT_PRINT, ts=self._now)

    # ------------------------------------------------------------------ cex perp
    # v0.3.0 (decision record C3): the floating-carry instrument. The synthetic
    # perp tracks the index (mark = spot composite) — basis drift is not the
    # research question here; funding float is. Costs (taker fee + half-spread)
    # are EXPLICIT waterfall lines, not embedded in this price (a CEX leg is not
    # an RFQ — see I-4's scope note in edge/all_in_edge.py).

    def perp_instrument(self) -> Instrument:
        p = self.params
        return Instrument(symbol=f"{p.symbol}-PERP", kind="perp", venue="SYNTH_CEX",
                          base=p.symbol, qty_precision=4)

    def perp_mark(self) -> Price:
        """CEX perp mark = the composite index level (source-tagged, I-1)."""
        return Price(value=self._spot, source=PriceSource.PERP_MARK, ts=self._now)

    def printed_funding_between(self, ts_from: int, ts_to: int) -> float:
        """Σ printed per-interval funding rates over (ts_from, ts_to].

        The accrual a short-perp position actually receives on a CEX: the
        printed settlement rates (observation noise included), interval-
        normalized inside the sum. Multiply by qty × reference notional.
        """
        return sum(o.rate_interval for o in self._obs if ts_from < o.ts <= ts_to)
