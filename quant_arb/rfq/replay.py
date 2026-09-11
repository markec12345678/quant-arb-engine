"""Replay — verify + descriptive report over the raw RFQ journal (W0 §5).

``python3 scripts/rfq_replay.py``            # verify + full report + status
``python3 scripts/rfq_replay.py --verify-only``

The report is DESCRIPTIVE ACCOUNTING ONLY (see quant_arb/rfq/edge.py):
source-split, never pooled; no uncertainty, no ranking, no GO/NO-GO.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from .edge import describe
from .ingest import DEFAULT_STATUS, REPO_ROOT, write_status
from .journal import RawRFQJournal
from .schema import ExternalRFQ


def load_status(path: str = DEFAULT_STATUS) -> Dict[str, Any] | None:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def replay(journal: RawRFQJournal, status_path: str = DEFAULT_STATUS,
           refresh_status: bool = False) -> Dict[str, Any]:
    """Full replay: chain verify (incl. head-vs-status truncation check),
    re-validate every record, recompute the deterministic all-in edge stats,
    refresh the status artifact, and return the report dict.

    ``refresh_status=True`` skips the head-vs-recorded-head comparison and
    re-records the live head — the documented recovery / first-run path
    (chain integrity is still fully verified internally)."""
    st = load_status(status_path)
    expect_head = None if refresh_status else (st or {}).get("integrity", {}).get("head_hash")
    summary = journal.verify(expect_head=expect_head)
    records: List[ExternalRFQ] = list(journal.iter_records())
    report = describe(records)
    report["journal"] = {
        "path": os.path.relpath(journal.path, REPO_ROOT),
        "lines": summary["lines"],
        "head_hash": summary["head_hash"],
        "first_ts": summary["first_ts"],
        "last_ts": summary["last_ts"],
        "truncation_check": ("re-recorded (refresh-status path)" if refresh_status else
                            ("passed (live head == recorded head)" if st else
                             "no prior status artifact (first run)")),
    }
    write_status(journal, status_path)
    return report


def render_markdown(report: Dict[str, Any]) -> str:
    j = report["journal"]
    c = report["counts"]
    lines = [
        "# W0 — raw RFQ journal replay (descriptive accounting)",
        "",
        f"* journal: `{j['path']}` · {j['lines']} lines · head `{j['head_hash'][:16]}…`",
        f"* truncation check: {j['truncation_check']}",
        f"* counts: total {c['total']} · by source {c['by_source']} · by status {c['by_status']}",
        "",
        "## ALL-IN EDGE (bps of reference; source-split, never pooled)",
        "",
    ]
    for src in ("real", "synthetic"):
        e = report["edges"][src]
        q = e["quantiles_all_in_edge_bps"]
        if e["records"] == 0:
            lines.append(f"* **{src}**: 0 records")
            continue
        lines.append(
            f"* **{src}**: {e['records']} records · {e['n_quoted']} quoted "
            f"({e['n_firm']} firm / {e['n_indicative']} indicative) · "
            f"mean {e['mean_all_in_edge_bps']} bps · "
            f"p50 {q.get('p50')} · p05 {q.get('p05')} · p95 {q.get('p95')} · "
            f"n>0 {e['n_positive_all_in_edge']}")
        for inst, m in e["mean_by_instrument_bps"].items():
            lines.append(f"    - {inst}: mean {m} bps")
    dq = report["data_quality"]
    lines += [
        "",
        "## Data quality",
        "",
        f"* reference age (ms): {dq['reference_age_ms_quantiles']}",
        f"* latency (ms): {dq['latency_ms_quantiles']}",
        "",
        f"> {report['epistemic_note']}",
        "",
    ]
    return "\n".join(lines)
