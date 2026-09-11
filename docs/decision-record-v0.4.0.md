# Decision Record — v0.4.0 «Trend-aware horizon σ (round 2)»

Date: 2026-09-11 (session 4) · Engine version 0.3.0 → 0.4.0
Status: BINDING before any v0.4.0 run is executed (pre-registration discipline).

## Why v0.4.0 exists — the measured residual of v0.3.0

v0.3.0 separated σ_level from σ_H, named both, and reported the horizon
calibration honestly: **35.0 % empirical breach vs 4.55 % nominal** (280
checks), documented as "iid-block scaling underestimates autocorrelated regime
drift". This round asks the natural next question, and only this question:
**can a principled backward-looking estimator close the gap — and what part of
the gap is unestimable from history, no matter the estimator?**

## Disclosed exploration (performed BEFORE this record was sealed)

Candidate estimators were screened on the FROZEN v0.3 journals (commit
e250695, 40 seeds, 280 settled windows with full funding_daily history). The
screening script ships with the repo (`research/exploration/screen_sigma_v04.py`)
so the exploration itself is auditable. It is in-sample on the same generator —
a disclosed limitation, mitigated by the holdout design in C4.

| Candidate | Estimand | Breach | Mean σ | Verdict |
|---|---|---|---|---|
| A — v0.3 iid-block (`σ_L·√(H/L)`) | window-mean dispersion, extrapolated | 35.0 % | 1.74 pp | baseline (kept as audit value) |
| B — HAC / Newey–West Bartlett `√(LRV/H)` | variance of the mean of a STATIONARY process | **73.2 %** | 0.53 pp | **REJECTED** |
| C — local-level two-scale (window-mean increments) | stochastic-drift variance | 49.6 % | 1.90 pp | **REJECTED** |
| F — A + trend-continuation term | dispersion + trend exposure | **10.4 %** | 5.00 pp | **CHOSEN** |

Two findings worth recording in their own right:
1. **The textbook fix is measurably the wrong tool here.** HAC targets the
   variance of the sample mean of a stationary series. In a world whose funding
   level DRIFTS (ramp, collapse), the prediction error of "mean funding over
   the next H days vs the current level estimate" is dominated by the drift —
   a quantity HAC explicitly averages away. B measured WORSE than doing
   nothing (73.2 % vs 35.0 %). "Standard" ≠ "correct for this estimand".
2. **All 29 residual breaches under F are positive-direction** (realized carry
   above the ex-ante estimate — the EWMA lags the ramp), and **28/29 sit at
   entries made on days 20–40**, where the visible ramp is too short for ANY
   backward-looking slope measurement. The residual is early-history
   uncertainty, not estimator mis-specification. This motivates the stop rule
   below: pushing breach to the 4.55 % nominal with more estimator iterations
   would be overfitting the calibration metric, not honesty.

Phase decomposition of the v0.3 population: all 280 settled entries opened in
the ramp phase (risk caps fill the book early), so the "collapse break risk"
hypothesis is NOT what the 35 % was made of — it was trend drift all along.

## Changes (pre-registered)

### C1 — σ_H v2: trend-aware horizon σ (the ONE estimator change)
`horizon_sigma_trend_apr(obs, horizon_days, trend_window_days=60)`:

```
σ_A   = v0.3 overlapping-window iid-block value  (kept VERBATIM as the audit component)
β̂     = OLS slope of daily printed APRs over the last min(n_days, 60) days
σ_H   = sqrt( σ_A² + (|β̂| · H / 2)² )
```

- **Meaning, stated once**: σ_H is the honest ex-ante uncertainty of "mean
  funding APR over the next H days around the current level estimate" =
  dispersion risk (σ_A) + trend-continuation exposure (|β̂|·H/2 — how far a
  continuing local trend moves the window mean). Both terms deterministic,
  backward-looking only, no RNG (bit-for-bit reproducible runs preserved).
- `trend_window_days = 60` pre-registered; measured insensitive 30–90 on the
  screening set (breach 9.3–10.4 %, mean σ 4.8–5.5 pp) — not a tuned razor.
- Fail-closed semantics unchanged: fewer than 3 daily observations, or σ_H = 0
  → the perp z-gate FAILS (persistence unproven), exactly as in v0.3.0.
- ONE σ, ONE meaning, EVERYWHERE it appears: the z_perp gate, the carry
  buffer (k·σ_H), the family_eval journal field, and the settle
  research_compare all use the same trend-aware number. The v0.3 value σ_A
  is journaled NEXT TO IT as the audit component — the upgrade is auditable,
  never asserted.

