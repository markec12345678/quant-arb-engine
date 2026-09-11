# Decision Record — v0.5.0 «Asymmetric carry buffer (adverse-side horizon σ)»

Date: 2026-09-11 (session 5) · Engine version 0.4.0 → 0.5.0
Status: BINDING before any v0.5.0 run is executed (pre-registration discipline).
Sealed by the commit that first adds this file to the repository — that commit
predates every v0.5.0-configured pipeline run (the sweep journals are tracked
in git, so the ordering is auditable from history alone).

## Why v0.5.0 exists — the measured question left by v0.4.0

v0.4.0's P4 was REFUTED as measured: the ranking hit-rate fell 60.2 % → 11.4 %
(seeds 1–40, like-for-like) because the two-sided trend term |β̂|·H/2 charges
the floating family for BOTH trend directions, while the PnL geometry of a
long-carry position is one-sided: a CONTINUING RISING trend adds carry. The
v0.4 record closed with the recorded v0.5 question — downside semi-deviation
for a long-carry position. This round asks exactly that question and no other.

## The estimand argument (stated before any v0.5 number)

For a long-carry position (long spot + short perp), the PnL error is
`window_mean_apr − ex_ante_apr`. Under a visible trend β̂:

- **β̂ < 0 (falling):** trend continuation IS the adverse central case — the
  window mean sits ≈ ex_ante − |β̂|·H/2 below the estimate. Charged in full,
  exactly as v0.4 charged it.
- **β̂ > 0 (rising):** the error under continuation is ≈ +|β̂|·H/2 (upside —
  MORE carry); under trend death ≈ 0 (the EWMA lag puts a small positive
  floor under it); only a full REGIME REVERSAL produces a downside of
  magnitude ≈ |β̂|·H/2. The probability of that reversal is **unknowable from
  backward-looking data** (the world's regime turns are ~2 per 200 days and
  their timing carries no visible precursor).

So the trend charge lives on an ignorance interval for the reversal weight:
**v0.4 priced the pessimistic bound** (reversal weighted like continuation —
the full |β̂|·H/2 charged against the edge on every day, rising or falling);
**v0.5 prices the optimistic bound** (reversal weighted at zero — a falling
trend still charged in full, a rising trend uncharged). No interior weight is
chosen: any value strictly between 0 and 1 is an ungrounded tuning knob —
precisely the estimator fishing the v0.4 STOP RULE forbids. The empirical
honesty check on the side that can hurt the book is the one-sided DOWNSIDE
calibration panel (P1); the cost of the optimistic bound is measured and
reported (P4, P5), never patched.

## Disclosed exploration (performed BEFORE this record was sealed)

`research/exploration/screen_asym_v05.py`, run on the FROZEN v0.4 journals
(commit 2b12b34, seeds 1–60, 420 settled positions; the script ships with the
repo so the exploration is auditable). In-sample on the same generator — a
disclosed limitation, mitigated by the holdout design in C4. The re-derivation
cross-check matches the journaled v0.4 σ to 0.0002 pp (the screening is exact
up to journal rounding).

| Candidate | Estimand | Two-sided breach | Downside breach | Upside surprise | Mean σ |
|---|---|---|---|---|---|
| S — v0.4 symmetric `\|β̂\|·H/2` | both trend directions charged | **11.0 %** (46/0 pos/neg) | — | — | 4.81 pp |
| G1 — adverse-side `max(0, −β̂)·H/2` | falling trend charged in full; rising uncharged | — | **0.0 %** (nominal 2.28 %) | **21.2 %** | 3.23 pp |

Would-be re-ranking under G1, re-ranked exactly from the journaled per-day
state (σ_iid, β̂, waterfall buffer, net edge, expected APR; the forward family
untouched): contested 1966 · selection flips vs v0.4: 1121 · hit-rate
**62.8 % pooled / 61.9 % seeds 1–40** (v0.4 measured 11.4 %; v0.3 baseline
60.2 %) · day-bucket split: window-avoids-collapse 32.0 % vs window-touches
87.8 % · collapse-phase forward share 69.7 % (v0.4: 95.7 %) · implied z-gate
pass 86.2 % (v0.4: 83.4 %), collapse-phase gated-in 66.0 %.

Three findings recorded in their own right:
1. **All 46 v0.4 residual breaches are positive-direction.** In 420 settles
   the two-sided trend band was never breached on the DOWNSIDE: on this
   population the symmetric term's protective work was pure upside
   over-pricing — the measured anatomy of the P4 refutation.
