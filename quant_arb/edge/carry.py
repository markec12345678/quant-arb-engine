"""Implied-carry math — the Route B kernel.

CEX funding observations → realized-funding APR estimate (+ estimator σ)
forward quote → forward-implied APR
gap z-score = (realized − implied) / √(σ_realized² + σ_implied²)

Hour-normalization happens inside FundingObservation; every function here is
interval-agnostic by construction (NEW-19 discipline).
"""

from __future__ import annotations

import math
from typing import Sequence, Tuple

from ..models.market_data import FundingObservation


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
