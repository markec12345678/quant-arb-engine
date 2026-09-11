# Architecture — quant-arb-engine

## Separation of concerns (the binding principle)

```
funding-arb @ 0373f5d    LOCKED measurement system (Phase-2 A/B/C paper runner)
        ↕ shares nothing but concepts
quant-arb-engine         new development — paper/research only
        ↕ observed read-only
funding-arb-tower        command center (never trades)
```

The measurement system must never be contaminated by new development, and the
research engine must never be tempted to touch live infrastructure. There is
no import, no shared state, no shared database between the repos — the only
transfer is **conceptual knowledge** (schemas, invariants, lessons).

## Module contracts

| module | contract |
|---|---|
| `models/market_data.py` | `Price = value + PriceSource + ts` (I-1). `FundingObservation` normalizes per-interval rates to hourly/annualized. `RFQQuote` embeds the entire fee model in the quoted price; `all_in_cost_bps` is the crossing cost vs `ref_mid`, counted once (I-4). |
| `models/opportunity.py` | The universal shape every strategy emits: executable legs (direction, qty, fill price), `requested_size_usd` **and** `executed_size_usd = qty × px` (I-2/I-6), carry estimate (locked vs estimated + σ), edge numbers, horizon, confidence. |
| `models/journal.py` | Append-only JSONL. `validate_record()` runs **before** every write: I-1 price source, I-2 executed notional, I-3 signed-only PnL field names, I-5 quantity chain flag, I-6 both size fields, canonical epistemic note + unit fields on summaries. Violations raise `JournalInvariantError`; nothing invalid is ever persisted. |
| `edge/carry.py` | `ewma_funding(obs, half_life_h) → (apr, σ_apr)` — the σ is the estimator's standard error (std/√eff_n), not funding vol. `forward_implied_apr`, `carry_gap_z` (gap over √(σ_realized² + σ_desk²)). |
| `edge/all_in_edge.py` | The waterfall: `gross − entry − exit − slippage − carry_uncertainty − execution_risk = net_executable_edge`. Each line explicit and journaled. `EdgeParams` holds the **pre-registered gates** (`min_net_edge_bps=10`, `min_z=2.0`). |
| `feeds/mock_rfq.py` | Deterministic seeded world: spot GBM; funding APR as OU around a regime-dependent mean; noisy 8h funding prints; a desk that prices forwards off a *slow* EWMA of observed funding + quote noise. `SYNTHETIC_MOCK` price source everywhere (I-1 honesty). |
| `strategies/*` | `Strategy.scan(ctx, size, tenor) → [Opportunity]`. Implemented: `ForwardBasisStrategy` (Route B). Planned: funding-arb port, spot/perp basis — same interface. |
| `risk/caps.py` | `check(opp, open_count, caps) → (ok, reasons[])` — every reject is enumerated and journaled. Research placeholders until W0 returns real desk terms. |
| `positions.py` | `PaperPosition`: OPEN → SETTLED. Settle computes per-leg **signed** PnL `(exit − entry) × qty × direction` (I-3), verifies exit ts > entry ts (I-5), and returns the ex-ante vs realized comparison payload. |
| `pipeline.py` | The run loop: advance day → settle matured → (every N days) journal quotes → scan → risk-gate → open. Summary enforces the unit rule (aggregate Σ% vs mean per position) and the epistemic note. The settle payload's `research_compare` carries, since v0.2.0, the ex-ante estimator state (`ex_ante_apr`, `ex_ante_sigma_apr`) next to the realized comparison — added keys only, backwards-compatible. |
| `research/stats.py` | Pure-stdlib distribution helpers (`mean`, sample std, numpy-style linear percentiles, `dist_obj`). Machinery diagnostics on a synthetic world — never market evidence. |

## Data flow (forward basis, current)

```
mock CEX funding prints ──► EWMA (apr, σ) ──┐
                                             ├─► gap z-score ──► gate z ≥ 2
desk forward RFQ quote ──► implied APR ─────┘
                                             │
spot RFQ + fwd RFQ ──► ALL-IN EDGE waterfall ──► gate net ≥ 10bps
                                             │
                       risk caps (notional/tenor/open-count) ──► open paper position
                                             │
                       settle at expiry: signed PnL per leg + research compare
                       (locked premium vs realized funding path vs perp alternative)
```

## The synthetic regime (why the demo shows what it shows)

`_uptrend_then_flat`: funding APR mean ramps 8% → 18% between day 30 and 120,
then flat. The desk's slow (30-day half-life) pricing lags the ramp → the gap
opens (z ≥ 2, net edge viable) → gated entries. In the flat regime the desk
catches up → gap closes → rejections. Sample run (seed 7, 200 days, 90d tenor):
152 quotes → 16 gated opportunities → 10 risk rejects (open-position cap) →
6 opened → 3 settled (+$7,878 synthetic) with realized ≈ locked premium minus
exit spread, which is exactly what a dated forward must do.

**The synthetic numbers validate the machinery, not any market.** Changing the
seed changes the numbers; the invariants do not change.

## Extension points (in order of arrival)

1. **W1 real feed** — `WintermuteFeed` (or a journal-replayer of W1 RFQ quotes)
   implementing `funding_obs / spot_quotes / forward_quote` with
   `PriceSource.DESK_RFQ_QUOTE`. Strategy code unchanged. **Unchanged by
   v0.2.0** — the research layer reads journals only; a real feed still
   implements the same feed surface and swaps in behind the existing
   interface.
2. **Funding-arb port** — the locked system's scanner semantics become a
   second `Strategy` emitting the same `Opportunity` shape; its venue
   tickers/funding map onto `Price`/`FundingObservation` with honest sources.
3. **Research layer** — **EXISTS (v0.2.0)**: `scripts/research_sweep.py`
   runs the deterministic pipeline across seeds 1..40 (one invariant-enforced
   journal per seed under `research/artifacts/sweep_runs/`) and overwrites
   two stable artifacts — `research/artifacts/run-latest.json`
   (representative seed, full detail) and
   `research/artifacts/sweep-latest.json` (pooled machinery-validation
   stats: realized-vs-locked, z-gate calibration, gate fire rate, reject
   census, per-seed rows). The tower dashboard consumes both **read-only**;
   they are derived summaries, not journal-managed records — the journals
   stay the source of truth. Next in this lane: carry curves, gap
   persistence, quote-cost distributions, opportunity ranking.
4. **Execution abstraction** — RFQ lifecycle state machine (quote → accept →
   fill → settle) with fail-closed transitions, patterned on phase3-lab's
   certified separation (only after W2/W3 decisions).

## Non-goals (binding until a recorded decision changes them)

live trading · NODE auto-trading · real capital · FIX production execution ·
ML deciding about money · portfolio allocator · complex strategies without data.
