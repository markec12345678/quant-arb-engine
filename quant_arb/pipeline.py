"""Research pipeline — feed → strategy → ALL-IN EDGE → risk caps → journal.

One run = one deterministic synthetic world + one append-only journal + a
summary that obeys the epistemic and unit rules. Nothing here can trade.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .edge.all_in_edge import EdgeParams
from .feeds.mock_rfq import DAY_MS, MockRFQFeed, MockRFQFeedParams
from .models.journal import EPISTEMIC_NOTE, Journal
from .models.opportunity import Opportunity
from .positions import PaperPosition
from .risk.caps import ResearchCaps, check as risk_check
from .strategies.base import ScanContext
from .strategies.forward_basis import ForwardBasisStrategy


@dataclass
class RunConfig:
    days: int = 200
    seed: int = 7
    tenor_days: int = 90
    quote_every_days: int = 5
    requested_size_usd: float = 100_000.0     # research placeholder (desk min TBD in W0)
    ewma_half_life_h: float = 240.0
    warmup_days: int = 15                     # no quotes before the estimator stabilizes
    feed_params: MockRFQFeedParams = field(default_factory=MockRFQFeedParams)
    edge_params: EdgeParams = field(default_factory=EdgeParams)
    caps: ResearchCaps = field(default_factory=ResearchCaps)


def _uptrend_then_flat(day: int) -> float:
    """Synthetic regime: the funding-APR mean ramps 8% → 18% between day 30 and
    120, then stays flat.

    The desk's slow pricing lags the ramp (gap opens) and catches up in the
    flat regime (gap closes) — so the demo shows both gated entries and
    rejections, exactly the shape Route B would face on real data.
    """
    ramp = min(max((day - 30) / 90.0, 0.0), 1.0)
    return 0.08 + ramp * 0.10


def run(cfg: RunConfig, out_path: str) -> Dict:
    feed = MockRFQFeed(seed=cfg.seed, params=cfg.feed_params, mean_fn=_uptrend_then_flat)
    strategy = ForwardBasisStrategy(params=cfg.edge_params, ewma_half_life_h=cfg.ewma_half_life_h)
    journal = Journal(out_path)

    open_positions: List[PaperPosition] = []
    settled_payloads: List[Dict] = []
    n_quotes = 0
    n_opportunities = 0
    n_rejects = 0

    for day in range(1, cfg.days + 1):
        feed.advance_day()

        # settle positions whose tenor has elapsed
        still_open: List[PaperPosition] = []
        for pos in open_positions:
            if day >= pos.settle_day:
                settle_print = feed.settlement_print()
                spot_bid, _ = feed.spot_quotes()
                payload = pos.settle(settle_ts=feed.now_ms,
                                      forward_settle_px=settle_print,
                                      spot_exit_px=spot_bid.px)
                payload["entry_legs"] = [l.to_payload() for l in pos.legs]
                # research comparison: what the perp alternative would have paid
                alt_apr = feed.realized_funding_apr_between(pos.opened_day, pos.settle_day)
                payload["research_compare"] = {
                    "perp_alternative_apr": None if alt_apr != alt_apr else round(alt_apr, 6),
                    "locked_premium_usd": round(pos.opportunity.carry.expected_usd, 6),
                    "note": "locked forward premium vs realized funding path over the same window",
                    # v0.2.0 research layer: ex-ante estimator state at entry (added keys
                    # only — backwards-compatible), consumed by the z-gate calibration
                    # diagnostic in scripts/research_sweep.py.
                    "ex_ante_apr": pos.opportunity.metadata.get("realized_apr"),
                    "ex_ante_sigma_apr": pos.opportunity.metadata.get("realized_sigma_apr"),
                }
                journal.append("position_settled", payload)
                settled_payloads.append(payload)
            else:
                still_open.append(pos)
        open_positions = still_open

        # quoting day
        if day >= cfg.warmup_days and day % cfg.quote_every_days == 0:
            spot_bid, spot_ask = feed.spot_quotes()
            fwd_bid, fwd_ask = feed.forward_quotes(cfg.tenor_days)
            for q in (spot_bid, spot_ask, fwd_bid, fwd_ask):
                journal.append("quote", q.to_payload())
                n_quotes += 1

            ctx = ScanContext(
                ts=feed.now_ms,
                funding_obs=feed.funding_obs,
                spot_bid=spot_bid, spot_ask=spot_ask,
                fwd_bid=fwd_bid, fwd_ask=fwd_ask,
                desk_quote_sigma_apr=cfg.feed_params.desk_quote_noise_apr,
            )
            opps = strategy.scan(ctx, cfg.requested_size_usd, cfg.tenor_days)
            for opp in opps:
                n_opportunities += 1
                journal.append("opportunity", _opp_payload(opp))
                ok, reasons = risk_check(opp, len(open_positions), cfg.caps)
                if ok:
                    pos = PaperPosition(
                        position_id=f"PP-{feed.day:04d}-{len(settled_payloads) + len(open_positions) + 1:03d}",
                        opportunity=opp, opened_day=day, settle_day=day + cfg.tenor_days)
                    open_positions.append(pos)
                    journal.append("position_opened", {
                        "position_id": pos.position_id,
                        "settle_ts": feed.now_ms + cfg.tenor_days * DAY_MS,
                        "legs": [l.to_payload() for l in opp.legs],
                        "opportunity": _opp_payload(opp),
                    })
                else:
                    n_rejects += 1
                    journal.append("decision", {
                        "action": "reject", "reasons": reasons,
                        "strategy_id": opp.strategy_id, "day": day,
                    })

    # ---------------------------------------------------------------- summary
    n_settled = len(settled_payloads)
    realized_pnl_usd = sum(p["signed_pnl_usd"] for p in settled_payloads)
    notional = cfg.requested_size_usd
    per_pos_pct = [p["signed_pnl_usd"] / notional * 100.0 for p in settled_payloads]
    aggregate_pct = sum(per_pos_pct)
    mean_pct = aggregate_pct / n_settled if n_settled else 0.0
    ex_ante_net = [p["ex_ante_net_edge_bps"] / 1e4 * 100.0 for p in settled_payloads]

    summary = {
        "synthetic": True,
        "seed": cfg.seed,
        "days": cfg.days,
        "tenor_days": cfg.tenor_days,
        "quotes": n_quotes,
        "opportunities_gated_in": n_opportunities,
        "risk_rejects": n_rejects,
        "positions_opened": n_opportunities - n_rejects,
        "positions_settled": n_settled,
        "positions_still_open": len(open_positions),
        "realized_signed_pnl_usd": round(realized_pnl_usd, 2),
        "aggregate_pct_of_notional": round(aggregate_pct, 4),
        "mean_per_position_pct": round(mean_pct, 4),
        "ex_ante_net_edge_mean_pct": round(sum(ex_ante_net) / n_settled, 4) if n_settled else None,
        "unit_rule": "aggregate = Σ(per-position % of notional) over settled positions; "
                     "mean = aggregate / N. Never read the aggregate as per-cycle.",
        "epistemic_note": EPISTEMIC_NOTE,
    }
    journal.append("run_summary", summary)
    journal.close()
    return summary


def _opp_payload(opp: Opportunity) -> dict:
    return opp.to_payload()