2. **The recovery concentrates where the world's geometry puts it.** From
   mid-ramp on, the desk's 30-day-lag implied APR sits far below the realized
   window mean (even for windows that touch the collapse, the flat-high
   plateau dominates), so restored perp selections win ex-post.
3. **The honest price, measured twice.** (a) Early-flat contests (days 25–40)
   still select the forward on net edge — legitimately: at day 25 the ramp is
   unforeseeable, and the perp's σ_A buffer is genuine dispersion risk — and
   lose ex-post when the ramp lifts the floating side: the irreducible
   information limit, 32.0 % in the avoids bucket. (b) The early-collapse
   transition leak: β̂ stays positive for ~10–15 days after the regime turn
   (the preceding ramp still dominates the 60-day window), so G1 leaves those
   days uncharged and the perp can win them (collapse forward share
   95.7 % → 69.7 %). v0.4's symmetric charge deflected exactly those days —
   right for the wrong reason: it charged a RISING trend's magnitude while
   the world fell.

## Changes (pre-registered)

### C1 — σ_H v3: adverse-side horizon σ (the ONE estimator change)
`horizon_sigma_downside_apr(obs, horizon_days, trend_window_days=60)`:

```
σ_A     = v0.3 overlapping-window iid-block value   (audit component, kept verbatim)
β̂       = OLS slope of daily printed APRs over the last min(n, 60) days   (identical to v0.4)
adverse = max(0, −β̂) · H / 2                        (falling trend: full charge)
σ_down  = sqrt( σ_A² + adverse² )
```

- **Meaning, stated once**: σ_down is the adverse-direction (PnL-negative for
  a long-carry holder) uncertainty of "mean funding APR over the next H days
  around the current level estimate" — dispersion risk (σ_A, which hurts the
  downside in full) plus adverse trend continuation. A falling visible trend
  is charged exactly what v0.4 charged it; a rising visible trend is charged
  zero trend exposure (reversal priced at zero — the optimistic bound of the
  reversal-ignorance interval, per the estimand argument above). Deterministic,
  backward-looking only, no RNG.
- `trend_window_days = 60` pre-registered — carried over from v0.4 unchanged,
  not re-tuned. Fail-closed semantics unchanged: fewer than 3 daily
  observations, or σ_down = 0 → the perp z-gate FAILS (persistence unproven).
- **ONE σ, ONE meaning, EVERYWHERE**: the z_perp gate (now a downside
  persistence ratio — expected carry in units of adverse-side uncertainty),
  the carry buffer (k·σ_down), `family_eval.sigma_horizon_apr`, and the settle
  `research_compare.ex_ante_sigma_horizon_apr` all carry σ_down. The v0.4
  two-sided value and the v0.3 iid value are journaled NEXT TO IT as audit
  components — the upgrade is auditable, never asserted.
- The ex-ante carry ESTIMATE itself stays the level EWMA (a trend-projected
  mean would be a larger estimand change — explicitly not taken here).

### C2 — Journal additions (additive; no new record types; no invariant changes)
- `family_eval.detail` gains `sigma_horizon_twosided_apr` (the v0.4 audit
  value); `sigma_horizon_diag` gains `adverse_trend_term_apr` and
  `twosided_trend_term_apr` (method label updated). `sigma_horizon_iid_apr`
  (v0.3 audit) kept.
- `position_settled.research_compare` gains `ex_ante_sigma_horizon_twosided_apr`.
- `family_eval.sigma_horizon_apr` and `research_compare.ex_ante_sigma_horizon_apr`
  now carry the ADVERSE-SIDE value for BOTH families (forward journals it as a
  diagnostic only, as before — its gate structure is untouched).

### C3 — Gate and constant consequences (none changed by hand; all flow through C1)
Constants stay exactly as pre-registered (`min_z = 2.0`, `min_net_edge_bps =
10.0`, `k = 1.0`, exit 8.0, slip 3.0, exec 5.0, perp taker 5.0, perp
half-spread 1.0, trend_window 60). The MEASURED consequences of the smaller
rising-regime σ are accepted up front and reported as measured: the perp
z-gate binds less in rising/flat regimes (would-be z-pass 86.2 % vs v0.4's
83.4 %), perp carry buffers shrink there, perp selections recover, the settle
population becomes perp-heavy (risk caps: the book fills early), and
early-collapse transition days leak to the perp for ~10–15 days after a
regime turn until β̂ turns negative. No gate threshold is moved to compensate
— that would be moving goalposts after seeing the ball.

