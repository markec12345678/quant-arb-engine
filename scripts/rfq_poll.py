"""W0: poll the connected real venue source (OKX) — ingestion ONLY.

  python3 scripts/rfq_poll.py                # one poll = 4 RFQ records
  python3 scripts/rfq_poll.py --dry-run      # validate, write NOTHING

The connected source (docs/w0-venue-source-connection.md, sealed v0.7.0):
OKX public order books — BTC-USDT spot + BTC-USDT-PERP perp, buy + sell,
10,000 USDT notional per record. No orders, no trading, no research: the
records land in the hash-chained venue journal and the derived status
artifact refreshes (the tower reads it read-only).

Journal + status defaults are the VENUE lane's own paths (tracked on the
rfq-data branch; the sealed desk-feed default journal.jsonl stays
gitignored and untouched). Pass --journal/--status as a pair, same rule as
rfq_ingest/rfq_replay.

Restore precheck (the durable lane's discipline): when the status artifact
already exists, the journal's chain head is verified against the RECORDED
head BEFORE anything is appended — a truncated or corrupted restore fails
closed here, nothing new is written onto a broken journal.

Exit codes: 0 = every instrument produced a record (quoted, rejected or
no_response); 1 = schema failure (fail-closed, nothing further appended) or
a COLD fetch failure (an instrument got no record because the venue did not
answer AND no prior reference existed — partial data already appended stays
journaled; the GitHub lane pushes it and then fails the run visibly).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from quant_arb.rfq.ingest import REPO_ROOT, dry_run, ingest, write_status
from quant_arb.rfq.journal import RawRFQJournal, RFQJournalError
from quant_arb.rfq.providers.venue_book import (OKXBookRFQProvider,
                                                venue_field_map)
from quant_arb.rfq.schema import RFQSchemaError

VENUE_JOURNAL = os.path.join(REPO_ROOT, "research", "artifacts", "rfq",
                             "journal-venue.jsonl")
VENUE_STATUS = os.path.join(REPO_ROOT, "research", "artifacts",
                            "rfq-status-venue.json")


def prior_references_from_journal(journal_path: str) -> dict:
    """Freshest reference per instrument from the journal tail — the honest
    fallback for no_response records (V-8). Reads the whole (bounded-cadence)
    journal and keeps each instrument's LAST record's reference."""
    refs: dict = {}
    if not os.path.exists(journal_path):
        return refs
    last: dict = {}
    with open(journal_path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                rec = json.loads(s)
            except json.JSONDecodeError:
                continue
            rfq = rec.get("rfq") or {}
            inst = rfq.get("instrument")
            if inst:
                last[inst] = rfq
    for inst, rfq in last.items():
        try:
            refs[inst] = (float(rfq["reference_price"]), int(rfq["reference_ts"]))
        except (KeyError, TypeError, ValueError):
            continue
    return refs


def restore_precheck(journal_path: str, status_path: str) -> None:
    """Fail-closed truncation bound BEFORE appending: the live journal head
    must match the head recorded in the status artifact (the restore path's
    honesty check — W0 §2's honest-limitation bound)."""
    if not (os.path.exists(status_path) and os.path.exists(journal_path)):
        return  # first run / fresh workspace — nothing recorded yet
    with open(status_path, "r", encoding="utf-8") as f:
        st = json.load(f)
    expect = (st.get("integrity") or {}).get("head_hash")
    if not expect:
        return
    journal = RawRFQJournal(journal_path, create_parent=False)
    journal.verify(expect_head=expect)   # raises RFQJournalError on mismatch


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--journal", default=VENUE_JOURNAL,
                    help="venue journal path (default: the tracked venue lane "
                         "journal; pass --status as the matching pair)")
    ap.add_argument("--status", default=VENUE_STATUS,
                    help="derived status artifact path (refreshed after the poll)")
    ap.add_argument("--notional", type=float, default=10_000.0,
                    help="requested notional per RFQ, quote ccy (default 10000)")
    ap.add_argument("--depth", type=int, default=25,
                    help="book levels fetched per instrument (default 25)")
    ap.add_argument("--timeout", type=float, default=10.0,
                    help="per-request timeout seconds (default 10)")
    ap.add_argument("--keep-going", action="store_true",
                    help="count+report invalid payloads instead of aborting")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate + preview WITHOUT writing anything")
    args = ap.parse_args()

    prior = prior_references_from_journal(args.journal)
    provider = OKXBookRFQProvider(notional=args.notional, depth=args.depth,
                                  timeout_s=args.timeout,
                                  prior_references=prior)
    field_map = venue_field_map()

    if args.dry_run:
        journal = RawRFQJournal(args.journal, create_parent=False)
        print(f"[rfq-poll] DRY-RUN provider={provider.describe()} "
              f"journal={args.journal} prior_refs={sorted(prior)}")
        report = dry_run(provider, journal, field_map)
        print(f"[rfq-poll] would-append={report['would_append']} "
              f"would-skip={report['would_skip']} "
              f"would-be-sources={report['would_be_sources']}")
        for row in report["preview"]:
            print(f"  preview: {row['rfq_id']} {row['instrument']} @ {row['venue']} "
                  f"{row['side']} {row['status']} [source={row['source']}]")
        for err in report["skip_errors"]:
            print(f"  would-skip: {err['error']}")
        cold = provider.cold_failures()
        for c in cold:
            print(f"  cold-failure (no record): {c}")
        print("[rfq-poll] DRY-RUN: nothing written — no journal line, no lock, "
              "no status refresh")
        return 0 if (report["would_skip"] == 0 and not cold) else 1

    try:
        restore_precheck(args.journal, args.status)
    except RFQJournalError as e:
        print(f"[rfq-poll] RESTORE PRECHECK FAILED (nothing appended): {e}",
              file=sys.stderr)
        return 1

    journal = RawRFQJournal(args.journal)
    print(f"[rfq-poll] provider={provider.describe()} journal={args.journal} "
          f"notional={args.notional:.0f} USDT depth={args.depth}")
    try:
        run = ingest(provider, journal, field_map,
                     stop_on_error=not args.keep_going)
    except RFQSchemaError as e:
        print(f"[rfq-poll] FAIL-CLOSED: {e}", file=sys.stderr)
        return 1
    print(f"[rfq-poll] appended={run['appended']} skipped={run['skipped']}")
    for err in run["skip_errors"]:
        print(f"  skip: {err['error']}")
    status = write_status(journal, args.status, extra={
        "op": "venue-poll", "provider": run["provider"],
        "appended": run["appended"], "skipped": run["skipped"],
        "venue": "okx", "notional_usdt": args.notional, "depth": args.depth})
    print(f"[rfq-poll] status: lines={status['integrity']['lines']} "
          f"head={status['integrity']['head_hash'][:16]}… "
          f"sources={status['integrity']['sources']}")
    print(f"[rfq-poll] artifact: {os.path.relpath(args.status, REPO_ROOT)}")

    cold = provider.cold_failures()
    if cold:
        for c in cold:
            print(f"[rfq-poll] COLD FETCH FAILURE (no record for this "
                  f"instrument): {c}", file=sys.stderr)
        print("[rfq-poll] partial data above stays journaled; run exits 1 so "
              "the lane shows the gap (the push still happens — durability "
              "of partial real data beats losing it).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
