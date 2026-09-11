"""Ingestion orchestration + status artifact (W0 §2/§3/§5).

provider → normalize → schema-validate → immutable journal append → refresh
``research/artifacts/rfq-status.json`` (the derived summary the tower reads
read-only, same contract as run-latest/sweep-latest).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from .journal import RawRFQJournal
from .providers.base import FieldMap
from .schema import ExternalRFQ, RFQSchemaError

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_JOURNAL = os.path.join(REPO_ROOT, "research", "artifacts", "rfq",
                               "journal.jsonl")
DEFAULT_STATUS = os.path.join(REPO_ROOT, "research", "artifacts", "rfq-status.json")


def load_field_map(path: Optional[str]) -> FieldMap:
    if path is None:
        return FieldMap()
    with open(path, "r", encoding="utf-8") as f:
        return FieldMap.from_dict(json.load(f))


def ingest(provider, journal: RawRFQJournal, field_map: FieldMap,
           stop_on_error: bool = True) -> Dict[str, Any]:
    """Ingest every provider record into the journal; return a run summary.

    Fail-closed by default: the first invalid payload — a normalization
    error (missing mapped field, unparseable value) OR a journal-append
    violation (schema, duplicate rfq_id) — aborts the run with nothing
    further written (records before it stay journaled — the journal is
    append-only; the error names the offending record and its index). With
    ``stop_on_error=False`` (explicit opt-in) invalid payloads are counted
    and skipped — useful for messy first-contact desk exports; every skip
    is reported, never silent. Per-record isolation is provided by the
    provider's ``safe_records`` walk: one malformed row never aborts the
    report (v0.6.1 fix — previously a normalization error escaped the
    generator and crashed even keep-going runs).
    """
    n_ok = 0
    n_skip = 0
    errors: list = []
    for i, rec, err in provider.safe_records(field_map):
        if err is not None:
            if stop_on_error:
                raise err
            n_skip += 1
            errors.append({"index": i, "error": str(err)})
            continue
        assert rec is not None
        try:
            journal.append(rec)
            n_ok += 1
        except RFQSchemaError as e:
            if stop_on_error:
                raise
            n_skip += 1
            errors.append({"index": i, "error": str(e)})
    return {"provider": provider.describe(), "appended": n_ok, "skipped": n_skip,
            "skip_errors": errors}


def dry_run(provider, journal: RawRFQJournal, field_map: FieldMap,
            preview: int = 5) -> Dict[str, Any]:
    """Validate a provider's records WITHOUT writing anything.

    First-contact tool: reports exactly what ``ingest`` WOULD do — per-record
    schema validation (every violation reported, none silent), duplicate
    rfq_id detection against the journal's existing ids (read-only scan) AND
    within the batch, a would-be sources census, and a preview of the first
    valid records. Disk state is untouched: no journal line, no lock file,
    no status refresh (it is a preview, not an operation).
    """
    existing_ids: set = set()
    unparseable = 0
    if os.path.exists(journal.path):
        with open(journal.path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    rec = json.loads(s)
                except json.JSONDecodeError:
                    unparseable += 1
                    continue
                rid = (rec.get("rfq") or {}).get("rfq_id")
                if rid is not None:
                    existing_ids.add(rid)
    seen = set(existing_ids)
    n_ok = n_skip = 0
    sources: Dict[str, int] = {}
    errors: list = []
    preview_rows: list = []
    for i, rec, err in provider.safe_records(field_map):
        if err is not None:
            n_skip += 1
            errors.append({"index": i, "error": str(err)})
            continue
        assert rec is not None
        try:
            # defence in depth: re-validate on the read path, same as verify()
            ExternalRFQ.from_payload(rec.to_payload())
            if rec.rfq_id in seen:
                origin = ("already journaled" if rec.rfq_id in existing_ids
                          else "within this batch")
                raise RFQSchemaError(
                    f"[R-1] duplicate rfq_id {rec.rfq_id!r} — {origin}")
            seen.add(rec.rfq_id)
        except RFQSchemaError as e:
            n_skip += 1
            errors.append({"index": i, "error": str(e)})
            continue
        n_ok += 1
        sources[rec.source] = sources.get(rec.source, 0) + 1
        if len(preview_rows) < preview:
            preview_rows.append({
                "rfq_id": rec.rfq_id, "instrument": rec.instrument,
                "venue": rec.venue, "side": rec.side, "status": rec.status,
                "source": rec.source, "ts": rec.ts})
    return {
        "provider": provider.describe(),
        "journal_path": journal.path,
        "journal_exists": os.path.exists(journal.path),
        "journal_records": len(existing_ids),
        "journal_unparseable_lines": unparseable,
        "would_append": n_ok,
        "would_skip": n_skip,
        "would_be_sources": sources,
        "skip_errors": errors,
        "preview": preview_rows,
        "wrote_nothing": True,
    }


def write_status(journal: RawRFQJournal, status_path: str = DEFAULT_STATUS,
                 extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Verify the journal and write the derived status artifact.

    The status artifact records the chain HEAD hash — this is what bounds
    tail truncation (W0 §2 honest limitation): the next verify() compares
    the live head against it.
    """
    summary = journal.verify()
    tail = journal.tail(5)
    instruments, venues = set(), set()
    last_ts = None
    for rec in journal.iter_records():
        instruments.add(rec.instrument)
        venues.add(rec.venue)
        last_ts = rec.ts if last_ts is None else max(last_ts, rec.ts)
    status: Dict[str, Any] = {
        "artifact": "rfq-status",
        "w0_version": 1,
        "journal_path": os.path.relpath(journal.path, REPO_ROOT),
        "integrity": {
            "ok": True,
            "lines": summary["lines"],
            "head_hash": summary["head_hash"],
            "sources": summary["sources"],
        },
        "census": {
            "instruments": sorted(instruments),
            "venues": sorted(venues),
            "last_quote_ts": last_ts,
        },
        "tail": [{"seq": t.get("seq"), "rfq_id": (t.get("rfq") or {}).get("rfq_id"),
                  "source": t.get("source"),
                  "ts": (t.get("rfq") or {}).get("ts")} for t in tail],
        "note": ("Raw RFQ journal (immutable, hash-chained). Synthetic records "
                 "are test-only and never research-eligible. Descriptive "
                 "accounting only — no research conclusions until a W1 "
                 "decision record is sealed."),
    }
    if extra:
        status["last_operation"] = extra
    os.makedirs(os.path.dirname(status_path) or ".", exist_ok=True)
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, sort_keys=True)
        f.write("\n")
    return status