### C4 — Sweep & confirmation design (measurement otherwise IDENTICAL to v0.4)
- **Quadruple calibration panels** (same journal-only re-derivation):
  `panel_level` (v0.2 audit) · `panel_horizon_iid` (v0.3 audit) ·
  `panel_horizon_twosided` (v0.4 audit, two-sided breach) · `panel_horizon`
  (v0.5 redefined = adverse-side, **one-sided** breach:
  `window_mean − ex_ante < −z·σ_down`, nominal one-sided 2.28 %) — plus
  `panel_horizon_upside` (`window_mean − ex_ante > +z·σ_down`), reported as
  the honest cost and explicitly NOT a calibration target.
- **Entry-history decomposition** of the downside panel (≤45 vs >45 observed
  days at entry), as in v0.4.
- **Holdout ladder**: seeds 1–60 = screening set (the frozen v0.4 journals the
  candidate was screened on — disclosed in-sample); seeds **61–80 = holdout,
  never used in any decision in any engine version** (v0.4 used 1–40
  screening + 41–60 holdout; both are now decision-touched, so the ladder
  extends, it never re-rolls).
- **Ranking** reported pooled (1–80) AND screening (1–60) AND like-for-like
  (1–40 — the seed set the v0.3 60.2 % and v0.4 11.4 % baselines were measured
  on; used ONLY for the P3/P5 verdicts, never for a second headline).
- **Contest day-bucket decomposition** of the full-window hit-rate: window
  avoids collapse (d ≤ 60) vs window touches collapse (d > 60) — the boundary
  is `COLLAPSE_START(150) − tenor(90)`, derived from the pre-registered regime
  boundary, not tuned.
- **Estimator screening block** in the artifact: the exploration table above,
  verbatim, labeled in-sample-disclosed.
- Cross-version population note: v0.5 settle populations are perp-heavy and
  differ from v0.4's — the frozen v0.4 numbers live at 2b12b34 and are never
  silently re-labelled; each artifact states its engine_version.

### Explicitly NOT changing
World v2, both strategy families, the ranking rule (higher net edge, tie →
forward), risk caps, journal invariants I-1…I-6 and write-time enforcement,
the ex-ante carry estimate (level EWMA), the NO-GO list, the canonical
epistemic note and unit rule, funding-arb@0373f5d (untouched), W0/W1 ownership
(real RFQ feed only after the user's W0).

## Falsifiable predictions (written before any v0.5.0 run)

- **P1**: pooled downside-panel breach ≤ 8 % (one-sided nominal 2.28 %;
  disclosed would-be 0.0 % on the v0.4 settle population — the v0.5 population
  is perp-heavy and includes late-ramp opens whose windows touch the collapse,
  so headroom is kept at ≈ the same 3.3×-nominal margin v0.4 pre-registered).
- **P2**: holdout (seeds 61–80) downside-panel breach within ±6 pp of the
  screening set (1–60) — the estimator is not seed-idiosyncratic.
- **P3**: like-for-like (seeds 1–40) full-window contest hit-rate ≥ 50 %
  (v0.4: 11.4 %; v0.3: 60.2 %; would-be: 61.9 %) — recovery to a
  majority-correct ranking, claimed only at the majority bar.
- **P4** (the honest price, compound — both parts must hold): (a) hit-rate on
  window-avoids-collapse contests ≤ hit-rate on window-touches contests
  − 20 pp (the early-flat information limit concentrates the misses); AND
  (b) the upside surprise panel > 15 % (the un-charged favorable drift is
  visible as frequent positive surprises — the asymmetry mechanism's
  signature, reported, never patched).
- **P5**: forward share of contested selections in the collapse phase ≥ 60 %
  (v0.4: 95.7 %; would-be: 69.7 % — the transition leak is priced in; the
  claim is the signed charge still takes over after the β̂ lag, keeping the
  collapse majority-forward).

## STOP RULE (against weight fishing)

Exactly ONE estimator change is pre-registered (C1). Whatever the measured
outcomes, there are NO reversal-weight iterations, NO interior weights, NO
trend-window retuning inside v0.5.0. If P1 fails (> 8 % downside), the
recorded finding is: the optimistic bound under-protects the adverse side
even in a world whose reversals are rare and slow — and the answer for any
real market is not an interior weight chosen on synthetic data but W0's real
feed. If P3 fails, the recovery story is refuted as measured. The nominal is
a property of a correct σ on the stated side; the estimator is not a knob for
reaching it.
