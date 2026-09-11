#!/usr/bin/env python3
"""Multi-seed research sweep — the v0.3 research layer (SYNTHETIC, paper-only).

Runs the deterministic pipeline for seeds 1..N (one invariant-enforced journal
per seed under research/artifacts/sweep_runs/), pools machinery-validation
statistics across every journal, and overwrites two STABLE artifact files:

  research/artifacts/run-latest.json    — representative seed, full detail
  research/artifacts/sweep-latest.json  — cross-seed aggregates

The two -latest.json files are DERIVED SUMMARIES (plain JSON, stable
filenames, overwritten each sweep). They are NOT journal-managed records and
carry no invariants of their own: the append-only journals written by
``quant_arb.pipeline.run`` remain the source of truth — this script only
READS them back. The tower dashboard consumes both artifacts read-only.

v0.3.0 additions (decision record docs/decision-record-v0.3.0.md):
- family census from family_eval records (both families, every quote day);
- RANKING hit-rate: on genuinely contested quote days (both families gated
  in), did the selected family's ex-post carry beat the forgone one's?
  Ex-post carries are re-derived from the journal alone (funding_daily window
  means vs the locked/implied premium) — truncated contests excluded+counted;
- DUAL z-gate calibration: the σ_level panel (the honest v0.2 finding, kept
  for audit) and the σ_H horizon panel (the redefined diagnostic);
- carry curve + per-day family edge series for the representative run;
- falsifiable predictions P1/P2/P3 from the decision record, scored.

v0.4.0 additions (decision record docs/decision-record-v0.4.0.md):
- TRIPLE z-gate calibration: σ_level (v0.2 audit) + σ_H iid-block (v0.3
  audit) + σ_H trend-aware (the redefined v0.4 diagnostic);
- HOLDOUT confirmation: seeds 1..40 are the screening set (the seeds the
  estimator candidates were screened on — disclosed in-sample), seeds
  41..60 are holdout, never used in any decision; panels and ranking are
  reported pooled AND split;
- ENTRY-HISTORY decomposition of the trend panel (breaches at entries with
  ≤45 vs >45 observed days) — the "residual is early-history" claim becomes
  a measured number;
- ESTIMATOR SCREENING block: the four candidate estimators measured on the
  frozen v0.3 journals, verbatim and labeled in-sample-disclosed;
- predictions P1..P5 from the v0.4 decision record, scored as measured.

v0.5.0 additions (decision record docs/decision-record-v0.5.0.md):
- QUADRUPLE z-gate calibration + the honest-cost panel: σ_level (v0.2 audit) +
  σ_H iid-block (v0.3 audit) + σ_H two-sided trend (v0.4 audit) + σ_H
  adverse-side (the redefined v0.5 diagnostic — ONE-SIDED downside breach,
  nominal 2.28%) + the upside-surprise panel (the un-charged favorable drift,
  reported as cost, explicitly NOT a calibration target);
- HOLDOUT LADDER: seeds 1..60 = screening set (the frozen v0.4 journals the
  candidate was screened on — both v0.4 sets are now decision-touched, so the
  ladder EXTENDS), seeds 61..80 = holdout, never used in any decision in any
  engine version; the ladder never re-rolls;
- RANKING reported pooled (1..80) AND screening (1..60) AND like-for-like
  (1..40 — the seed set the v0.3 60.2% and v0.4 11.4% baselines were measured
  on; used ONLY for the P3/P5 verdicts, never for a second headline);
- CONTEST DAY-BUCKET decomposition of the full-window hit-rate: window
  avoids collapse (d ≤ COLLAPSE_START − tenor) vs window touches collapse —
  the boundary is derived from the pre-registered regime boundary, not tuned;
- ESTIMATOR SCREENING block: the asymmetric-buffer candidates (S symmetric
  v0.4 baseline vs G1 adverse-side) measured on the frozen v0.4 journals,
  verbatim and labeled in-sample-disclosed;
- predictions P1..P5 from the v0.5 decision record, scored as measured — P4
  is the compound honest-price prediction (day-bucket gap AND upside panel).

A stale per-seed journal is removed before its run so that one sweep = one
file = one audit trail (the journal itself appends; nothing here weakens its
write-time validation). Runs are bit-reproducible: seeds are explicit, no
time-based seeds anywhere; only the journal wall-clock timestamps and
``generated_at`` move between sweeps.

Everything printed and written is a diagnostic of the MACHINERY on
deterministic synthetic worlds — never evidence about any market. Numbers
are reported AS COMPUTED; no parameter is tuned to make a statistic look
good (in particular both calibration panels are honesty checks, not scores).

Example:
    python3 scripts/research_sweep.py
    python3 scripts/research_sweep.py --seeds 10 --days 120 --tenor 60
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_arb.edge.all_in_edge import EdgeParams   # noqa: E402
from quant_arb.models.journal import read_all       # noqa: E402
from quant_arb.pipeline import (                    # noqa: E402
    FORWARD_FAMILY, PERP_FAMILY, RunConfig, run,
)
from quant_arb.research.stats import dist_obj, mean  # noqa: E402

ENGINE_VERSION = "0.5.0"

# Nominal two-sided breach probability of a ±2σ band under a normal
# estimator (2·(1−Φ(2)) ≈ 4.55%) — the reference the two-sided AUDIT panels
# are compared against.
NOMINAL_TWO_SIDED_PCT = 4.55

# Nominal ONE-SIDED breach probability of a −2σ adverse band under a normal
# estimator (1−Φ(2) ≈ 2.28%) — the reference the v0.5 redefined (adverse-side)
# panel is compared against.
NOMINAL_ONE_SIDED_PCT = 2.28

# World-v2 regime boundaries (decision record C1) — used ONLY for the phase
# split in the ranking/phase predictions and the pre-registered contest
# day-bucket boundary (COLLAPSE_START − tenor), never inside the pipeline.
COLLAPSE_START_DAY = 150

# Like-for-like seed set (1..40) — the seed set the v0.3 60.2% hit-rate and
# v0.4 11.4% hit-rate baselines were measured on. Used ONLY for the P3/P5
# verdicts, never for a second headline (decision record v0.5.0 C4).
LIKE_FOR_LIKE_SEEDS = 40

BANNER = """
================================================================
 quant-arb-engine · research sweep v0.5 (SYNTHETIC, paper-only)
 multi-seed machinery diagnostics on deterministic mock worlds
 — nothing here trades, nothing here spends, nothing here
 claims an edge. Numbers validate CODE PATHS, never markets.
