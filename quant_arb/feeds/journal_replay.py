"""W1-INFRA: the RFQ journal replay feed (v0.6.2, sealed docs/w1-replay-adapter.md).

Replays a W0 raw RFQ journal through the engine's typed quote vocabulary —
the bridge between the immutable real-world record and the research layer
that W1's own sealed decision record will drive. Infrastructure, not
research: this module produces **no research number**.

Mapping = sealed rules M-1…M-10 of the design record:
  eligibility (quoted+firm only) · requesting side → desk bid/ask · I-1
  provenance on every Price (DESK_RFQ_QUOTE / SYNTHETIC_MOCK on px; the
  record's reference source on ref_mid, unknown → REFERENCE_OTHER) ·
  size = notional/px (same-ccy) · ttl = expiry−ts · forward tenor from the
  ``-FWD-{n}D`` symbol suffix · one feed = one instrument family (spot
  ``{SYM}``, forward ``{SYM}-FWD-{n}D``, perp ``{SYM}-PERP``) · quote days =
  UTC days with eligible records · the source wall (any synthetic record →
  constructor refuses unless allow_synthetic, machinery-test only) ·
  read-only (chain verified at load, journal never written) · refused
  surfaces raise NotImplementedError naming the missing data class (funding
  observations and settlement prints are NOT RFQ fields — synthesizing them
  would be an estimator smuggled in through infrastructure).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..models.market_data import (INSTRUMENT_KINDS, Instrument, Price,
                                  PriceSource, RFQQuote)
from ..rfq.journal import RawRFQJournal
from ..rfq.schema import ExternalRFQ

_DAY_MS = 86_400_000


class ReplayError(RuntimeError):
    """Raised on replay-contract violations (wall, tenor convention, exhaustion)."""


def _utc_day(ts: int) -> int:
    return ts // _DAY_MS


def _ref_source(rec: ExternalRFQ) -> PriceSource:
    """M-3: the record's reference provenance — valid enum name, else explicit OTHER."""
    try:
        return PriceSource(rec.reference_source)
    except ValueError:
        return PriceSource.REFERENCE_OTHER


@dataclass
class _QuoteDay:      # internal day index (mutable accumulator, not engine vocabulary)
    day_key: int                      # UTC day number
    last_ts: int                      # M-7: the day's last eligible ts
    spot_buy: Optional[ExternalRFQ]   # latest user-buy spot record (desk ask)
    spot_sell: Optional[ExternalRFQ]  # latest user-sell spot record (desk bid)
    forwards: Dict[int, Dict[str, ExternalRFQ]]  # tenor → {"buy":…, "sell":…}
    perp: Optional[ExternalRFQ]       # latest perp-kind record this day