### C2 — Journal additions (additive; no new record types, no invariant changes)
- `family_eval.detail` gains: `sigma_horizon_iid_apr` (the v0.3 audit value)
  and the trend diagnostics (`trend_window_days`, `beta_hat_apr_per_day`,
  `trend_term_apr`, `sigma_iid_block`).
- `position_settled.research_compare` gains: `ex_ante_sigma_horizon_iid_apr`.
- `family_eval.sigma_horizon_apr` (the validated numeric field) now carries the
  TREND-AWARE value for BOTH families (the forward family journals it as a
  diagnostic only, as before — its gate structure is untouched).

### C3 — Gate and constant consequences (none changed by hand; all flow through C1)
Constants stay exactly as pre-registered in v0.3.0 (`min_z = 2.0`,
`min_net_edge_bps = 10.0`, `k = 1.0`, exit 8.0, slip 3.0, exec 5.0, perp
taker 5.0, perp half-spread 1.0). The MEASURED consequences of a larger,
honest σ_H are accepted up front and reported as measured: the perp z-gate
binds harder (screening: z-pass at entry 96.8 % → 65.4 %), perp carry buffers
grow, perp selections shrink, and the collapse phase should gate the perp out
almost entirely (|β̂| large negative → trend term large). No gate threshold is
moved to compensate — that would be moving goalposts after seeing the ball.

### C4 — Sweep & confirmation design (measurement otherwise IDENTICAL to v0.3)
- **Triple calibration panels** (same formula as v0.3, journals only):
  `panel_level` (v0.2 audit, kept), `panel_horizon_iid` (v0.3 audit, kept),
  `panel_horizon` (v0.4 redefined = trend-aware).
- **Entry-history decomposition** of the trend panel: breaches at entries with
  n_days ≤ 45 vs > 45 — the "residual is early-history" claim becomes a
  measured artifact number, not a narrative.
- **Estimator screening block** in the artifact: the table above, verbatim,
  labeled in-sample-disclosed.
- **Holdout confirmation**: the sweep runs seeds 1–40 (screening set —
  comparability with v0.3) PLUS seeds 41–60 (holdout, never used in any
  decision). Panels and ranking are reported pooled AND holdout-only.
- Cross-version comparability note: v0.4 settle populations differ from v0.3
  (perp opens become rarer) — the frozen v0.3 numbers live at e250695 and are
  never silently re-labelled; each artifact states its engine_version.

### Explicitly NOT changing
World v2, both strategy families, the ranking rule (higher net edge, tie →
forward), risk caps, journal invariants I-1…I-6 and write-time enforcement,
the NO-GO list, the canonical epistemic note and unit rule,
funding-arb@0373f5d (untouched), W0/W1 ownership (real RFQ feed only after
the user's W0).

## Falsifiable predictions (written before any v0.4.0 run)

- **P1**: pooled trend-panel breach ≤ 15 % (v0.3: 35.0 %; screening: 10.4 %).
  If above 15 %, the trend term is rejected in the artifact notes as
  insufficient — reported either way, not tuned.
- **P2**: holdout (seeds 41–60) trend-panel breach within ±6 pp of the
  screening-set (1–40) breach — the estimator is not seed-idiosyncratic.
- **P3**: perp gated-in share of family evals ≤ 75 % (v0.3: 99.4 %) — the
  honest σ makes the persistence gate materially binding.
- **P4**: ranking hit-rate within ±5 pp of 60.2 % (measured on full-window
  contests; the contest set shrinks by design — that is P3's consequence, not
  a failure).
- **P5**: forward share of contested selections in the collapse phase ≥ 70 %
  (v0.3: 79.5 %) — phase behaviour preserved or sharpened.

## STOP RULE (against estimator fishing)

Exactly ONE estimator change is pre-registered (C1). Whatever the measured
breach, there are NO further σ estimator iterations inside v0.4.0. If the
pooled breach stays > 15 % or the holdout diverges > 6 pp, the recorded
finding is: backward-looking history cannot reach the nominal calibration in
a drifting-regime world, and the honest path forward is decision-time
empirical calibration factors (a v0.5 pre-registration question), never more
estimator tuning until the number looks good. The nominal is a property of a
CORRECT σ; the estimator is not a knob for reaching the nominal.
