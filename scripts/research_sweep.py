#!/usr/bin/env python3
"""Multi-seed research sweep — the v0.2 research layer (SYNTHETIC, paper-only).

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

A stale per-seed journal is removed before its run so that one sweep = one
file = one audit trail (the journal itself appends; nothing here weakens its
write-time validation). Runs are bit-reproducible: seeds are explicit, no
time-based seeds anywhere; only the journal wall-clock timestamps and
``generated_at`` move between sweeps.

Everything printed and written is a diagnostic of the MACHINERY on
deterministic synthetic worlds — never evidence about any market. Numbers
are reported AS COMPUTED; no parameter is tuned to make a statistic look
good (in particular the z-gate calibration is an honesty check, not a
score).

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
from quant_arb.pipeline import RunConfig, run       # noqa: E402
from quant_arb.research.stats import dist_obj, mean  # noqa: E402

ENGINE_VERSION = "0.2.0"

# Nominal two-sided breach probability of a ±2σ band under a normal
# estimator (2·(1−Φ(2)) ≈ 4.55%) — the reference the empirical z-gate
# calibration rate is compared against.
NOMINAL_TWO_SIDED_PCT = 4.55

BANNER = """
================================================================
 quant-arb-engine · research sweep (SYNTHETIC, paper-only)
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

    Formulas (size = requested_size_usd):
      pnl_pct_of_notional        = signed_pnl_usd / size * 100
      locked_premium_bps         = locked_premium_usd / size * 1e4
      realized_minus_locked_bps  = (signed_pnl_usd - locked_premium_usd) / size * 1e4
      locked_premium_apr         = (locked_premium_bps / 1e4) * 365 / held_days
    """
    rc = payload.get("research_compare") or {}
    signed = _num(payload.get("signed_pnl_usd"))
    locked = _num(rc.get("locked_premium_usd"))
    perp = _num(rc.get("perp_alternative_apr"))
    held = int(payload["settle_day"]) - int(payload["opened_day"])
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
        "locked_premium_usd": None if locked is None else round(locked, 6),
        "locked_premium_bps": None if locked is None else round(locked / size_usd * 1e4, 4),
        "realized_minus_locked_bps": (None if (signed is None or locked is None)
                                      else round((signed - locked) / size_usd * 1e4, 4)),
        "perp_alternative_apr": None if perp is None else round(perp, 6),
        "locked_premium_apr": None,
        "quantity_chain_ok": payload.get("quantity_chain_ok"),
    }
    if locked is not None and held > 0:
        locked_apr = (locked / size_usd * 1e4 / 1e4) * 365.0 / held
        row["locked_premium_apr"] = round(locked_apr, 6)
    return row


def z_gate_checks(settled_payloads: list, threshold_z: float) -> tuple[int, int]:
    """(breaches, n_checks) for the estimator-σ honesty diagnostic.

    A check needs all three: ex_ante_apr, ex_ante_sigma_apr (v0.2.0 settle
    payload) and a valid perp_alternative_apr. Breach iff
    |perp_alternative_apr − ex_ante_apr| > threshold_z · ex_ante_sigma_apr.
    """
    breaches = 0
    n_checks = 0
    for p in settled_payloads:
        rc = p.get("research_compare") or {}
        ex_apr = _num(rc.get("ex_ante_apr"))
        ex_sigma = _num(rc.get("ex_ante_sigma_apr"))
        perp = _num(rc.get("perp_alternative_apr"))
        if ex_apr is None or ex_sigma is None or perp is None:
            continue
        n_checks += 1
        if abs(perp - ex_apr) > threshold_z * ex_sigma:
            breaches += 1
    return breaches, n_checks


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
    ap.add_argument("--seeds", type=int, default=40,
                    help="N → seeds 1..N (default 40)")
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

        rml = [r["realized_minus_locked_bps"] for r in rows
               if r["realized_minus_locked_bps"] is not None]
        per_seed.append({
            "seed": seed,
            "quotes": summary["quotes"],
            "gated": summary["opportunities_gated_in"],
            "risk_rejects": summary["risk_rejects"],
            "opened": summary["positions_opened"],
            "settled": summary["positions_settled"],
            "still_open": summary["positions_still_open"],
            "realized_usd": summary["realized_signed_pnl_usd"],
            "aggregate_pct": summary["aggregate_pct_of_notional"],
            "mean_pct": summary["mean_per_position_pct"],
            "realized_minus_locked_bps_mean": round(mean(rml), 4) if rml else None,
        })

        if seed == args.demo_seed:
            header = next((r for r in recs if r["type"] == "run_header"), None)
            opps = [r for r in recs if r["type"] == "opportunity"]
            demo = {
                "run_id": header["run_id"] if header else None,
                "journal_path": _rel(jpath, repo_root),
                "summary": summary,
                "settled": rows,
                "opportunity_example": opps[-1]["payload"] if opps else None,
            }

    # ------------------------------------------------------------- aggregates
    totals = {
        "quotes": sum(p["quotes"] for p in per_seed),
        "quote_events": 0,
        "gated": sum(p["gated"] for p in per_seed),
        "risk_rejects": sum(p["risk_rejects"] for p in per_seed),
        "opened": sum(p["opened"] for p in per_seed),
        "settled": sum(p["settled"] for p in per_seed),
        "still_open": sum(p["still_open"] for p in per_seed),
    }
    totals["quote_events"] = totals["quotes"] // 4   # 4 quote records per quoting day
    gate_fire_pct = (round(totals["gated"] / totals["quote_events"] * 100.0, 1)
                     if totals["quote_events"] else None)
    # Extra (allowed) diagnostic: gated opportunities per quote RECORD — the
    # same numerator over the raw quote count, for anyone who prefers that unit.
    gate_fire_per_quote_pct = (round(totals["gated"] / totals["quotes"] * 100.0, 1)
                               if totals["quotes"] else None)

    reject_reasons = [{"reason": reason, "count": count}
                      for reason, count in sorted(reject_counter.items(),
                                                  key=lambda kv: (-kv[1], kv[0]))]

    pnl_pct = [r["pnl_pct_of_notional"] for r in pooled_rows
               if r["pnl_pct_of_notional"] is not None]
    rml_all = [r["realized_minus_locked_bps"] for r in pooled_rows
               if r["realized_minus_locked_bps"] is not None]
    locked_minus_perp = [(r["locked_premium_apr"] - r["perp_alternative_apr"]) * 1e4
                         for r in pooled_rows
                         if r["locked_premium_apr"] is not None
                         and r["perp_alternative_apr"] is not None]
    settled_stats = {
        "n": len(pooled_rows),
        "pnl_pct_of_notional": dist_obj(pnl_pct),
        "realized_minus_locked_bps": dist_obj(rml_all),
        "locked_minus_perp_alt_apr_bps": dist_obj(locked_minus_perp),
    }
    n_skipped_perp = len(pooled_rows) - len(locked_minus_perp)
    if n_skipped_perp:
        settled_stats["n_skipped_perp_null"] = n_skipped_perp

    breaches, n_checks = z_gate_checks(pooled_payloads, threshold_z)
    z_gate = {
        "threshold_z": threshold_z,
        "nominal_two_sided_pct": NOMINAL_TWO_SIDED_PCT,
        "empirical_breach_pct": (round(breaches / n_checks * 100.0, 1)
                                 if n_checks else None),
        "n_checks": n_checks,
        "n_breaches": breaches,
        "definition": ("share of settled entries where |realized funding APR over the "
                       "held window - ex-ante EWMA APR| > threshold_z * ex-ante estimator sigma"),
    }

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ------------------------------------------------------ artifact 1: run
    assert demo is not None   # demo_seed validated to lie within 1..seeds
    run_doc = {
        "generated_at": generated_at,
        "engine_version": ENGINE_VERSION,
        "run_id": demo["run_id"],
        "journal_path": demo["journal_path"],
        "summary": demo["summary"],
        "settled": demo["settled"],
        "opportunity_example": demo["opportunity_example"],
    }

    # ---------------------------------------------------- artifact 2: sweep
    sweep_doc = {
        "generated_at": generated_at,
        "engine_version": ENGINE_VERSION,
        "params": {
            "seeds": seeds,
            "days": args.days,
            "tenor_days": args.tenor,
            "size_usd": args.size,
            "quote_every_days": cfg0.quote_every_days,
            "warmup_days": cfg0.warmup_days,
            "ewma_half_life_h": cfg0.ewma_half_life_h,
        },
        "totals": totals,
        "gate_fire_rate_pct": gate_fire_pct,
        "gate_fire_rate_per_quote_record_pct": gate_fire_per_quote_pct,
        "reject_reasons": reject_reasons,
        "settled_stats": settled_stats,
        "z_gate_calibration": z_gate,
        "per_seed": per_seed,
        "notes": {
            "synthetic": True,
            "epistemic_note": demo["summary"]["epistemic_note"],
            "unit_rule": demo["summary"]["unit_rule"],
        },
    }

    run_path = os.path.join(out_dir, "run-latest.json")
    sweep_path = os.path.join(out_dir, "sweep-latest.json")
    for path, doc in ((run_path, run_doc), (sweep_path, sweep_doc)):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, allow_nan=False)
            fh.write("\n")

    # ------------------------------------------------------------ console
    print(f"sweep            : seeds 1..{args.seeds} · {args.days} days · "
          f"tenor {args.tenor}d · size {args.size:,.0f} USD/position")
    print(f"journals         : {_rel(os.path.join(sweep_dir, 'run_seed_0001.jsonl'), repo_root)} "
          f".. run_seed_{seeds[-1]:04d}.jsonl")
    print("-" * 64)
    print(f"quotes           : {totals['quotes']} (quote events: {totals['quote_events']})")
    print(f"gated in         : {totals['gated']} "
          f"(gate fire rate: {_f(gate_fire_pct, '.1f')}% of quoting days)")
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
    print(f"  pnl % of notional   : mean {_f(d['mean'])} · std {_f(d['std'], '.4f')} · "
          f"p5 {_f(d['p5'], '.4f')} · p50 {_f(d['p50'], '.4f')} · p95 {_f(d['p95'], '.4f')}")
    d = ss["realized_minus_locked_bps"]
    print(f"  realized−locked bps : mean {_f(d['mean'])} · std {_f(d['std'], '.4f')} · "
          f"p5 {_f(d['p5'], '.4f')} · p95 {_f(d['p95'], '.4f')}  (dated-forward lock vs exit costs)")
    d = ss["locked_minus_perp_alt_apr_bps"]
    print(f"  locked−perp alt bps : mean {_f(d['mean'])} · p5 {_f(d['p5'], '.4f')} · "
          f"p95 {_f(d['p95'], '.4f')}  (opportunity cost, synthetic)")
    if "n_skipped_perp_null" in ss:
        print(f"  (n_skipped_perp_null = {ss['n_skipped_perp_null']})")
    print(f"z-gate calibration : empirical {_f(z_gate['empirical_breach_pct'], '.1f')}% "
          f"over {z_gate['n_checks']} checks (nominal 2σ ≈ {z_gate['nominal_two_sided_pct']}%) "
          f"— estimator-σ honesty check, reported as computed")
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
