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
| `edge/carry.py` | **Three sigmas, one gate (v0.5)**: `ewma_funding(obs, h) → (apr, σ_level)` — estimator standard error (std/√eff_n), the uncertainty of "what funding pays NOW"; `horizon_sigma_apr(obs, H) → (σ_A, diag)` — empirical dispersion of H-day window means (daily print aggregation → overlapping L-day windows → iid-block scaling; deterministic, no RNG; diagnostics journaled with every use); `horizon_sigma_trend_apr(obs, H, M=60) → (σ_twosided, diag)` — v0.4: √(σ_A² + (|β̂|·H/2)²), kept verbatim as the audit component; `horizon_sigma_downside_apr(obs, H, M=60) → (σ_down, diag)` — **v0.5 gate σ: √(σ_A² + (max(0,−β̂)·H/2)²)** — the FALLING visible trend charged in full (identical to v0.4's charge), a rising trend charged zero trend exposure (reversal priced at zero: the optimistic bound of the reversal-ignorance interval, per the decision record's estimand argument); the v0.4 two-sided and v0.3 iid values journaled next to it as audit components; fail-closed under 3 days or degenerate zero. Also `forward_implied_apr`, `carry_gap_z`, `daily_printed_aprs`. |
| `edge/all_in_edge.py` | The waterfall: `gross − entry − exit − slippage − carry_uncertainty − execution_risk = net_executable_edge`. Each line explicit and journaled. Two evaluators: `evaluate_forward_basis` (carry buffer from σ_level — carry is locked, only benchmark/early-exit risk) and `evaluate_perp_carry` (carry buffer from σ_H — funding floats, horizon risk is real; entry adds EXPLICIT CEX lines: taker fee + half-spread). `EdgeParams` holds the **pre-registered gates** (`min_net_edge_bps=10`, `min_z=2.0`, `perp_taker_fee_bps=5`, `perp_half_spread_bps=1`). |
| `feeds/mock_rfq.py` | Deterministic seeded **world v2**: spot GBM; funding APR as OU around a regime mean that ramps 8 % → 18 % (days 30–120), holds, then COLLAPSES 18 % → 4 % (days 150–180); noisy 8h funding prints; a desk that prices forwards off a *slow* EWMA of observed funding + quote noise; `perp_mark()` (PERP_MARK source) and `printed_funding_between(ts_from, ts_to)` for accrual. `SYNTHETIC_MOCK` price source everywhere (I-1 honesty). |
| `strategies/*` | `Strategy.evaluate(ctx, size, tenor) → FamilyEvaluation` (gates, edges, BOTH sigmas, signal_z, detail — journaled for every family every quote day) + `scan(...) → [Opportunity]`. Implemented: `ForwardBasisStrategy` (Route B, lock carry; net-edge gate, level z kept as diagnostic; journals σ_down as diagnostic only — its gate structure is untouched) and `PerpCarryStrategy` (float carry; net-edge gate AND horizon persistence z_perp = E/σ_down ≥ min_z — a downside persistence ratio since v0.5 — fail-closed when σ_down = 0). Planned: funding-arb port — same interface. |
| `risk/caps.py` | `check(opp, open_count, caps) → (ok, reasons[])` — every reject is enumerated and journaled. Research placeholders until W0 returns real desk terms. |
| `positions.py` | `PaperPosition`: OPEN → SETTLED. Settle computes per-leg **signed** PnL `(exit − entry) × qty × direction` (I-3) — forward legs at the settlement print, perp legs at the exit mark, spot at the desk bid — verifies exit ts > entry ts (I-5), adds the signed `funding_accrual_usd` (perp family: Σ printed rates × qty × entry ref mid, a documented approximation) and returns the ex-ante vs realized comparison payload. |
| `pipeline.py` | The run loop: advance day → journal `funding_daily` (the observation stream — source of truth for every research re-derivation) → settle matured → (every N days) journal quotes → **evaluate BOTH families → journal `family_eval` (with selection known) → ranking (higher net edge wins, tie → forward, pre-registered) → scan winner → risk-gate → open**. Summary enforces the unit rule (aggregate Σ % vs mean per position) and the epistemic note; `research_compare` carries the ex-ante estimator state (apr, σ_level, σ_down adverse-side + the v0.4 two-sided and v0.3 iid audit values). |
| `research/stats.py` | Pure-stdlib distribution helpers (`mean`, sample std, numpy-style linear percentiles, `dist_obj`). Machinery diagnostics on a synthetic world — never market evidence. |

## Data flow (two families + ranking, v0.5)

