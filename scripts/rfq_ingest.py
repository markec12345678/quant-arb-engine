"""W0: raw RFQ ingestion — the real-world data layer (paper/research only).

Providers:
  --provider file      REAL: desk export / user-held RFQ history (JSONL, JSON array, CSV)
                       requires --path and (usually) --field-map
  --provider synthetic TEST ONLY (source="synthetic", never research-eligible):
                       deterministic pipeline exerciser; requires --n

Journal (immutable, hash-chained):
  --journal PATH       default: research/artifacts/rfq/journal.jsonl (gitignored —
                       raw desk data may be proprietary)
  --smoke-journal      use the tracked synthetic smoke journal instead:
                       research/artifacts/rfq/journal-synthetic-smoke.jsonl

Every run refreshes research/artifacts/rfq-status.json (the tower reads it
read-only). Fail-closed on schema violations by default; --keep-going counts
and reports skips instead (for messy first-contact exports).

--dry-run validates + previews WITHOUT writing anything (no journal line,
no lock, no status refresh) — the first-contact tool for an unknown export
format; exit code 1 if any record would be skipped.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from quant_arb.rfq.ingest import (DEFAULT_JOURNAL, DEFAULT_STATUS, REPO_ROOT,
                                  dry_run, ingest, load_field_map,
                                  write_status)
from quant_arb.rfq.journal import RawRFQJournal
from quant_arb.rfq.providers.file_ingest import FileRFQProvider
from quant_arb.rfq.providers.synthetic import SyntheticRFQProvider
from quant_arb.rfq.schema import RFQSchemaError

SMOKE_JOURNAL = os.path.join(REPO_ROOT, "research", "artifacts", "rfq",
                             "journal-synthetic-smoke.jsonl")
EXAMPLE_MAP = os.path.join(REPO_ROOT, "quant_arb", "rfq", "providers",
                           "example_field_map.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", required=True, choices=["file", "synthetic"])
    ap.add_argument("--path", help="file provider: path to the export")
    ap.add_argument("--field-map", help=f"file provider: JSON field map (example: {EXAMPLE_MAP})")
    ap.add_argument("--n", type=int, default=200, help="synthetic provider: record count")
    ap.add_argument("--seed", type=int, default=7, help="synthetic provider: RNG seed")
    ap.add_argument("--journal", default=DEFAULT_JOURNAL)
    ap.add_argument("--smoke-journal", action="store_true",
                    help="target the tracked synthetic smoke journal")
    ap.add_argument("--keep-going", action="store_true",
                    help="count+report invalid payloads instead of aborting")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate + preview WITHOUT writing anything "
                         "(no journal line, no lock, no status refresh); "
                         "exit 1 if any record would be skipped")
    args = ap.parse_args()

    journal_path = SMOKE_JOURNAL if args.smoke_journal else args.journal

    if args.provider == "file":
        if not args.path:
            print("[rfq-ingest] --path is required for --provider file", file=sys.stderr)
            return 2
        provider = FileRFQProvider(args.path)
    else:
        provider = SyntheticRFQProvider(n=args.n, seed=args.seed)
        if not args.smoke_journal and args.journal == DEFAULT_JOURNAL:
            print("[rfq-ingest] refusing to write synthetic records into the REAL journal "
                  "(source wall). Pass --smoke-journal or an explicit --journal.",
                  file=sys.stderr)
            return 2

    field_map = load_field_map(args.field_map)
    if args.dry_run:
        # create_parent=False: a preview must not even create directories
        journal = RawRFQJournal(journal_path, create_parent=False)
        print(f"[rfq-ingest] DRY-RUN provider={provider.describe()} "
              f"journal={journal_path}")
        report = dry_run(provider, journal, field_map)
        print(f"[rfq-ingest] would-append={report['would_append']} "
              f"would-skip={report['would_skip']} "
              f"would-be-sources={report['would_be_sources']}")
        print(f"[rfq-ingest] journal state: exists={report['journal_exists']} "
              f"records={report['journal_records']} "
              f"unparseable={report['journal_unparseable_lines']}")
        for row in report["preview"]:
            print(f"  preview: {row['rfq_id']} {row['instrument']} @ {row['venue']} "
                  f"{row['side']} {row['status']} [source={row['source']}]")
        for err in report["skip_errors"]:
            print(f"  would-skip: {err['error']}")
        print("[rfq-ingest] DRY-RUN: nothing written — no journal line, no lock, "
              "no status refresh")
        return 0 if report["would_skip"] == 0 else 1
    journal = RawRFQJournal(journal_path)
    print(f"[rfq-ingest] provider={provider.describe()} journal={journal_path}")
    try:
        run = ingest(provider, journal, field_map, stop_on_error=not args.keep_going)
    except RFQSchemaError as e:
        print(f"[rfq-ingest] FAIL-CLOSED: {e}", file=sys.stderr)
        return 1
    print(f"[rfq-ingest] appended={run['appended']} skipped={run['skipped']}")
    for err in run["skip_errors"]:
        print(f"  skip: {err['error']}")
    status = write_status(journal, DEFAULT_STATUS, extra={
        "op": "ingest", "provider": run["provider"], "appended": run["appended"],
        "skipped": run["skipped"]})
    print(f"[rfq-ingest] status: lines={status['integrity']['lines']} "
          f"head={status['integrity']['head_hash'][:16]}… "
          f"sources={status['integrity']['sources']}")
    print(f"[rfq-ingest] artifact: {os.path.relpath(DEFAULT_STATUS, REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
