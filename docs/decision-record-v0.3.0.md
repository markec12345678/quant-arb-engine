# Decision Record — v0.3.0 «Instrument choice & honest horizon σ»

Date: 2026-09-11 (session 3) · Engine version 0.2.0 → 0.3.0
Status: BINDING before any v0.3.0 run is executed (pre-registration discipline).

## Why v0.3.0 exists — the two honest findings of v0.2.0

1. **z-gate calibration is broken as a horizon statement.** The sweep measured
   98.7 % empirical breach vs 4.55 % nominal (74/75). Cause, diagnosed and
   reported as-is in v0.2.0: `sigma_apr` from `ewma_funding` is the *instantaneous*
   standard error of the level estimate (std/√eff_n). It never pretended to
   measure the uncertainty of the *mean funding over a 90-day held window* — but
   the calibration diagnostic (and any reader) treated it that way. An honest
   engine cannot ship a σ whose meaning changes depending on who reads it.
2. **The world was one-sided, so the instrument question never existed.**
   `locked_minus_perp_alt_apr_bps = −613.6` mean: the dated forward ALWAYS
   underperformed the floating perp alternative, because the synthetic regime
   only ramps carry up (8 % → 18 %) — the desk lags, realized leads, and the
   floating side always wins. A basis-lock strategy can only show its value
   when carry can COLLAPSE. That regime was absent by construction.

Both findings are machinery diagnostics on synthetic data (EPISTEMIC NOTE
applies verbatim). They motivate changes to the synthetic world and the
strategy layer — never to the epistemic rules, the journal invariants, or the
NO-GO list.

## Changes (pre-registered)

### C1 — World v2: carry build-up AND carry collapse
`mean_fn` becomes: ramp 8 % → 18 % over days 30–120 (unchanged), flat to day
150, **decay 18 % → 4 % over days 150–180, flat 4 % to day 200**.
Rationale: the instrument-choice question («lock the premium via a dated
forward» vs «float the realized funding via a short perp») is two-sided only
when carry can fall hard enough, late enough, that a 30-day-lagging desk is
still pricing stale-high premiums. This is also the realistic scenario Route B
hedges against. Consequence, accepted up front: **v0.1/v0.2 numeric baselines
are not reproducible under world v2** — they remain frozen in git history
(commit 578effa) and in the archived artifacts of that commit. No old artifact
is silently re-labelled; every v0.3.0 artifact states `engine_version: 0.3.0`.

### C2 — Horizon σ estimator (new, honest, deterministic)
`horizon_sigma_apr(obs, horizon_days)`:
- aggregate observed funding prints to daily mean APRs (only data the strategy
  can see — print-level noise included, generator parameters never read);