```
mock CEX funding prints ──► EWMA (apr, σ_level) ──┐
         │                                         ├─► level z (diagnostic only)
         └──► σ_down = √(σ_A² + (max(0,−β̂)H/2)²) ─┘
              (adverse-side; σ_A = v0.3 audit value, σ_twosided = v0.4 audit,
               both journaled next to the gate σ every use)

desk forward RFQ ──► implied APR ──► forward_basis_v1 ── net-edge gate
CEX perp mark ────────────────────► perp_carry_v1 ───── net-edge gate AND z_perp = E/σ_down ≥ 2
                                                   (carry buffer k·σ_down — adverse-side)
        BOTH families evaluated + journaled EVERY quote day (family_eval)
                   ↓
        RANKING: execute the higher net executable edge (tie → forward)
                   ↓
        risk caps (notional/tenor/open-count) ──► open paper position
                   ↓
        settle at expiry: signed PnL per leg (+ signed funding accrual for perp)
        research compare: locked premium vs realized funding path + ex-ante state
```

## The synthetic regime v2 (why the demo shows what it shows)

`_world_v2_regime`: funding APR mean ramps 8 % → 18 % between days 30–120,
flat to day 150, **collapses 18 % → 4 % over days 150–180**, flat 4 % after.
The desk's slow (30-day half-life) pricing lags both turns:

- during the build-up the desk under-prices carry → the floating perp family
  has the higher ex-post carry (the realized path beat the stale desk premium
  in v0.3, when the small iid σ_H let it win the ranking 60.2 % of contests).
  **v0.4 honest twist**: the trend-aware carry buffer deflates the perp's net
  executable edge, so the ranking flipped to the LOCKED forward on ~94 % of
  selected days — and the ex-post hit-rate fell to 11.4 % (P4 REFUTED, the
  round's headline: honest two-sided uncertainty pricing has a measured price
  in a world whose drift was upside for the floating side). **v0.5 resolution**:
  the adverse-side buffer charges only the FALLING trend, so the perp's net
  edge recovers during the ramp and the ranking returns to majority-correct
  (61.9 % like-for-like, P3 SUPPORTED) — the executed numbers landed on the
  pre-registered would-be re-ranking almost exactly;
- during/after the collapse the desk's stale-high premiums become the trade →
  the dated forward wins the ranking (68.9 % of collapse-phase contests
  like-for-like, P5 SUPPORTED — down from v0.4's 95.7 %: the β̂ regime-turn
  lag leaves the first ~10–15 collapse days uncharged, an honest price
  reported, not patched).

Sample run (seed 7, 200 days, 90d tenor): 152 quotes → 76 family evals →
33 contested → 38 selected → 26 risk rejects (open-position cap) → 12 opened
→ 7 settled (5 forward + 2 perp, +$15,986 synthetic) — and the calibration
panels pooled across 80 seeds (560 settled checks): σ_level 67.1 % (audit) ·
σ_H iid 33.8 % (audit) · σ_H two-sided 10.7 % (v0.4 audit) · **σ_down
adverse-side 0.0 % (v0.5 redefined; one-sided nominal 2.28 %)** · upside
surprise 19.8 % (the honest cost of the optimistic bound, NOT a calibration
target); holdout (61..80) Δ +0.0 pp.

**The synthetic numbers validate the machinery, not any market.** Changing the
seed changes the numbers; the invariants do not change.

## Extension points (in order of arrival)

1. **W1 real feed** — `WintermuteFeed` (or a journal-replayer of W1 RFQ quotes)
   implementing `funding_obs / spot_quotes / forward_quote / perp_mark` with
   `PriceSource.DESK_RFQ_QUOTE`. Strategy code unchanged. **Unchanged by
   v0.3.0** — the research layer reads journals only; a real feed still
   implements the same feed surface and swaps in behind the existing
   interface.
2. **Funding-arb port** — the locked system's scanner semantics become a
   third `Strategy` emitting the same `Opportunity` shape; its venue
   tickers/funding map onto `Price`/`FundingObservation` with honest sources.
3. **Research layer** — **EXISTS (v0.2.0 → v0.4.0)**: `scripts/research_sweep.py`
   runs the deterministic pipeline across seeds 1..40 (one invariant-enforced
   journal per seed under `research/artifacts/sweep_runs/`) and overwrites
   two stable artifacts — `run-latest.json` (representative seed: summary,
   settled rows, opportunity example, carry curve, family edge series) and
   `sweep-latest.json` (totals, family census, ranking hit-rate, dual
   z-gate calibration panels, scored predictions P1/P2/P3, reject census,
   per-seed rows). The tower dashboard consumes both **read-only**; they are
   derived summaries, not journal-managed records — the journals stay the
   source of truth. Next in this lane: quote-cost distributions, ranking
   features beyond net edge (σ-adjusted), W1 feed replay.
4. **Execution abstraction** — RFQ lifecycle state machine (quote → accept →
   fill → settle) with fail-closed transitions, patterned on phase3-lab's
   certified separation (only after W2/W3 decisions).

## Non-goals (binding until a recorded decision changes them)

live trading · NODE auto-trading · real capital · FIX production execution ·
ML deciding about money · portfolio allocator · complex strategies without data.
