#!/usr/bin/env python3
"""EXPLORATORY ONLY (never shipped as engine code): asymmetric carry-buffer
candidate screening on the FROZEN v0.4 journals (commit 2b12b34, seeds 1..60).
Grounds the v0.5 pre-registration; the screening itself is DISCLOSED in
docs/decision-record-v0.5.0.md.

The v0.4 P4 refutation measured the decision price of the TWO-SIDED trend
buffer: charging |beta_hat|*H/2 against the perp's net edge deflates the
floating family, the ranking flips to the locked forward, and the hit-rate
fell 60.2% -> 11.4%. The recorded v0.5 question: downside semi-deviation for a
long-carry position.

Candidates (both deterministic, backward-looking only, no new knobs):
  S   v0.4 symmetric trend term  |beta_hat|*H/2     (pessimistic bound of the
      reversal-ignorance interval: a trend reversal is priced with the same
      weight as trend continuation)
  G1  adverse-side trend term    max(0, -beta_hat)*H/2   (optimistic bound:
      only a FALLING visible trend is charged; a rising trend's adverse
      scenario -- regime reversal -- is priced at zero)

Both keep the v0.3 iid-block dispersion component sigma_A verbatim inside the
quadrature, and both use the same pre-registered constants as v0.4
(trend_window_days=60, H=90, k=1, min_z=2, min_net_edge_bps=10).

Measured on the frozen journals, three sides:
  (1) SETTLE PANEL side: per settled position, the window-mean error vs the
      ex-ante APR. Two-sided breach under S (reproduces the v0.4 panel),
      DOWNSIDE breach under G1 (err < -2*sigma_down), UPSIDE surprise under
      G1 (err > +2*sigma_down), direction split of S's breaches.
  (2) WOULD-BE RANKING side: re-rank every contested family_eval day under G1
      using ONLY journaled per-day state (sigma_iid_block, beta_hat, waterfall
      buffer, net edge, expected_apr; the forward family is untouched), then
      re-score the ex-post hit-rate exactly as scripts/research_sweep.py does.
      This is exact up to journal rounding: the journals carry the full
      ex-ante decision state.
  (3) GATE side: implied perp z-gate / net-edge gate pass rates under G1,
      overall and by world phase.
"""
import json
import math
import statistics
from pathlib import Path

RUNS = sorted(Path("research/artifacts/sweep_runs").glob("run_seed_*.jsonl"))
H = 90.0
Z = 2.0
K = 1.0                # carry_uncertainty_k (pre-registered)
MIN_NET_EDGE_BPS = 10.0
TREND_WINDOW = 60
COLLAPSE_START = 150
RAMP_END = 120
DAYS = 200
# window-touch boundary: a d+90 window includes collapse days iff d > 60
TOUCH_BOUNDARY = COLLAPSE_START - int(H)

FORWARD = "forward_basis_v1"
PERP = "perp_carry_v1"


