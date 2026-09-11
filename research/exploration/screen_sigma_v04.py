#!/usr/bin/env python3
"""EXPLORATORY ONLY (never shipped as engine code): sigma_H candidate screening
on the FROZEN v0.3 journals (commit e250695). Grounds the v0.4 pre-registration;
the screening itself is DISCLOSED in docs/decision-record-v0.4.0.md.

Candidates (all deterministic, backward-looking only):
  A  v0.3 iid-block overlapping-window means, sqrt(H/L) scaling   (current gate)
  B  HAC / Newey-West Bartlett long-run variance, sqrt(LRV/H)     (stationary-mean estimand)
  C  local-level two-scale from window-mean INCREMENTS:
        Var(dW_L) = s_drift^2/L + 2*s_noise^2/L^2  -> sigma_H = sqrt(s_d^2*H/3 + s_n^2/H)
  F  A + local-trend momentum term: sigma = sqrt(A^2 + (|beta_hat|*H/2)^2),
        beta_hat = OLS slope of daily APR over last M=min(n,60) days

Measured: breach rate of |window_mean_apr - ex_ante_apr| > 2*sigma at entry,
over every settled position of all 40 seeds, plus phase decomposition of A's
breaches, per-candidate mean sigma, and the implied perp z-gate pass rate.
"""
import json
import math
import statistics
from pathlib import Path

RUNS = sorted(Path("research/artifacts/sweep_runs").glob("run_seed_*.jsonl"))
H = 90.0
Z = 2.0
COLLAPSE_START = 150
RAMP_END = 120


def sigma_A(vals, h):
    n = len(vals)
    if n < 2:
        return 0.0
    L = min(int(h), max(2, n // 2))
    wins = [sum(vals[i:i + L]) / L for i in range(0, n - L + 1)]
    if len(wins) < 2:
        return 0.0
    return statistics.pstdev(wins) * math.sqrt(h / L)


def sigma_B(vals, h):
    n = len(vals)
    if n < 4:
        return 0.0
    K = min(n // 4, 30)
    m = sum(vals) / n
    g = [sum((vals[t] - m) * (vals[t + k] - m) for t in range(n - k)) / n
         for k in range(K + 1)]
    lrv = g[0] + 2.0 * sum((1.0 - k / (K + 1)) * g[k] for k in range(1, K + 1))
    return math.sqrt(max(lrv, 0.0) / h)


def sigma_C(vals, h):
    n = len(vals)
    if n < 12:
        return 0.0
    L1 = max(2, n // 8)
    L2 = max(L1 + 2, min(int(h), n // 2))
    L2 = min(L2, n - 1)
    if L2 <= L1:
        return 0.0

    def dvar(L):
        wins = [sum(vals[i:i + L]) / L for i in range(0, n - L + 1)]
        d = [wins[i + 1] - wins[i] for i in range(len(wins) - 1)]
        return statistics.pstdev(d) ** 2 if len(d) > 1 else 0.0

    v1, v2 = dvar(L1), dvar(L2)
    denom = 2.0 * (1.0 / L1 - 1.0 / L2)
    s_n2 = (v1 * L1 - v2 * L2) / denom if denom != 0 else 0.0
    s_n2 = max(s_n2, 0.0)
    s_d2 = max(v1 * L1 - 2.0 * s_n2 / L1, 0.0)
    return math.sqrt(s_d2 * h / 3.0 + s_n2 / h)


def _slope(vals, M):
    m = min(len(vals), M)
    if m < 3:
        return 0.0
    y = vals[-m:]
    x = list(range(m))
    mx, my = sum(x) / m, sum(y) / m
    num = sum((x[i] - mx) * (y[i] - my) for i in range(m))
    den = sum((x[i] - mx) ** 2 for i in range(m))
    return num / den if den else 0.0


def sigma_F(vals, h, M=60):
    a = sigma_A(vals, h)
    b = abs(_slope(vals, M))
    return math.sqrt(a * a + (b * h / 2.0) ** 2)


CANDS = {"A_iid_block": sigma_A, "B_hac": sigma_B, "C_local_level": sigma_C,
         "F_trend": sigma_F}

breaches = {k: 0 for k in CANDS}
checks = {k: 0 for k in CANDS}
sig_sum = {k: 0.0 for k in CANDS}
phase_tot = {"ramp": 0, "flat_high": 0, "collapse": 0, "post": 0}
phase_br = {"ramp": 0, "flat_high": 0, "collapse": 0, "post": 0}
zpass_A = zpass_F = ztot = 0

for path in RUNS:
    funding = {}
    settles = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("type") == "funding_daily":
            funding[r["payload"]["day"]] = r["payload"]["apr_printed"]
        elif r.get("type") == "position_settled":
            settles.append(r["payload"])

    for p in settles:
        rc = p.get("research_compare") or {}
        ex_apr = rc.get("ex_ante_apr")
        if ex_apr is None:
            continue
        od, sd = p["opened_day"], p["settle_day"]
        days = [d for d in funding if od < d <= sd]
        if not days:
            continue
        wmean = sum(funding[d] for d in days) / len(days)
        vals = [funding[d] for d in sorted(funding) if d <= od]
        if len(vals) < 2:
            continue
        err = abs(wmean - ex_apr)
        ph = ("ramp" if od <= RAMP_END else "flat_high" if od <= COLLAPSE_START
              else "collapse" if od <= 180 else "post")
        phase_tot[ph] += 1
        for k, fn in CANDS.items():
            s = fn(vals, H)
            if s <= 0:
                continue
            checks[k] += 1
            sig_sum[k] += s
            if err > Z * s:
                breaches[k] += 1
                if k == "A_iid_block":
                    phase_br[ph] += 1
        ztot += 1
        if ex_apr / sigma_A(vals, H) >= Z:
            zpass_A += 1
        if ex_apr / sigma_F(vals, H) >= Z:
            zpass_F += 1

print(f"seeds={len(RUNS)} settles_with_window={ztot}")
print(f"phase totals: {phase_tot}")
print(f"A breaches by phase: {phase_br}")
for k in CANDS:
    br = 100.0 * breaches[k] / checks[k] if checks[k] else float("nan")
    print(f"{k:>14}: breach {br:5.1f}%  ({breaches[k]}/{checks[k]})  mean_sigma={sig_sum[k]/max(checks[k],1)*100:.2f}pp")
print(f"implied perp z-gate pass @entry: A {zpass_A}/{ztot} = {100.0*zpass_A/ztot:.1f}%   F {zpass_F}/{ztot} = {100.0*zpass_F/ztot:.1f}%")
