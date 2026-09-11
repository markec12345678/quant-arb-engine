# quant-arb-engine

Next-generation **multi-strategy arbitrage / quant research engine** — built in
parallel to the locked funding-arb baseline. **Paper / research only: it never
submits an order, never holds capital, never talks to a live venue.**

> Built 2026-09-11 per the recorded decision in
> [`docs/decision-record-2026-09-11.md`](docs/decision-record-2026-09-11.md).
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
                    QUANT ARB ENGINE
                           │
             ┌─────────────┼─────────────┐
             ↓             ↓             ↓
          Funding        Basis        Forward     ← strategies (Funding Arb
           Arb            Arb           Arb         ported later; Forward Basis
             │             │             │           implemented now, mock feed)
             └─────────────┼─────────────┘
                           ↓
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
| `quant_arb/edge/carry.py` | Implied-carry math: EWMA funding APR + estimator σ, forward-implied APR, gap z-score |
| `quant_arb/edge/all_in_edge.py` | **ALL-IN EDGE waterfall** — every subtraction explicit, nothing folded into gross (I-4) |
| `quant_arb/feeds/mock_rfq.py` | Deterministic synthetic world (seeded): CEX funding prints + OTC desk spot/forward RFQ quotes. **SYNTHETIC — research only** |
| `quant_arb/strategies/forward_basis.py` | **Route B** (primary research direction): implied carry (CEX funding) vs priced forward premium → gated ALL-IN EDGE → paper signal |
| `quant_arb/risk/caps.py` | Research caps — per-position notional, tenor, open-position count; enumerated reject reasons |
| `quant_arb/positions.py` | Paper position state machine: `OPEN → SETTLED`, **signed PnL only** (I-3) |
| `quant_arb/pipeline.py` | Research run loop: feed → strategy → edge → risk → journal; summary with unit discipline |
| `quant_arb/research/stats.py` | Pure-stdlib distribution helpers (mean, sample std, numpy-style linear percentiles) for sweep summaries — machinery diagnostics, never market evidence |
| `scripts/research_run.py` | CLI entry point (single run) |
| `scripts/research_sweep.py` | Multi-seed sweep CLI (v0.2); overwrites the stable `run-latest.json` / `sweep-latest.json` derived summaries for the tower |

## Run the research demo (zero network, zero capital)

```bash
python3 scripts/research_run.py                 # 200 synthetic days, seed 7
python3 scripts/research_run.py --days 120 --seed 3 --tenor 60
```

Writes an append-only journal to `research/artifacts/run_<ts>.jsonl` and prints a
summary. Requires Python ≥ 3.10, **stdlib only — no dependencies.**

## Research layer (v0.2)

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
  the exact pipeline summary, every settled position with lock diagnostics, and
  the last journaled opportunity payload.
- `research/artifacts/sweep-latest.json` — cross-seed aggregates: totals, gate
  fire rate, reject-reason census, pooled settled stats, z-gate calibration,
  per-seed rows.

The two `-latest.json` files are **derived summaries** (plain JSON, not
journal-managed); the append-only invariant-enforced journals remain the source
of truth. Runs are deterministic — seeds are explicit, never time-based.

What the stats MEAN:

- **gate_fire_rate_pct** — share of quoting days on which the pre-registered
  gates fired (z ≥ 2 AND net edge ≥ 10 bps). On the synthetic ramp the desk
  lags the funding regime *by construction*, so this is high by design of the
  mock world — it measures world construction, not strategy selectivity.
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
- **locked_minus_perp_alt_apr_bps** — locked premium APR vs the perp funding
  alternative over the same window (opportunity cost, synthetic).
- **z_gate_calibration** — honesty check of the estimator σ: if the EWMA
  estimator σ were an honest uncertainty for the held window, ≈ 4.55%
  (2σ two-sided) of settled entries would breach
  `|realized window APR − ex-ante EWMA APR| > 2σ`. The empirical rate is
  reported AS COMPUTED and never tuned. (On the synthetic ramp it is very
  high: the estimator σ measures *instantaneous* estimation error, not
  horizon uncertainty — regime drift over the 90-day window dominates. That is
  a property of the σ's meaning, and knowing it is the point of the check.)

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
