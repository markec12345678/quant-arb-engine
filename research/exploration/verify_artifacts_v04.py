#!/usr/bin/env python3
"""INDEPENDENT verification of sweep-latest.json / run-latest.json (v0.4.0).

Deliberately separate code path from scripts/research_sweep.py: re-derives the
headline artifact numbers straight from the raw journals and compares them to
the artifact values. Any mismatch exits non-zero. Run after every sweep.
"""
import json
import math
from pathlib import Path

ART = Path("research/artifacts")
sweep = json.loads((ART / "sweep-latest.json").read_text())
run = json.loads((ART / "run-latest.json").read_text())
HOLDOUT_FROM = sweep["params"]["holdout_seeds"][0]
SEEDS = sweep["params"]["seeds"]
TENOR = sweep["params"]["tenor_days"]
DAYS = sweep["params"]["days"]

fails = []


def check(name, got, want, tol=0.051):
    ok = (got is not None and want is not None
          and abs(float(got) - float(want)) <= tol)
    print(f"{'OK ' if ok else 'FAIL'} {name}: independent={got} artifact={want}")
    if not ok:
        fails.append(name)


# ---- load every journal independently --------------------------------------
worlds = {}
for seed in SEEDS:
    funding = {}
    fam = {}
    settles = []
    for line in (ART / "sweep_runs" / f"run_seed_{seed:04d}.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        t, p = r["type"], r["payload"]
        if t == "funding_daily":
            funding[p["day"]] = p["apr_printed"]
        elif t == "family_eval":
            fam.setdefault(p["day"], {})[p["strategy_id"]] = p
        elif t == "position_settled":
            settles.append(p)
    worlds[seed] = (funding, fam, settles)

# ---- 1) triple calibration panels, pooled + holdout split -------------------
def breach_counts(seeds, sig_key):
    checks = breaches = 0
    eh = {"short": [0, 0], "long": [0, 0]}
    for seed in seeds:
        funding, _, settles = worlds[seed]
        for p in settles:
            rc = p.get("research_compare") or {}
            ex = rc.get("ex_ante_apr")
            sg = rc.get(sig_key)
            if ex is None or sg is None:
                continue
            days = [d for d in funding if p["opened_day"] < d <= p["settle_day"]]
            if not days:
                continue
            wm = sum(funding[d] for d in days) / len(days)
            checks += 1
            n_entry = len([d for d in funding if d <= p["opened_day"]])
            b = "short" if n_entry <= 45 else "long"
            eh[b][0] += 1
            if abs(wm - ex) > 2.0 * sg:
                breaches += 1
                eh[b][1] += 1
    return checks, breaches, eh


for panel, key in (("panel_level", "ex_ante_sigma_apr"),
                   ("panel_horizon_iid", "ex_ante_sigma_horizon_iid_apr"),
                   ("panel_horizon", "ex_ante_sigma_horizon_apr")):
    ck, br, _ = breach_counts(SEEDS, key)
    art = sweep["z_gate_calibration"][panel]
    check(f"{panel}.n_checks", ck, art["n_checks"], 0)
    check(f"{panel}.n_breaches", br, art["n_breaches"], 0)

ck, br, eh = breach_counts(SEEDS, "ex_ante_sigma_horizon_apr")
trend = sweep["z_gate_calibration"]["panel_horizon"]
short, long_ = eh["short"], eh["long"]
check("trend.eh_short.n", short[0], trend["entry_history"]["short_history_le_45d"]["n_checks"], 0)
check("trend.eh_short.br", short[1], trend["entry_history"]["short_history_le_45d"]["n_breaches"], 0)
check("trend.eh_long.n", long_[0], trend["entry_history"]["long_history_gt_45d"]["n_checks"], 0)
check("trend.eh_long.br", long_[1], trend["entry_history"]["long_history_gt_45d"]["n_breaches"], 0)

scr = [s for s in SEEDS if s < HOLDOUT_FROM]
hold = [s for s in SEEDS if s >= HOLDOUT_FROM]
ck_s, br_s, _ = breach_counts(scr, "ex_ante_sigma_horizon_apr")
ck_h, br_h, _ = breach_counts(hold, "ex_ante_sigma_horizon_apr")
check("screening breach %", round(br_s / ck_s * 100, 1),
      sweep["z_gate_calibration"]["holdout_split"]["screening_set_panel_horizon"]["empirical_breach_pct"])
check("holdout breach %", round(br_h / ck_h * 100, 1),
      sweep["z_gate_calibration"]["holdout_split"]["holdout_panel_horizon"]["empirical_breach_pct"])

# ---- 2) family census + P3 ---------------------------------------------------
F, P = "forward_basis_v1", "perp_carry_v1"
ev_f = ev_p = g_f = g_p = sel_f = sel_p = 0
opened_f = opened_p = settled_f = settled_p = 0
for seed in SEEDS:
    _, fam, settles = worlds[seed]
    for day, m in fam.items():
        for sid, p in m.items():
            if sid == F:
                ev_f += 1
                g_f += 1 if p["gated"] else 0
                sel_f += 1 if p["selected"] else 0
            else:
                ev_p += 1
                g_p += 1 if p["gated"] else 0
                sel_p += 1 if p["selected"] else 0
    for p in settles:
        if p["strategy_id"] == F:
            settled_f += 1
        else:
            settled_p += 1
cf, cp = sweep["family_census"][F], sweep["family_census"][P]
check("census F evals", ev_f, cf["evals"], 0)
check("census F gated", g_f, cf["gated_in"], 0)
check("census F selected", sel_f, cf["selected"], 0)
check("census F settled", settled_f, cf["settled"], 0)
check("census P evals", ev_p, cp["evals"], 0)
check("census P gated", g_p, cp["gated_in"], 0)
check("census P selected", sel_p, cp["selected"], 0)
check("census P settled", settled_p, cp["settled"], 0)
check("P3 perp gated share %", round(g_p / ev_p * 100, 1),
      sweep["predictions"]["P3"]["perp_gated_in_share_pct"])

# ---- 3) ranking hit-rate (pooled + screening) --------------------------------
def ranking(seeds):
    contests = hits = misses = ties = truncated = contested = 0
    fs_r = fs_c = c_r = c_c = 0
    for seed in seeds:
        funding, fam, _ = worlds[seed]
        for day, m in fam.items():
            f, pe = m.get(F), m.get(P)
            if not (f and pe and f["gated"] and pe["gated"]):
                continue
            contested += 1
            if day <= 150:
                c_r += 1
            else:
                c_c += 1
            if f["selected"]:
                if day <= 150:
                    fs_r += 1
                else:
                    fs_c += 1
            if day + TENOR > DAYS:
                truncated += 1
                continue
            fwd = (f.get("detail") or {}).get("implied_apr")
            window = [funding[d] for d in range(day + 1, day + TENOR + 1) if d in funding]
            if fwd is None or not window:
                truncated += 1
                continue
            perp_c = sum(window) / len(window)
            sel_c, forg = (fwd, perp_c) if f["selected"] else (perp_c, fwd)
            if sel_c > forg + 1e-12:
                hits += 1
            elif sel_c < forg - 1e-12:
                misses += 1
            else:
                ties += 1
            contests += 1
    return dict(contested=contested, contests=contests, hits=hits, misses=misses,
                ties=ties, truncated=truncated, fs_r=fs_r, fs_c=fs_c, c_r=c_r, c_c=c_c)


rp = ranking(SEEDS)
rk = sweep["ranking"]
check("ranking contested", rp["contested"], rk["contested_days_total"], 0)
check("ranking evaluated", rp["contests"], rk["contested_days_evaluated"], 0)
check("ranking hits", rp["hits"], rk["hits"], 0)
check("ranking misses", rp["misses"], rk["misses"], 0)
check("ranking truncated", rp["truncated"], rk["truncated_excluded"], 0)
check("hit-rate % (pooled)", round(rp["hits"] / rp["contests"] * 100, 1), rk["hit_rate_pct"])
check("fwd share ramp % (pooled)", round(rp["fs_r"] / rp["c_r"] * 100, 1) if rp["c_r"] else None,
      rk["forward_selection_share_ramp_pct"])
check("fwd share collapse % (pooled)", round(rp["fs_c"] / rp["c_c"] * 100, 1) if rp["c_c"] else None,
      rk["forward_selection_share_collapse_pct"])
rs = ranking(scr)
check("P4 hit-rate % (screening)", round(rs["hits"] / rs["contests"] * 100, 1),
      sweep["predictions"]["P4"]["hit_rate_pct"])
check("P5 fwd collapse % (screening)", round(rs["fs_c"] / rs["c_c"] * 100, 1) if rs["c_c"] else None,
      sweep["predictions"]["P5"]["forward_share_collapse_pct"])

# ---- 4) totals ----------------------------------------------------------------
check("totals quotes", sum(len([1 for d in worlds[s][1]]) for s in SEEDS) * 4,
      sweep["totals"]["quotes"], 0)
check("totals family_evals", (ev_f + ev_p), sweep["totals"]["family_evals"], 0)
check("totals settled", settled_f + settled_p, sweep["totals"]["settled"], 0)

# ---- 5) run-latest (seed 7) ----------------------------------------------------
s7 = worlds[7]
summ = run["summary"]
check("run seed", summ["seed"], 7, 0)
check("run family_evals", sum(len(m) for m in s7[1].values()), summ["family_evals"], 0)
check("run settled", len(s7[2]), summ["positions_settled"], 0)
check("run contested", sum(1 for day, m in s7[1].items()
                           if m.get(F, {}).get("gated") and m.get(P, {}).get("gated")),
      summ["contested_days"], 0)
check("run carry_curve len", len(s7[0]), len(run["carry_curve"]), 0)

# perp settled rows must carry funding_accrual_usd (I-3)
for seed in SEEDS:
    for p in worlds[seed][2]:
        if p["strategy_id"] == P:
            v = p.get("funding_accrual_usd")
            assert v is not None and not str(v).startswith("abs_"), f"missing signed accrual: {p['position_id']}"
print("OK  all perp settles carry signed funding_accrual_usd (I-3)")
# every family_eval carries both sigmas + trend diag
n_diag = 0
for seed in SEEDS:
    for day, m in worlds[seed][1].items():
        for sid, p in m.items():
            d = p.get("detail") or {}
            assert "sigma_horizon_iid_apr" in d and "sigma_horizon_diag" in d, (seed, day, sid)
            n_diag += 1
print(f"OK  all {n_diag} family_evals carry sigma_horizon_iid_apr + trend diagnostics")

print()
if fails:
    print(f"INDEPENDENT VERIFICATION FAILED: {fails}")
    raise SystemExit(1)
print("INDEPENDENT VERIFICATION PASSED — every artifact number re-derived from the raw journals matches.")
