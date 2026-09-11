"""Market-data primitives — invariant-first.

The funding-arb audit (NEW-16/17/18/20, fee double-count, quantity chain)
taught that measurement defects are silent unless the *schema itself* forbids
them. This module is that lesson turned into types:

I-1  a Price is never a naked number — it always carries an explicit source
     tag and a timestamp (NEW-16: "mark price" that was actually a ticker).
I-4  an RFQ quote's fee model is fully embedded in the quoted price — the
     all-in cost is the distance from the reference mid, counted once.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PriceSource(str, Enum):
    """Explicit provenance for every price that enters the engine."""

    SPOT_BOOK_MID = "spot_book_mid"
    SPOT_BOOK_LAST = "spot_book_last"
    PERP_MARK = "perp_mark"
    PERP_INDEX = "perp_index"
    PERP_LAST = "perp_last"
    DESK_RFQ_QUOTE = "desk_rfq_quote"          # OTC desk quote (e.g. Wintermute NODE)
    SETTLEMENT_PRINT = "settlement_print"      # final settlement / fixing
    SYNTHETIC_MOCK = "synthetic_mock"          # deterministic research world


INSTRUMENT_KINDS = ("spot", "perp", "forward", "cfd", "option")


@dataclass(frozen=True)
class Instrument:
    """A tradable definition, venue-agnostic.

    Dated instruments (forwards) must carry ``expiry_ts`` — the audit's
    interval/timestamp discipline applies to tenor as well as price.
    """

    symbol: str
    kind: str                     # one of INSTRUMENT_KINDS
    venue: str
    base: str
    quote: str = "USD"
    contract_size: float = 1.0
    tick_size: Optional[float] = None
    qty_precision: int = 8
    expiry_ts: Optional[int] = None   # unix ms; required for kind == "forward"

    def __post_init__(self) -> None:
        if self.kind not in INSTRUMENT_KINDS:
            raise ValueError(f"unknown instrument kind: {self.kind!r}")
        if not self.symbol or not self.venue or not self.base:
            raise ValueError("symbol, venue and base are required")
        if self.kind == "forward" and self.expiry_ts is None:
            raise ValueError(f"forward {self.symbol} requires expiry_ts")
        if self.contract_size <= 0:
            raise ValueError("contract_size must be positive")
        if self.qty_precision < 0 or self.qty_precision > 12:
            raise ValueError("qty_precision must be in 0..12")


@dataclass(frozen=True)
class Price:
    """I-1: value + explicit source + timestamp. No exceptions."""

    value: float
    source: PriceSource
    ts: int                        # unix ms

    def __post_init__(self) -> None:
        if not math.isfinite(self.value) or self.value <= 0:
            raise ValueError(f"invalid price value: {self.value!r}")
        if self.ts <= 0:
            raise ValueError("price requires a positive unix-ms timestamp")

    def to_payload(self) -> dict:
        return {"value": self.value, "source": self.source.value, "ts": self.ts}

    @staticmethod
    def from_payload(d: dict) -> "Price":
        return Price(value=float(d["value"]), source=PriceSource(d["source"]), ts=int(d["ts"]))


@dataclass(frozen=True)
class FundingObservation:
    """One realized funding settlement on a CEX perp.

    ``rate_interval`` is the rate *per settlement interval* (fraction, e.g.
    0.0001 = 1 bp per interval). Hour-normalization happens here — the audit's
    cross-interval discipline (NEW-19) is not left to callers.
    """

    venue: str
    symbol: str
    rate_interval: float
    interval_h: float              # 1, 4, 8 …
    ts: int

    def __post_init__(self) -> None:
        if self.interval_h <= 0:
            raise ValueError("interval_h must be positive")
        if not math.isfinite(self.rate_interval):
            raise ValueError("rate_interval must be finite")
        if self.ts <= 0:
            raise ValueError("funding observation requires a positive timestamp")

    @property
    def rate_hourly(self) -> float:
        return self.rate_interval / self.interval_h

    @property
    def apr(self) -> float:
        """Annualized percentage rate equivalent of this settlement."""
        return self.rate_hourly * 24.0 * 365.0


@dataclass(frozen=True)
class RFQQuote:
    """One OTC desk quote.

    I-4: the entire fee model of an RFQ fill is embedded in the price. The
    all-in cost of taking this quote is its distance from ``ref_mid`` — it is
    never added again anywhere downstream.

    ``side`` is from the *desk's* perspective: the desk sells at ``ask`` and
    buys at ``bid``.
    """

    quote_id: str
    instrument: Instrument
    side: str                      # "bid" | "ask"
    px: Price                      # source: DESK_RFQ_QUOTE (or SYNTHETIC_MOCK in research)
    size_quote: float              # quoted size, base units
    ref_mid: Price                 # composite reference mid for benchmarking
    ttl_ms: int

    def __post_init__(self) -> None:
        if self.side not in ("bid", "ask"):
            raise ValueError(f"RFQ side must be bid/ask, got {self.side!r}")
        if self.px.source not in (PriceSource.DESK_RFQ_QUOTE, PriceSource.SYNTHETIC_MOCK):
            raise ValueError(f"RFQ px must be a desk quote or synthetic mock source, got {self.px.source}")
        if self.size_quote <= 0 or self.ttl_ms <= 0:
            raise ValueError("size_quote and ttl_ms must be positive")

    @property
    def all_in_cost_bps(self) -> float:
        """Cost of crossing this quote vs the reference mid, in bps (positive = cost)."""
        if self.side == "ask":
            return (self.px.value - self.ref_mid.value) / self.ref_mid.value * 1e4
        return (self.ref_mid.value - self.px.value) / self.ref_mid.value * 1e4

    def to_payload(self) -> dict:
        return {
            "quote_id": self.quote_id,
            "instrument": self.instrument.symbol,
            "kind": self.instrument.kind,
            "venue": self.instrument.venue,
            "side": self.side,
            "price": self.px.to_payload(),
            "size_quote": self.size_quote,
            "ref_mid": self.ref_mid.to_payload(),
            "ttl_ms": self.ttl_ms,
            "all_in_cost_bps": round(self.all_in_cost_bps, 6),
        }
