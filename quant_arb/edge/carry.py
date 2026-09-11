"""Implied-carry math — the Route B kernel.

CEX funding observations → realized-funding APR estimate (+ estimator σ)
forward quote → forward-implied APR
gap z-score = (realized − implied) / √(σ_realized² + σ_implied²)

Hour-normalization happens inside FundingObservation; every function here is
interval-agnostic by construction (NEW-19 discipline).

v0.3.0 — two sigmas with two MEANINGS (decision record C2):
- ``ewma_funding``  → σ_level: uncertainty of "what funding is paying NOW"
  (standard error of the weighted level estimate);
- ``horizon_sigma_apr`` → σ_H: empirical dispersion of "mean funding over an
  H-day window", estimated from overlapping historical window means. The
  v0.2.0 calibration finding (98.7 % breach vs 4.55 % nominal) was exactly the
  confusion of the two; they are now separate, named, and journaled apart.

v0.4.0 — σ_H round 2 (decision record docs/decision-record-v0.4.0.md):
- ``horizon_sigma_trend_apr`` → σ_H v2 = trend-aware horizon σ:
  dispersion (the v0.3 value, kept verbatim as the audit component) PLUS the
  trend-continuation exposure |β̂|·H/2. The v0.3 value alone measured 35.0 %
  breach vs the 4.55 % nominal — the residual was trend drift, which no
  stationary-mean estimator (HAC measured 73.2 %, REJECTED) captures. One σ,
  one meaning: the z_perp gate, the carry buffer and the journal all carry
  the same trend-aware number; the v0.3 component is journaled next to it.
"""

from __future__ import annotations

import math
import statistics
from typing import List, Sequence, Tuple

from ..models.market_data import FundingObservation


def daily_printed_aprs(obs: Sequence[FundingObservation]) -> List[Tuple[int, float]]:
    """Aggregate observed funding prints to daily mean APRs.

    Only what a strategy can see: print-level observation noise included,
    generator parameters never read. Returns [(day_index, apr), ...] sorted,
    day_index counted from the first observation day (day 1 = first day with
    at least one print).
    """
    if not obs:
        return []
    t0 = obs[0].ts
    day_ms = 86_400_000
    buckets: dict[int, List[float]] = {}
    for o in obs:
        day = (o.ts - t0) // day_ms + 1
        buckets.setdefault(day, []).append(o.rate_hourly)
    out = []
    for day in sorted(buckets):
        rates = buckets[day]
        apr = sum(rates) / len(rates) * 24.0 * 365.0
        out.append((day, apr))
    return out