class JournalReplayFeed:
    """Read-only replay of one W0 journal for ONE instrument family.

    ``symbol`` is the family's spot symbol (e.g. ``"BTC-USD"``); forwards are
    matched as ``{symbol}-FWD-{n}D`` (M-6) and the perp as ``{symbol}-PERP``.
    """

    def __init__(self, journal: RawRFQJournal, symbol: str,
                 *, allow_synthetic: bool = False) -> None:
        summary = journal.verify()          # M-9: full chain walk + re-validation
        sources: Dict[str, int] = summary["sources"]
        if sources.get("synthetic", 0) and not allow_synthetic:
            raise ReplayError(
                f"[M-8] source wall: journal contains {sources['synthetic']} synthetic "
                f"record(s) — research replay refuses. allow_synthetic=True is the "
                "machinery-test mode (px.source=SYNTHETIC_MOCK travels with every quote).")

        if "-" not in symbol:
            raise ReplayError(f"[M-7] family symbol {symbol!r} must be BASE-QUOTE form")
        self.symbol = symbol
        base, quote = symbol.split("-", 1)
        self._base, self._quote = base, quote
        self._journal = journal
        self._summary = summary
        self._allow_synthetic = allow_synthetic

        days: Dict[int, _QuoteDay] = {}
        unusable: List[str] = []
        n_used = 0
        for rec in journal.iter_records():
            family = self._family_of(rec)
            if family is None:
                continue
            if not (rec.status == "quoted" and rec.quote_type == "firm"):
                continue                                            # M-1
            if rec.notional_ccy != rec.price_ccy:
                unusable.append(f"{rec.rfq_id}: notional_ccy={rec.notional_ccy} "
                                f"!= price_ccy={rec.price_ccy} (M-4)")
                continue
            if rec.quoted_price is None or rec.quoted_price <= 0:
                unusable.append(f"{rec.rfq_id}: unusable quoted_price (M-4)")
                continue
            d = days.setdefault(_utc_day(rec.ts),
                                _QuoteDay(day_key=_utc_day(rec.ts), last_ts=rec.ts,
                                          spot_buy=None, spot_sell=None,
                                          forwards={}, perp=None))
            d.last_ts = max(d.last_ts, rec.ts)                       # M-7
            if family == "spot":
                if rec.side == "buy":
                    d.spot_buy = rec          # latest wins (journal order)
                else:
                    d.spot_sell = rec
            elif family == "forward":
                tenor = self._tenor_of(rec)                          # M-6
                slot = d.forwards.setdefault(tenor, {})
                slot["buy" if rec.side == "buy" else "sell"] = rec
            elif family == "perp":
                d.perp = rec
            n_used += 1
        self._days: List[_QuoteDay] = [days[k] for k in sorted(days)]
        self._unusable = unusable
        self._n_used = n_used
        self._idx = -1                   # replay not started (M-7)

    # ------------------------------------------------------------ family helpers

    def _family_of(self, rec: ExternalRFQ) -> Optional[str]:
        if rec.instrument == self.symbol and rec.instrument_kind == "spot":
            return "spot"
        if rec.instrument_kind == "forward" and rec.instrument.startswith(
                f"{self.symbol}-FWD-"):
            return "forward"
        if rec.instrument_kind == "perp" and rec.instrument == f"{self.symbol}-PERP":
            return "perp"
        return None

    def _tenor_of(self, rec: ExternalRFQ) -> int:
        suffix = rec.instrument[len(self.symbol) + len("-FWD-"):]
        if not (suffix.endswith("D") and suffix[:-1].isdigit()):
            raise ReplayError(
                f"[M-6] forward symbol {rec.instrument!r} does not follow the "
                f"sealed {{symbol}}-FWD-{{n}}D convention (record {rec.rfq_id})")
        return int(suffix[:-1])

    def _px_source(self, rec: ExternalRFQ) -> PriceSource:
        return (PriceSource.SYNTHETIC_MOCK if rec.source == "synthetic"
                else PriceSource.DESK_RFQ_QUOTE)

    def _quote_of(self, rec: ExternalRFQ, side: str, kind: str,
                  expiry_ts: Optional[int]) -> RFQQuote:
        px = Price(value=rec.quoted_price, source=self._px_source(rec), ts=rec.ts)
        ref = Price(value=rec.reference_price, source=_ref_source(rec),
                    ts=rec.reference_ts)
        return RFQQuote(
            quote_id=rec.rfq_id,
            instrument=Instrument(symbol=rec.instrument, kind=kind, venue=rec.venue,
                                  base=self._base, quote=self._quote,
                                  expiry_ts=expiry_ts),
            side=side,
            px=px,
            size_quote=rec.requested_notional / rec.quoted_price,   # M-4
            ref_mid=ref,
            ttl_ms=rec.quote_expiry_ts - rec.ts,                    # M-5
        )

    def _require_started(self) -> _QuoteDay:
        if self._idx < 0:
            raise ReplayError("[M-7] replay not started — call advance_day() first")
        return self._days[self._idx]

    # ------------------------------------------------------------ timeline (M-7)

    def advance_day(self) -> None:
        if self._idx + 1 >= len(self._days):
            raise ReplayError(
                f"[M-7] journal replay exhausted: {len(self._days)} quote day(s) "
                "available for this family")
        self._idx += 1

    def day(self) -> int:
        return self._idx + 1

    def now_ms(self) -> int:
        return self._require_started().last_ts

    # ------------------------------------------------------------ quote surfaces

    def spot(self) -> float:
        """Latest eligible spot reference mid (walks back over past days)."""
        for d in reversed(self._days[: self._idx + 1]):
            for rec in (d.spot_buy, d.spot_sell):
                if rec is not None:
                    return rec.reference_price
        raise ReplayError(f"[M-7] no eligible spot record for {self.symbol} yet")

    def spot_quotes(self) -> Tuple[RFQQuote, RFQQuote]:
        d = self._require_started()
        if d.spot_sell is None or d.spot_buy is None:
            missing = "sell(bid)" if d.spot_sell is None else "buy(ask)"
            raise ReplayError(
                f"[M-2] quote day {self.day()} has no {missing} spot record for "
                f"{self.symbol} — the pair cannot be surfaced honestly")
        bid = self._quote_of(d.spot_sell, "bid", "spot", d.spot_sell.quote_expiry_ts)
        ask = self._quote_of(d.spot_buy, "ask", "spot", d.spot_buy.quote_expiry_ts)
        return bid, ask

    def forward_quotes(self, tenor_days: int) -> Tuple[RFQQuote, RFQQuote]:
        d = self._require_started()
        slot = d.forwards.get(tenor_days)
        if not slot or "sell" not in slot or "buy" not in slot:
            raise ReplayError(
                f"[M-6] quote day {self.day()} lacks a full {self.symbol}-FWD-"
                f"{tenor_days}D pair — the pair cannot be surfaced honestly")
        bid = self._quote_of(slot["sell"], "bid", "forward", slot["sell"].quote_expiry_ts)
        ask = self._quote_of(slot["buy"], "ask", "forward", slot["buy"].quote_expiry_ts)
        return bid, ask

    def perp_mark(self) -> Price:
        for d in reversed(self._days[: self._idx + 1]):
            if d.perp is not None:
                rec = d.perp
                return Price(value=rec.reference_price, source=_ref_source(rec),
                             ts=rec.reference_ts)
        raise ReplayError(f"[M-7] no eligible perp record for {self.symbol}-PERP yet")

    # ------------------------------------------------------------ instruments

    def spot_instrument(self) -> Instrument:
        d = self._require_started()
        rec = d.spot_buy or d.spot_sell
        if rec is None:
            raise ReplayError(f"[M-7] no spot record on quote day {self.day()}")
        return Instrument(symbol=self.symbol, kind="spot", venue=rec.venue,
                          base=self._base, quote=self._quote)

    def forward_instrument(self, tenor_days: int) -> Instrument:
        d = self._require_started()
        slot = d.forwards.get(tenor_days)
        if not slot:
            raise ReplayError(f"[M-6] no forward record for {self.symbol}-FWD-"
                              f"{tenor_days}D on quote day {self.day()}")
        rec = slot.get("buy") or slot.get("sell")
        return Instrument(symbol=f"{self.symbol}-FWD-{tenor_days}D", kind="forward",
                          venue=rec.venue, base=self._base, quote=self._quote,
                          expiry_ts=rec.quote_expiry_ts)

    def perp_instrument(self) -> Instrument:
        for d in reversed(self._days[: self._idx + 1]):
            if d.perp is not None:
                return Instrument(symbol=f"{self.symbol}-PERP", kind="perp",
                                  venue=d.perp.venue, base=self._base,
                                  quote=self._quote)
        raise ReplayError(f"[M-7] no eligible perp record for {self.symbol}-PERP yet")

    # ------------------------------------------------------------ refused (M-10)

    @property
    def funding_obs(self):
        raise NotImplementedError(
            "[M-10] CEX funding settlements are not RFQ fields — the 15-field "
            "schema carries quote events only (docs/w1-replay-adapter.md §1). "
            "Synthesizing funding from forwards would be an estimator smuggled "
            "in through infrastructure; the data class belongs to the W1 "
            "research design record.")

    def printed_funding_between(self, ts_from: int, ts_to: int) -> float:
        raise NotImplementedError("[M-10] funding prints are not RFQ fields "
                                  "(docs/w1-replay-adapter.md §1)")

    def realized_funding_apr_between(self, day_from: int, day_to: int) -> float:
        raise NotImplementedError("[M-10] true funding APR is not observable from "
                                  "an RFQ journal (docs/w1-replay-adapter.md §1)")

    def settlement_print(self) -> Price:
        raise NotImplementedError("[M-10] final fixings are market data beyond "
                                  "the 15-field schema (docs/w1-replay-adapter.md §1)")

    def true_apr(self) -> float:
        raise NotImplementedError("[M-10] ground-truth APR does not exist in a "
                                  "replay of quotes (docs/w1-replay-adapter.md §1)")

    # ------------------------------------------------------------ describe

    def describe(self) -> Dict[str, Any]:
        return {
            "kind": "journal-replay-feed",
            "symbol": self.symbol,
            "journal": self._journal.path,
            "chain": {"lines": self._summary["lines"],
                      "head_hash": self._summary["head_hash"]},
            "sources": self._summary["sources"],
            "synthetic_mode": self._allow_synthetic,
            "quote_days": len(self._days),
            "records_used": self._n_used,
            "unusable": list(self._unusable),
        }