================================================================
"""


def _num(x) -> float | None:
    """Coerce to float; None/NaN/inf/non-numeric → None (keeps JSON strict)."""
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    return xf if math.isfinite(xf) else None


def _rel(path: str, root: str) -> str:
    """Repo-relative, forward-slash path when possible (else absolute)."""
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        return path.replace(os.sep, "/")
    if rel.startswith(".."):
        return path.replace(os.sep, "/")
    return rel.replace(os.sep, "/")


def settled_row(payload: dict, size_usd: float) -> dict:
    """One settled position → the run-latest.json `settled[]` row.

    Family-appropriate fields carry None for the other family (explicit, not
    silently absent). Formulas (size = requested_size_usd):
      pnl_pct_of_notional        = signed_pnl_usd / size * 100
      locked_premium_bps         = locked_premium_usd / size * 1e4      (forward)
      realized_minus_locked_bps  = (signed_pnl − locked) / size * 1e4   (forward)
      funding_accrual_bps        = funding_accrual_usd / size * 1e4     (perp)
      realized_minus_expected_bps= (accrual − ex_ante_apr·held/365·size)/size·1e4 (perp)
    """
    rc = payload.get("research_compare") or {}
    signed = _num(payload.get("signed_pnl_usd"))
    locked = _num(rc.get("locked_premium_usd"))
    accrual = _num(payload.get("funding_accrual_usd"))
    perp = _num(rc.get("perp_alternative_apr"))
    ex_apr = _num(rc.get("ex_ante_apr"))
    held = int(payload["settle_day"]) - int(payload["opened_day"])
    is_perp = payload.get("strategy_id") == PERP_FAMILY

    expected_carry = (None if (ex_apr is None or held <= 0)
                      else ex_apr * held / 365.0 * size_usd)
    row = {
        "position_id": payload.get("position_id"),
        "strategy_id": payload.get("strategy_id"),
        "opened_day": payload.get("opened_day"),
        "settle_day": payload.get("settle_day"),
        "held_days": held,
        "signed_pnl_usd": None if signed is None else round(signed, 6),
        "pnl_pct_of_notional": None if signed is None else round(signed / size_usd * 100.0, 6),
        "ex_ante_net_edge_bps": payload.get("ex_ante_net_edge_bps"),
        "ex_ante_gross_edge_bps": payload.get("ex_ante_gross_edge_bps"),
        # forward family (locked carry)
        "locked_premium_usd": None if (is_perp or locked is None) else round(locked, 6),
        "locked_premium_bps": None if (is_perp or locked is None) else round(locked / size_usd * 1e4, 4),
        "realized_minus_locked_bps": (None if (is_perp or signed is None or locked is None)
                                      else round((signed - locked) / size_usd * 1e4, 4)),
        "locked_premium_apr": None,
        # perp family (floating carry)
        "funding_accrual_usd": None if (not is_perp or accrual is None) else round(accrual, 6),
        "funding_accrual_bps": None if (not is_perp or accrual is None) else round(accrual / size_usd * 1e4, 4),
        "realized_minus_expected_bps": (None if (not is_perp or accrual is None or expected_carry is None)
                                        else round((accrual - expected_carry) / size_usd * 1e4, 4)),
        # shared
        "perp_alternative_apr": None if perp is None else round(perp, 6),
        "quantity_chain_ok": payload.get("quantity_chain_ok"),
    }
    if not is_perp and locked is not None and held > 0:
        locked_apr = (locked / size_usd * 1e4 / 1e4) * 365.0 / held
        row["locked_premium_apr"] = round(locked_apr, 6)
    return row


def calibration_panels(seed_worlds: list, threshold_z: float, holdout_from: int) -> dict:
    """Quadruple σ honesty diagnostic + the honest-cost panel, re-derived from
    the journals alone (decision record v0.5.0 C4).

    ``seed_worlds`` = [(settled_payloads, funding_daily_map, seed), ...] — every
    seed is evaluated against ITS OWN world's funding stream. For every settled
    position with a FULL funding_daily window:
      window_mean_apr = mean(apr_printed over (opened_day, settle_day])
      LEVEL            breach ⇔ |window_mean − ex_ante_apr| > z · σ_level
      HORIZON-IID      breach ⇔ |window_mean − ex_ante_apr| > z · σ_H(iid-block)
      HORIZON-TWOSIDED breach ⇔ |window_mean − ex_ante_apr| > z · σ_H(|β̂|·H/2)
      HORIZON (v0.5)   breach ⇔  window_mean − ex_ante_apr  < −z · σ_down
      HORIZON-UPSIDE   breach ⇔  window_mean − ex_ante_apr  > +z · σ_down
    The level/iid/two-sided panels reproduce the v0.2/v0.3/v0.4 findings (all
    kept for audit); the adverse-side panel is the v0.5.0 redefined diagnostic
    (one-sided, nominal 2.28%); the upside panel reports the un-charged
    favorable drift as the honest cost of the optimistic bound — explicitly NOT
    a calibration target. Panels are computed POOLED, on the SCREENING SET
    (seeds < holdout_from — the seeds the estimator candidates were screened
    on) and on the HOLDOUT (seeds ≥ holdout_from — never used in any decision).
    Every panel decomposes breaches by entry-history length (≤45 vs >45
    observed days); the pre-registered decomposition of record is the one on
    the adverse-side panel.
    """
    # (panel key, research_compare σ key, label, sidedness)
    panels_spec = (
        ("panel_level", "ex_ante_sigma_apr", "level", "two"),
        ("panel_horizon_iid", "ex_ante_sigma_horizon_iid_apr", "horizon_iid", "two"),
        ("panel_horizon_twosided", "ex_ante_sigma_horizon_twosided_apr", "horizon_twosided", "two"),
        ("panel_horizon", "ex_ante_sigma_horizon_apr", "horizon_adverse", "down"),
        ("panel_horizon_upside", "ex_ante_sigma_horizon_apr", "horizon_adverse_upside", "up"),
    )
    subsets = {
        "pooled": lambda seed: True,
        "screening_set": lambda seed: seed < holdout_from,
        "holdout": lambda seed: seed >= holdout_from,
    }
    out: dict = {}
    for subset_name, keep in subsets.items():
        for panel_name, sig_key, label, sided in panels_spec:
            checks = breaches = 0
            eh = {"short_history_le_45d": [0, 0], "long_history_gt_45d": [0, 0]}
            for settled_payloads, funding_daily, seed in seed_worlds:
                if not keep(seed):
                    continue
                for p in settled_payloads:
                    rc = p.get("research_compare") or {}
                    ex_apr = _num(rc.get("ex_ante_apr"))
                    ex_sig = _num(rc.get(sig_key))
                    if ex_apr is None or ex_sig is None:
                        continue
                    days = [d for d in funding_daily
                            if p["opened_day"] < d <= p["settle_day"]]
                    if not days:
                        continue
                    wmean = sum(funding_daily[d] for d in days) / len(days)
                    n_entry_days = len([d for d in funding_daily
                                        if d <= p["opened_day"]])
                    bucket = ("short_history_le_45d" if n_entry_days <= 45
                              else "long_history_gt_45d")
                    diff = wmean - ex_apr
                    hit = {"two": abs(diff) > threshold_z * ex_sig,
                           "down": diff < -threshold_z * ex_sig,
                           "up": diff > threshold_z * ex_sig}[sided]
                    checks += 1
                    eh[bucket][0] += 1
                    if hit:
                        breaches += 1
                        eh[bucket][1] += 1
            entry_history = {}
            for bucket, (ck, br) in eh.items():
                entry_history[bucket] = {
                    "n_checks": ck, "n_breaches": br,
                    "empirical_breach_pct": round(br / ck * 100.0, 1) if ck else None,
                }
            out.setdefault(subset_name, {})[panel_name] = {
                "sigma": label,
                "sided": {"two": "two-sided", "down": "one-sided downside",
                          "up": "one-sided upside"}[sided],
                "n_checks": checks,
                "n_breaches": breaches,
                "empirical_breach_pct": round(breaches / checks * 100.0, 1) if checks else None,
                "entry_history": entry_history,
            }
    return out


def ranking_stats_accum(acc: dict, fam_by_day: dict, funding_daily: dict,
                        tenor: int, days: int) -> None:
    """Accumulate the ranking hit-rate from ONE seed's world into ``acc``.

    Contested quote day = both families gated in (a genuine contest). The
    ex-post carries over the SAME window (d, d+tenor]:
      forward (locked)   = implied_apr at day d (the premium the desk priced)
      perp (floating)    = mean(apr_printed over the window) — from funding_daily
    Hit = the SELECTED family's ex-post carry beat the forgone family's.
    Truncated contests (window crosses the run end) are excluded and counted.

    v0.5.0 (C4): every EVALUATED contest is also bucketed by whether its
    window touches the pre-registered collapse regime — boundary
    COLLAPSE_START − tenor (derived from the regime boundary, not tuned):
      avoids  ⇔ day ≤ 150 − tenor      touches ⇔ day > 150 − tenor
    """
    bucket_boundary = COLLAPSE_START_DAY - tenor
    for day, fams in fam_by_day.items():
        f, pe = fams.get(FORWARD_FAMILY), fams.get(PERP_FAMILY)
        if not (f and pe and f["gated"] and pe["gated"]):
            continue
        # P2 measures SELECTION by phase — every contested day counts, no
        # window requirement (the selection already happened ex-ante).
        acc["contested_total"] += 1
        if day <= COLLAPSE_START_DAY:
            acc["contests_ramp"] += 1
        else:
            acc["contests_collapse"] += 1
        if f["selected"]:
            if day <= COLLAPSE_START_DAY:
                acc["fwd_selected_ramp"] += 1
            else:
                acc["fwd_selected_collapse"] += 1
        # hit-rate needs the full ex-post window inside the run
        if day + tenor > days:
            acc["truncated"] += 1
            continue
        fwd_carry = _num((f.get("detail") or {}).get("implied_apr"))
        window = [funding_daily[d] for d in range(day + 1, day + tenor + 1)
                  if d in funding_daily]
        perp_carry = sum(window) / len(window) if window else None
        if fwd_carry is None or perp_carry is None:
            acc["truncated"] += 1        # cannot evaluate without both carries
            continue
        acc["contests"] += 1
        bucket = "avoids" if day <= bucket_boundary else "touches"
        acc[f"contests_{bucket}"] += 1
        sel_forward = bool(f["selected"])
        sel_carry, forgone_carry = (fwd_carry, perp_carry) if sel_forward else (perp_carry, fwd_carry)
        if sel_carry > forgone_carry + 1e-12:
            acc["hits"] += 1
            acc[f"hits_{bucket}"] += 1
        elif sel_carry < forgone_carry - 1e-12:
            acc["misses"] += 1
        else:
            acc["ties"] += 1


def ranking_finalize(acc: dict, tenor: int) -> dict:
    contests = acc["contests"]
    def _bucket(name: str) -> dict:
        ck = acc.get(f"contests_{name}", 0)
        hi = acc.get(f"hits_{name}", 0)
        return {
            "n_contests": ck,
            "hits": hi,
            "hit_rate_pct": round(hi / ck * 100.0, 1) if ck else None,
            "definition": ("window avoids collapse" if name == "avoids"
                            else "window touches collapse"),
        }
    return {
        "contested_days_total": acc["contested_total"],
        "contested_days_evaluated": contests,
        "truncated_excluded": acc["truncated"],
        "hits": acc["hits"],
        "misses": acc["misses"],
        "ties": acc["ties"],
        "hit_rate_pct": round(acc["hits"] / contests * 100.0, 1) if contests else None,
        "day_bucket": {
            "boundary_day": COLLAPSE_START_DAY - tenor,
            "window_avoids_collapse": _bucket("avoids"),
            "window_touches_collapse": _bucket("touches"),
            "definition": ("contest day split at COLLAPSE_START(150) − tenor, derived "
                           "from the pre-registered regime boundary, not tuned: avoids ⇔ "
                           "the full (d, d+tenor] window sits before the collapse phase"),
        },
        "forward_selection_share_ramp_pct": (round(acc["fwd_selected_ramp"] / acc["contests_ramp"] * 100.0, 1)
                                             if acc["contests_ramp"] else None),
        "forward_selection_share_collapse_pct": (round(acc["fwd_selected_collapse"] / acc["contests_collapse"] * 100.0, 1)
                                                 if acc["contests_collapse"] else None),
        "contests_ramp_phase": acc["contests_ramp"],
        "contests_collapse_phase": acc["contests_collapse"],
        "definition": ("contested day = both families gated in; hit-rate needs a full tenor "
                       "window (ex-post carries: forward = desk-implied APR at entry (locked), "
                       "perp = mean printed daily APR over the window; hit = the selected "
                       "family's ex-post carry beat the forgone family's); phase shares are "
                       "selection-based over ALL contested days (no window requirement) — "
                       "windows cannot cover the collapse phase (tenor exceeds the run tail)"),
    }


def _f(x, spec: str = "+.4f") -> str:
    """Format-or-'n/a' so None stats never crash the console report."""
    return ("n/a" if x is None else format(x, spec))


def _d(dist: dict) -> str:
    """One-line summary of a dist_obj (mean signed, dispersion unsigned)."""
    return (f"mean {_f(dist['mean'])} · std {_f(dist['std'], '.4f')} · "
            f"p5 {_f(dist['p5'], '.4f')} · p50 {_f(dist['p50'], '.4f')} · "
            f"p95 {_f(dist['p95'], '.4f')}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="quant-arb-engine multi-seed research sweep (synthetic, paper-only)")
    ap.add_argument("--seeds", type=int, default=80,
                    help="N → seeds 1..N (default 80: screening 1..60 + holdout 61..80)")
    ap.add_argument("--holdout-from", type=int, default=61,
                    help="first holdout seed (pre-registered 61; seeds below = screening set)")
    ap.add_argument("--days", type=int, default=200)
    ap.add_argument("--tenor", type=int, default=90)
    ap.add_argument("--size", type=float, default=100_000.0,
                    help="requested notional per paper position (USD)")
    ap.add_argument("--demo-seed", type=int, default=7,
                    help="representative seed detailed in run-latest.json")
    ap.add_argument("--out-dir", type=str, default=None,
                    help="artifact directory (default research/artifacts at repo root)")
    args = ap.parse_args()
    if args.seeds < 1:
        ap.error("--seeds must be >= 1")
    if not (2 <= args.holdout_from <= args.seeds):
        ap.error(f"--holdout-from must lie within 2..{args.seeds}")
    if not (1 <= args.demo_seed <= args.seeds):
        ap.error(f"--demo-seed must lie within 1..{args.seeds}")

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = args.out_dir or os.path.join(repo_root, "research", "artifacts")
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(repo_root, out_dir)
    sweep_dir = os.path.join(out_dir, "sweep_runs")
    os.makedirs(sweep_dir, exist_ok=True)

    seeds = list(range(1, args.seeds + 1))
    cfg0 = RunConfig(days=args.days, seed=seeds[0], tenor_days=args.tenor,
                     requested_size_usd=args.size)
    threshold_z = EdgeParams().min_z   # pre-registered gate constant, not a sweep knob

    print(BANNER)

    per_seed: list[dict] = []
    reject_counter: Counter = Counter()
    pooled_rows: list[dict] = []
    pooled_payloads: list[dict] = []
    fam_totals: Counter = Counter()
    seed_worlds: list = []                    # [(settled_payloads, funding_daily, seed), ...]
    rank_acc = {"contested_total": 0, "contests": 0, "truncated": 0, "hits": 0, "misses": 0, "ties": 0,
                "contests_ramp": 0, "contests_collapse": 0,
                "fwd_selected_ramp": 0, "fwd_selected_collapse": 0,
                "contests_avoids": 0, "hits_avoids": 0, "contests_touches": 0, "hits_touches": 0}
    # screening-set twin (seeds 1..holdout_from-1) — the frozen v0.4 journals
    # the asymmetric-buffer candidate was screened on (disclosed in-sample).
    rank_acc_screening = {k: 0 for k in rank_acc}
    # like-for-like twin (seeds 1..40) — the seed set the v0.3 60.2 % and v0.4
    # 11.4 % baselines were measured on; used ONLY for the P3/P5 verdicts,
    # never for a second headline (decision record v0.5.0 C4).
    rank_acc_like = {k: 0 for k in rank_acc}
    demo = None

    for seed in seeds:
        cfg = RunConfig(days=args.days, seed=seed, tenor_days=args.tenor,
                        requested_size_usd=args.size)
        jpath = os.path.join(sweep_dir, f"run_seed_{seed:04d}.jsonl")
        if os.path.exists(jpath):
            os.remove(jpath)   # one sweep = one file = one audit trail per seed
        summary = run(cfg, jpath)

        recs = read_all(jpath)   # read-back: journals are the source of truth
        settled_payloads = [r["payload"] for r in recs if r["type"] == "position_settled"]
        for r in recs:
            if r["type"] == "decision" and r["payload"].get("action") == "reject":
                reject_counter.update(r["payload"].get("reasons", []))
        rows = [settled_row(p, args.size) for p in settled_payloads]
        pooled_rows.extend(rows)
        pooled_payloads.extend(settled_payloads)

        # family_eval census + per-day pairing
        fam_by_day: dict = {}
        for r in recs:
            if r["type"] != "family_eval":
                continue
            p = r["payload"]
            fam_by_day.setdefault(p["day"], {})[p["strategy_id"]] = p
            fam_totals[f"{p['strategy_id']}:evals"] += 1
            if p["gated"]:
                fam_totals[f"{p['strategy_id']}:gated_in"] += 1
            if p["selected"]:
                fam_totals[f"{p['strategy_id']}:selected"] += 1
        fd = {r["payload"]["day"]: r["payload"]["apr_printed"]
              for r in recs if r["type"] == "funding_daily"}
        # every seed's ranking contests accumulate against its OWN funding stream
        ranking_stats_accum(rank_acc, fam_by_day, fd, args.tenor, args.days)
        if seed < args.holdout_from:
            ranking_stats_accum(rank_acc_screening, fam_by_day, fd, args.tenor, args.days)
        if seed <= LIKE_FOR_LIKE_SEEDS:
            ranking_stats_accum(rank_acc_like, fam_by_day, fd, args.tenor, args.days)
        seed_worlds.append((settled_payloads, fd, seed))

        per_seed.append({
            "seed": seed,
            "quotes": summary["quotes"],
            "family_evals": summary["family_evals"],
            "contested_days": summary["contested_days"],
            "selected_days": summary["selected_days"],
            "risk_rejects": summary["risk_rejects"],
            "opened": summary["positions_opened"],
            "settled": summary["positions_settled"],
            "still_open": summary["positions_still_open"],
            "realized_usd": summary["realized_signed_pnl_usd"],
            "aggregate_pct": summary["aggregate_pct_of_notional"],
            "mean_pct": summary["mean_per_position_pct"],
        })

        if seed == args.demo_seed:
            header = next((r for r in recs if r["type"] == "run_header"), None)
            opps = [r for r in recs if r["type"] == "opportunity"]
            carry_curve = [{"day": d, "apr_printed": round(fd[d], 6)}
                           for d in sorted(fd)]
            family_edge_series = []
            for day in sorted(fam_by_day):
                f = fam_by_day[day].get(FORWARD_FAMILY) or {}
                pe = fam_by_day[day].get(PERP_FAMILY) or {}
                family_edge_series.append({
                    "day": day,
                    "forward_net_edge_bps": f.get("net_executable_edge_bps"),
                    "perp_net_edge_bps": pe.get("net_executable_edge_bps"),
                    "selected": (FORWARD_FAMILY if f.get("selected")
                                 else PERP_FAMILY if pe.get("selected") else None),
                })
            demo = {
                "run_id": header["run_id"] if header else None,
                "journal_path": _rel(jpath, repo_root),
                "summary": summary,
                "settled": rows,
                "opportunity_example": opps[-1]["payload"] if opps else None,
                "carry_curve": carry_curve,
                "family_edge_series": family_edge_series,
                "funding_daily": fd,
                "fam_by_day": fam_by_day,
            }

    # ------------------------------------------------------------- aggregates
    totals = {
        "quotes": sum(p["quotes"] for p in per_seed),
        "quote_events": 0,
        "family_evals": sum(p["family_evals"] for p in per_seed),
        "contested_days": sum(p["contested_days"] for p in per_seed),
        "selected_days": sum(p["selected_days"] for p in per_seed),
        "risk_rejects": sum(p["risk_rejects"] for p in per_seed),
        "opened": sum(p["opened"] for p in per_seed),
        "settled": sum(p["settled"] for p in per_seed),
        "still_open": sum(p["still_open"] for p in per_seed),
    }
    totals["quote_events"] = totals["quotes"] // 4   # 4 quote records per quoting day
    selection_rate_pct = (round(totals["selected_days"] / totals["quote_events"] * 100.0, 1)
                          if totals["quote_events"] else None)

    reject_reasons = [{"reason": reason, "count": count}
                      for reason, count in sorted(reject_counter.items(),
                                                  key=lambda kv: (-kv[1], kv[0]))]

    # ranking: pooled across every seed's own world (contests vs own funding
    # stream) + the screening-set twin + the like-for-like twin for the
    # P3/P5 verdicts against the v0.3/v0.4 baselines
    ranking = ranking_finalize(rank_acc, args.tenor)
    ranking_screening = ranking_finalize(rank_acc_screening, args.tenor)
    ranking_like = ranking_finalize(rank_acc_like, args.tenor)

    # per-family settled distributions
    fam_rows = {FORWARD_FAMILY: [r for r in pooled_rows if r["strategy_id"] == FORWARD_FAMILY],
                PERP_FAMILY: [r for r in pooled_rows if r["strategy_id"] == PERP_FAMILY]}
    family_census = {
        "_definition": ("opened = opens that SETTLED within the run (the settled "
                        "population; the still-open remainder is in totals.still_open) — "
                        "same semantics as every engine version since v0.3.0"),
    }
    for sid in (FORWARD_FAMILY, PERP_FAMILY):
        rows_f = fam_rows[sid]
        pnl = [r["pnl_pct_of_notional"] for r in rows_f if r["pnl_pct_of_notional"] is not None]
        entry = {
            "evals": fam_totals[f"{sid}:evals"],
            "gated_in": fam_totals[f"{sid}:gated_in"],
            "selected": fam_totals[f"{sid}:selected"],
            "opened": sum(1 for p in pooled_payloads if p.get("strategy_id") == sid),
            "settled": len(rows_f),
            "settled_stats": {"n": len(rows_f), "pnl_pct_of_notional": dist_obj(pnl)},
        }
        if sid == FORWARD_FAMILY:
            rml = [r["realized_minus_locked_bps"] for r in rows_f
                   if r["realized_minus_locked_bps"] is not None]
            entry["settled_stats"]["realized_minus_locked_bps"] = dist_obj(rml)
        else:
            rme = [r["realized_minus_expected_bps"] for r in rows_f
                   if r["realized_minus_expected_bps"] is not None]
            acc = [r["funding_accrual_bps"] for r in rows_f
                   if r["funding_accrual_bps"] is not None]
            entry["settled_stats"]["realized_minus_expected_bps"] = dist_obj(rme)
            entry["settled_stats"]["funding_accrual_bps"] = dist_obj(acc)
        family_census[sid] = entry

    pnl_pct = [r["pnl_pct_of_notional"] for r in pooled_rows
               if r["pnl_pct_of_notional"] is not None]
    settled_stats = {"n": len(pooled_rows), "pnl_pct_of_notional": dist_obj(pnl_pct)}

    panels = calibration_panels(seed_worlds, threshold_z, args.holdout_from)
    pooled = panels["pooled"]
    level_b = pooled["panel_level"]["empirical_breach_pct"]
    iid_b = pooled["panel_horizon_iid"]["empirical_breach_pct"]
    twosided_b = pooled["panel_horizon_twosided"]["empirical_breach_pct"]
    down_b = pooled["panel_horizon"]["empirical_breach_pct"]
    up_b = pooled["panel_horizon_upside"]["empirical_breach_pct"]
    z_gate = {
        "threshold_z": threshold_z,
        "nominal_two_sided_pct": NOMINAL_TWO_SIDED_PCT,
        "nominal_one_sided_pct": NOMINAL_ONE_SIDED_PCT,
        "panel_level": pooled["panel_level"],
        "panel_horizon_iid": pooled["panel_horizon_iid"],
        "panel_horizon_twosided": pooled["panel_horizon_twosided"],
        "panel_horizon": pooled["panel_horizon"],
        "panel_horizon_upside": pooled["panel_horizon_upside"],
        "holdout_split": {
            "holdout_seeds": f"{args.holdout_from}..{args.seeds}",
            "screening_set_seeds": f"1..{args.holdout_from - 1}",
            "screening_set_panel_horizon": panels["screening_set"]["panel_horizon"],
            "holdout_panel_horizon": panels["holdout"]["panel_horizon"],
            "screening_set_panel_horizon_iid": panels["screening_set"]["panel_horizon_iid"],
            "holdout_panel_horizon_iid": panels["holdout"]["panel_horizon_iid"],
            "screening_set_panel_horizon_twosided": panels["screening_set"]["panel_horizon_twosided"],
            "holdout_panel_horizon_twosided": panels["holdout"]["panel_horizon_twosided"],
            "screening_set_panel_horizon_upside": panels["screening_set"]["panel_horizon_upside"],
            "holdout_panel_horizon_upside": panels["holdout"]["panel_horizon_upside"],
            "definition": ("holdout ladder: seeds 1..60 = the frozen v0.4 journals the "
                           "candidate was screened on (both v0.4 sets are now "
                           "decision-touched, so the ladder EXTENDS — it never re-rolls); "
                           "seeds 61..80 = holdout, never used in any decision in any "
                           "engine version"),
        },
        "estimator_screening": {
            "source": "frozen v0.4 journals @ 2b12b34 — research/exploration/screen_asym_v05.py",
            "disclosure": "in-sample candidate screening on the same generator, performed "
                          "BEFORE the v0.5 decision record was sealed; the holdout design "
                          "in C4 is the mitigation",
            "candidates": [
                {"id": "S_symmetric", "estimand": "v0.4 baseline — both trend directions charged |beta_hat|·H/2",
                 "two_sided_breach_pct": 11.0, "mean_sigma_pp": 4.81,
                 "verdict": "baseline — kept as the audit value (the pessimistic bound of the "
                            "reversal-ignorance interval)"},
                {"id": "G1_adverse_side", "estimand": "falling trend charged in full max(0,−beta_hat)·H/2; "
                                            "rising uncharged (decision record C1)",
                 "downside_breach_pct": 0.0, "upside_surprise_pct": 21.2, "mean_sigma_pp": 3.23,
                 "verdict": "CHOSEN — the optimistic bound; no interior weight is grounded, "
                            "so none is used"},
            ],
            "residual_anatomy": "all 46 v0.4 residual breaches POSITIVE-direction — on the "
                                 "v0.4 population the symmetric term's protective work was "
                                 "pure upside over-pricing (the measured anatomy of the P4 "
                                 "refutation); would-be re-ranking under G1: hit-rate 62.8 % "
                                 "pooled / 61.9 % seeds 1..40, collapse forward share 69.7 % "
                                 "(v0.4: 95.7 %) — the beta_hat regime-turn lag (~10–15 d) "
                                 "measured as the honest price",
        },
        "definition": ("share of settled entries (full funding_daily window) where the "
                       "stated band is breached; σ_level = instantaneous estimator standard "
                       "error (the v0.2.0 finding, kept for audit), σ_H(iid) = overlapping-window "
                       "horizon dispersion (the v0.3.0 finding, kept for audit), σ_H(twosided) = "
                       "iid + |β̂|·H/2 two-sided trend charge (the v0.4.0 finding, kept for audit), "
                       "σ_down = iid + max(0,−β̂)·H/2 adverse-side trend charge (the v0.5.0 "
                       "redefined diagnostic — ONE-SIDED downside breach, nominal 2.28%). The "
                       "upside panel is the honest cost of the optimistic bound, reported, "
                       "NOT a calibration target"),
    }

    # -------------------------------------------- predictions P1..P5 (as measured)
    contested_share_pct = (round(totals["contested_days"] / totals["selected_days"] * 100.0, 1)
                           if totals["selected_days"] else None)
    sb = panels["screening_set"]["panel_horizon"]["empirical_breach_pct"]
    hb = panels["holdout"]["panel_horizon"]["empirical_breach_pct"]
    perp_evals = fam_totals[f"{PERP_FAMILY}:evals"]
    perp_gated_share = (round(fam_totals[f"{PERP_FAMILY}:gated_in"] / perp_evals * 100.0, 1)
                        if perp_evals else None)
    hit_like = ranking_like["hit_rate_pct"]
    hit_screening = ranking_screening["hit_rate_pct"]
    hit_pooled = ranking["hit_rate_pct"]
    avoids_hr = ranking["day_bucket"]["window_avoids_collapse"]["hit_rate_pct"]
    touches_hr = ranking["day_bucket"]["window_touches_collapse"]["hit_rate_pct"]
    fshare_collapse_like = ranking_like["forward_selection_share_collapse_pct"]
    fshare_collapse_screening = ranking_screening["forward_selection_share_collapse_pct"]
    p4a_ok = (avoids_hr is not None and touches_hr is not None
              and avoids_hr <= touches_hr - 20.0)
    p4b_ok = up_b is not None and up_b > 15.0
    p4_verdict = ("SUPPORTED" if (p4a_ok and p4b_ok)
                  else "REFUTED" if (avoids_hr is not None and touches_hr is not None
                                     and up_b is not None) else "UNDECIDED")
    predictions = {
        "P1": {
            "statement": "pooled downside-panel breach ≤ 8% (one-sided nominal 2.28%; disclosed "
                          "would-be 0.0% on the v0.4 settle population — the v0.5 population is "
                          "perp-heavy and includes late-ramp opens whose windows touch the collapse)",
            "pooled_downside_breach_pct": down_b,
            "verdict": ("SUPPORTED" if down_b is not None and down_b <= 8.0
                        else "REJECTED" if down_b is not None else "UNDECIDED"),
        },
        "P2": {
            "statement": "holdout (61..80) downside-panel breach within ±6 pp of the screening "
                          "set (1..60) — the estimator is not seed-idiosyncratic",
            "screening_set_breach_pct": sb,
            "holdout_breach_pct": hb,
            "delta_pp": None if (sb is None or hb is None) else round(hb - sb, 1),
            "verdict": ("SUPPORTED" if (sb is not None and hb is not None and abs(hb - sb) <= 6.0)
                        else "REJECTED" if (sb is not None and hb is not None) else "UNDECIDED"),
        },
        "P3": {
            "statement": "like-for-like (seeds 1..40) full-window contest hit-rate ≥ 50% "
                          "(v0.4: 11.4%; v0.3: 60.2%; disclosed would-be: 61.9%) — recovery to "
                          "a majority-correct ranking, claimed only at the majority bar",
            "hit_rate_pct": hit_like,
            "v0_4_baseline_pct": 11.4,
            "v0_3_baseline_pct": 60.2,
            "verdict": ("SUPPORTED" if hit_like is not None and hit_like >= 50.0
                        else "REFUTED" if hit_like is not None else "UNDECIDED"),
        },
        "P4": {
            "statement": "the honest price, COMPOUND — (a) hit-rate on window-avoids-collapse "
                          "contests ≤ hit-rate on window-touches contests − 20 pp (the early-flat "
                          "information limit concentrates the misses) AND (b) the upside surprise "
                          "panel > 15% (the un-charged favorable drift visible as frequent "
                          "positive surprises — the asymmetry mechanism's signature); measured on "
                          "the pooled (1..80) ranking, screening/like-for-like splits reported "
                          "alongside; reported, never patched",
            "avoids_hit_rate_pct": avoids_hr,
            "touches_hit_rate_pct": touches_hr,
            "gap_pp": None if (avoids_hr is None or touches_hr is None)
                      else round(avoids_hr - touches_hr, 1),
            "part_a_holds": p4a_ok,
            "upside_surprise_pct": up_b,
            "part_b_holds": p4b_ok,
            "verdict": p4_verdict,
        },
        "P5": {
            "statement": "forward share of contested selections in the collapse phase ≥ 60% "
                          "(v0.4: 95.7%; disclosed would-be: 69.7% — the transition leak is "
                          "priced in; the claim is the signed charge still takes over after the "
                          "β̂ lag, keeping the collapse majority-forward); like-for-like (1..40)",
            "forward_share_collapse_pct": fshare_collapse_like,
            "verdict": ("SUPPORTED" if (fshare_collapse_like is not None
                                        and fshare_collapse_like >= 60.0)
                        else "NOT SUPPORTED" if fshare_collapse_like is not None else "UNDECIDED"),
        },
    }

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ------------------------------------------------------ artifact 1: run
    run_doc = {
        "generated_at": generated_at,
        "engine_version": ENGINE_VERSION,
        "run_id": demo["run_id"],
        "journal_path": demo["journal_path"],
        "summary": demo["summary"],
        "settled": demo["settled"],
        "opportunity_example": demo["opportunity_example"],
        "carry_curve": demo["carry_curve"],
        "family_edge_series": demo["family_edge_series"],
    }

    # ---------------------------------------------------- artifact 2: sweep
    sweep_doc = {
        "generated_at": generated_at,
        "engine_version": ENGINE_VERSION,
        "params": {
            "seeds": seeds,
            "screening_set_seeds": [s for s in seeds if s < args.holdout_from],
            "holdout_seeds": [s for s in seeds if s >= args.holdout_from],
            "like_for_like_seeds": [s for s in seeds if s <= LIKE_FOR_LIKE_SEEDS],
            "days": args.days,
            "tenor_days": args.tenor,
            "size_usd": args.size,
            "quote_every_days": cfg0.quote_every_days,
            "warmup_days": cfg0.warmup_days,
            "ewma_half_life_h": cfg0.ewma_half_life_h,
            "world": "v2 (ramp 8→18% d30–120, flat→150, collapse 18→4% d150–180, flat 4%)",
            "sigma_horizon_method": "adverse-side (iid-block dispersion + max(0,−beta_hat)·H/2 "
                                    "falling-trend charge, rising uncharged; trend_window_days=60) "
                                    "— decision record v0.5.0 C1; the optimistic bound of the "
                                    "reversal-ignorance interval (v0.4 was the pessimistic bound)",
        },
        "totals": totals,
        "selection_rate_pct": selection_rate_pct,
        "contested_share_of_selected_days_pct": contested_share_pct,
        "reject_reasons": reject_reasons,
        "family_census": family_census,
        "ranking": ranking,
        "ranking_screening_set": ranking_screening,
        "ranking_like_for_like": ranking_like,
        "settled_stats": settled_stats,
        "z_gate_calibration": z_gate,
        "predictions": predictions,
        "per_seed": per_seed,
        "notes": {
            "synthetic": True,
            "epistemic_note": demo["summary"]["epistemic_note"],
            "unit_rule": demo["summary"]["unit_rule"],
            "stop_rule": "exactly ONE estimator change is pre-registered (v0.5.0 C1 — the "
                        "adverse-side charge); whatever the measured outcomes there are NO "
                        "reversal-weight iterations, NO interior weights, NO trend-window "
                        "retuning inside v0.5.0. If P1 fails the recorded finding is: the "
                        "optimistic bound under-protects the adverse side even in a world whose "
                        "reversals are rare and slow — and the answer for any real market is "
                        "not an interior weight chosen on synthetic data but W0's real feed. "
                        "The nominal is a property of a correct σ on the stated side; the "
                        "estimator is not a knob for reaching the nominal (decision record "
                        "STOP RULE)",
            "population_note": "v0.5 settle populations are perp-heavy and differ from v0.4's — "
                               "the frozen v0.4 numbers live at 2b12b34 and are never silently "
                               "re-labelled; each artifact states its engine_version",
        },
    }

    run_path = os.path.join(out_dir, "run-latest.json")
    sweep_path = os.path.join(out_dir, "sweep-latest.json")
    for path, doc in ((run_path, run_doc), (sweep_path, sweep_doc)):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, allow_nan=False)
            fh.write("\n")

    # ------------------------------------------------------------ console
    print(f"sweep            : seeds 1..{args.seeds} (screening 1..{args.holdout_from - 1} + "
          f"holdout {args.holdout_from}..{args.seeds}; like-for-like 1..{LIKE_FOR_LIKE_SEEDS}) · "
          f"{args.days} days · tenor {args.tenor}d · size {args.size:,.0f} USD/position")
    print(f"journals         : {_rel(os.path.join(sweep_dir, 'run_seed_0001.jsonl'), repo_root)} "
          f".. run_seed_{seeds[-1]:04d}.jsonl")
    print("-" * 64)
    print(f"quotes           : {totals['quotes']} (quote events: {totals['quote_events']})")
    print(f"family evals     : {totals['family_evals']} · gated-in family-days "
          f"{fam_totals[f'{FORWARD_FAMILY}:gated_in']}F/{fam_totals[f'{PERP_FAMILY}:gated_in']}P · "
          f"selected days {totals['selected_days']} (contested {totals['contested_days']})")
    print(f"risk rejects     : {totals['risk_rejects']}")
    print(f"positions        : opened {totals['opened']} · settled {totals['settled']} · "
          f"still open {totals['still_open']}")
    if reject_reasons:
        print("top reject reasons (all seeds, journaled decision records):")
        for i, rr in enumerate(reject_reasons[:5], 1):
            print(f"  {i}. {rr['count']:>6} × {rr['reason']}")
    print("-" * 64)
    ss = settled_stats
    print(f"settled (pooled) : n = {ss['n']}")
    d = ss["pnl_pct_of_notional"]
    print(f"  pnl % of notional   : {_d(d)}")
    for sid, short in ((FORWARD_FAMILY, "forward"), (PERP_FAMILY, "perp")):
        fc = family_census[sid]
        d = fc["settled_stats"]["pnl_pct_of_notional"]
        print(f"  {short:8s} settled  : n = {fc['settled']} · {_d(d)}")
        if sid == FORWARD_FAMILY:
            d = fc["settled_stats"]["realized_minus_locked_bps"]
            print(f"    realized−locked bps : {_d(d)}  (lock holds through settlement)")
        else:
            d = fc["settled_stats"]["realized_minus_expected_bps"]
            print(f"    accrual−expected bps: {_d(d)}  (floating carry vs ex-ante EWMA)")
    print("-" * 64)
    rk = ranking
    print(f"ranking          : contested {rk['contested_days_evaluated']} "
          f"(truncated excluded {rk['truncated_excluded']}) · "
          f"hit-rate {_f(rk['hit_rate_pct'], '.1f')}% · "
          f"hits {rk['hits']} / misses {rk['misses']} / ties {rk['ties']}")
    print(f"  by seed set   : pooled 1..{args.seeds} {_f(hit_pooled, '.1f')}% · "
          f"screening 1..{args.holdout_from - 1} {_f(hit_screening, '.1f')}% · "
          f"like-for-like 1..{LIKE_FOR_LIKE_SEEDS} {_f(hit_like, '.1f')}% "
          f"(v0.4: 11.4 · v0.3: 60.2)")
    db = rk["day_bucket"]
    print(f"  day buckets   : avoids d≤{db['boundary_day']} {_f(db['window_avoids_collapse']['hit_rate_pct'], '.1f')}% "
          f"({db['window_avoids_collapse']['hits']}/{db['window_avoids_collapse']['n_contests']}) · "
          f"touches d>{db['boundary_day']} {_f(db['window_touches_collapse']['hit_rate_pct'], '.1f')}% "
          f"({db['window_touches_collapse']['hits']}/{db['window_touches_collapse']['n_contests']})")
    print(f"  forward selected: ramp {_f(rk['forward_selection_share_ramp_pct'], '.1f')}% · "
          f"collapse {_f(rk['forward_selection_share_collapse_pct'], '.1f')}% of contests "
          f"(like-for-like collapse {_f(fshare_collapse_like, '.1f')}%)")
    print(f"z-gate calibration (quadruple + honest-cost panel, pooled):")
    print(f"  σ_level           : empirical {_f(level_b, '.1f')}% over {pooled['panel_level']['n_checks']} checks "
          f"(the v0.2.0 finding, kept for audit)")
    print(f"  σ_H (iid)         : empirical {_f(iid_b, '.1f')}% over {pooled['panel_horizon_iid']['n_checks']} checks "
          f"(the v0.3.0 finding, kept for audit)")
    print(f"  σ_H (two-sided)   : empirical {_f(twosided_b, '.1f')}% over {pooled['panel_horizon_twosided']['n_checks']} checks "
          f"(the v0.4.0 finding, kept for audit; nominal 2σ ≈ {NOMINAL_TWO_SIDED_PCT}%)")
    print(f"  σ_H (adverse)     : empirical {_f(down_b, '.1f')}% over {pooled['panel_horizon']['n_checks']} checks "
          f"(v0.5.0 redefined, one-sided; nominal −2σ ≈ {NOMINAL_ONE_SIDED_PCT}%)")
    print(f"  upside surprise   : empirical {_f(up_b, '.1f')}% over {pooled['panel_horizon_upside']['n_checks']} checks "
          f"(the honest cost of the optimistic bound — NOT a calibration target)")
    eh = pooled["panel_horizon"]["entry_history"]
    for bucket, label in (("short_history_le_45d", "entry history ≤ 45d"),
                          ("long_history_gt_45d", "entry history > 45d")):
        b = eh[bucket]
        print(f"    {label:20s}: {_f(b['empirical_breach_pct'], '.1f')}% "
              f"({b['n_breaches']}/{b['n_checks']})")
    print(f"  holdout split : screening-set 1..{args.holdout_from - 1} {_f(sb, '.1f')}% vs "
          f"holdout {args.holdout_from}..{args.seeds} {_f(hb, '.1f')}% "
          f"(Δ {_f(predictions['P2']['delta_pp'], '+.1f')} pp)")
    print("predictions (pre-registered in the v0.5.0 decision record, scored as measured):")
    for pid, pv in predictions.items():
        extra = ""
        if pid == "P4":
            extra = (f" [a: {_f(avoids_hr, '.1f')} vs {_f(touches_hr, '.1f')} "
                     f"(Δ {_f(predictions['P4']['gap_pp'], '+.1f')} pp) · "
                     f"b: {_f(up_b, '.1f')}%]")
        print(f"  {pid}: {pv['verdict']}{extra}")
    print("-" * 64)
    realized = [p["realized_usd"] for p in per_seed]
    if realized:
        print(f"per-seed realized : min {min(realized):+,.2f} / "
              f"median {sorted(realized)[len(realized) // 2]:+,.2f} / "
              f"max {max(realized):+,.2f} USD (synthetic)")
    print(f"artifacts         : {_rel(run_path, repo_root)}")
    print(f"                    {_rel(sweep_path, repo_root)}")
    print("-" * 64)
    print("UNIT RULE   :", sweep_doc["notes"]["unit_rule"])
    print("EPISTEMICS  :", sweep_doc["notes"]["epistemic_note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
