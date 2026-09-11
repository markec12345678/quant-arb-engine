"""Forward Basis strategy — Route B, the primary research direction.

    CEX funding observations  (already-collected data, hour-normalized)
         ↓  EWMA + σ_level
    realized funding APR
         ↓  vs
    forward-implied APR       (the desk's priced carry, from the RFQ quote)
         ↓  gap z-score (v0.3.0: RETIRED as a gate, retained as a diagnostic — C4)
    ALL-IN EDGE waterfall     (gross premium − entry − exit − buffers)
         ↓  viability gate (pre-registered min_net_edge_bps)
    paper opportunity          (long spot @ desk ask + short forward @ desk bid)

Paper/research only. Carry is LOCKED at inception (dated forward): the
expected carry is the priced premium itself; σ covers benchmark and early-exit
mark risk, not funding-settlement uncertainty.

v0.3.0 decision record C4 — why the level z-gate was retired here: the dated
forward locks its carry at inception, so persistence of the funding LEVEL is
not required for the lock to be what it is. The level z actually measures
"the floating alternative looks better", which is the RANKING layer's job
(C5), not this family's gate. The z survives as ``signal_z`` / metadata
diagnostic, journaled in every family_eval record.
"""

from __future__ import annotations

from typing import List

from ..edge.all_in_edge import EdgeParams, evaluate_forward_basis
from ..edge.carry import carry_gap_z, ewma_funding, forward_implied_apr, horizon_sigma_apr
from ..models.market_data import PriceSource
from ..models.opportunity import CarryEstimate, ExecutableLeg, Opportunity
from .base import FamilyEvaluation, ScanContext


class ForwardBasisStrategy:
    strategy_id = "forward_basis_v1"

    def __init__(self, params: EdgeParams | None = None, ewma_half_life_h: float = 240.0) -> None:
        self.params = params or EdgeParams()
        self.ewma_half_life_h = ewma_half_life_h

    def evaluate(self, ctx: ScanContext, requested_size_usd: float,
                 tenor_days: float) -> FamilyEvaluation:
        p = self.params
        realized_apr, sigma_level_apr = ewma_funding(ctx.funding_obs, self.ewma_half_life_h)
        sigma_h_apr, sigma_diag = horizon_sigma_apr(ctx.funding_obs, tenor_days)

        spot_mid = ctx.spot_ask.ref_mid.value
        spot_ask = ctx.spot_ask.px.value
        fwd_bid = ctx.fwd_bid.px.value
        fwd_ask = ctx.fwd_ask.px.value
        fwd_mid = (fwd_bid + fwd_ask) / 2.0

        implied_apr = forward_implied_apr(spot_mid, fwd_mid, tenor_days)
        z_level = carry_gap_z(realized_apr, sigma_level_apr, implied_apr, ctx.desk_quote_sigma_apr)

        waterfall = evaluate_forward_basis(
            fwd_mid=fwd_mid, spot_mid=spot_mid, spot_ask=spot_ask, fwd_bid=fwd_bid,
            tenor_days=tenor_days, realized_sigma_apr=sigma_level_apr, params=p)

        # Pre-registered gate (C4): net edge only. The level z is a diagnostic.
        gates = {"net_edge_gate": waterfall.viable(p)}
        return FamilyEvaluation(
            strategy_id=self.strategy_id,
            gated=all(gates.values()),
            gates=gates,
            gross_edge_bps=waterfall.gross_edge_bps,
            net_executable_edge_bps=waterfall.net_executable_edge_bps,
            sigma_level_apr=sigma_level_apr,
            sigma_horizon_apr=sigma_h_apr,
            signal_z=z_level,
            detail={
                "realized_apr": round(realized_apr, 6),
                "implied_apr": round(implied_apr, 6),
                "gap_apr": round(realized_apr - implied_apr, 6),
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
        waterfall = ev.detail["waterfall"]   # rounded payload — display only
        z_level = ev.signal_z

        realized_apr = ev.detail["realized_apr"]
        sigma_level_apr = ev.sigma_level_apr
        sigma_h_apr = ev.sigma_horizon_apr
        implied_apr = ev.detail["implied_apr"]
        gates = dict(ev.gates)

        spot_mid = ctx.spot_ask.ref_mid.value
        spot_ask = ctx.spot_ask.px.value
        fwd_bid = ctx.fwd_bid.px.value

        # Paper execution: long spot at the desk ask, short the forward at the desk bid.
        # Quantity-chain discipline (NEW-17/R8 lesson): BOTH legs carry the SAME
        # base quantity, derived from the composite reference mid — a true hedge,
        # not a USD-notional match that leaves a residual delta.
        qty_base = round(requested_size_usd / spot_mid, 4)
        spot_leg = ExecutableLeg(
            instrument=ctx.spot_ask.instrument, direction=+1, qty=qty_base,
            px=ctx.spot_ask.px, requested_size_usd=requested_size_usd)
        fwd_leg = ExecutableLeg(
            instrument=ctx.fwd_bid.instrument, direction=-1, qty=qty_base,
            px=ctx.fwd_bid.px, requested_size_usd=requested_size_usd)

        locked_premium_usd = (fwd_bid - spot_ask) * qty_base   # cash PnL if held to settlement
        carry = CarryEstimate(
            locked=True,
            expected_usd=locked_premium_usd,
            sigma_usd=sigma_level_apr * requested_size_usd * tenor_days / 365.0,
            description="locked forward premium over tenor; σ = benchmark/early-exit mark risk",
        )

        confidence = min(1.0, max(z_level, 0.0) / (2.0 * p.min_z))
        opp = Opportunity(
            strategy_id=self.strategy_id,
            ts=ctx.ts,
            legs=(spot_leg, fwd_leg),
            carry=carry,
            gross_edge_bps=ev.gross_edge_bps,
            net_executable_edge_bps=ev.net_executable_edge_bps,
            horizon_days=tenor_days,
            signal_z=z_level,
            confidence=round(confidence, 4),
            metadata={
                "realized_apr": realized_apr,
                "realized_sigma_apr": round(sigma_level_apr, 6),
                "sigma_horizon_apr": round(sigma_h_apr, 6),
                "forward_implied_apr": implied_apr,
                "gap_apr": round(realized_apr - implied_apr, 6),
                "signal_z_level": round(z_level, 4),
                "ref_mid": spot_mid,
                "gates": gates,
                "waterfall": waterfall,
                "price_sources": {
                    "spot_ask": ctx.spot_ask.px.source.value,
                    "fwd_bid": ctx.fwd_bid.px.source.value,
                    "ref_mid": ctx.spot_ask.ref_mid.source.value,
                },
            },
        )
        return [opp]
