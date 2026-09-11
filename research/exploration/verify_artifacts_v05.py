#!/usr/bin/env python3
"""INDEPENDENT verification of sweep-latest.json / run-latest.json (v0.5.0).

Deliberately separate code path from scripts/research_sweep.py: re-derives the
headline artifact numbers straight from the raw journals and compares them to
the artifact values. Any mismatch exits non-zero. Run after every sweep.

v0.5.0 additions vs the v0.4 verifier: the QUADRUPLE panels + the upside
honest-cost panel (with per-sided breach logic), the three-set ranking split
(pooled / screening / like-for-like) with the contest day-bucket decomposition,
the holdout ladder (61..80), the adverse-method diagnostics presence check on
family_eval records, and the journal-precision audit round-trip of the v0.4
two-sided value on settled entries.
"""
import json
import math
from pathlib import Path

ART = Path("research/artifacts")
sweep = json.loads((ART / "sweep-latest.json").read_text())
run = json.loads((ART / "run-latest.json").read_text())
SEEDS = sweep["params"]["seeds"]
HOLDOUT_FROM = sweep["params"]["holdout_seeds"][0]
LIKE = sweep["params"]["like_for_like_seeds"][-1]
TENOR = sweep["params"]["tenor_days"]
DAYS = sweep["params"]["days"]
COLLAPSE = 150          # pre-registered regime boundary (world v2)
Z = sweep["z_gate_calibration"]["threshold_z"]

fails = []


def check(name, got, want, tol=0.051):
    ok = (got is not None and want is not None
          and abs(float(got) - float(want)) <= tol)
    print(f"{'OK ' if ok else 'FAIL'} {name}: independent={got} artifact={want}")
    if not ok:
        fails.append(name)


def check_eq(name, got, want):
    ok = got == want
    print(f"{'OK ' if ok else 'FAIL'} {name}: independent={got!r} artifact={want!r}")
    if not ok:
        fails.append(name)