def horizon_sigma_apr(obs: Sequence[FundingObservation], horizon_days: float) -> Tuple[float, dict]:
    """σ of the mean funding APR over an H-day window, from history alone.

    Estimator (decision record C2 — deterministic, no RNG):
    1. daily mean APRs from the observation stream (print noise included);
    2. window length L = min(H, max(2, n_days // 2));
    3. σ_L = population std over ALL overlapping L-day window means (step 1);
    4. σ_H = σ_L · sqrt(H / L)   (iid-block scaling — a documented
       approximation, honest about being one).

    Returns (sigma_apr, diagnostics) — diagnostics journaled with every use so
    the approximation is auditable, never asserted.
    """
    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    dailies = daily_printed_aprs(obs)
    n = len(dailies)
    if n < 2:
        return 0.0, {"method": "insufficient_history", "n_days": n,
                     "window_days": 0, "n_windows": 0, "scale_sqrt": 1.0}
    L = min(int(horizon_days), max(2, n // 2))
    vals = [apr for _, apr in dailies]
    windows = [sum(vals[i:i + L]) / L for i in range(0, n - L + 1)]
    n_windows = len(windows)
    sigma_L = statistics.pstdev(windows) if n_windows > 1 else 0.0
    scale = math.sqrt(horizon_days / L) if L > 0 else 1.0
    sigma_H = sigma_L * scale
    return sigma_H, {
        "method": "overlapping_window_means_iid_scaled",
        "n_days": n,
        "window_days": L,
        "n_windows": n_windows,
        "scale_sqrt": round(scale, 4),
    }


def horizon_sigma_trend_apr(
    obs: Sequence[FundingObservation], horizon_days: float,
    trend_window_days: int = 60,
) -> Tuple[float, dict]:
    """σ_H v2 — trend-aware horizon σ (decision record v0.4.0 C1).

    The honest ex-ante uncertainty of "mean funding APR over the next H days
    around the current level estimate":

        σ_A = v0.3 overlapping-window iid-block value   (audit component, kept)
        β̂   = OLS slope of daily printed APRs over the last min(n, M) days
        σ_H = sqrt( σ_A² + (|β̂| · H / 2)² )

    Interpretation of the trend term: how far a CONTINUING local trend moves
    the future window mean away from today's level — the exact quantity the
    v0.3 calibration residual was made of (ramp drift), and the quantity a
    stationary-mean estimator (HAC) averages away. Deterministic, no RNG;
    backward-looking only (generator parameters never read).

    Fail-closed: fewer than 3 daily observations, or a degenerate zero σ_H →
    returns 0.0 so the perp z-gate FAILS (persistence unproven), same
    semantics as v0.3.0. Returns (sigma_apr, diagnostics); diagnostics are
    journaled with every use so the upgrade is auditable, never asserted.
    """
    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    if trend_window_days < 3:
        raise ValueError("trend_window_days must be >= 3")

    sigma_iid, diag_iid = horizon_sigma_apr(obs, horizon_days)
    dailies = daily_printed_aprs(obs)
    n = len(dailies)
    if n < 3 or sigma_iid <= 0:
        return 0.0, {"method": "insufficient_history", "n_days": n,
                     "trend_window_days": 0, "sigma_iid_block": round(sigma_iid, 6),
                     "beta_hat_apr_per_day": 0.0, "trend_term_apr": 0.0}

    m = min(n, int(trend_window_days))
    y = [apr for _, apr in dailies[-m:]]
    x = list(range(m))
    mx = sum(x) / m
    my = sum(y) / m
    num = sum((x[i] - mx) * (y[i] - my) for i in range(m))
    den = sum((x[i] - mx) ** 2 for i in range(m))
    beta = num / den if den > 0 else 0.0          # APR per day, signed
    trend_term = abs(beta) * horizon_days / 2.0   # exposure is two-sided
    sigma_h = math.hypot(sigma_iid, trend_term)
    if sigma_h <= 0:
        return 0.0, {"method": "degenerate_zero", "n_days": n,
                     "trend_window_days": m, "sigma_iid_block": round(sigma_iid, 6),
                     "beta_hat_apr_per_day": 0.0, "trend_term_apr": 0.0}
    return sigma_h, {
        "method": "iid_block_plus_trend_continuation",
        "n_days": n,
        "trend_window_days": m,
        "sigma_iid_block": round(sigma_iid, 6),
        "beta_hat_apr_per_day": round(beta, 8),
        "trend_term_apr": round(trend_term, 6),
        "iid_block_diag": diag_iid,
    }


def ewma_funding(obs: Sequence[FundingObservation], half_life_h: float = 72.0) -> Tuple[float, float]:
    """EWMA estimate of the funding APR and the σ of the *estimate*.

    Returns (apr_est, sigma_apr_est). The σ is the standard error of the
    weighted mean (std / √effective_sample_size) — the statistically honest
    uncertainty of "what funding is paying right now", not the vol of funding
    itself.
    """
    if not obs:
        raise ValueError("no funding observations")
    if half_life_h <= 0:
        raise ValueError("half_life_h must be positive")
    ref_ts = obs[-1].ts
    weights: list[float] = []
    rates: list[float] = []
    for o in obs:
        age_h = max(0.0, (ref_ts - o.ts) / 3.6e6)
        weights.append(0.5 ** (age_h / half_life_h))
        rates.append(o.rate_hourly)
    wsum = sum(weights)
    est_h = sum(w * r for w, r in zip(weights, rates)) / wsum
    var_h = sum(w * (r - est_h) ** 2 for w, r in zip(weights, rates)) / wsum
    std_h = math.sqrt(max(var_h, 0.0))
    eff_n = (wsum * wsum) / sum(w * w for w in weights)
    sigma_est_h = std_h / math.sqrt(max(eff_n, 1.0))
    h_to_apr = 24.0 * 365.0
    return est_h * h_to_apr, sigma_est_h * h_to_apr


def forward_implied_apr(spot: float, forward: float, tenor_days: float) -> float:
    """Annualized premium implied by a forward price vs spot."""
    if spot <= 0 or forward <= 0 or tenor_days <= 0:
        raise ValueError("spot, forward and tenor must be positive")
    return (forward / spot - 1.0) * 365.0 / tenor_days


def carry_gap_z(realized_apr: float, realized_sigma_apr: float, implied_apr: float,
                implied_sigma_apr: float = 0.0) -> float:
    """Persistence signal: realized funding vs the carry the desk is pricing in."""
    total_sigma = math.hypot(realized_sigma_apr, implied_sigma_apr)
    if total_sigma <= 0:
        raise ValueError("zero total sigma — gap z is undefined")
    return (realized_apr - implied_apr) / total_sigma
