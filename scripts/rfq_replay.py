"""W0: replay / verify the raw RFQ journal — descriptive accounting only.

  python3 scripts/rfq_replay.py                # verify + full report + status
  python3 scripts/rfq_replay.py --verify-only  # integrity check only
  python3 scripts/rfq_replay.py --markdown     # human-readable report to stdout

Chain verify (tamper/reorder/insertion), truncation check vs the recorded
status head, per-record schema re-validation, deterministic ALL-IN EDGE
statistics (source-split, never pooled). NO research conclusions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from quant_arb.rfq.ingest import DEFAULT_STATUS, REPO_ROOT
from quant_arb.rfq.journal import RawRFQJournal, RFQJournalError
from quant_arb.rfq.replay import replay, render_markdown

SMOKE_JOURNAL = os.path.join(REPO_ROOT, "research", "artifacts", "rfq",
                             "journal-synthetic-smoke.jsonl")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--journal", default=None,
                    help="default: the smoke journal if the real one is absent")
    ap.add_argument("--smoke-journal", action="store_true")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--refresh-status", action="store_true",
                    help="re-record the live chain head (recovery / first-run path; "
                         "chain integrity still fully verified)")
    args = ap.parse_args()

    if args.journal:
        path = args.journal
    elif args.smoke_journal:
        path = SMOKE_JOURNAL
    else:
        from quant_arb.rfq.ingest import DEFAULT_JOURNAL
        path = DEFAULT_JOURNAL if os.path.exists(DEFAULT_JOURNAL) else SMOKE_JOURNAL

    journal = RawRFQJournal(path, create_parent=False)
    print(f"[rfq-replay] journal={path}")
    try:
        if args.verify_only:
            from quant_arb.rfq.replay import load_status
            st = load_status(DEFAULT_STATUS)
            expect = (st or {}).get("integrity", {}).get("head_hash")
            summary = journal.verify(expect_head=expect)
            print(f"[rfq-replay] OK lines={summary['lines']} "
                  f"head={summary['head_hash'][:16]}… sources={summary['sources']} "
                  f"truncation={'checked' if expect else 'no-prior-status'}")
            return 0
        report = replay(journal, DEFAULT_STATUS, refresh_status=args.refresh_status)
    except RFQJournalError as e:
        print(f"[rfq-replay] INTEGRITY FAILURE: {e}", file=sys.stderr)
        return 1

    if args.markdown:
        print(render_markdown(report))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
