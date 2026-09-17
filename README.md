# quant-arb-engine

[![CI](https://github.com/markec12345678/quant-arb-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/markec12345678/quant-arb-engine/actions/workflows/ci.yml)

Next-generation **multi-strategy arbitrage / quant research engine** — built in
parallel to the locked funding-arb baseline. **Paper / research only: it never
submits an order, never holds capital, never talks to a live venue.**

> Built 2026-09-11 per the recorded decision in
> [`docs/decision-record-2026-09-11.md`](docs/decision-record-2026-09-11.md);
> v0.3.0 per [`docs/decision-record-v0.3.0.md`](docs/decision-record-v0.3.0.md);
> v0.4.0 per [`docs/decision-record-v0.4.0.md`](docs/decision-record-v0.4.0.md);
> v0.5.0 per [`docs/decision-record-v0.5.0.md`](docs/decision-record-v0.5.0.md);
> v0.6.0–v0.6.5 (the W0 real-RFQ ingestion line and the W1-INFRA bridge —
> infrastructure, no estimator work) per the sealed records
> [`docs/w0-rfq-ingestion.md`](docs/w0-rfq-ingestion.md) ·
> [`docs/w0-webhook-hardening.md`](docs/w0-webhook-hardening.md) ·
> [`docs/w1-replay-adapter.md`](docs/w1-replay-adapter.md) ·
> [`docs/w1-coverage-report.md`](docs/w1-coverage-report.md) ·
> the first-feed runbook [`docs/runbook-first-feed.md`](docs/runbook-first-feed.md);
> v0.7.0 — **the real venue-book source connection (OKX public books, the
> poller slot lands)** — per
> [`docs/w0-venue-source-connection.md`](docs/w0-venue-source-connection.md).
> The measured system ([funding-arb](https://github.com/markec12345678/funding-arb)
> @ `0373f5d`) stays untouched — Phase-2 concluded with verdict C (results
> locked, root-caused, archived):
> **the old system measured reality; this engine now ingests it.**

---

## Why this exists

The 8-round audit of funding-arb (43 findings) proved three things that shape
every module here:

1. **Fees and execution costs decide the economics** — funding income alone was
   consumed by costs on the paper sample. So the cost model is not a detail,
   it is the engine's core (`ALL-IN EDGE` waterfall).
2. **Measurement defects are silent unless invariants are enforced in code**
   (NEW-16 "mark price" that was a ticker; NEW-17 per-leg notionals ≠ requested;
   NEW-18 requested-vs-actual ambiguity; NEW-20 inverted PnL signs). Here those
   lessons are **write-time invariant checks** (I-1…I-6) — a record that violates
   one is rejected, not silently written.
3. **Numbers need epistemic discipline.** Synthetic/paper results are phrased as
   *diagnostics*, never as evidence of an edge. Every run's summary carries the
   canonical note (see §Epistemics).

## Architecture

```
                    QUANT ARB ENGINE  (v0.6 — W0: real RFQ ingestion layer)
                           │
             ┌─────────────┼─────────────┐
             ↓             ↓             ↓
        Forward Basis   Perp Carry    Funding Arb   ← strategy families
        (lock carry)    (float carry)  (port later)    (universal shape)
             │             │             │
             └─────────────┼─────────────┘
                           ↓
                    RANKING LAYER          ← both evaluated every quote day;
                           ↓                 execute the higher net edge
                    ALL-IN EDGE            ← gross − entry − exit − slippage
                           ↓                 − carry uncertainty − exec risk
                    RISK ENGINE            ← caps: notional / tenor / open count
                           ↓
                    PAPER EXECUTION        ← position state machine, signed PnL
                           ↓
                    RESEARCH / RESULTS     ← append-only journal (JSONL)
                           ↑
              W0 · RAW RFQ JOURNAL       ← NEW v0.6: immutable hash-chained
                           ↑               real-world ingestion layer
                    RFQ PROVIDERS          ← file ingest / webhook receiver /
                                             synthetic (test-only) adapters
```

Module map:

| module | role |
|---|---|
| `quant_arb/models/market_data.py` | `Venue`-agnostic primitives: `Instrument`, `Price` (**value + source + ts — never a naked number, I-1**), `FundingObservation` (hour-normalized), `RFQQuote` (fee model fully embedded in the quoted price, I-4) |
| `quant_arb/models/opportunity.py` | **Universal opportunity model** — legs with direction, executable entry/exit, requested **and** executed size (I-2/I-6), carry estimate, edge, confidence |
| `quant_arb/models/journal.py` | Append-only JSONL event journal with **write-time invariant enforcement** (I-1…I-6) |
| `quant_arb/edge/carry.py` | Implied-carry math: **three sigmas, one gate** — `ewma_funding` → σ_level (instantaneous estimator error), `horizon_sigma_apr` → σ_A (iid-block window dispersion, v0.3 audit), `horizon_sigma_trend_apr` → σ_H two-sided (v0.4 audit), `horizon_sigma_downside_apr` → **σ_down, the adverse-side gate σ of v0.5** (falling trend charged in full, rising uncharged); forward-implied APR; gap z-score |
| `quant_arb/edge/all_in_edge.py` | **ALL-IN EDGE waterfall** — every subtraction explicit, nothing folded into gross (I-4). Two waterfalls: `evaluate_forward_basis` (locked premium) and `evaluate_perp_carry` (floating carry, explicit CEX cost lines) |
| `quant_arb/feeds/mock_rfq.py` | Deterministic synthetic world **v2** (seeded): CEX funding prints + OTC desk spot/forward RFQ quotes + perp mark; regime ramps **and collapses**. **SYNTHETIC — research only** |
| `quant_arb/feeds/journal_replay.py` | **W1-INFRA (v0.6.2)**: `JournalReplayFeed` — replays a W0 raw RFQ journal into the typed quote vocabulary (sealed `docs/w1-replay-adapter.md`, mapping M-1…M-10: quoted+firm eligibility, requesting-side→desk bid/ask, I-1 provenance incl. the new `REFERENCE_OTHER`, size=notional/px, ttl=expiry−ts, `-FWD-{n}D` tenor convention fail-closed, one feed=one family, source wall at the Price layer, read-only, funding/settlement surfaces refused loudly). Bridge for the W1 research record — infrastructure, not research |
| `quant_arb/feeds/coverage.py` | **W1-INFRA (v0.6.3)**: `journal_coverage()` + `render_report()` — the research-readiness census of a W0 journal (sealed `docs/w1-coverage-report.md`, rules C-1…C-9: per-family eligibility breakdown with the honest cost of collection friction (expired/rejected/no_response/indicative counted, not silently dropped), day coverage with partial-pair days named, tenor census, unclassified bad-symbol/other-kind buckets — report-don't-refuse, never crashes on what it counts; source wall; read-only; deterministic). The output the future W1 sealed record cites as inclusion criteria — measurement, not research |
| `quant_arb/strategies/forward_basis.py` | **Route B, family `forward_basis_v1`** (lock carry): long spot @ desk ask + short dated forward @ desk bid; gates on net edge (level z retired to diagnostic — decision record C4) |
| `quant_arb/strategies/perp_carry.py` | **Family `perp_carry_v1`** (float carry): long spot @ desk ask + short CEX perp @ mark; floating funding accrual at settle; gates on net edge AND horizon persistence z_perp = E/σ_down ≥ 2 (a downside persistence ratio since v0.5) |
| `quant_arb/risk/caps.py` | Research caps — per-position notional, tenor, open-position count; enumerated reject reasons |
| `quant_arb/positions.py` | Paper position state machine: `OPEN → SETTLED`, **signed PnL only** (I-3); perp legs settle at mark + signed funding accrual |
| `quant_arb/pipeline.py` | Research run loop: feed → **both families → ranking** → edge → risk → journal; `family_eval` + `funding_daily` journaling; summary with unit discipline |
| `quant_arb/research/stats.py` | Pure-stdlib distribution helpers (mean, sample std, numpy-style linear percentiles) for sweep summaries — machinery diagnostics, never market evidence |
| `scripts/research_run.py` | CLI entry point (single run) |
| `scripts/research_sweep.py` | Multi-seed sweep CLI (v0.5: 80 seeds = screening 1..60 + holdout 61..80 + like-for-like 1..40); overwrites the stable `run-latest.json` / `sweep-latest.json` derived summaries for the tower |
| `quant_arb/rfq/` | **W0 (v0.6): the real-world data layer** — `schema.py` `ExternalRFQ` (the 15 user-specified fields + the `source` epistemic wall + verbatim `raw`, write-time invariants R-1…R-13), `journal.py` immutable hash-chained raw journal (tamper/reorder/insertion detection; head-vs-status truncation bound), `edge.py` deterministic ALL-IN EDGE accounting (I-4 descendant: fees charged exactly once), `replay.py` descriptive reporting |
| `quant_arb/rfq/providers/` | Pluggable adapters — `file_ingest.py` (REAL: desk exports JSONL/JSON/CSV), `webhook.py` (REAL: push receiver, one command when a provider exists; **v0.6.4 hardened** — sealed `docs/w0-webhook-hardening.md`: per-append status refresh via the `on_append` hook so the tower stays live while the always-on path ingests, honest response semantics (derived-artifact failure → `status_refresh:"stale"`, never a fake ingestion failure), honest 500 surface (class travels, traceback doesn't, nothing journaled)), `synthetic.py` (TEST ONLY, `source="synthetic"` hardwired), `base.py` declarative `FieldMap` normalization (ISO→epoch, bps→pct, side/status synonyms) |
| `scripts/rfq_ingest.py` · `rfq_replay.py` · `rfq_webhook_recv.py` · `rfq_coverage.py` · `rehearse_first_feed.py` | W0/W1-INFRA CLIs — ingest (`--dry-run` first-contact validation writes NOTHING) / verify+replay (descriptive accounting only) / webhook receiver (refreshes `rfq-status.json` per accepted record — `--no-status-refresh` escape for bursts; `--status` mirrors `--journal`) / coverage census (`--json`, `--family`; the one-command research-readiness answer before any W1 record is sealed) / **the first-feed rehearsal** — the full runbook as one executable dress rehearsal on stand-in data, zero repo writes (run it today) |

## Run the research demo (zero network, zero capital)

```bash
python3 scripts/research_run.py                 # 200 synthetic days, seed 7
python3 scripts/research_run.py --days 120 --seed 3 --tenor 60
```

Writes an append-only journal to `research/artifacts/run_<ts>.jsonl` and prints a
summary. Requires Python ≥ 3.10, **stdlib only — no dependencies.**

## W0 (v0.6) — Real RFQ ingestion: the transition to the real world

Full design record: [`docs/w0-rfq-ingestion.md`](docs/w0-rfq-ingestion.md)
(sealed 2026-09-11, **before** implementation). W0 is the user-approved parallel
move: while funding-arb collects its 7-day Phase-2 baseline untouched, the engine
builds the **real-world data layer** — not a new estimator, not a research round:

* **`ExternalRFQ` schema** — the 15 user-specified fields (instrument, venue,
  timestamp, side, requested notional, quoted price, firm/indicative, quote
  expiry, fees, spread, reference market price, market-data timestamp, latency,
  response status, unique RFQ ID), each with a write-time invariant (R-1…R-13,
  fail-closed). Reference prices carry provenance (I-1 descendant); market data
  from the future is rejected (R-11).
* **Immutable raw RFQ journal** — append-only JSONL, **hash-chained** per line:
  tampering, reordering and insertion are detected and named by line; the head
  hash is re-checked against the derived status artifact, bounding tail
  truncation. The provider payload is preserved **verbatim** alongside the
  normalized record. The REAL journal (`research/artifacts/rfq/journal.jsonl`)
  is **gitignored by design** (desk data may be proprietary).
* **The source wall** — every record carries `source: real | synthetic`;
  synthetic is hardwired in the test generator and structurally excluded from
  research aggregation (the report shows sources **split, never pooled**). The
  ingest CLI **refuses** to write synthetic records into the real journal.
* **Deterministic ALL-IN EDGE accounting** (per record, bps of reference):
  `price_edge − fees` with fees charged **exactly once** (only when NOT embedded
  in the quoted price — the I-4 lesson). Descriptive statistics only: **no
  uncertainty term, no ranking, no GO/NO-GO** — that chain on real data is W1
  research and requires its own sealed decision record first.
* **Provider adapters** — `file` (REAL: desk exports / user-held RFQ history in
  JSONL/JSON/CSV via a declarative `--field-map`), `webhook` (REAL: one-command
  push receiver for Paradigm-style providers, shared-secret token supported),
  `venue_book` (REAL since v0.7.0: the connected **OKX public-book poller** —
  see below), `synthetic` (TEST ONLY, the pipeline exerciser). The
  authenticated-desk-REST poller remains a slot for the day desk credentials
  exist — writing it without credentials would be untestable theater.

```bash
# THE FIRST-FEED DAY, rehearsed today on stand-in data (zero repo writes):
# the full sequence — dry-run → ingest → webhook → verify → census → replay
# — as one executable dress rehearsal (runbook: docs/runbook-first-feed.md)
python3 scripts/rehearse_first_feed.py

# FIRST CONTACT with an unknown export format: validate + preview, write NOTHING
# (per-row schema + field-map validation, duplicate detection, would-be census;
#  exit 1 if any row would be skipped — fix the map/export before real ingest)
python3 scripts/rfq_ingest.py --provider file --path export.jsonl \
    --field-map quant_arb/rfq/providers/example_field_map.json --dry-run

# ingest a real desk export (first real-data path, usable today)
python3 scripts/rfq_ingest.py --provider file --path export.jsonl \
    --field-map quant_arb/rfq/providers/example_field_map.json

# pipeline smoke (synthetic, test-only, tracked journal)
python3 scripts/rfq_ingest.py --provider synthetic --n 200 --seed 7 --smoke-journal

# verify chain + truncation bound; descriptive replay report; status artifact
python3 scripts/rfq_replay.py --verify-only
python3 scripts/rfq_replay.py --markdown

# push-provider receiver (run when a feed exists; binds 127.0.0.1)
# every ACCEPTED record also refreshes rfq-status.json — the tower stays live
python3 scripts/rfq_webhook_recv.py --port 3901 --token SHARED_SECRET

# research-readiness census of the journal (families, eligibility, days, tenors)
python3 scripts/rfq_coverage.py            # human report
python3 scripts/rfq_coverage.py --json     # machine-readable, for the W1 record

# THE CONNECTED REAL VENUE SOURCE (v0.7.0): poll OKX public books —
# BTC-USDT spot + BTC-USDT-PERP perp, buy + sell, 10k USDT notional per record.
# The durable lane runs this on GitHub Actions (single writer, pushes to the
# rfq-data branch); --dry-run is the safe first contact, writes NOTHING
python3 scripts/rfq_poll.py --dry-run
python3 scripts/rfq_poll.py --journal research/artifacts/rfq/journal-venue.jsonl \
    --status research/artifacts/rfq-status-venue.json

# reproduce every W0 invariant check from the repo alone (116 checks, exit = failures)
# — this exact command is the CI gate that runs on GitHub on every push to main
python3 research/exploration/verify_w0_invariants.py
```

**v0.7.0 — the real source is connected.** The poller slot landed as the
**OKX venue-book lane** (sealed record:
[`docs/w0-venue-source-connection.md`](docs/w0-venue-source-connection.md)):
BTC-USDT spot + BTC-USDT-PERP perp, both sides, 10,000 USDT notional per
record, depth VWAP fills, the venue's published taker fees with provenance in
every record's raw, deterministic retry-safe ids, and honest
rejected/no_response surfaces. Venue selection was evidence-first (needing
sandbox AND GitHub-runner reachability — Bybit/Binance geo-block the
runner plane; Hyperliquid's only BTC spot is wrapped UBTC, a different W1
family; Kraken's spot taker fee is 0.40%). Collection is **ingestion only,
no trading ever**. The durable lane: GitHub Actions every 30 min (+dispatch
bridge), single writer, in-run chain verification, artifacts pushed to the
`rfq-data` branch (journal + status + census + descriptive report) — the
sealed desk path `journal.jsonl` stays gitignored, untouched.

Honest status as shipped: real records exist via the venue lane (count in
`research/artifacts/rfq-status-venue.json` on `rfq-data`); a desk feed
remains at **0 records** — no desk credentials exist in this environment.
The machinery is complete, invariant-checked (**116 checks**: fully
reproducible from the repo via
`research/exploration/verify_w0_invariants.py`: chain tamper/reorder/insert/
truncate detection, duplicate-id rejection (journal + within-batch), future
reference rejection, determinism, source wall, edge accounting, field-map
synonyms, dry-run writes-nothing, malformed-row isolation, webhook receiver —
token gate, duplicate/future-ts rejection, malformed JSON, only-valid-journaled,
the v0.6.4 webhook hardening — per-append status refresh, stale-marker
honesty, 500 surface, zero pollution of the real artifact,
the W1-INFRA replay adapter — source wall, provenance mapping, tenor
convention, refused funding/settlement surfaces, read-only replay — the
W1-INFRA coverage census — eligibility breakdown, day/tenor coverage,
unclassified buckets, CLI e2e — the first-feed rehearsal — and the v0.7.0
venue source: VWAP math hand-computed, ctVal contract multiplier, insufficient
depth → rejected, fetch failure → no_response with honest prior reference,
cold-failure discipline, R-1 retry safety, the W1 family census on real-shaped
records, zero pollution) — the same two steps run as **CI on GitHub on every
push/PR to main** (`.github/workflows/ci.yml`: whole-tree byte-compilation,
then the 116-check harness). The operational sequence for a desk-feed day is
[`docs/runbook-first-feed.md`](docs/runbook-first-feed.md); the venue lane's
own sequence is its workflow + §7 of the runbook.

## W1-INFRA (v0.6.2) — the RFQ journal replay adapter

Full design record: [`docs/w1-replay-adapter.md`](docs/w1-replay-adapter.md)
(sealed 2026-09-11, **before** implementation). The bridge half of extension
point 2: it replays a W0 journal into the engine's typed quote vocabulary
(`RFQQuote` / `Price` / `Instrument`), so the future W1 research record —
sealed separately, when real data exists — consumes provenance-carrying quotes
instead of raw records. **Infrastructure, not research**: no uncertainty, no
ranking, no GO/NO-GO number comes out of it.

* The **honest capability map** (design record §1): the 15-field schema
carries **quote events** — spot pairs, forward pairs, perp marks and reference
mids replay. Funding observations, settlement prints and true APR are NOT RFQ
fields and are **refused loudly** (M-10): synthesizing them from forwards would
be an estimator smuggled in through infrastructure. Perp-carry settlement on
real data needs a data class beyond the schema — that decision belongs to the
W1 research record (or the user, for a schema extension).
* The **source wall doubles at the Price layer** (M-8): any synthetic record →
the constructor refuses; `allow_synthetic=True` is the machinery-test mode and
stamps `SYNTHETIC_MOCK` on every quote — the wall travels inside the data,
I-1 enforces it downstream.

## W1-INFRA (v0.6.3) — the coverage report (research-readiness census)

Full design record: [`docs/w1-coverage-report.md`](docs/w1-coverage-report.md)
(sealed 2026-09-11, **before** implementation). The measurement half that
closes W1-INFRA: when a real feed connects, **one command** answers what the
journal actually supports — per family: eligibility breakdown (the honest
cost of collection friction: expired / no_response / indicative counted,
not silently dropped), quote-day coverage with partial-pair days named, tenor
census, perp days, venues, and unclassified bad-symbol/other-kind buckets
(report-don't-refuse — the mirror image of the adapter's M-6 refusal; the
census's job is to *reveal* convention violations before replay is attempted).

* Its entire purpose: the future W1 research design record **cites this
census as its inclusion criteria** — reproducible, from real data only (the
source wall applies: synthetic journals refused by default).
* **Census, not research** (sealed decision 5): no averages, no spreads, no
edges — the moment a statistic stops being a census it becomes W1 research
and needs its own sealed record. Empty journals are a valid report (0
families), never an error.
* Ships with an additive observability fix: `JournalReplayFeed.describe()`
gains an `ineligible` counter (M-1 drops, counted not silently dropped).

```bash
python3 scripts/rfq_coverage.py --json   # the one-command readiness answer
```

## v0.3 — Instrument choice, honest horizon σ, ranking (decision record)

v0.2.0's two honest findings drove v0.3.0 (full reasoning in
[`docs/decision-record-v0.3.0.md`](docs/decision-record-v0.3.0.md), written
**before** any v0.3 run):

1. **The z-gate calibration was reading σ_level as if it were a horizon
   statement** (98.7 % breach vs 4.55 % nominal). v0.3 defines σ_H
   (`horizon_sigma_apr`: overlapping-window dispersion, deterministic) and
   journals both sigmas apart — the artifact now carries **two calibration
   panels**, the level one kept for audit.
2. **The world was one-sided** (carry only ramped up), so the instrument
   question never existed. World v2 ramps 8 % → 18 % **and then collapses
   18 % → 4 %** (days 150–180): the regime where a dated forward locking a
   stale-high premium can beat floating on a short perp.

New machinery:

- **Second family `perp_carry_v1`** — long spot @ desk ask + short CEX perp
  @ mark: the floating twin of Route B, with explicit CEX cost lines
  (taker fee + half-spread) in its waterfall and signed printed-funding
  accrual at settle.
- **Ranking layer (C5)** — every quote day both families are evaluated and
  journaled (`family_eval`, gated or not — full decision audit); among
  gated-in families the higher net executable edge is executed, tie →
  forward.
- **`funding_daily`** — the observation stream is journaled itself, so every
  research metric is re-derived from the journal alone.

40-seed sweep results (SYNTHETIC diagnostics, machinery validation only):

- ranking **hit-rate 60.2 %** on 791 full-window contested days (contested =
  both families gated in — 99.4 % of quote days in this world, which
  **refuted** prediction P3 "contests are a minority": interesting finding,
  reported as measured);
- **P2 supported**: forward selected 30.2 % of ramp-phase contests vs
  79.5 % of collapse-phase contests — the ranking flips with the regime
  exactly as the lag model predicts;
- **P1 supported**: σ_H panel breach 35.0 % vs σ_level 67.1 % (pooled) —
  halved and below the pre-registered 50 % rejection bar, still honestly
  above the 4.55 % nominal (iid-block scaling underestimates
  autocorrelated regime drift — a documented limitation, not a tuned number);
- per-family settled: forward n=182, mean +2.03 % (realized − locked
  −3.1 bps — the lock still holds through settlement); perp n=98, mean
  +3.32 % (accrual − expected +36.9 bps — floating carry beat its ex-ante
  estimate in the build-up world).

Interpretation RULE (unchanged): machinery diagnostics on a synthetic world.
They validate code paths, never market edges.

## v0.4 — Trend-aware horizon σ, round 2 (decision record)

v0.3.0's honest residual — **35.0 % horizon breach vs 4.55 % nominal** — drove
v0.4.0 (full reasoning, disclosed candidate screening and the STOP RULE in
[`docs/decision-record-v0.4.0.md`](docs/decision-record-v0.4.0.md), written
**before** any v0.4 run):

1. **Disclosed screening on the frozen v0.3 journals** (the script ships in
   `research/exploration/`): the textbook fix — HAC / Newey–West — measured
   **73.2 % breach**, WORSE than doing nothing: it targets the variance of a
   *stationary* mean, the wrong estimand when the funding level drifts. A
   local-level two-scale estimator measured 49.6 %. Both REJECTED, with the
   numbers.
2. **The chosen estimator**: `horizon_sigma_trend_apr` —
   σ_H = √(σ_A² + (|β̂|·H/2)²) where σ_A is the v0.3 value (kept verbatim as
   the audit component) and β̂ the OLS slope of daily printed APRs over the
   last 60 days (measured insensitive 30–90). Meaning: dispersion risk +
   trend-continuation exposure. One σ, one meaning — the z_perp gate, the
   carry buffer and the journal all carry the same number.
3. **Holdout confirmation design**: seeds 1..40 = the screening set
   (disclosed in-sample); seeds 41..60 = holdout, never used in any decision;
   panels reported pooled AND split.

60-seed results (SYNTHETIC diagnostics, machinery validation only):

- **P1 SUPPORTED**: trend-panel breach **11.0 %** pooled (from 35.0 %);
- **P2 SUPPORTED**: holdout 12.1 % vs screening set 10.4 % (Δ +1.7 pp) — the
  estimator generalizes across seeds, it is not a screening artifact;
- **entry-history decomposition** (the residual made measurable): breaches at
  entries with ≤ 45 observed days **15.0 %** vs **0.8 %** with > 45 days —
  the remaining miscalibration is early-history uncertainty (a regime too
  young to be visible), while with enough history the trend-aware σ is now
  slightly conservative (0.8 % < 4.55 % nominal);
- **P3 REFUTED**: perp gated-in share 83.4 % (predicted ≤ 75 %) — the honest σ
  makes the persistence gate bind (99.4 % → 83.4 %) but less than predicted;
- **P4 REFUTED — the round's headline finding**: ranking hit-rate
  **11.4 %** on the screening set (v0.3: 60.2 %). The two-sided trend term in
  the carry buffer deflates the floating family's net executable edge, the
  ranking flips to the locked forward on ~94 % of selected days, and the
  ex-post scorecard (all full-window contests are ramp-phase in this world)
  says that was the wrong call: the realized carry kept beating the stale desk
  premium. **Honest uncertainty pricing has a measured price.** The stop rule
  forbids patching this inside v0.4; the asymmetric question — should a carry
  buffer price DOWNSIDE semi-deviation rather than two-sided σ, since drift
  is upside for a long-carry position — is the pre-registration question for
  v0.5, recorded here as a finding, not fixed silently.
- **P5 SUPPORTED**: forward share of contested selections in the collapse
  phase 95.8 % (v0.3: 79.5 %) — phase behaviour preserved and sharpened.

Interpretation RULE (unchanged): machinery diagnostics on a synthetic world.
They validate code paths, never market edges.

## v0.5 — Asymmetric carry buffer, adverse-side horizon σ (decision record)

v0.4.0's P4 refutation — hit-rate **60.2 % → 11.4 %** — left a recorded
question: should the carry buffer price **downside semi-deviation** for a
long-carry position, since a continuing RISING trend is upside? v0.5.0 asked
exactly that (full estimand argument, disclosed screening and STOP RULE in
[`docs/decision-record-v0.5.0.md`](docs/decision-record-v0.5.0.md), sealed
**before** any v0.5 run):

1. **The estimand argument, stated before any number**: for a long-carry
   position the PnL error under a falling visible trend is adverse
   (≈ −|β̂|·H/2 — continuation IS the adverse central case, charged in full
   exactly as v0.4 charged it); under a rising trend the error is upside
   (continuation adds carry, trend death lands ≈ 0), and only a full regime
   REVERSAL hurts — a tail whose probability is **unknowable from
   backward-looking data**. The reversal weight therefore lives on an
   ignorance interval: v0.4 priced the **pessimistic bound** (reversal weighted
   like continuation), v0.5 prices the **optimistic bound** (reversal at
   zero). No interior weight is chosen — that would be the estimator fishing
   the STOP RULE forbids.
2. **Disclosed screening on the frozen v0.4 journals** (2b12b34, 420 settles,
   exact re-derivation to 0.0002 pp): the v0.4 symmetric term's residual
   breaches were **46/46 positive-direction** — its protective work was pure
   upside over-pricing (the measured anatomy of P4). The adverse-side
   candidate: downside breach **0.0 %** (one-sided nominal 2.28 %), upside
   surprise 21.2 %, mean σ 3.23 pp — CHOSEN as the optimistic bound. Would-be
   re-ranking: hit-rate 62.8 % pooled / 61.9 % seeds 1..40.
3. **The estimator**: `horizon_sigma_downside_apr` —
   σ_down = √(σ_A² + (max(0, −β̂)·H/2)²) with β̂ identical to v0.4's. One σ,
   one meaning: the z_perp gate (now a **downside persistence ratio**), the
   carry buffer and the journal all carry σ_down; the v0.4 two-sided and v0.3
   iid values are journaled next to it as audit components.

80-seed results (SYNTHETIC diagnostics, machinery validation only; the
executed numbers landed on the pre-registered would-be predictions almost
exactly — 62.8 %/61.9 % predicted, 62.8 %/61.9 % measured):

- **P1 SUPPORTED**: pooled downside-panel breach **0.0 %** over 560 checks
  (one-sided nominal 2.28 %; ≤ 8 % pre-registered);
- **P2 SUPPORTED**: holdout (seeds 61..80, never used in any decision in any
  engine version) 0.0 % vs screening set (1..60) 0.0 % — the ladder extends,
  it never re-rolls;
- **P3 SUPPORTED — the recovery**: like-for-like (seeds 1..40) full-window
  hit-rate **61.9 %** (v0.4: 11.4 %; v0.3: 60.2 %): removing the un-grounded
  upside charge restores the majority-correct ranking without touching a
  single gate threshold;
- **P4 SUPPORTED — the honest price, measured twice**: (a) day-bucket split
  32.9 % (window avoids collapse, d ≤ 60) vs 88.0 % (touches, d > 60) — the
  early-flat information limit concentrates the misses exactly where
  pre-registered; AND (b) the upside-surprise panel **19.8 %** — the
  un-charged favorable drift is visible as frequent positive surprises.
  Reported as cost, never patched;
- **P5 SUPPORTED**: forward share of contested selections in the collapse
  phase **68.9 %** like-for-like (v0.4: 95.7 %) — the β̂ regime-turn lag
  (~10–15 days after the collapse starts, the ramp still dominates the
  60-day window) leaks those days to the perp; the signed charge takes over
  after the lag and keeps the collapse majority-forward.

The round's reading, stated plainly: on this synthetic world the v0.4
pessimistic bound paid a measured decision price (P4 refuted) for protection
the ex-post record shows it never used (0 downside breaches in 420 settles);
the v0.5 optimistic bound recovers the ranking and pays its own price in the
places the record can see — the early-flat information limit and the
regime-turn lag. The nominal for a real market is neither bound: it is W0's
real feed. Interpretation RULE unchanged.

## Research layer (v0.2 → v0.5)

Multi-seed sweep on top of the single-run pipeline — the machinery-validation
layer:

```bash
python3 scripts/research_sweep.py                     # 80 seeds (screening 1..60 + holdout 61..80; like-for-like 1..40)
python3 scripts/research_sweep.py --seeds 10 --days 120 --tenor 60   # quick subset
```

Runs the full pipeline per seed (one invariant-enforced journal per seed under
`research/artifacts/sweep_runs/`), pools the statistics and overwrites two
**stable artifact files**, consumed read-only by the tower dashboard:

- `research/artifacts/run-latest.json` — the representative seed (default 7):
  the exact pipeline summary, every settled position with lock/accrual
  diagnostics, the last journaled opportunity payload, the **carry curve**
  (daily printed APR) and the **per-day family edge series** (net edge of
  both families + who was selected).
- `research/artifacts/sweep-latest.json` — cross-seed aggregates: totals,
  family census, **ranking hit-rate (pooled / screening / like-for-like with
  the contest day-bucket decomposition)**, **quadruple z-gate calibration
  panels + the upside honest-cost panel** (level / iid / two-sided / adverse
  + holdout ladder split + entry-history decomposition), the disclosed
  estimator screening block, reject-reason census, pooled settled
  stats, **scored predictions P1..P5**, per-seed rows.

The two `-latest.json` files are **derived summaries** (plain JSON, not
journal-managed); the append-only invariant-enforced journals remain the source
of truth. Runs are deterministic — seeds are explicit, never time-based.

What the stats MEAN:

- **selection / contested / hit-rate** — selection = quote days where some
  family gated in and was chosen; contested = both gated in (a genuine
  contest); hit-rate = share of full-window contests where the SELECTED
  family's ex-post carry beat the forgone family's (forward = desk-implied
  APR at entry; perp = realized mean printed APR over the window).
- **family_census** — per family: evals / gated_in / selected / opened /
  settled + settled distributions (`realized_minus_locked_bps` for the
  forward, `funding_accrual_bps` and `realized_minus_expected_bps` for the
  perp).
- **reject_reasons** — census of risk-cap rejects across all journals; the
  open-position concentration cap dominates, as the single-run demo predicts.
- **settled_stats.pnl_pct_of_notional** — distribution of realized signed PnL
  per settled position, as % of requested notional, pooled across seeds.
- **realized_minus_locked_bps** — `(realized settlement PnL − premium locked at
  inception)` in bps of notional: **how well the dated-forward lock holds
  through settlement**. Expected ≈ −(exit cost): everything but the exit
  crossing is contractually fixed, so the number should be small and negative —
  in this world the realized exit crossing is the desk spot half-spread at
  unwind (3 bps on exit notional), while the waterfall books the conservative
  pre-registered `exit_cost_bps = 8` buffer ex ante. A tight, small-negative
  distribution means the lock machinery works.
- **z_gate_calibration (dual panel)** — honesty checks of the two sigmas. If
  σ were an honest uncertainty for the held window, ≈ 4.55 % (2σ two-sided)
  of settled entries would breach `|window-mean APR − ex-ante APR| > 2σ`.
  The **level panel** reproduces the v0.2.0 finding (estimator standard error
  is NOT a horizon statement — kept for audit). The **horizon panel** is the
  redefined diagnostic on σ_H; both are reported AS COMPUTED and never tuned.
- **predictions P1/P2/P3** — the falsifiable statements written in the decision
  record BEFORE the runs, scored by the sweep as measured (verdicts included
  in the artifact; refuted predictions are reported, never buried).

Interpretation RULE: these are machinery diagnostics on a synthetic world.
They validate code paths, never market edges.

## Invariants (audit lessons → enforced code)

| id | rule | origin |
|---|---|---|
| I-1 | every price carries an explicit source tag + timestamp | NEW-16 |
| I-2 | per-leg notional is recorded **as executed** (qty × actual fill px) | NEW-17 |
| I-3 | PnL is **signed** `(exit − entry) × qty × direction`; no `abs()` anywhere | NEW-20 |
| I-4 | all-in cost counted **exactly once** (RFQ spread *is* the fee) | R8 fee audit |
| I-5 | quantity chain quote → fill → settlement must match exactly | R8 quantity audit |
| I-6 | `requested_size_usd` and `executed_size_usd` are distinct, always both written | NEW-18 |

## Epistemics (non-negotiable)

- Synthetic and paper results are **diagnostics, never evidence**. Canonical
  phrasing of any paper number: *"Na trenutnem vzorcu in uporabljeni
  rekonstrukciji ni dokaza za pozitiven edge."*
- Unit discipline: aggregates are Σ(per-position % of notional) over N positions —
  always reported alongside the per-position mean, never misread as per-cycle.
- The mock feed exists so the machinery is exercised and reviewable **before**
  any real data arrives (W1). When real RFQ quotes exist, a real feed class
  implements the same interface and the strategy code does not change.
- **W0 addendum (v0.6):** the raw RFQ journal's synthetic records are *test
  fixtures*, never evidence — the source wall (`real` | `synthetic`) is enforced
  in code on ingest, in aggregation, and in the CLI; research-eligible statistics
  are computed over `real` records only, always reported source-split.

## What is deliberately NOT here

No live trading · no NODE auto-trading · no real capital · no FIX production
execution · no ML deciding about money · no portfolio allocator · no complex
strategies without data. The engine is **paper/research only** until the W2 gate
of the [Wintermute plan](https://github.com/markec12345678/funding-arb-tower/blob/main/docs/wintermute-node-analysis.md)
passes on ≥30 days of real journaled quotes.

## Family

| repo | role |
|---|---|
| [funding-arb](https://github.com/markec12345678/funding-arb) | the measured system — **locked** @ `0373f5d` (Phase-2 A/B/C paper validation) |
| [phase3-lab](https://github.com/markec12345678/phase3-lab) | execution-safety laboratory (certified, port blocked by Phase-2 verdict) |
| [funding-arb-tower](https://github.com/markec12345678/funding-arb-tower) | read-only command center + the research plan/decision records |
| **quant-arb-engine** (this repo) | next-generation research engine — paper only · CI on every push (whole-tree byte-compile + the 116-check invariant harness) · W0 real venue lane: OKX public books → rfq-data branch (ingestion only, no trading) |
