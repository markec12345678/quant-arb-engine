# The first-feed runbook (v0.6.5)

* status: operational runbook — the sequenced, exact commands for the day a
  real RFQ feed connects. NOT a sealed design record: no new invariants, no
  data semantics — it only sequences machinery that is already shipped and
  sealed (see the index at the bottom). NOT research: nothing here produces
  a research number; W1 remains gated on its own sealed decision record.

## 0. Day −1: rehearse (today, zero risk)

Run the full sequence below against **stand-in desk data in a scratch
workspace** — every real command, every honest rejection surface, nothing
written to the repo:

```bash
python3 scripts/rehearse_first_feed.py
```

Expected: every step PASSes, ends with `REHEARSAL COMPLETE`, exit 0. If any
step fails, the machinery is not ready for the real day — fix before
connecting anything.

## 1. First contact with the real export — `--dry-run` (writes NOTHING)

```bash
python3 scripts/rfq_ingest.py --provider file \
    --path <desk-export.json> \
    --field-map <your-field-map.json> \
    --dry-run
```

What success looks like: `would-append=N`, `would-skip=0`, exit 0 — and
nothing written (no journal line, no lock, no status refresh, no dirs).
Every would-be skip is **named**: `[MAP]` field-map errors (fix the map and
re-run), `[R-1]` duplicates with their origin (journal-vs-batch). Exit 1
means "something would be skipped" — that is information, not failure.

## 2. Ingest for real

```bash
python3 scripts/rfq_ingest.py --provider file \
    --path <desk-export.json> \
    --field-map <your-field-map.json> \
    [--keep-going]        # count+report skips instead of aborting
```

The journal is immutable and hash-chained; duplicate rfq_ids are refused
(R-1); every accepted record lands verbatim (`raw` preserved). The derived
status artifact (`research/artifacts/rfq-status.json` — the tower reads it
read-only) is refreshed, recording the new chain head. Operators running
non-default journals pass matching `--journal`/`--status` pairs.

## 3. Verify integrity

```bash
python3 scripts/rfq_replay.py --verify-only
```

Chain walk (tamper/reorder/insertion), per-record schema re-validation, and
the truncation bound: the live head is compared against the head recorded in
the status artifact. `truncation=checked` is the healthy word.

## 4. Research-readiness census (the W1 inclusion-criteria artifact)

```bash
python3 scripts/rfq_coverage.py --json > coverage-latest.json
```

One command answers what the journal supports: per family — eligibility
breakdown (expired/no-response/indicative counted, not silently dropped),
quote-day coverage with partial-pair days named, tenor census, unclassified
buckets. **Keep this output**: the future W1 sealed decision record cites it
as its inclusion criteria. Census, not research — no averages, no spreads.

## 5. Push providers (the always-on lane)

```bash
python3 scripts/rfq_webhook_recv.py --port 3901 --token SHARED_SECRET
```

Every **accepted** record also refreshes the status artifact (the tower
stays live while you ingest; `--no-status-refresh` is the burst escape).
Honest surfaces: 401 bad/missing token · 400 malformed JSON · 422 schema
violation or duplicate rfq_id (invariant id in the response) · 500 internal
error (class travels) · on 200, `status_refresh` is `"ok"` or `"stale"`
(derived-artifact failure never masquerades as an ingestion failure — the
journal is the source of truth).

## 6. W1 — deliberately NOT in this runbook

The first research round on real data (uncertainty → ranking → GO/NO-GO)
requires its **own sealed decision record, written before any number
exists**, and it must answer the funding-data question (the 15-field schema
carries quote events only — adapter record §1). That is a separate day with
its own discipline.

## Honest limits

* **0 real records** exist as of this writing — every command above is
  exercised on stand-in data by the rehearsal until a feed connects.
* The source wall: synthetic records are never research-eligible; the
  census and the replay adapter refuse synthetic journals by default.
* Everything here is descriptive/collection only. No live trading anywhere,
  ever, in this system.

## Sealed-records index (authority chain)

| record | seals | written before |
|---|---|---|
| `docs/w0-rfq-ingestion.md` (v0.6.0) | schema R-1…R-13, immutable journal, adapters, edge accounting | the W0 code |
| `docs/w1-replay-adapter.md` (v0.6.2) | replay mapping M-1…M-10, honest capability map | the adapter code |
| `docs/w1-coverage-report.md` (v0.6.3) | census rules C-1…C-9 | the census code |
| `docs/w0-webhook-hardening.md` (v0.6.4) | live-status + honest-error rules H-1…H-5 | the hardening code |
| `docs/decision-record-v0.3.0/v0.4.0/v0.5.0.md` | the mock-world research rounds | their respective runs |
