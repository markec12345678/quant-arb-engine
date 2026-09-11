# W0 — Real RFQ ingestion (design record, sealed before implementation)

* status: **SEALED 2026-09-11** (before any W0 code was written)
* author context: user-approved parallel strategy — funding-arb locked @ 0373f5d
  collecting its 7-day paper baseline (A/B/C ~Sep 17); quant-arb-engine develops
  W0 now. **No live trading. Paper/research only.**
* version: 0.6.0 · follows decision-record-v0.5.0 (c7d5c5b)

---

## 0. What W0 is — and is not

W0 is the **transition from the synthetic world to the real world at the data
layer**: an immutable raw RFQ journal, a provider-adapter surface, ingestion,
logging, replay, and a **deterministic** ALL-IN EDGE accounting over whatever
RFQ records exist.

W0 is **not**:

* **not a new estimator** (the v0.5 STOP RULE on σ iterations is untouched —
  the synthetic-world σ story stays measured at both bounds, closed);
* **not a research round** — no predictions, no verdicts, no GO/NO-GO gates
  over real data. The chain *uncertainty → ranking → GO/NO-GO* on **real**
  RFQ data is W1 research and requires its own sealed decision record before
  any real-data research number is produced;
* **not connected to a live desk** — no RFQ API credentials exist in this
  environment. W0 ships the full ingestion machinery plus adapters that a
  feed can be plugged into the day one exists (file export ingest today;
  webhook receiver for push providers; poller skeleton slot).

## 1. The raw record schema (user-specified, 15 required fields)

Every external RFQ is normalized to `ExternalRFQ` (module
`quant_arb/rfq/schema.py`). Required fields — the user's list verbatim:

| # | field | type / constraint | invariant |
|---|---|---|---|
| 1 | `rfq_id` | str, unique across the journal | R-1 |
| 2 | `instrument` | str symbol + `instrument_kind` (spot/perp/forward/cfd/option); forward must carry `expiry_ts` | R-2 |
| 3 | `venue` | str, the quoting venue/provider | R-2 |
| 4 | `ts` | unix ms, the quote timestamp; > 0 | R-3 |
| 5 | `side` | `buy` \| `sell` — the side **we requested** | R-4 |
| 6 | `requested_notional` | > 0, with `notional_ccy` | R-4 |
| 7 | `quoted_price` | > 0, finite, with `price_ccy`; required when status = `quoted` | R-5 |
| 8 | `quote_type` | `firm` \| `indicative` (executable vs indicative); required when status = `quoted` | R-6 |
| 9 | `quote_expiry_ts` | unix ms ≥ `ts`; required when status = `quoted` | R-7 |
| 10 | `fees` | `fees_pct` ≥ 0 (as reported, % of notional) + `fees_included_in_price: bool` — **never ambiguous** | R-8 |
| 11 | `spread` | `spread_bps` ≥ 0, full quoted bid-ask spread as reported; null if not reported | R-9 |
| 12 | `reference_price` | > 0 + `reference_source` tag (I-1 provenance discipline: never a naked number) | R-10 |
| 13 | `reference_ts` | unix ms **≤ `ts`** — market data cannot be from the future | R-11 |
| 14 | `latency_ms` | ≥ 0 (request → response) | R-12 |
| 15 | `status` | `quoted` \| `rejected` \| `expired` \| `no_response` | R-13 |

Plus two W0-critical fields of our own:

* `source`: **`real` \| `synthetic`** — the epistemic wall. Every synthetic
  record is marked at birth; research aggregation paths accept `real` only
  (enforced in code, not by convention);
* `raw`: the provider's payload preserved **verbatim** (the audit lesson:
  normalization may add fields but must never lose what the desk actually
  sent).

Validation is write-time and fail-closed (`RFQSchemaError` → nothing reaches
the file). Field #12's provenance rule descends directly from I-1; #13 from
the NEW-16 "mark that was actually a stale ticker" lesson.

## 2. The immutable raw journal

`quant_arb/rfq/journal.py` — `RawRFQJournal`, JSONL, append-only:

* every line: `{seq, received_ts, source, rfq, prev_hash, hash}`;
* `hash = sha256(canonical_json(seq, prev_hash, received_ts, source, rfq))`;
* the chain makes **tampering, reordering and insertion** detectable anywhere
  in the file (`verify()` recomputes the walk; mismatch at line k → error
  naming k);
