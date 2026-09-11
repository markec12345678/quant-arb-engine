# W1-INFRA: the RFQ journal coverage report (v0.6.3)

* status: SEALED design record — written 2026-09-11, BEFORE implementation
* version: 0.6.3 · follows the replay adapter (docs/w1-replay-adapter.md,
  sealed 0.6.2) · same discipline as W0
* discipline: **infrastructure, not research.** The coverage report is a
  measurement — a census of what a W0 journal actually contains. It produces
  **no research number** (no uncertainty, no ranking, no GO/NO-GO). Its entire
  purpose is to feed the *inclusion criteria* of the future W1 research design
  record: before that record is sealed, the researcher must be able to state,
  from real data, which families/days/tenors exist and in what completeness.

## 0. What this is — and is not

```
W0 raw journal (immutable, hash-chained)
        │  verify chain (read-only) → source wall → census rules C-1…C-9
        ▼
coverage report (families · eligibility breakdown · day coverage · tenors)
        │
        ▼
W1 research design record (LATER, user-gated, sealed before any number)
   — its §inclusion-criteria cites this census, not ad-hoc queries
```

The structural gap this closes: the replay adapter (M-1) silently skips
ineligible records — correct for quote surfacing, but a researcher looking at
a fresh real journal could not distinguish "500 records, 10 eligible" from
"12 records" without re-implementing the walk. The census makes the journal's
research-readiness **a one-command, reproducible fact**. One additive
observability fix ships with it: `JournalReplayFeed.describe()` gains an
`ineligible` counter (records of its family that failed M-1) — additive, M-1
semantics unchanged, same precedent as the v0.6.1 additive hardening.

## 1. What it measures

Per instrument family, over the WHOLE journal (no family pre-selected):

| measurement | meaning |
|---|---|
| `total_records` / `eligible` | all family records vs M-1-eligible (quoted+firm) |
| `ineligible.by_status` | expired / rejected / no_response counts — the honest cost of collection friction |
| `ineligible.indicative` | quoted but not firm — surfaceable as information, not as executable quotes |
| `unusable` | M-4 failures (ccy mismatch, non-positive px), each named |
| `quote_days` / `first_day` / `last_day` | UTC days with ≥1 eligible record (M-7's day unit) |
| `spot_days` / `spot_full_pair_days` | days with any eligible spot vs days with BOTH sides (M-2's honest-pair requirement) |
| `partial_spot_days` | day numbers where only one side exists — the pair cannot be surfaced |
| `tenors` | per tenor `{records, full_pair_days}` — the forward surface census |
| `perp_days` | days with an eligible perp-kind record |
| `venues` | the desks that quoted this family |

Plus journal-level `unclassified`: `bad_symbols` (forward symbols violating
the M-6 `{SYM}-FWD-{n}D` convention, or roots not in BASE-QUOTE form) and
`other_kinds` (instrument kinds outside spot/forward/perp, e.g. cfd/option).

## 2. The census rules (sealed C-1…C-9)

- **C-1 family detection.** spot → the instrument itself is the family root;
  forward → strip the `-FWD-{n}D` suffix; perp → strip `-PERP`. The root must
  be BASE-QUOTE form (contains `-`); otherwise the record is `bad_symbols`.
- **C-2 report-don't-refuse.** A malformed forward symbol does NOT raise (the
  replay adapter's M-6 raises — correct there, wrong here): the census's job
  is to *reveal* convention violations before replay is attempted. It buckets
  them and keeps walking. The census never crashes on what it is counting.
- **C-3 eligibility = M-1** (status `quoted` AND quote_type `firm`), counted
  per status and per quote_type — the observability fix.
- **C-4 unusable = M-4** (notional_ccy ≠ price_ccy, non-positive quoted_price),
  each named with its rfq_id, same message shape as the replay adapter.
- **C-5 quote day = M-7's day unit** (UTC day of `ts`, eligible records only).
- **C-6 pair completeness.** A day's spot surface is complete iff both
  requesting sides have an eligible record that day (M-2); a tenor's day
  surface is complete iff both sides have an eligible forward record that
  day. Partial days are listed by 1-based day number (the feed's numbering).
- **C-7 source wall — same gate as M-8.** A journal containing synthetic
  records is REFUSED by default (`allow_synthetic=True` is the machinery-test
  mode and the report says so). The census output feeds the W1 sealed record:
  it must describe REAL data only. The wall lives in one place.
- **C-8 read-only.** Chain verified at load (M-9's walk); the journal is
  byte-identical after; nothing is written anywhere (no lock, no status
  refresh — a census is not a W0 ingestion event).
- **C-9 deterministic and family-optional.** `--family SYMBOL` restricts the
  report to one family; default = all families, sorted by symbol. Output is a
  plain JSON-serializable dict + a human rendering; identical journal →
  identical report.

## 3. Output contract

Module `quant_arb/feeds/coverage.py`: `journal_coverage(journal, family=None,
*, allow_synthetic=False) -> dict` and `render_report(cov) -> str`.
CLI `scripts/rfq_coverage.py`: `--journal` (default the real journal path) ·
`--smoke-journal` (selects the tracked synthetic journal — still walled
without `--allow-synthetic`) · `--allow-synthetic` · `--family` · `--json`.
Exit 0 on a produced report (an empty real journal honestly reports 0
families); exit 1 on wall refusal, chain failure, or I/O error.

## 4. Sealed decisions

1. The census refuses synthetic journals by default (C-7 = M-8's gate), so no
   coverage fact that could cite its way into a W1 record ever derives from
   synthetic data.
2. Report-don't-refuse for symbol conventions (C-2) — the deliberate mirror
   image of M-6; the two behaviors are complementary, not contradictory.
3. `ineligible` is a first-class output (C-3), not a footnote: collection
   friction (expired/no-response/indicative) is research-relevant cost.
4. The additive `describe()["ineligible"]` counter on the replay feed ships
   with this record; M-1..M-10 semantics are untouched; the sealed v0.6.2
   record is NOT edited (this document is the authority for the addition).
5. No aggregation beyond counting: no averages, no spreads, no edges — the
   moment a statistic stops being a census, it becomes W1 research and needs
   its own sealed record.
6. Empty journals are a valid report (0 families), never an error.