- window length L = min(H, max(2, n_days // 2));
- σ_L = population std of ALL overlapping L-day window means (step 1 day);
- σ_H = σ_L · sqrt(H / L) (iid-block scaling, documented approximation);
- no RNG anywhere — the estimator is a pure function of the observation
  history, so runs stay bit-for-bit reproducible.
Meaning, stated once and enforced by naming: **σ_level = uncertainty of "what
funding is paying now"; σ_H = empirical dispersion of "mean funding over an
H-day window"**. The z-gate calibration diagnostic is redefined to use σ_H
(the old σ_level calibration stays in the artifact as a second, clearly named
panel so the fix is auditable, not asserted).

### C3 — Second strategy family: `perp_carry_v1` (the benchmark becomes a strategy)
Same trade shape as the forward family — long spot @ desk ask — but the carry
leg is a SHORT CEX PERP (synthetic `SYN-PERP` on `SYNTH_CEX`): floating
realized funding, no premium lock. CEX cost model differs from RFQ by design
and is counted as EXPLICIT waterfall lines (taker fee + half-spread on entry
and exit), mirroring the real CEX-vs-OTC distinction (I-4 stays intact: RFQ
fees remain embedded in the quoted price; CEX fees are explicit line items —
never both for the same leg).
Ex-ante carry = EWMA APR (σ_level estimator, unchanged) over the tenor; the
carry-uncertainty buffer uses **σ_H** (funding floats → horizon risk is real).
Funding accrual at settle = Σ printed per-interval rates over the held window
× qty × entry reference mid (the audited "% of trade notional" convention,
documented as an approximation in the settle payload).

### C4 — Gate structure change (recorded decision, constants unchanged)
- `forward_basis_v1`: the old level z-gate (realized vs implied) is RETIRED as
  a gate and retained as a journaled diagnostic (`signal_z_level`). The family
  gates on the pre-registered net-edge gate only. Rationale: the dated forward
  locks its carry at inception — persistence of the funding level is not
  required for the lock to be what it is; the level z actually measures
  "the floating alternative looks better", which is the RANKING's job now,
  not this family's gate.
- `perp_carry_v1`: gates on net-edge AND `z_perp = E[y] / σ_H ≥ min_z` — the
  floating carry over the horizon must be statistically distinguishable from
  zero. Symmetric in spirit to the forward's cost-survival gate.
- Constants unchanged: `min_z = 2.0`, `min_net_edge_bps = 10.0`,
  `carry_uncertainty_k = 1.0`, `exit_cost_bps = 8.0`, `slippage_buffer_bps = 3.0`,
  `execution_risk_buffer_bps = 5.0`. New placeholders: `perp_taker_fee_bps = 5.0`,
  `perp_half_spread_bps = 1.0` (CEX cost model, research estimates).

### C5 — Ranking layer (the universal opportunity model earns its name)
Every quote day, BOTH families are evaluated ex-ante and journaled
(`family_eval`: gates, gross/net edge, σ_level, σ_H, selected, executed — even
when gated out: full decision audit, nothing silently dropped). Execution rule:
**among gated-in families, execute the one with the higher net executable edge;
tie → forward (locked carry preferred at equal net, pre-registered)**. Risk
caps apply after ranking, unchanged (global open-position cap 5, single book).

### C6 — Journal schema additions (invariant-first)
- `family_eval` (per family per quote day): requires strategy_id, gated bool,
  gates dict, net_executable_edge_bps, sigma_level_apr, sigma_horizon_apr,
  selected bool — a violation raises before anything is written.
- `funding_daily` (per day): {day, apr_printed, n_prints} — the observation
  stream the strategies actually see, so the research layer can re-derive
  window-realized carry from the journal alone (journal = source of truth).
- `position_settled` gains an optional signed `funding_accrual_usd` (required
  for `perp_carry_v1` settles, forbidden unsigned variants per I-3).
Research metrics re-defined on journals only: **ranking hit-rate** (on quote
days where BOTH families gated in — a genuine contest — did the selected
family's ex-post carry beat the forgone family's, using funding_daily window
means vs the locked premium), plus per-family settled distributions and the
dual z-calibration panels. Truncated contests (window crosses the run end) are
excluded and counted, never silently dropped.

## Explicitly NOT changing
- The NO-GO list (no live trading, no NODE auto-trading, no real capital, no
  FIX production, no ML money decisions, no portfolio allocator).
- Journal invariants I-1…I-6 and write-time enforcement.
- The canonical epistemic note and the unit rule (they travel with every
  summary and every artifact).
- funding-arb@0373f5d (untouched; the tower stays a read-only observer).
- W0/W1 ownership: real RFQ quotes still arrive only as a new feed class
  behind the same interface, after the user's W0 onboarding.

## Falsifiable predictions (written before running)
- P1: the horizon calibration breach rate drops far below the 98.7 % level
  reading; if it stays > 50 % the σ_H estimator is rejected in the artifact
  notes as still insufficient (reported either way, not tuned).
- P2: the ranking layer selects the perp family predominantly during the
  up-ramp and the forward family after the collapse begins (stale-high desk
  premiums); if it does not, the lag model is weaker than believed.
- P3: contested days (both families gated in) are a minority of quote days;
  the hit-rate on them is the first genuine multi-strategy result of the engine.