* there is **no update/delete API** — immutability by construction;
* single-writer discipline: an advisory lockfile guards concurrent appends;
* **honest limitation, stated up front**: pure tail truncation (dropping the
  *last* lines) is not detectable from the file alone — the chain head hash
  is therefore persisted in the derived status artifact after every ingest
  (`research/artifacts/rfq-status.json`) and re-checked by `verify()`, so
  truncation is caught at the next verification against the recorded head.

Paths (governance by design):

* real feed journal: `research/artifacts/rfq/journal.jsonl` — **gitignored**
  (raw desk data may be proprietary; size unbounded);
* synthetic smoke journal: `research/artifacts/rfq/journal-synthetic-smoke.jsonl`
  — tracked, deterministic, every line `source: "synthetic"`, exists to make
  the machinery reviewable before real data exists (same purpose as the mock
  feed, stated in the README epistemics).

## 3. Provider surface (pluggable, normalize-at-the-edge)

`quant_arb/rfq/providers/base.py` — an `RFQProvider` yields raw payloads plus
a declarative **field map** (`ExternalRFQFieldMap`) that maps provider key
names → schema fields with value transforms (ISO-8601 → unix ms, bps → pct,
side synonyms). Normalization is provider-side; the journal stores the
verbatim raw alongside the normalized record.

Shipped adapters:

1. **file_ingest** (real, usable today) — desk exports / user-held RFQ
   history in JSONL, JSON array or CSV; `--field-map <json>`; example map
   shipped at `quant_arb/rfq/providers/example_field_map.json`;
2. **webhook** (real, run when a provider exists) — a stdlib HTTP receiver
   (`scripts/rfq_webhook_recv.py`) that accepts POSTed RFQ payloads, applies
   the field map, validates and journals immutably; one command to run;
   providers that push (Paradigm-style) point at it;
3. **synthetic** (TEST ONLY, `source="synthetic"` hardwired) — seeded
   deterministic generator that exercises every schema path including
   rejects, indicative quotes, stale references and latency jitter.

A polling adapter for an authenticated REST desk is a **slot**, not code —
writing it without credentials would be untestable theater. It lands with W1
when the user connects a source.

## 4. Deterministic ALL-IN EDGE (accounting, not estimation)

`quant_arb/rfq/edge.py` — per record, in bps of reference:

```
price_edge_bps   = side_sign × (reference_price − quoted_price) / reference_price × 1e4
                   (buy below reference = positive edge; sell above = positive)
fee_cost_bps     = fees_pct × 100      — counted ONLY when fees_included_in_price = false
                                        (I-4 descendant: exactly once, never twice)
all_in_edge_bps  = price_edge_bps − fee_cost_bps
```

Descriptive reporting only (`replay.py`): counts by source/status/quote_type,
edge distribution (mean, quantiles) split by instrument/venue, reference-age
and latency stats, firm-vs-indicative split. Every report carries the
epistemic note and the source wall (synthetic split shown separately, never
pooled into research aggregates). **No uncertainty term, no ranking, no
GO/NO-GO** — those need W1 pre-registration on real data.

## 5. CLI surface

```bash
# ingest from a real export
python3 scripts/rfq_ingest.py --provider file --path <export.jsonl> --field-map <map.json>

# ingest from the synthetic generator (pipeline test only)
python3 scripts/rfq_ingest.py --provider synthetic --n 200 --seed 7

# verify chain + invariants + head-vs-status check; refresh status artifact
python3 scripts/rfq_replay.py                 # verify + full descriptive report
python3 scripts/rfq_replay.py --verify-only   # integrity check only
```

Every operation refreshes `research/artifacts/rfq-status.json` (records by
source, chain head hash, instruments/venues, last ts, integrity verdict) —
the tower reads this file read-only, same contract as run-latest/sweep-latest.

## 6. Sealed decisions

1. Schema as §1 (the user's 15 fields + source + verbatim raw); validation
   fail-closed at write time.
2. Journal as §2 (hash-chained append-only JSONL; head-hash persisted in the
   status artifact to bound tail truncation; real journal gitignored,
   synthetic smoke journal tracked).
3. Adapters as §3 (file + webhook + synthetic today; poller slot for W1).
4. All-in edge as §4 — deterministic accounting only; NO estimator, NO
   research verdicts, NO GO/NO-GO in W0.
5. Funding-arb untouched @ 0373f5d throughout; no live trading anywhere;
   first real-data research (uncertainty/ranking) requires a NEW sealed
   decision record before any number is produced.
