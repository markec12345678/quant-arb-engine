"""Research pipeline v0.3 — feed → BOTH families → ranking → caps → journal.

One run = one deterministic synthetic world + one append-only journal + a
summary that obeys the epistemic and unit rules. Nothing here can trade.

v0.3.0 (decision record docs/decision-record-v0.3.0.md):
- World v2: carry ramps 8 % → 18 % (days 30–120), holds, then COLLAPSES
  18 % → 4 % (days 150–180) — the regime where locking a premium can beat
  floating. The instrument-choice question now exists.
- Every quote day BOTH families are evaluated ex-ante and journaled
  (family_eval: gated or not — full decision audit, nothing dropped).
- Ranking (C5): among gated-in families execute the higher net executable
  edge; tie → forward (locked carry preferred at equal net, pre-registered).
- funding_daily journals the observation stream (journal = source of truth
  for every research re-derivation downstream).
- perp_carry_v1 settles with signed printed-funding accrual (I-3).
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
from .strategies.base import FamilyEvaluation, ScanContext
from .strategies.forward_basis import ForwardBasisStrategy
from .strategies.perp_carry import PerpCarryStrategy

FORWARD_FAMILY = ForwardBasisStrategy.strategy_id      # "forward_basis_v1"
PERP_FAMILY = PerpCarryStrategy.strategy_id            # "perp_carry_v1"


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


def _world_v2_regime(day: int) -> float:
    """Synthetic regime v2 (decision record C1): build-up AND collapse.

    ramp 8 % → 18 % over days 30–120 (the desk lags → floating wins),
    flat 18 % to day 150,
    collapse 18 % → 4 % over days 150–180 (stale-high desk premiums → the
    dated forward's moment), flat 4 % to the end.

    This is the two-sided world the v0.2.0 one-sided regime could not offer:
    the instrument choice (lock vs float) now has a genuine answer that
    changes over time.
    """
    ramp = min(max((day - 30) / 90.0, 0.0), 1.0)
    if day <= 150:
        return 0.08 + ramp * 0.10
    if day <= 180:
        return 0.18 - (day - 150) / 30.0 * 0.14
    return 0.04


def run(cfg: RunConfig, out_path: str) -> Dict:
    feed = MockRFQFeed(seed=cfg.seed, params=cfg.feed_params, mean_fn=_world_v2_regime)
    strategies = {
        FORWARD_FAMILY: ForwardBasisStrategy(params=cfg.edge_params, ewma_half_life_h=cfg.ewma_half_life_h),
        PERP_FAMILY: PerpCarryStrategy(params=cfg.edge_params, ewma_half_life_h=cfg.ewma_half_life_h),
    }
    journal = Journal(out_path)

    open_positions: List[PaperPosition] = []
    settled_payloads: List[Dict] = []
    n_quotes = 0
    n_family_evals = 0
    n_rejects = 0
    contested_days = 0
    selected_days = 0
    family_counts: Dict[str, Dict[str, int]] = {
        sid: {"evals": 0, "gated_in": 0, "selected": 0, "opened": 0, "settled": 0}
        for sid in strategies
    }

    def _funding_daily_payload(day: int) -> Dict:
        obs = feed.funding_obs[-3:]          # this day's three 8h prints
        apr = sum(o.rate_hourly for o in obs) / len(obs) * 24.0 * 365.0
        return {"day": day, "apr_printed": round(apr, 6), "n_prints": len(obs)}

    for day in range(1, cfg.days + 1):
        feed.advance_day()
        journal.append("funding_daily", _funding_daily_payload(day))

        # settle positions whose tenor has elapsed
        still_open: List[PaperPosition] = []
        for pos in open_positions:
            if day >= pos.settle_day:
                settle_print = feed.settlement_print()
                spot_bid, _ = feed.spot_quotes()
                if pos.opportunity.strategy_id == PERP_FAMILY:
                    # Floating carry: accrual = Σ printed per-interval rates over
                    # the held window × qty × entry reference mid — the audited
                    # "% of trade notional" convention, a DOCUMENTED approximation
                    # (per-settlement notional actually varies with the mark).
                    perp_legs = [l for l in pos.legs if l.instrument.kind == "perp"]
                    if not perp_legs:
                        raise RuntimeError(f"{pos.position_id}: perp family position without a perp leg")
                    qty = perp_legs[0].qty
                    ref_mid = float(pos.opportunity.metadata.get("ref_mid", 0.0)) or settle_print.value
                    accrual = feed.printed_funding_between(pos.opened_ts, feed.now_ms) * qty * ref_mid
                    payload = pos.settle(
                        settle_ts=feed.now_ms, forward_settle_px=settle_print,
                        spot_exit_px=spot_bid.px, perp_exit_mark=feed.perp_mark(),
                        funding_accrual_usd=accrual)
                    alt_note = None
                else:
                    payload = pos.settle(
                        settle_ts=feed.now_ms, forward_settle_px=settle_print,
                        spot_exit_px=spot_bid.px)
                    alt_note = "locked forward premium vs realized funding path over the same window"

                payload["entry_legs"] = [l.to_payload() for l in pos.legs]
                # research comparison: what the OTHER carry expression would have paid
                alt_apr = feed.realized_funding_apr_between(pos.opened_day, pos.settle_day)
                md = pos.opportunity.metadata
                payload["research_compare"] = {
                    "perp_alternative_apr": None if alt_apr != alt_apr else round(alt_apr, 6),
                    "locked_premium_usd": round(pos.opportunity.carry.expected_usd, 6),
                    "note": alt_note or "floating carry: realized printed funding vs ex-ante EWMA; "
                                        "accrual = Σ rates × qty × entry ref mid (documented approximation)",
                    # ex-ante estimator state at entry — consumed by the z-gate
                    # calibration diagnostics in scripts/research_sweep.py
                    "ex_ante_apr": md.get("expected_apr", md.get("realized_apr")),
                    "ex_ante_sigma_apr": md.get("sigma_level_apr", md.get("realized_sigma_apr")),
                    "ex_ante_sigma_horizon_apr": md.get("sigma_horizon_apr"),
                    # v0.4.0 (C2): the v0.3 iid-block component at entry — the
                    # audit value next to the trend-aware gate σ, so the sweep
                    # can show BOTH panels without reconstruction.
                    "ex_ante_sigma_horizon_iid_apr": md.get("sigma_horizon_iid_apr"),
                }
                journal.append("position_settled", payload)
                settled_payloads.append(payload)
                family_counts[pos.opportunity.strategy_id]["settled"] += 1
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
                perp_mark=feed.perp_mark(),
                perp_instrument=feed.perp_instrument(),
                desk_quote_sigma_apr=cfg.feed_params.desk_quote_noise_apr,
            )

            # ---- evaluate BOTH families (C5/C6), THEN journal with selection known
            evals: Dict[str, FamilyEvaluation] = {
                sid: strat.evaluate(ctx, cfg.requested_size_usd, cfg.tenor_days)
                for sid, strat in strategies.items()
            }
            gated = {sid: ev for sid, ev in evals.items() if ev.gated}
            best_sid = None
            if gated:
                # C5: execute the higher net executable edge; tie → forward
                # (locked carry preferred at equal net — pre-registered).
                best_sid = max(gated, key=lambda sid: (gated[sid].net_executable_edge_bps,
                                                       sid == FORWARD_FAMILY))
                contested_days += 1 if len(gated) == 2 else 0
                selected_days += 1

            for sid, ev in evals.items():
                selected = sid == best_sid
                family_counts[sid]["evals"] += 1
                family_counts[sid]["gated_in"] += 1 if ev.gated else 0
                family_counts[sid]["selected"] += 1 if selected else 0
                journal.append("family_eval", {
                    "day": day,
                    "strategy_id": sid,
                    "gated": ev.gated,
                    "selected": selected,
                    "gates": dict(ev.gates),
                    "gross_edge_bps": round(ev.gross_edge_bps, 4),
                    "net_executable_edge_bps": round(ev.net_executable_edge_bps, 4),
                    "sigma_level_apr": round(ev.sigma_level_apr, 6),
                    "sigma_horizon_apr": round(ev.sigma_horizon_apr, 6),
                    "signal_z": None if ev.signal_z is None else round(ev.signal_z, 4),
                    "detail": dict(ev.detail),
                })
                n_family_evals += 1

            if best_sid is not None:
                opps = strategies[best_sid].scan(ctx, cfg.requested_size_usd, cfg.tenor_days)
                for opp in opps:
                    # audit trail: what this execution was ranked over (C5)
                    try:
                        opp.metadata["ranked_over"] = [sid for sid in gated if sid != best_sid]
                    except TypeError:
                        pass                      # metadata already an immutable mapping
                    journal.append("opportunity", _opp_payload(opp))
                    ok, reasons = risk_check(opp, len(open_positions), cfg.caps)
                    if ok:
                        pos = PaperPosition(
                            position_id=f"PP-{feed.day:04d}-{len(settled_payloads) + len(open_positions) + 1:03d}",
                            opportunity=opp, opened_day=day, settle_day=day + cfg.tenor_days,
                            opened_ts=feed.now_ms)
                        open_positions.append(pos)
                        family_counts[best_sid]["opened"] += 1
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
    ex_ante_net_mean = sum(ex_ante_net) / n_settled if n_settled else None

    quote_events = n_quotes // 4
    summary = {
        "synthetic": True,
        "seed": cfg.seed,
        "days": cfg.days,
        "tenor_days": cfg.tenor_days,
        "quotes": n_quotes,
        "quote_events": quote_events,
        "family_evals": n_family_evals,
        "gated_in_family_days": sum(c["gated_in"] for c in family_counts.values()),
        "contested_days": contested_days,
        "selected_days": selected_days,
        "risk_rejects": n_rejects,
        "positions_opened": sum(c["opened"] for c in family_counts.values()),
        "positions_settled": n_settled,
        "positions_still_open": len(open_positions),
        "per_family": {sid: dict(c) for sid, c in family_counts.items()},
        "realized_signed_pnl_usd": round(realized_pnl_usd, 2),
        "aggregate_pct_of_notional": round(aggregate_pct, 4),
        "mean_per_position_pct": round(mean_pct, 4),
        "ex_ante_net_edge_mean_pct": None if ex_ante_net_mean is None else round(ex_ante_net_mean, 4),
        "unit_rule": "aggregate = Σ(per-position % of notional) over settled positions; "
                     "mean = aggregate / N. Never read the aggregate as per-cycle.",
        "epistemic_note": EPISTEMIC_NOTE,
    }
    journal.append("run_summary", summary)
    journal.close()
    return summary


def _opp_payload(opp: Opportunity) -> dict:
    return opp.to_payload()
