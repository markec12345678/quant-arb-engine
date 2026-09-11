"""Deterministic ALL-IN EDGE accounting over journaled RFQ records (W0 §4).

This is ACCOUNTING, not estimation (the user's own framing: W0 is not a new
estimator). Per record, in bps of the reference price:

    price_edge_bps  = side_sign * (reference - quoted) / reference * 1e4
                      (buy below reference = positive; sell above = positive)
    fee_cost_bps    = fees_pct * 100  — charged ONLY when
                      fees_included_in_price is false (I-4 descendant:
                      counted exactly once, never silently twice)
    all_in_edge_bps = price_edge_bps - fee_cost_bps

Descriptive statistics only. NO uncertainty term, NO ranking, NO GO/NO-GO —
those are W1 research and require a sealed decision record first. The source
wall applies: research-eligible statistics are computed over source="real"
records only; synthetic records are reported separately, never pooled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .schema import EPISTEMIC_NOTE, ExternalRFQ


@dataclass(frozen=True)
class RFQEdge:
    """All-in edge of one journaled RFQ record (deterministic arithmetic)."""

    rfq_id: str
    instrument: str
    venue: str
    side: str
    quote_type: Optional[str]
    status: str
    source: str

    price_edge_bps: Optional[float]     # None when not quoted
    fee_cost_bps: Optional[float]
    all_in_edge_bps: Optional[float]

    @staticmethod
    def of(rec: ExternalRFQ) -> "RFQEdge":
        if rec.status != "quoted" or rec.quoted_price is None:
            return RFQEdge(rfq_id=rec.rfq_id, instrument=rec.instrument,
                           venue=rec.venue, side=rec.side,
                           quote_type=rec.quote_type, status=rec.status,
                           source=rec.source,
                           price_edge_bps=None, fee_cost_bps=None,
                           all_in_edge_bps=None)
        side_sign = 1.0 if rec.side == "buy" else -1.0
        price_edge_bps = (side_sign * (rec.reference_price - rec.quoted_price)
                          / rec.reference_price * 1e4)
        # I-4 descendant: charge fees exactly once — only when NOT embedded
        fee_cost_bps = 0.0 if (rec.fees_included_in_price or False) else rec.fees_pct * 100.0
        return RFQEdge(
            rfq_id=rec.rfq_id, instrument=rec.instrument, venue=rec.venue,
            side=rec.side, quote_type=rec.quote_type, status=rec.status,
            source=rec.source,
            price_edge_bps=round(price_edge_bps, 6),
            fee_cost_bps=round(fee_cost_bps, 6),
            all_in_edge_bps=round(price_edge_bps - fee_cost_bps, 6),
        )


def _quantiles(xs: List[float]) -> Dict[str, float]:
    if not xs:
        return {}
    s = sorted(xs)

    def q(p: float) -> float:
        idx = p * (len(s) - 1)
        lo = int(idx)
        hi = min(lo + 1, len(s) - 1)
        frac = idx - lo
        return round(s[lo] * (1 - frac) + s[hi] * frac, 4)

    return {"p05": q(0.05), "p25": q(0.25), "p50": q(0.50),
            "p75": q(0.75), "p95": q(0.95)}


def describe(records: List[ExternalRFQ]) -> Dict:
    """Descriptive report over journaled records — source-split, never pooled.

    Structure:
      integrity-free (the journal verifies itself); this is pure accounting.
      counts: by source, by status, by quote_type, by venue
      edges: {real: {...}, synthetic: {...}} — each with n_quoted, mean,
             quantiles, n_positive; per-instrument and per-venue mean tables
      staleness: reference-age ms quantiles + latency ms quantiles
      epistemic note: verbatim
    """
    by_source: Dict[str, List[ExternalRFQ]] = {"real": [], "synthetic": []}
    for r in records:
        by_source.setdefault(r.source, []).append(r)

    def edge_block(recs: List[ExternalRFQ]) -> Dict:
        edges = [RFQEdge.of(r) for r in recs]
        quoted = [e for e in edges if e.all_in_edge_bps is not None]
        xs = [e.all_in_edge_bps for e in quoted]  # type: ignore[misc]
        by_inst: Dict[str, List[float]] = {}
        by_venue: Dict[str, List[float]] = {}
        firm = [e for e in quoted if e.quote_type == "firm"]
        for e in quoted:
            by_inst.setdefault(e.instrument, []).append(e.all_in_edge_bps)  # type: ignore[misc]
            by_venue.setdefault(e.venue, []).append(e.all_in_edge_bps)      # type: ignore[misc]
        return {
            "records": len(recs),
            "n_quoted": len(quoted),
            "n_firm": len(firm),
            "n_indicative": len(quoted) - len(firm),
            "mean_all_in_edge_bps": (round(sum(xs) / len(xs), 4) if xs else None),
            "quantiles_all_in_edge_bps": _quantiles(xs),
            "n_positive_all_in_edge": sum(1 for x in xs if x > 0),
            "mean_by_instrument_bps": {k: round(sum(v) / len(v), 4)
                                       for k, v in sorted(by_inst.items())},
            "mean_by_venue_bps": {k: round(sum(v) / len(v), 4)
                                  for k, v in sorted(by_venue.items())},
        }

    ages = [r.reference_age_ms for r in records]
    lat = [r.latency_ms for r in records]
    statuses: Dict[str, int] = {}
    for r in records:
        statuses[r.status] = statuses.get(r.status, 0) + 1

    return {
        "epistemic_note": EPISTEMIC_NOTE,
        "counts": {
            "total": len(records),
            "by_source": {k: len(v) for k, v in by_source.items()},
            "by_status": dict(sorted(statuses.items())),
        },
        "edges": {
            "real": edge_block(by_source["real"]),
            "synthetic": edge_block(by_source["synthetic"]),
            "pooled": None,  # deliberately absent: the source wall forbids pooling
        },
        "data_quality": {
            "reference_age_ms_quantiles": _quantiles([float(a) for a in ages]),
            "latency_ms_quantiles": _quantiles([float(x) for x in lat]),
        },
    }
