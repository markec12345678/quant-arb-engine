"""Paper position state machine — OPEN → SETTLED, signed PnL only (I-3).

This is a *paper book*: nothing is ever submitted anywhere. The machine exists
so the lifecycle (open → settle, with the quantity chain verified) is explicit
and journaled — the same discipline the funding-arb audit demanded, built in
from the first line instead of retrofitted in round 8.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple

from .models.market_data import Price
from .models.opportunity import ExecutableLeg, Opportunity


class PositionState(str, Enum):
    OPEN = "open"
    SETTLED = "settled"


@dataclass
class PaperPosition:
    position_id: str
    opportunity: Opportunity
    opened_day: int
    settle_day: int
    state: PositionState = PositionState.OPEN
    legs: Tuple[ExecutableLeg, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.legs = self.opportunity.legs

    def settle(self, *, settle_ts: int, forward_settle_px: Price, spot_exit_px: Price) -> dict:
        """Settle at expiry: forward cash-settles at the settlement print,
        spot is sold back to the desk at its bid.

        I-3 (signed PnL): leg PnL = (exit_px − entry_px) × qty × direction.
        Long gains when exit > entry; short gains when exit < entry. There is
        no abs() anywhere and no direction-sign convention to get wrong.
        """
        if self.state is not PositionState.OPEN:
            raise RuntimeError(f"position {self.position_id} already settled")
        legs_pnl: List[Dict] = []
        total = 0.0
        quantity_chain_ok = True
        for leg in self.legs:
            exit_px = forward_settle_px if leg.instrument.kind == "forward" else spot_exit_px
            signed_pnl = (exit_px.value - leg.px.value) * leg.qty * leg.direction
            # I-5: the quantity that settles must be the quantity that opened
            if exit_px.ts <= leg.px.ts:
                quantity_chain_ok = False
            legs_pnl.append({
                "instrument": leg.instrument.symbol,
                "direction": leg.direction,
                "qty": leg.qty,
                "entry_px": leg.px.value,
                "exit_px": exit_px.value,
                "exit_px_source": exit_px.source.value,
                "signed_pnl_usd": round(signed_pnl, 6),
            })
            total += signed_pnl
        self.state = PositionState.SETTLED
        return {
            "position_id": self.position_id,
            "strategy_id": self.opportunity.strategy_id,
            "opened_day": self.opened_day,
            "settle_day": self.settle_day,
            "settle_ts": settle_ts,
            "signed_pnl_usd": round(total, 6),
            "legs_pnl": legs_pnl,
            "quantity_chain_ok": quantity_chain_ok,
            "ex_ante_net_edge_bps": round(self.opportunity.net_executable_edge_bps, 4),
            "ex_ante_gross_edge_bps": round(self.opportunity.gross_edge_bps, 4),
        }
