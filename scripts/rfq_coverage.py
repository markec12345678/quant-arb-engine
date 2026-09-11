"""W1-INFRA: the RFQ journal coverage report — research-readiness census.

A read-only census of what a W0 raw journal actually contains: instrument
families, eligibility breakdown (expired/no-response/indicative — the honest
cost of collection friction), quote-day coverage, forward tenor census,
unclassified buckets. Measurement, not research: no averages, no spreads, no
edges — anything beyond counting is W1 research and needs its own sealed
record (docs/w1-coverage-report.md).

Usage:
  python scripts/rfq_coverage.py                     # the real journal
  python scripts/rfq_coverage.py --json              # machine-readable
  python scripts/rfq_coverage.py --family BTC-USD    # one family
  python scripts/rfq_coverage.py --smoke-journal --allow-synthetic   # machinery test

The source wall applies: a journal containing synthetic records is refused
unless --allow-synthetic (the census feeds W1 inclusion criteria — it must
describe real data only). Exit 0 on a produced report (an empty real journal
honestly reports 0 families); exit 1 on wall refusal, chain failure, or
I/O error. Writes NOTHING — the journal is byte-identical after (C-8).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from quant_arb.feeds.coverage import CoverageError, journal_coverage, render_report
from quant_arb.rfq.ingest import DEFAULT_JOURNAL, REPO_ROOT
from quant_arb.rfq.journal import RawRFQJournal

SMOKE_JOURNAL = os.path.join(REPO_ROOT, "research", "artifacts", "rfq",
                             "journal-synthetic-smoke.jsonl")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--journal", default=DEFAULT_JOURNAL,
                    help="path to the W0 raw journal (default: the real journal)")
    ap.add_argument("--smoke-journal", action="store_true",
                    help="target the tracked synthetic smoke journal "
                         "(still walled without --allow-synthetic)")
    ap.add_argument("--allow-synthetic", action="store_true",
                    help="machinery-test mode: census a synthetic journal "
                         "(the report says so)")
    ap.add_argument("--family", default=None,
                    help="restrict the census to one family symbol (BASE-QUOTE form)")
    ap.add_argument("--json", action="store_true",
                    help="emit the machine-readable report only")
    args = ap.parse_args()

    path = SMOKE_JOURNAL if args.smoke_journal else args.journal
    if not os.path.exists(path):
        print(f"coverage: journal not found: {path}", file=sys.stderr)
        return 1

    try:
        journal = RawRFQJournal(path, create_parent=False)   # C-8: read-only
        cov = journal_coverage(journal, family=args.family,
                               allow_synthetic=args.allow_synthetic)
    except CoverageError as e:
        print(f"coverage: {e}", file=sys.stderr)
        return 1
    except Exception as e:                                    # chain / I/O failures
        print(f"coverage: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    print(json.dumps(cov, indent=2) if args.json else render_report(cov))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
