#!/usr/bin/env python3
"""Research run — deterministic synthetic world, zero network, zero capital.

Example:
    python3 scripts/research_run.py
    python3 scripts/research_run.py --days 120 --seed 3 --tenor 60
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_arb.pipeline import RunConfig, run  # noqa: E402

BANNER = """
================================================================
 quant-arb-engine · research run (SYNTHETIC, paper-only)
 nothing here trades, nothing here spends, nothing here claims
 an edge. The output is a diagnostic of the MACHINERY on a
 deterministic mock world — not evidence about any market.
================================================================
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="quant-arb-engine synthetic research run")
    ap.add_argument("--days", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--tenor", type=int, default=90)
    ap.add_argument("--size", type=float, default=100_000.0,
                    help="requested notional per paper position (USD; research placeholder)")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "research", "artifacts")
    os.makedirs(out_dir, exist_ok=True)
    out_path = args.out or os.path.join(out_dir, f"run_{time.strftime('%Y%m%d_%H%M%S')}.jsonl")

    print(BANNER)
    cfg = RunConfig(days=args.days, seed=args.seed, tenor_days=args.tenor,
                    requested_size_usd=args.size)
    summary = run(cfg, out_path)

    print(f"journal          : {out_path}")
    print(f"seed / days      : {summary['seed']} / {summary['days']} (tenor {summary['tenor_days']}d)")
    print(f"quotes journaled : {summary['quotes']}")
    print(f"gated in         : {summary['opportunities_gated_in']} "
          f"(risk rejects: {summary['risk_rejects']})")
    print(f"positions        : opened {summary['positions_opened']} · "
          f"settled {summary['positions_settled']} · still open {summary['positions_still_open']}")
    print("-" * 64)
    print(f"realized signed PnL : {summary['realized_signed_pnl_usd']:+.2f} USD")
    print(f"aggregate % of notional (SUM over settled): {summary['aggregate_pct_of_notional']:+.4f} %")
    print(f"mean per position    : {summary['mean_per_position_pct']:+.4f} %")
    if summary["ex_ante_net_edge_mean_pct"] is not None:
        print(f"ex-ante net edge mean: {summary['ex_ante_net_edge_mean_pct']:+.4f} %")
    print("-" * 64)
    print("UNIT RULE   :", summary["unit_rule"])
    print("EPISTEMICS  :", summary["epistemic_note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
