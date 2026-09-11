"""W1-INFRA: the RFQ journal coverage report (v0.6.3, sealed docs/w1-coverage-report.md).

A census of what a W0 raw journal actually contains, per instrument family:
eligibility breakdown (the honest cost of collection friction), day coverage,
tenor census, unclassified buckets. Measurement, not research — this module
produces **no research number**; its output exists so the future W1 research
design record can cite reproducible inclusion criteria instead of ad-hoc
queries.

Census = sealed rules C-1…C-9 of the design record:
  family detection (spot root / strip -FWD-{n}D / strip -PERP, BASE-QUOTE
  form) · report-don't-refuse for symbol conventions (the mirror image of the
  replay adapter's M-6 refusal — a census must not crash on what it counts) ·
  eligibility = M-1 counted per status/quote_type · unusable = M-4 named ·
  quote day = M-7's UTC day · pair completeness = M-2's both-sides rule ·
  the source wall (synthetic journals refused without allow_synthetic, same
  gate as M-8) · read-only (chain verified at load, journal byte-identical
  after, nothing written) · deterministic, family-optional.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..rfq.journal import RawRFQJournal
from ..rfq.schema import ExternalRFQ

_DAY_MS = 86_400_000


class CoverageError(RuntimeError):
    """Raised on census-contract violations (source wall, chain, family arg)."""


def _utc_day(ts: int) -> int:
    return ts // _DAY_MS


def _iso_day(day_key: int) -> str:
    return datetime.fromtimestamp(day_key * _DAY_MS // 1000,
                                   tz=timezone.utc).strftime("%Y-%m-%d")


def _root_of(rec: ExternalRFQ) -> Optional[str]:
    """C-1: family root of a record, or None when unclassifiable."""
    if rec.instrument_kind == "spot":
        root = rec.instrument
    elif rec.instrument_kind == "forward":
        if "-FWD-" not in rec.instrument:
            return None                                   # C-2: bad symbol
        root = rec.instrument.split("-FWD-", 1)[0]
        suffix = rec.instrument[len(root) + len("-FWD-"):]
        if not (suffix.endswith("D") and suffix[:-1].isdigit()):
            return None                                   # C-2: bad tenor convention
    elif rec.instrument_kind == "perp":
        if not rec.instrument.endswith("-PERP"):
            return None                                   # C-2: bad symbol
        root = rec.instrument[: -len("-PERP")]
    else:
        return "OTHER-KIND"      # C-2: cfd/option/… → other_kinds bucket
    if "-" not in root:                                    # C-1: BASE-QUOTE form
        return None
    return root


def _tenor_of(rec: ExternalRFQ) -> Optional[int]:
    """C-1 helper: forward tenor in days, None when the convention is broken."""
    root = rec.instrument.split("-FWD-", 1)[0]
    suffix = rec.instrument[len(root) + len("-FWD-"):]
    if suffix.endswith("D") and suffix[:-1].isdigit():
        return int(suffix[:-1])
    return None


class _FamilyCensus:      # internal accumulator (not engine vocabulary)
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.total = 0
        self.eligible = 0
        self.ineligible_status: Dict[str, int] = {}
        self.ineligible_indicative = 0
        self.unusable: List[str] = []
        self.days: Dict[int, Dict[str, Any]] = {}   # day_key → surfaces
        self.venues: set = set()

    def _day(self, day_key: int) -> Dict[str, Any]:
        return self.days.setdefault(day_key, {
            "spot_sides": set(), "forward": {},      # tenor → set of sides
            "perp": False,
        })

    def add(self, rec: ExternalRFQ) -> None:
        self.total += 1
        self.venues.add(rec.venue)
        if not (rec.status == "quoted" and rec.quote_type == "firm"):
            if rec.status != "quoted":
                self.ineligible_status[rec.status] = (
                    self.ineligible_status.get(rec.status, 0) + 1)   # C-3
            else:
                self.ineligible_indicative += 1                      # C-3
            return
        if rec.notional_ccy != rec.price_ccy:
            self.unusable.append(f"{rec.rfq_id}: notional_ccy={rec.notional_ccy} "
                                 f"!= price_ccy={rec.price_ccy} (M-4)")
            return
        if rec.quoted_price is None or rec.quoted_price <= 0:
            self.unusable.append(f"{rec.rfq_id}: unusable quoted_price (M-4)")
            return
        self.eligible += 1
        d = self._day(_utc_day(rec.ts))
        side = "buy" if rec.side == "buy" else "sell"
        if rec.instrument_kind == "spot":
            d["spot_sides"].add(side)
        elif rec.instrument_kind == "forward":
            tenor = _tenor_of(rec)
            if tenor is not None:
                d["forward"].setdefault(tenor, set()).add(side)
        elif rec.instrument_kind == "perp":
            d["perp"] = True

    def report(self) -> Dict[str, Any]:
        keys = sorted(self.days)
        spot_days = [k for k in keys if self.days[k]["spot_sides"]]
        full_pair = [k for k in spot_days
                     if self.days[k]["spot_sides"] == {"buy", "sell"}]
        partial = [i + 1 for i, k in enumerate(spot_days)
                   if self.days[k]["spot_sides"] != {"buy", "sell"}]
        tenors: Dict[str, Dict[str, int]] = {}
        for k in keys:
            for tenor, sides in self.days[k]["forward"].items():
                t = tenors.setdefault(str(tenor), {"records": 0, "full_pair_days": 0})
                t["records"] += len(sides)
                if sides == {"buy", "sell"}:
                    t["full_pair_days"] += 1
        return {
            "symbol": self.symbol,
            "total_records": self.total,
            "eligible": self.eligible,
            "ineligible": {"by_status": dict(sorted(self.ineligible_status.items())),
                           "indicative": self.ineligible_indicative},
            "unusable": list(self.unusable),
            "quote_days": len(keys),
            "first_day": _iso_day(keys[0]) if keys else None,
            "last_day": _iso_day(keys[-1]) if keys else None,
            "spot_days": len(spot_days),
            "spot_full_pair_days": len(full_pair),
            "partial_spot_days": partial,
            "tenors": dict(sorted(tenors.items(), key=lambda kv: int(kv[0]))),
            "perp_days": sum(1 for k in keys if self.days[k]["perp"]),
            "venues": sorted(self.venues),
        }


def journal_coverage(journal: RawRFQJournal, family: Optional[str] = None, *,
                     allow_synthetic: bool = False) -> Dict[str, Any]:
    """C-1…C-9 census of one W0 journal. Read-only; refuses synthetic data."""
    summary = journal.verify()          # C-8: full chain walk first
    sources: Dict[str, int] = summary["sources"]
    if sources.get("synthetic", 0) and not allow_synthetic:
        raise CoverageError(
            f"[C-7] source wall: journal contains {sources['synthetic']} synthetic "
            f"record(s) — coverage refuses (the census feeds W1 inclusion "
            "criteria; it must describe real data only). allow_synthetic=True is "
            "the machinery-test mode.")

    if family is not None and "-" not in family:
        raise CoverageError(f"[C-1] family symbol {family!r} must be BASE-QUOTE form")

    families: Dict[str, _FamilyCensus] = {}
    bad_symbols: List[str] = []
    other_kinds: List[str] = []
    for rec in journal.iter_records():
        root = _root_of(rec)
        if root == "OTHER-KIND":
            other_kinds.append(f"{rec.rfq_id}: instrument_kind={rec.instrument_kind}")
            continue
        if root is None:
            bad_symbols.append(
                f"{rec.rfq_id}: instrument={rec.instrument!r} "
                f"(kind={rec.instrument_kind}) violates the family convention")
            continue
        if family is not None and root != family:
            continue
        families.setdefault(root, _FamilyCensus(root)).add(rec)

    return {
        "kind": "rfq-journal-coverage",
        "journal": journal.path,
        "chain": {"lines": summary["lines"], "head_hash": summary["head_hash"]},
        "sources": sources,
        "synthetic_mode": allow_synthetic,
        "families": [families[k].report() for k in sorted(families)],
        "unclassified": {"bad_symbols": bad_symbols, "other_kinds": other_kinds},
    }


def render_report(cov: Dict[str, Any]) -> str:
    """C-9: the human rendering (deterministic; plain text)."""
    out: List[str] = []
    out.append(f"RFQ journal coverage — {cov['journal']}")
    out.append(f"  chain: {cov['chain']['lines']} line(s), "
               f"head {cov['chain']['head_hash'][:16]}…")
    out.append(f"  sources: {cov['sources']}"
               + ("  [MACHINERY-TEST MODE — synthetic allowed]" if cov["synthetic_mode"] else ""))
    fams = cov["families"]
    out.append(f"  families: {len(fams)}")
    for f in fams:
        out.append(f"  • {f['symbol']}: {f['total_records']} record(s), "
                   f"{f['eligible']} eligible, "
                   f"{f['total_records'] - f['eligible'] - len(f['unusable'])} "
                   f"ineligible, {len(f['unusable'])} unusable")
        ine = f["ineligible"]
        parts = [f"{v} {k}" for k, v in ine["by_status"].items()]
        if ine["indicative"]:
            parts.append(f"{ine['indicative']} indicative")
        if parts:
            out.append(f"      ineligible: {', '.join(parts)}")
        for u in f["unusable"]:
            out.append(f"      unusable: {u}")
        out.append(f"      quote days: {f['quote_days']}"
                   + (f" ({f['first_day']} … {f['last_day']})" if f["quote_days"] else ""))
        out.append(f"      spot: {f['spot_days']} day(s), "
                   f"{f['spot_full_pair_days']} full pair(s)"
                   + (f", partial day(s) {f['partial_spot_days']}"
                      if f["partial_spot_days"] else ""))
        if f["tenors"]:
            t = ", ".join(f"{k}D: {v['records']} rec, {v['full_pair_days']} full pair(s)"
                          for k, v in f["tenors"].items())
            out.append(f"      forwards: {t}")
        if f["perp_days"]:
            out.append(f"      perp days: {f['perp_days']}")
        out.append(f"      venues: {', '.join(f['venues'])}")
    un = cov["unclassified"]
    if un["bad_symbols"] or un["other_kinds"]:
        out.append(f"  unclassified: {len(un['bad_symbols'])} bad symbol(s), "
                   f"{len(un['other_kinds'])} other kind(s)")
        for b in un["bad_symbols"] + un["other_kinds"]:
            out.append(f"      {b}")
    if not fams and not un["bad_symbols"] and not un["other_kinds"]:
        out.append("  (no classifiable records — an honest empty census)")
    out.append("  census only — no research number (docs/w1-coverage-report.md §4)")
    return "\n".join(out)
