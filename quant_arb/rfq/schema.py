"""External RFQ records — the W0 real-world schema (user-specified, 15 fields).

W0 design record: docs/w0-rfq-ingestion.md (sealed 2026-09-11 before code).

Every field the user listed is required and validated at write time;
validation is fail-closed (`RFQSchemaError` → nothing reaches the journal).
Two W0-critical additions:

* ``source`` — the epistemic wall: "real" | "synthetic". Synthetic records
  are marked at birth and are structurally excluded from research
  aggregation paths (``is_research_eligible``); the separation is enforced
  in code, not by convention.
* ``raw`` — the provider payload verbatim; normalization may add fields but
  must never lose what the desk actually sent (the audit's lesson about
  silently-transformed provenance).

Invariant descendants from the engine canon: R-10 (reference price is never
a naked number — carries a source tag, I-1) and R-11 (market data cannot be
from the future — reference_ts <= ts, NEW-16).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

SCHEMA_VERSION = 1

SOURCES = ("real", "synthetic")
SIDES = ("buy", "sell")
QUOTE_TYPES = ("firm", "indicative")
STATUSES = ("quoted", "rejected", "expired", "no_response")
INSTRUMENT_KINDS = ("spot", "perp", "forward", "cfd", "option")

# Reference-price provenance tags (I-1 discipline; extensible, lowercase).
REFERENCE_SOURCES = (
    "spot_book_mid", "spot_book_last", "perp_mark", "perp_index", "perp_last",
    "composite_index", "desk_reference", "settlement_print", "other_reported",
)

EPISTEMIC_NOTE = (
    "Descriptive accounting over journaled RFQ records only — no research "
    "conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data."
)


class RFQSchemaError(RuntimeError):
    """Raised when an external RFQ record would violate a schema invariant."""


def _req(cond: bool, inv: str, msg: str) -> None:
    if not cond:
        raise RFQSchemaError(f"[{inv}] {msg}")


def _is_pos_num(x: Any) -> bool:
    return (isinstance(x, (int, float)) and not isinstance(x, bool)
            and math.isfinite(float(x)) and float(x) > 0)


@dataclass(frozen=True)
class ExternalRFQ:
    """A normalized external RFQ record. See module docstring for the schema."""

    # --- the user's 15 required fields -----------------------------------
    rfq_id: str                                   # R-1 unique
    instrument: str                               # R-2 symbol
    venue: str                                    # R-2 quoting venue/provider
    ts: int                                       # R-3 quote timestamp, unix ms
    side: str                                     # R-4 the side WE requested
    requested_notional: float                     # R-4 > 0
    quoted_price: Optional[float]                 # R-5 required iff status == quoted
    quote_type: Optional[str]                     # R-6 firm | indicative, iff quoted
    quote_expiry_ts: Optional[int]                # R-7 >= ts, iff quoted
    fees_pct: float                               # R-8 as reported, % of notional
    fees_included_in_price: Optional[bool]        # R-8 never ambiguous, iff quoted
    spread_bps: Optional[float]                   # R-9 full quoted bid-ask, iff quoted
    reference_price: float                        # R-10 > 0, with provenance
    reference_ts: int                             # R-11 <= ts (no future data)
    latency_ms: float                             # R-12 >= 0
    status: str                                   # R-13 quoted|rejected|expired|no_response

    # --- W0 additions ------------------------------------------------------
    source: str                                   # real | synthetic (the epistemic wall)
    instrument_kind: str = "spot"
    notional_ccy: str = "USD"
    price_ccy: str = "USD"
    reference_source: str = "other_reported"      # R-10 provenance tag
    reject_reason: Optional[str] = None           # context when status != quoted
    raw: Dict[str, Any] = field(default_factory=dict)   # verbatim provider payload

    # ------------------------------------------------------------------ invariants

    def __post_init__(self) -> None:
        _req(isinstance(self.rfq_id, str) and len(self.rfq_id.strip()) > 0,
             "R-1", "rfq_id must be a non-empty string")
        _req(isinstance(self.instrument, str) and len(self.instrument.strip()) > 0,
             "R-2", "instrument must be a non-empty string")
        _req(isinstance(self.venue, str) and len(self.venue.strip()) > 0,
             "R-2", "venue must be a non-empty string")
        _req(self.instrument_kind in INSTRUMENT_KINDS,
             "R-2", f"instrument_kind must be one of {INSTRUMENT_KINDS}")
        _req(isinstance(self.ts, int) and self.ts > 0,
             "R-3", "ts must be a positive unix-ms int")
        _req(self.side in SIDES, "R-4", f"side must be one of {SIDES}")
        _req(_is_pos_num(self.requested_notional),
             "R-4", "requested_notional must be a positive number")
        _req(isinstance(self.notional_ccy, str) and len(self.notional_ccy.strip()) > 0,
             "R-4", "notional_ccy must be non-empty")
        _req(self.status in STATUSES, "R-13", f"status must be one of {STATUSES}")

        quoted = self.status == "quoted"
        if quoted:
            _req(_is_pos_num(self.quoted_price),
                 "R-5", "quoted_price is required and positive when status == quoted")
            _req(self.quote_type in QUOTE_TYPES,
                 "R-6", "quote_type (firm|indicative) is required when status == quoted")
            _req(isinstance(self.quote_expiry_ts, int) and self.quote_expiry_ts >= self.ts,
                 "R-7", "quote_expiry_ts >= ts is required when status == quoted")
            _req(isinstance(self.fees_included_in_price, bool),
                 "R-8", "fees_included_in_price must be explicit (bool) when status == quoted")
        else:
            _req(self.quoted_price is None and self.quote_type is None
                 and self.quote_expiry_ts is None and self.fees_included_in_price is None,
                 "R-5/6/7/8", "quote-only fields must be null when status != quoted")

        _req(isinstance(self.fees_pct, (int, float)) and not isinstance(self.fees_pct, bool)
             and math.isfinite(float(self.fees_pct)) and float(self.fees_pct) >= 0,
             "R-8", "fees_pct must be a finite number >= 0")
        if self.spread_bps is not None:
            _req(quoted, "R-9", "spread_bps may only be reported when status == quoted")
            _req(math.isfinite(float(self.spread_bps)) and float(self.spread_bps) >= 0,
                 "R-9", "spread_bps must be finite >= 0")
        _req(_is_pos_num(self.reference_price),
             "R-10", "reference_price must be a positive number")
        _req(self.reference_source in REFERENCE_SOURCES,
             "R-10", f"reference_source must be one of {REFERENCE_SOURCES}")
        _req(isinstance(self.reference_ts, int) and self.reference_ts > 0,
             "R-11", "reference_ts must be a positive unix-ms int")
        _req(self.reference_ts <= self.ts,
             "R-11", "market data cannot be from the future: reference_ts <= ts")
        _req(isinstance(self.latency_ms, (int, float)) and not isinstance(self.latency_ms, bool)
             and math.isfinite(float(self.latency_ms)) and float(self.latency_ms) >= 0,
             "R-12", "latency_ms must be finite >= 0")
        _req(self.source in SOURCES, "W0", f"source must be one of {SOURCES}")
        _req(isinstance(self.raw, dict), "W0", "raw must be the verbatim provider payload (object)")

    # ------------------------------------------------------------------ views

    @property
    def is_research_eligible(self) -> bool:
        """The epistemic wall: research aggregates accept real records only."""
        return self.source == "real"

    @property
    def reference_age_ms(self) -> int:
        """How stale the reference market data was at quote time (>= 0)."""
        return self.ts - self.reference_ts

    def to_payload(self) -> Dict[str, Any]:
        """Canonical journal payload (round-trip exact at this precision)."""
        return {
            "schema_version": SCHEMA_VERSION,
            "rfq_id": self.rfq_id,
            "instrument": self.instrument,
            "instrument_kind": self.instrument_kind,
            "venue": self.venue,
            "ts": int(self.ts),
            "side": self.side,
            "requested_notional": float(self.requested_notional),
            "notional_ccy": self.notional_ccy,
            "quoted_price": (None if self.quoted_price is None
                             else round(float(self.quoted_price), 10)),
            "quote_type": self.quote_type,
            "quote_expiry_ts": self.quote_expiry_ts,
            "fees_pct": round(float(self.fees_pct), 10),
            "fees_included_in_price": self.fees_included_in_price,
            "spread_bps": (None if self.spread_bps is None
                           else round(float(self.spread_bps), 6)),
            "reference_price": round(float(self.reference_price), 10),
            "price_ccy": self.price_ccy,
            "reference_source": self.reference_source,
            "reference_ts": int(self.reference_ts),
            "latency_ms": round(float(self.latency_ms), 3),
            "status": self.status,
            "reject_reason": self.reject_reason,
            "source": self.source,
            "raw": self.raw,
        }

    @staticmethod
    def from_payload(d: Dict[str, Any]) -> "ExternalRFQ":
        return ExternalRFQ(
            rfq_id=d["rfq_id"],
            instrument=d["instrument"],
            venue=d["venue"],
            ts=int(d["ts"]),
            side=d["side"],
            requested_notional=float(d["requested_notional"]),
            quoted_price=(None if d.get("quoted_price") is None
                          else float(d["quoted_price"])),
            quote_type=d.get("quote_type"),
            quote_expiry_ts=(None if d.get("quote_expiry_ts") is None
                             else int(d["quote_expiry_ts"])),
            fees_pct=float(d["fees_pct"]),
            fees_included_in_price=d.get("fees_included_in_price"),
            spread_bps=(None if d.get("spread_bps") is None
                        else float(d["spread_bps"])),
            reference_price=float(d["reference_price"]),
            reference_ts=int(d["reference_ts"]),
            latency_ms=float(d["latency_ms"]),
            status=d["status"],
            source=d["source"],
            instrument_kind=d.get("instrument_kind", "spot"),
            notional_ccy=d.get("notional_ccy", "USD"),
            price_ccy=d.get("price_ccy", "USD"),
            reference_source=d.get("reference_source", "other_reported"),
            reject_reason=d.get("reject_reason"),
            raw=d.get("raw", {}),
        )