def sigma_A(vals, h):
    n = len(vals)
    if n < 2:
        return 0.0
    L = min(int(h), max(2, n // 2))
    wins = [sum(vals[i:i + L]) / L for i in range(0, n - L + 1)]
    if len(wins) < 2:
        return 0.0
    return statistics.pstdev(wins) * math.sqrt(h / L)


def slope(vals, m_win):
    m = min(len(vals), m_win)
    if m < 3:
        return 0.0
    y = vals[-m:]
    x = list(range(m))
    mx, my = sum(x) / m, sum(y) / m
    num = sum((x[i] - mx) * (y[i] - my) for i in range(m))
    den = sum((x[i] - mx) ** 2 for i in range(m))
    return num / den if den else 0.0


def phase_of(day):
    return ("ramp" if day <= RAMP_END else "flat_high" if day <= COLLAPSE_START
            else "collapse" if day <= 180 else "post")


# ---------------------------------------------------------------- (1) panels
tot = {"S_two_sided": 0, "S_pos": 0, "S_neg": 0, "G1_down": 0, "G1_up": 0, "n": 0}
sig_sum = {"S": 0.0, "G1": 0.0}
phase_n: dict = {}
phase_g1down: dict = {}
# cross-check: recomputed S vs journaled ex-ante trend sigma
xcheck = {"n": 0, "max_abs_diff_pp": 0.0}

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
        ex_sym = rc.get("ex_ante_sigma_horizon_apr")
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
        a = sigma_A(vals, H)
        b = slope(vals, TREND_WINDOW)
        s_sym = math.hypot(a, abs(b) * H / 2.0)
        s_g1 = math.hypot(a, max(0.0, -b) * H / 2.0)
        err = wmean - ex_apr
        tot["n"] += 1
        sig_sum["S"] += s_sym
        sig_sum["G1"] += s_g1
        if s_sym > 0 and abs(err) > Z * s_sym:
            tot["S_two_sided"] += 1
            tot["S_pos" if err > 0 else "S_neg"] += 1
        if s_g1 > 0:
            if err < -Z * s_g1:
                tot["G1_down"] += 1
            elif err > Z * s_g1:
                tot["G1_up"] += 1
        ph = phase_of(od)
        phase_n[ph] = phase_n.get(ph, 0) + 1
        if s_g1 > 0 and err < -Z * s_g1:
            phase_g1down[ph] = phase_g1down.get(ph, 0) + 1
        if ex_sym is not None:
            xcheck["n"] += 1
            xcheck["max_abs_diff_pp"] = max(xcheck["max_abs_diff_pp"],
                                            abs(s_sym - ex_sym) * 100.0)

n = tot["n"]
print("=" * 72)
print(f"(1) SETTLE PANEL side — {n} settled positions, {len(RUNS)} frozen v0.4 journals")
print(f"    S two-sided breach : {100.0*tot['S_two_sided']/n:5.1f}%  "
      f"(pos {tot['S_pos']} / neg {tot['S_neg']})   [v0.4 panel measured 11.0%]")
print(f"    G1 DOWNSIDE breach : {100.0*tot['G1_down']/n:5.1f}%   (one-sided nominal 2.28%)")
print(f"    G1 UPSIDE surprise : {100.0*tot['G1_up']/n:5.1f}%   (reported, not a target)")
print(f"    mean sigma         : S {sig_sum['S']/n*100:.2f}pp · G1 {sig_sum['G1']/n*100:.2f}pp")
print(f"    G1 downside by entry phase: "
      f"{ {k: f'{phase_g1down.get(k,0)}/{phase_n.get(k,0)}' for k in phase_n} }")
print(f"    xcheck recomputed-S vs journaled ex-ante trend sigma: n={xcheck['n']}, "
      f"max|diff|={xcheck['max_abs_diff_pp']:.4f}pp")

# ---------------------------------------------------------- (2) would-be rank
acc = {"contested": 0, "contested40": 0, "hits": 0, "hits40": 0, "misses": 0, "misses40": 0,
       "evaluated": 0, "evaluated40": 0, "flips": 0, "flips40": 0,
       "fwd_sel_ramp": 0, "fwd_sel_collapse": 0, "cont_ramp": 0, "cont_collapse": 0,
       "fwd_sel_ramp40": 0, "cont_ramp40": 0, "fwd_sel_collapse40": 0, "cont_collapse40": 0,
       # day-bucket decomposition of full-window contests (collapse-touch boundary d>60)
       "touch_n": 0, "touch_hits": 0, "avoid_n": 0, "avoid_hits": 0,
       "touch_n40": 0, "touch_hits40": 0, "avoid_n40": 0, "avoid_hits40": 0,
       "perp_sel": 0, "perp_sel40": 0}
gate_acc = {"perp_evals": 0, "perp_gated": 0, "perp_gated_collapse": 0,
            "perp_evals_collapse": 0, "z_pass": 0, "net_pass": 0}

for path in RUNS:
    seed = int(path.stem.split("_")[-1])
    in40 = seed <= 40
    funding = {}
    fam_by_day = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("type") == "funding_daily":
            funding[r["payload"]["day"]] = r["payload"]["apr_printed"]
        elif r.get("type") == "family_eval":
            p = r["payload"]
            fam_by_day.setdefault(p["day"], {})[p["strategy_id"]] = p

    for day, fams in sorted(fam_by_day.items()):
        f, pe = fams.get(FORWARD), fams.get(PERP)
        if not (f and pe):
            continue
        pd = (pe.get("detail") or {})
        diag = pd.get("sigma_horizon_diag") or {}
        wf = pd.get("waterfall") or {}
        s_iid = diag.get("sigma_iid_block", 0.0) or 0.0
        beta = diag.get("beta_hat_apr_per_day", 0.0) or 0.0
        gate_acc["perp_evals"] += 1
        if day > COLLAPSE_START:
            gate_acc["perp_evals_collapse"] += 1
        # G1 sigma from journaled components (exact up to rounding)
        adverse = max(0.0, -beta) * H / 2.0
        s_g1 = math.hypot(s_iid, adverse)
        ex_apr = pd.get("expected_apr")
        z05 = (ex_apr / s_g1) if (s_g1 > 0 and ex_apr) else None
        zgate05 = z05 is not None and z05 >= Z
        buf04 = wf.get("carry_uncertainty_buffer_bps", 0.0) or 0.0
        net04 = wf.get("net_executable_edge_bps", 0.0) or 0.0
        buf05 = K * s_g1 * H / 365.0 * 1e4
        net05 = net04 + buf04 - buf05
        netgate05 = net05 >= MIN_NET_EDGE_BPS
        if zgate05:
            gate_acc["z_pass"] += 1
        if netgate05:
            gate_acc["net_pass"] += 1
        perp_gated05 = zgate05 and netgate05
        if perp_gated05:
            gate_acc["perp_gated"] += 1
            if day > COLLAPSE_START:
                gate_acc["perp_gated_collapse"] += 1

        f_gated = bool(f.get("gated"))
        if not (f_gated and perp_gated05):
            continue
        acc["contested"] += 1
        if in40:
            acc["contested40"] += 1
        fwd_net = f.get("net_executable_edge_bps")
        sel05 = PERP if net05 > fwd_net else FORWARD          # tie -> forward
        sel04 = FORWARD if f.get("selected") else PERP
        if sel05 != sel04:
            acc["flips"] += 1
            if in40:
                acc["flips40"] += 1
        if day <= COLLAPSE_START:
            acc["cont_ramp"] += 1
            if in40:
                acc["cont_ramp40"] += 1
            if sel05 == FORWARD:
                acc["fwd_sel_ramp"] += 1
                if in40:
                    acc["fwd_sel_ramp40"] += 1
        else:
            acc["cont_collapse"] += 1
            if in40:
                acc["cont_collapse40"] += 1
            if sel05 == FORWARD:
                acc["fwd_sel_collapse"] += 1
                if in40:
                    acc["fwd_sel_collapse40"] += 1
        if sel05 == PERP:
            acc["perp_sel"] += 1
            if in40:
                acc["perp_sel40"] += 1
        # full-window ex-post scoring (identical to research_sweep ranking)
        if day + int(H) > DAYS:
            continue
        fwd_carry = (f.get("detail") or {}).get("implied_apr")
        window = [funding[d] for d in range(day + 1, day + int(H) + 1) if d in funding]
        if fwd_carry is None or not window:
            continue
        perp_carry = sum(window) / len(window)
        sel_carry = fwd_carry if sel05 == FORWARD else perp_carry
        forgone = perp_carry if sel05 == FORWARD else fwd_carry
        hit = 1 if sel_carry > forgone + 1e-12 else 0
        acc["evaluated"] += 1
        acc["hits"] += hit
        if in40:
            acc["evaluated40"] += 1
            acc["hits40"] += hit
        if day > TOUCH_BOUNDARY:
            acc["touch_n"] += 1
            acc["touch_hits"] += hit
            if in40:
                acc["touch_n40"] += 1
                acc["touch_hits40"] += hit
        else:
            acc["avoid_n"] += 1
            acc["avoid_hits"] += hit
            if in40:
                acc["avoid_n40"] += 1
                acc["avoid_hits40"] += hit

print("=" * 72)
print("(2) WOULD-BE RANKING side under G1 (re-ranked from journaled state)")
print(f"    contested days     : {acc['contested']} (v0.4 journaled: 1902)")
print(f"    selection flips    : {acc['flips']} vs v0.4 (seeds 1..40: {acc['flips40']})")
print(f"    hit-rate  pooled   : {100.0*acc['hits']/max(acc['evaluated'],1):5.1f}%  "
      f"({acc['hits']}/{acc['evaluated']})   [v0.4 measured 11.7% pooled / 11.4% screening]")
print(f"    hit-rate  seeds1-40: {100.0*acc['hits40']/max(acc['evaluated40'],1):5.1f}%  "
      f"({acc['hits40']}/{acc['evaluated40']})   [v0.3 baseline 60.2% on the same seeds]")
print(f"    day-bucket decomposition (full-window contests, boundary d>{TOUCH_BOUNDARY}):")
print(f"      window avoids collapse (d<={TOUCH_BOUNDARY}): "
      f"{100.0*acc['avoid_hits']/max(acc['avoid_n'],1):5.1f}% ({acc['avoid_hits']}/{acc['avoid_n']})"
      f"   seeds1-40: {100.0*acc['avoid_hits40']/max(acc['avoid_n40'],1):5.1f}%")
print(f"      window touches collapse (d>{TOUCH_BOUNDARY}):  "
      f"{100.0*acc['touch_hits']/max(acc['touch_n'],1):5.1f}% ({acc['touch_hits']}/{acc['touch_n']})"
      f"   seeds1-40: {100.0*acc['touch_hits40']/max(acc['touch_n40'],1):5.1f}%")
print(f"    forward selection share: ramp {100.0*acc['fwd_sel_ramp']/max(acc['cont_ramp'],1):.1f}% "
      f"(v0.4: 91.8%) · collapse {100.0*acc['fwd_sel_collapse']/max(acc['cont_collapse'],1):.1f}% "
      f"(v0.4: 95.7%)")
print(f"    seeds1-40: ramp {100.0*acc['fwd_sel_ramp40']/max(acc['cont_ramp40'],1):.1f}% "
      f"(v0.3: 30.2%) · collapse {100.0*acc['fwd_sel_collapse40']/max(acc['cont_collapse40'],1):.1f}% "
      f"(v0.3: 79.5%)")

print("=" * 72)
print("(3) GATE side under G1 (implied from journaled components)")
print(f"    perp z-gate pass     : {100.0*gate_acc['z_pass']/max(gate_acc['perp_evals'],1):5.1f}% "
      f"(v0.4 journaled gated-in: 83.4%)")
print(f"    perp net-gate pass   : {100.0*gate_acc['net_pass']/max(gate_acc['perp_evals'],1):5.1f}%")
print(f"    perp gated-in (both) : {100.0*gate_acc['perp_gated']/max(gate_acc['perp_evals'],1):5.1f}%")
print(f"    perp gated-in, collapse-phase evals only: "
      f"{100.0*gate_acc['perp_gated_collapse']/max(gate_acc['perp_evals_collapse'],1):5.1f}% "
      f"({gate_acc['perp_gated_collapse']}/{gate_acc['perp_evals_collapse']})")
