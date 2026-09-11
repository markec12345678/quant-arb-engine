# quant-arb-engine

Next-generation **multi-strategy arbitrage / quant research engine** — built in
parallel to the locked funding-arb baseline. **Paper / research only: it never
submits an order, never holds capital, never talks to a live venue.**

> Built 2026-09-11 per the recorded decision in
> [`docs/decision-record-2026-09-11.md`](docs/decision-record-2026-09-11.md);
> v0.3.0 per [`docs/decision-record-v0.3.0.md`](docs/decision-record-v0.3.0.md).
> The measured system ([funding-arb](https://github.com/markec12345678/funding-arb)
> @ `0373f5d`) stays untouched and keeps collecting Phase-2 A/B/C evidence:
> **the old system measures reality; this engine explores the next generation.**

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
                    QUANT ARB ENGINE  (v0.3 — two families + ranking)
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
```

Module map:

| module | role |
|---|---|
| `quant_arb/models/market_data.py` | `Venue`-agnostic primitives: `Instrument`, `Price` (**value + source + ts — never a naked number, I-1**), `FundingObservation` (hour-normalized), `RFQQuote` (fee model fully embedded in the quoted price, I-4) |
| `quant_arb/models/opportunity.py` | **Universal opportunity model** — legs with direction, executable entry/exit, requested **and** executed size (I-2/I-6), carry estimate, edge, confidence |
| `quant_arb/models/journal.py` | Append-only JSONL event journal with **write-time invariant enforcement** (I-1…I-6) |
| `quant_arb/edge/carry.py` | Implied-carry math: **two sigmas with two meanings** — `ewma_funding` → σ_level (instantaneous estimator error), `horizon_sigma_apr` → σ_H (empirical dispersion of H-day window means, overlapping windows, deterministic); forward-implied APR; gap z-score |
| `quant_arb/edge/all_in_edge.py` | **ALL-IN EDGE waterfall** — every subtraction explicit, nothing folded into gross (I-4). Two waterfalls: `evaluate_forward_basis` (locked premium) and `evaluate_perp_carry` (floating carry, explicit CEX cost lines) |
| `quant_arb/feeds/mock_rfq.py` | Deterministic synthetic world **v2** (seeded): CEX funding prints + OTC desk spot/forward RFQ quotes + perp mark; regime ramps **and collapses**. **SYNTHETIC — research only** |
| `quant_arb/strategies/forward_basis.py` | **Route B, family `forward_basis_v1`** (lock carry): long spot @ desk ask + short dated forward @ desk bid; gates on net edge (level z retired to diagnostic — decision record C4) |
| `quant_arb/strategies/perp_carry.py` | **Family `perp_carry_v1`** (float carry): long spot @ desk ask + short CEX perp @ mark; floating funding accrual at settle; gates on net edge AND horizon persistence z_perp = E/σ_H ≥ 2 |
| `quant_arb/risk/caps.py` | Research caps — per-position notional, tenor, open-position count; enumerated reject reasons |
| `quant_arb/positions.py` | Paper position state machine: `OPEN → SETTLED`, **signed PnL only** (I-3); perp legs settle at mark + signed funding accrual |
| `quant_arb/pipeline.py` | Research run loop: feed → **both families → ranking** → edge → risk → journal; `family_eval` + `funding_daily` journaling; summary with unit discipline |
| `quant_arb/research/stats.py` | Pure-stdlib distribution helpers (mean, sample std, numpy-style linear percentiles) for sweep summaries — machinery diagnostics, never market evidence |
| `scripts/research_run.py` | CLI entry point (single run) |
| `scripts/research_sweep.py` | Multi-seed sweep CLI (v0.3); overwrites the stable `run-latest.json` / `sweep-latest.json` derived summaries for the tower |

## Run the research demo (zero network, zero capital)

```bash
python3 scripts/research_run.py                 # 200 synthetic days, seed 7
python3 scripts/research_run.py --days 120 --seed 3 --tenor 60
```

Writes an append-only journal to `research/artifacts/run_<ts>.jsonl` and prints a
summary. Requires Python ≥ 3.10, **stdlib only — no dependencies.**

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

## Research layer (v0.2 → v0.3)

Multi-seed sweep on top of the single-run pipeline — the machinery-validation
layer:

```bash
python3 scripts/research_sweep.py                     # 40 seeds (1..40), 200 days each
python3 scripts/research_sweep.py --seeds 10 --days 120 --tenor 60
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
  family census, **ranking hit-rate**, **dual z-gate calibration panels**, reject-reason
  census, pooled settled stats, **scored predictions P1/P2/P3**, per-seed rows.

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
  any real data arrives (W1). When real RFQ quotes exist, a `WintermuteFeed`
  implements the same interface and the strategy code does not change.

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
| **quant-arb-engine** (this repo) | next-generation research engine — paper only |