# ---- load every journal independently --------------------------------------
worlds = {}
for seed in SEEDS:
    funding = {}
    fam = {}
    settles = []
    n_records = {"quotes": 0, "family_evals": 0, "risk_rejects": 0,
                 "opened": 0, "settled": 0, "still_open": 0}
    for line in (ART / "sweep_runs" / f"run_seed_{seed:04d}.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        t, p = r["type"], r["payload"]
        if t == "funding_daily":
            funding[p["day"]] = p["apr_printed"]
        elif t == "family_eval":
            fam.setdefault(p["day"], {})[p["strategy_id"]] = p
            n_records["family_evals"] += 1
        elif t == "position_settled":
            settles.append(p)
            n_records["settled"] += 1
        elif t == "quote":
            n_records["quotes"] += 1
        elif t == "decision" and p.get("action") == "reject":
            n_records["risk_rejects"] += 1
        elif t == "position_opened":
            n_records["opened"] += 1
        elif t == "run_summary":
            n_records["still_open"] = p.get("positions_still_open", 0)
    worlds[seed] = (funding, fam, settles, n_records)

# ---- 1) quadruple + upside calibration panels, all three subsets -----------
def breach_counts(seeds, sig_key, sided):
    checks = breaches = 0
    eh = {"short": [0, 0], "long": [0, 0]}
    for seed in seeds:
        funding, _, settles, _ = worlds[seed]
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
            diff = wm - ex
            checks += 1
            n_entry = len([d for d in funding if d <= p["opened_day"]])
            b = "short" if n_entry <= 45 else "long"
            eh[b][0] += 1
            hit = {"two": abs(diff) > Z * sg,
                   "down": diff < -Z * sg,
                   "up": diff > Z * sg}[sided]
            if hit:
                breaches += 1
                eh[b][1] += 1
    return checks, breaches, eh


subsets = {
    "pooled": SEEDS,
    "screening_set": [s for s in SEEDS if s < HOLDOUT_FROM],
    "holdout": [s for s in SEEDS if s >= HOLDOUT_FROM],
}
panel_spec = (
    ("panel_level", "ex_ante_sigma_apr", "two"),
    ("panel_horizon_iid", "ex_ante_sigma_horizon_iid_apr", "two"),
    ("panel_horizon_twosided", "ex_ante_sigma_horizon_twosided_apr", "two"),
    ("panel_horizon", "ex_ante_sigma_horizon_apr", "down"),
    ("panel_horizon_upside", "ex_ante_sigma_horizon_apr", "up"),
)
zg = sweep["z_gate_calibration"]
for sub_name, sub_seeds in subsets.items():
    src = zg if sub_name == "pooled" else zg["holdout_split"]
    for panel, key, sided in panel_spec:
        ck, br, _ = breach_counts(sub_seeds, key, sided)
        if sub_name == "pooled":
            art = src[panel]
        else:
            # only the horizon-family panels carry a holdout split in the
            # artifact (the level panel is a v0.2 audit — no split by design)
            if panel == "panel_level":
                continue
            art = src[f"{sub_name}_{panel}"]
        pct = round(br / ck * 100.0, 1) if ck else None
        check(f"{sub_name}/{panel} breach pct", pct, art["empirical_breach_pct"])
        check_eq(f"{sub_name}/{panel} n_checks", ck, art["n_checks"])

# entry-history decomposition on the adverse panel (pooled)
ck, br, eh = breach_counts(SEEDS, "ex_ante_sigma_horizon_apr", "down")
art_eh = zg["panel_horizon"]["entry_history"]
for bucket, key in (("short", "short_history_le_45d"), ("long", "long_history_gt_45d")):
    pct = round(eh[bucket][1] / eh[bucket][0] * 100.0, 1) if eh[bucket][0] else None
    check(f"adverse panel entry-history {bucket} pct", pct,
          art_eh[key]["empirical_breach_pct"])
    check_eq(f"adverse panel entry-history {bucket} n_checks", eh[bucket][0],
             art_eh[key]["n_checks"])

# ---- 2) ranking: three seed sets + day buckets ------------------------------
def ranking_counts(seeds):
    acc = {"contested": 0, "contests": 0, "trunc": 0, "hits": 0, "misses": 0, "ties": 0,
           "ramp": 0, "collapse": 0, "fwd_ramp": 0, "fwd_collapse": 0,
           "avoids": [0, 0], "touches": [0, 0]}   # [contests, hits]
    boundary = COLLAPSE - TENOR
    for seed in seeds:
        funding, fam, _, _ = worlds[seed]
        for day, fams in fam.items():
            f, pe = fams.get("forward_basis_v1"), fams.get("perp_carry_v1")
            if not (f and pe and f["gated"] and pe["gated"]):
                continue
            acc["contested"] += 1
            phase = "ramp" if day <= COLLAPSE else "collapse"
            acc[phase] += 1
            if f["selected"]:
                acc[f"fwd_{phase}"] += 1
            if day + TENOR > DAYS:
                acc["trunc"] += 1
                continue
            fwd_carry = (f.get("detail") or {}).get("implied_apr")
            window = [funding[d] for d in range(day + 1, day + TENOR + 1)
                      if d in funding]
            if fwd_carry is None or not window:
                acc["trunc"] += 1
                continue
            perp_carry = sum(window) / len(window)
            acc["contests"] += 1
            b = "avoids" if day <= boundary else "touches"
            acc[b][0] += 1
            sel, forg = ((fwd_carry, perp_carry) if f["selected"]
                         else (perp_carry, fwd_carry))
            if sel > forg + 1e-12:
                acc["hits"] += 1
                acc[b][1] += 1
            elif sel < forg - 1e-12:
                acc["misses"] += 1
            else:
                acc["ties"] += 1
    return acc


rank_sets = {
    "ranking": SEEDS,
    "ranking_screening_set": [s for s in SEEDS if s < HOLDOUT_FROM],
    "ranking_like_for_like": [s for s in SEEDS if s <= LIKE],
}
for rank_key, sub_seeds in rank_sets.items():
    a = ranking_counts(sub_seeds)
    art = sweep[rank_key]
    hr = round(a["hits"] / a["contests"] * 100.0, 1) if a["contests"] else None
    check(f"{rank_key} hit-rate pct", hr, art["hit_rate_pct"])
    check_eq(f"{rank_key} contests", a["contests"], art["contested_days_evaluated"])
    check_eq(f"{rank_key} contested days", a["contested"], art["contested_days_total"])
    check_eq(f"{rank_key} hits", a["hits"], art["hits"])
    check_eq(f"{rank_key} truncated", a["trunc"], art["truncated_excluded"])
    fsc = (round(a["fwd_collapse"] / a["collapse"] * 100.0, 1)
           if a["collapse"] else None)
    check(f"{rank_key} collapse fwd share", fsc, art["forward_selection_share_collapse_pct"])
    if rank_key == "ranking":
        db = art["day_bucket"]
        for b in ("avoids", "touches"):
            hr_b = (round(a[b][1] / a[b][0] * 100.0, 1) if a[b][0] else None)
            art_b = db[f"window_{'avoids' if b == 'avoids' else 'touches'}_collapse"]
            check(f"day-bucket {b} hit-rate", hr_b, art_b["hit_rate_pct"])
            check_eq(f"day-bucket {b} contests", a[b][0], art_b["n_contests"])
        check_eq("day-bucket boundary", COLLAPSE - TENOR, db["boundary_day"])

# ---- 3) family census --------------------------------------------------------
# census semantics (unchanged since v0.3.0, stated in the artifact's
# _definition): "opened" counts opens that SETTLED within the run (the
# settled population). TRUE opens (incl. still-open) are verified via totals.
fam_tot = {"forward_basis_v1": [0, 0, 0, 0, 0], "perp_carry_v1": [0, 0, 0, 0, 0]}
# [evals, gated_in, selected, opened_and_settled, settled]
true_opens = {"forward_basis_v1": 0, "perp_carry_v1": 0}
for seed in SEEDS:
    _, fam, settles, n = worlds[seed]
    for day, fams in fam.items():
        for sid, p in fams.items():
            fam_tot[sid][0] += 1
            if p["gated"]:
                fam_tot[sid][1] += 1
            if p["selected"]:
                fam_tot[sid][2] += 1
    for p in settles:
        fam_tot[p["strategy_id"]][4] += 1
        fam_tot[p["strategy_id"]][3] += 1     # opened-and-settled (census def)
for seed in SEEDS:
    for line in (ART / "sweep_runs" / f"run_seed_{seed:04d}.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r["type"] == "position_opened":
            true_opens[r["payload"]["opportunity"]["strategy_id"]] += 1

for sid, tot in fam_tot.items():
    fc = sweep["family_census"][sid]
    check_eq(f"census {sid} evals", tot[0], fc["evals"])
    check_eq(f"census {sid} gated_in", tot[1], fc["gated_in"])
    check_eq(f"census {sid} selected", tot[2], fc["selected"])
    check_eq(f"census {sid} opened-and-settled", tot[3], fc["opened"])
    check_eq(f"census {sid} settled", tot[4], fc["settled"])
check_eq("true opens F+P == totals.opened",
         true_opens["forward_basis_v1"] + true_opens["perp_carry_v1"],
         sweep["totals"]["opened"])

# ---- 4) totals ----------------------------------------------------------------
tot = {k: 0 for k in ("quotes", "family_evals", "risk_rejects", "opened", "settled",
                       "still_open")}
for seed in SEEDS:
    _, _, _, n = worlds[seed]
    for k in tot:
        tot[k] += n[k]
check_eq("totals quotes", tot["quotes"], sweep["totals"]["quotes"])
check_eq("totals family_evals", tot["family_evals"], sweep["totals"]["family_evals"])
check_eq("totals risk_rejects", tot["risk_rejects"], sweep["totals"]["risk_rejects"])
check_eq("totals opened", tot["opened"], sweep["totals"]["opened"])
check_eq("totals settled", tot["settled"], sweep["totals"]["settled"])
check_eq("totals still_open", tot["still_open"], sweep["totals"]["still_open"])

# ---- 5) run-latest demo (seed 7 by default) -----------------------------------
demo_seed = sweep["params"]["seeds"][0]
# demo seed is not in params; recover from the journal path
jp = run["journal_path"]
demo_seed = int(jp.split("run_seed_")[1].split(".")[0])
_, _, settles, _ = worlds[demo_seed]
check_eq("run-latest settled rows", len(settles), len(run["settled"]))
check_eq("run-latest engine_version", run["engine_version"], "0.5.0")
check_eq("sweep engine_version", sweep["engine_version"], "0.5.0")
cc_days = len([1 for c in run["carry_curve"]])
_, fam_demo, _, _ = worlds[demo_seed]
check_eq("run-latest family_edge_series days", len(fam_demo), len(run["family_edge_series"]))

# ---- 6) signed accruals on perp settles (I-3 discipline) ----------------------
bad_accrual = 0
n_perp = 0
for seed in SEEDS:
    funding, _, settles, _ = worlds[seed]
    for p in settles:
        if p["strategy_id"] != "perp_carry_v1":
            continue
        n_perp += 1
        acc = p.get("funding_accrual_usd")
        if acc is None:
            bad_accrual += 1
        # sign sanity: positive APR window with positive qty must accrue >= 0
        days = [d for d in funding if p["opened_day"] < d <= p["settle_day"]]
        if days and acc is not None:
            wm = sum(funding[d] for d in days) / len(days)
            if wm > 0 and acc < 0:
                bad_accrual += 1
check_eq("perp settles with signed accrual anomalies", bad_accrual, 0)
check_eq("perp settle count", n_perp, fam_tot["perp_carry_v1"][4])

# ---- 7) family_eval diagnostics presence (v0.5 C2, adverse method) -----------
n_diag = 0
n_bad_method = 0
n_roundtrip_bad = 0
for seed in SEEDS:
    _, fam, _, _ = worlds[seed]
    for day, fams in fam.items():
        for sid, p in fams.items():
            d = p.get("detail") or {}
            diag = d.get("sigma_horizon_diag") or {}
            n_diag += 1
            if diag.get("method") not in ("iid_block_plus_adverse_trend",
                                          "insufficient_history", "degenerate_zero"):
                n_bad_method += 1
            if "sigma_horizon_twosided_apr" not in d:
                n_bad_method += 1
            # audit round-trip at journal precision (main path only)
            if diag.get("method") == "iid_block_plus_adverse_trend":
                rec = math.hypot(diag.get("sigma_iid_block", 0.0),
                                 diag.get("twosided_trend_term_apr", 0.0))
                if abs(rec - diag.get("sigma_twosided_apr", -1)) > 2e-6:
                    n_roundtrip_bad += 1
check_eq("family_eval diag method/keys anomalies", n_bad_method, 0)
check_eq("adverse diag round-trip anomalies", n_roundtrip_bad, 0)
check_eq("family_eval records seen", n_diag, sweep["totals"]["family_evals"])

# settle-side research_compare key presence (v0.5 C2)
n_rc = 0
for seed in SEEDS:
    _, _, settles, _ = worlds[seed]
    for p in settles:
        rc = p.get("research_compare") or {}
        if rc.get("ex_ante_sigma_horizon_twosided_apr") is None:
            n_rc += 1
check_eq("settles missing twosided research_compare key", n_rc, 0)

# ---- 8) predictions verdicts recomputed from independent stats ---------------
pred = sweep["predictions"]
down_pct = zg["panel_horizon"]["empirical_breach_pct"]
check_eq("P1 verdict recompute", ("SUPPORTED" if down_pct <= 8.0 else "REJECTED"),
         pred["P1"]["verdict"])
sb = zg["holdout_split"]["screening_set_panel_horizon"]["empirical_breach_pct"]
hb = zg["holdout_split"]["holdout_panel_horizon"]["empirical_breach_pct"]
check_eq("P2 verdict recompute",
         ("SUPPORTED" if abs(hb - sb) <= 6.0 else "REJECTED"), pred["P2"]["verdict"])
check_eq("P3 verdict recompute",
         ("SUPPORTED" if sweep["ranking_like_for_like"]["hit_rate_pct"] >= 50.0
          else "REFUTED"), pred["P3"]["verdict"])
av = sweep["ranking"]["day_bucket"]["window_avoids_collapse"]["hit_rate_pct"]
to = sweep["ranking"]["day_bucket"]["window_touches_collapse"]["hit_rate_pct"]
up = zg["panel_horizon_upside"]["empirical_breach_pct"]
check_eq("P4 verdict recompute",
         ("SUPPORTED" if (av <= to - 20.0 and up > 15.0) else "REFUTED"),
         pred["P4"]["verdict"])
check_eq("P5 verdict recompute",
         ("SUPPORTED"
          if sweep["ranking_like_for_like"]["forward_selection_share_collapse_pct"] >= 60.0
          else "NOT SUPPORTED"), pred["P5"]["verdict"])

print()
if fails:
    print(f"VERIFICATION FAILED: {len(fails)} mismatches -> {fails}")
    raise SystemExit(1)
print("ALL INDEPENDENT VERIFICATION CHECKS PASSED (v0.5.0)")
