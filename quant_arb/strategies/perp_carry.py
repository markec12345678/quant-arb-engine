"""Perp-carry strategy — the floating twin of Route B (v0.3.0, family C3).

    CEX funding observations  (already-collected data, hour-normalized)
         ↓  EWMA + σ_level            +  horizon σ_H (overlapping windows)
    expected funding APR over the tenor (FLOATING — not a contract term)
         ↓  vs
    zero carry (the honest benchmark for a floating leg)
         ↓  z_perp = E[y] / σ_H ≥ min_z   (persistence gate, pre-registered)
    ALL-IN EDGE waterfall      (gross expected carry − entry − exit − buffers)
         ↓  viability gate (pre-registered min_net_edge_bps)
    paper opportunity           (long spot @ desk ask + short CEX perp @ mark)

Paper/research only. The carry is NOT locked: realized funding accrues per
settlement print, and the horizon σ_H is genuine PnL risk — exactly the risk
the forward family pays a premium to remove. Ranking (pipeline, decision
record C5) decides which instrument expresses the carry view on a given day.
"""

from __future__ import annotations

import math
from typing import List

from ..edge.all_in_edge import EdgeParams, evaluate_perp_carry
from ..edge.carry import ewma_funding, horizon_sigma_trend_apr
from ..models.opportunity import CarryEstimate, ExecutableLeg, Opportunity
from .base import FamilyEvaluation, ScanContext


class PerpCarryStrategy:
    strategy_id = "perp_carry_v1"

    def __init__(self, params: EdgeParams | None = None, ewma_half_life_h: float = 240.0) -> None:
        self.params = params or EdgeParams()
        self.ewma_half_life_h = ewma_half_life_h

    def evaluate(self, ctx: ScanContext, requested_size_usd: float,
                 tenor_days: float) -> FamilyEvaluation:
        if ctx.perp_mark is None or ctx.perp_instrument is None:
            raise ValueError("perp_carry_v1 requires a perp mark + instrument in the scan context")

        p = self.params
        realized_apr, sigma_level_apr = ewma_funding(ctx.funding_obs, self.ewma_half_life_h)
        # v0.4.0 (decision record C1): trend-aware σ_H — dispersion + trend
        # continuation exposure. The v0.3 iid-block component is journaled
        # next to it as the audit value. One σ, one meaning, everywhere.
        sigma_h_apr, sigma_diag = horizon_sigma_trend_apr(ctx.funding_obs, tenor_days)
        sigma_h_iid = sigma_diag.get("sigma_iid_block", 0.0)

        spot_mid = ctx.spot_ask.ref_mid.value
        spot_ask = ctx.spot_ask.px.value

        waterfall = evaluate_perp_carry(
            spot_mid=spot_mid, spot_ask=spot_ask, expected_apr=realized_apr,
            horizon_sigma_apr=sigma_h_apr, tenor_days=tenor_days, params=p)

        # Pre-registered gates (C4): horizon persistence of the floating carry
        # vs zero, AND the all-in net-edge gate. Both must pass. With no
        # horizon history (σ_H = 0) persistence is UNPROVEN, not infinite —
        # the gate fails closed.
        if sigma_h_apr > 0:
            z_perp = realized_apr / sigma_h_apr
            z_gate = z_perp >= p.min_z
        else:
            z_perp = None
            z_gate = False
        gates = {
            "z_gate": z_gate,
            "net_edge_gate": waterfall.viable(p),
        }
        return FamilyEvaluation(
            strategy_id=self.strategy_id,
            gated=all(gates.values()),
            gates=gates,
            gross_edge_bps=waterfall.gross_edge_bps,
            net_executable_edge_bps=waterfall.net_executable_edge_bps,
            sigma_level_apr=sigma_level_apr,
            sigma_horizon_apr=sigma_h_apr,
            signal_z=None if (z_perp is None or math.isinf(z_perp)) else z_perp,
            detail={
                "expected_apr": round(realized_apr, 6),
                "sigma_horizon_iid_apr": round(sigma_h_iid, 6),
                "sigma_horizon_diag": sigma_diag,
                "waterfall": waterfall.to_payload(),
            },
        )

    def scan(self, ctx: ScanContext, requested_size_usd: float,
             tenor_days: float) -> List[Opportunity]:
        ev = self.evaluate(ctx, requested_size_usd, tenor_days)
        if not ev.gated:
            return []
        p = self.params

        realized_apr = ev.detail["expected_apr"]
        sigma_level_apr = ev.sigma_level_apr
        sigma_h_apr = ev.sigma_horizon_apr
        sigma_h_iid = ev.detail.get("sigma_horizon_iid_apr", 0.0)
        gates = dict(ev.gates)
        z_perp = ev.signal_z if ev.signal_z is not None else 0.0   # gated-in implies z ≥ min_z

        spot_mid = ctx.spot_ask.ref_mid.value
        spot_ask = ctx.spot_ask.px.value

        # Paper execution: long spot at the desk ask (RFQ — fees embedded in
        # the crossing, I-4) + short the CEX perp at its mark (fees are explicit
        # waterfall lines). Quantity chain (NEW-17/R8): BOTH legs carry the SAME
        # base quantity — a true delta hedge, not a USD-notional match.
        qty_base = round(requested_size_usd / spot_mid, 4)
        spot_leg = ExecutableLeg(
            instrument=ctx.spot_ask.instrument, direction=+1, qty=qty_base,
            px=ctx.spot_ask.px, requested_size_usd=requested_size_usd)
        perp_leg = ExecutableLeg(
            instrument=ctx.perp_instrument, direction=-1, qty=qty_base,
            px=ctx.perp_mark, requested_size_usd=requested_size_usd)

        expected_carry_usd = realized_apr * tenor_days / 365.0 * requested_size_usd
        carry = CarryEstimate(
            locked=False,
            expected_usd=expected_carry_usd,
            sigma_usd=sigma_h_apr * tenor_days / 365.0 * requested_size_usd,
            description="floating funding carry over tenor; σ_H = trend-aware horizon σ "
                        "(dispersion + trend-continuation exposure, v0.4.0 C1)",
        )

        confidence = min(1.0, z_perp / (2.0 * p.min_z))   # monotone in persistence
        opp = Opportunity(
            strategy_id=self.strategy_id,
            ts=ctx.ts,
            legs=(spot_leg, perp_leg),
            carry=carry,
            gross_edge_bps=ev.gross_edge_bps,
            net_executable_edge_bps=ev.net_executable_edge_bps,
            horizon_days=tenor_days,
            signal_z=ev.signal_z,
            confidence=round(confidence, 4),
            metadata={
                "expected_apr": realized_apr,
                "sigma_level_apr": round(sigma_level_apr, 6),
                "sigma_horizon_apr": round(sigma_h_apr, 6),
                "sigma_horizon_iid_apr": round(sigma_h_iid, 6),
                "ref_mid": spot_mid,
                "gates": gates,
                "waterfall": ev.detail["waterfall"],
                "price_sources": {
                    "spot_ask": ctx.spot_ask.px.source.value,
                    "perp_mark": ctx.perp_mark.source.value,
                    "ref_mid": ctx.spot_ask.ref_mid.source.value,
                },
            },
        )
        return [opp]
