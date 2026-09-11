"""ALL-IN EDGE waterfall — the R8 lesson as a first-class module.

    gross edge
      − entry fees          (crossing the RFQ quotes, mid-to-mid)
      − exit fees           (unwind / settlement crossing)
      − slippage buffer     (research estimate)
      − carry uncertainty   (k·σ of the carry/benchmark estimate over the tenor)
      − execution risk      (research estimate: rejects, requotes, TTL expiry)
      = net executable edge

Every subtraction is an explicit line item; nothing is silently folded into
the gross number (I-4: costs counted exactly once).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EdgeParams:
    """Pre-registered gate constants (W2 mirror). Changed only by recorded decision."""

    exit_cost_bps: float = 8.0            # expected unwind/settlement crossing
    carry_uncertainty_k: float = 1.0      # σ multiplier for the carry buffer
    slippage_buffer_bps: float = 3.0      # research estimate
    execution_risk_buffer_bps: float = 5.0  # research estimate (quote TTL, partial fills)
    min_net_edge_bps: float = 10.0        # W2-style pre-registered viability gate
    min_z: float = 2.0                    # statistical persistence gate


@dataclass(frozen=True)
class EdgeWaterfall:
    gross_edge_bps: float
    entry_cost_bps: float
    exit_cost_bps: float
    carry_uncertainty_buffer_bps: float
    slippage_buffer_bps: float
    execution_risk_buffer_bps: float

    @property
    def net_executable_edge_bps(self) -> float:
        return (self.gross_edge_bps - self.entry_cost_bps - self.exit_cost_bps
                - self.carry_uncertainty_buffer_bps - self.slippage_buffer_bps
                - self.execution_risk_buffer_bps)

    def viable(self, params: EdgeParams) -> bool:
        return self.net_executable_edge_bps >= params.min_net_edge_bps

    def to_payload(self) -> dict:
        return {
            "gross_edge_bps": round(self.gross_edge_bps, 4),
            "entry_cost_bps": round(self.entry_cost_bps, 4),
            "exit_cost_bps": round(self.exit_cost_bps, 4),
            "carry_uncertainty_buffer_bps": round(self.carry_uncertainty_buffer_bps, 4),
            "slippage_buffer_bps": round(self.slippage_buffer_bps, 4),
            "execution_risk_buffer_bps": round(self.execution_risk_buffer_bps, 4),
            "net_executable_edge_bps": round(self.net_executable_edge_bps, 4),
        }


def evaluate_forward_basis(*, fwd_mid: float, spot_mid: float, spot_ask: float, fwd_bid: float,
                           tenor_days: float, realized_sigma_apr: float,
                           params: EdgeParams) -> EdgeWaterfall:
    """Waterfall for a long-spot + short-forward cash-and-carry.

    gross  = (fwd_mid − spot_mid) / spot_mid           — the priced premium, mid-to-mid
    entry  = crossing the spot ask + the forward bid   — counted once, here
    carry buffer = k · σ_apr · tenor/365               — benchmark + early-exit mark risk
    """
    if min(fwd_mid, spot_mid, spot_ask, fwd_bid) <= 0 or tenor_days <= 0:
        raise ValueError("prices and tenor must be positive")
    gross = (fwd_mid - spot_mid) / spot_mid * 1e4
    entry = (spot_ask - spot_mid) / spot_mid * 1e4 + (fwd_mid - fwd_bid) / fwd_mid * 1e4
    carry_buf = params.carry_uncertainty_k * realized_sigma_apr * tenor_days / 365.0 * 1e4
    return EdgeWaterfall(
        gross_edge_bps=gross,
        entry_cost_bps=entry,
        exit_cost_bps=params.exit_cost_bps,
        carry_uncertainty_buffer_bps=carry_buf,
        slippage_buffer_bps=params.slippage_buffer_bps,
        execution_risk_buffer_bps=params.execution_risk_buffer_bps,
    )
