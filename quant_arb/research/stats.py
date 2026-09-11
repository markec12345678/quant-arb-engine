"""Pure-stdlib distribution helpers for the research sweep.

Every function here summarizes research-run distributions. They are
MACHINERY DIAGNOSTICS on a synthetic world: they describe how the engine's
code paths behave on deterministic mock data. They are never market
evidence and never proof of an edge.

Design choices (documented once, applied everywhere):

- **Sample vs population std**: ``pstdev_or_sample`` returns the *sample*
  standard deviation (``statistics.stdev``, n−1 denominator) for n > 1. The
  sweep pools small numbers of settled positions, where the sample estimator
  is the conservative (wider) choice; for n ≤ 1 there is no dispersion to
  estimate, so it returns 0.0. Despite the historical name, population std
  is NOT used for n > 1.
- **Percentiles**: ``percentile_linear`` implements the numpy "linear"
  interpolation method — ``rank = q/100 · (n−1)`` over the sorted values,
  linear interpolation between the floor and ceil of the rank. Single-element
  sequences return that element for every q; empty sequences raise
  ``ValueError`` (callers handle empties before calling).
- **Rounding**: ``dist_obj`` rounds to 4 decimals; an empty input yields all
  nulls so downstream JSON schemas stay uniform.
"""

from __future__ import annotations

import math
import statistics
from typing import Dict, Optional, Sequence


def mean(xs: Sequence[float]) -> Optional[float]:
    """Arithmetic mean; ``None`` for an empty sequence (semantics are the caller's)."""
    return statistics.fmean(xs) if len(xs) else None


def pstdev_or_sample(xs: Sequence[float]) -> float:
    """Sample standard deviation for n > 1 (``statistics.stdev``); 0.0 for n ≤ 1.

    See the module docstring for the sample-vs-population rationale.
    """
    return statistics.stdev(xs) if len(xs) > 1 else 0.0


def percentile_linear(xs: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile (numpy "linear" method), q in [0, 100].

    ``rank = q/100 · (n−1)`` over the ascending-sorted values; the result
    interpolates linearly between the values at ⌊rank⌋ and ⌈rank⌉.
    """
    if not xs:
        raise ValueError("percentile of an empty sequence")
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    rank = (q / 100.0) * (len(s) - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return s[int(lo)]
    frac = rank - lo
    return s[lo] * (1.0 - frac) + s[hi] * frac


def dist_obj(xs: Sequence[float]) -> Dict[str, Optional[float]]:
    """Distribution summary: mean/std/p5/p50/p95/min/max, rounded to 4 decimals.

    An empty sequence returns all nulls (uniform schema for consumers).
    """
    if not xs:
        return {"mean": None, "std": None, "p5": None, "p50": None,
                "p95": None, "min": None, "max": None}
    return {
        "mean": round(mean(xs), 4),              # type: ignore[arg-type]
        "std": round(pstdev_or_sample(xs), 4),
        "p5": round(percentile_linear(xs, 5.0), 4),
        "p50": round(percentile_linear(xs, 50.0), 4),
        "p95": round(percentile_linear(xs, 95.0), 4),
        "min": round(min(xs), 4),
        "max": round(max(xs), 4),
    }
