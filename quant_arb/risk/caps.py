"""Research risk caps — paper-only enforcement of the exposure discipline.

Every reject reason is enumerated and journaled; nothing is silently dropped.
These are research placeholders: real desk minimums/credit terms arrive from W0
and will be recorded in a decision record before they change anything here.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models.opportunity import Opportunity


@dataclass(frozen=True)
class ResearchCaps:
    max_notional_usd_per_position: float = 100_000.0   # research placeholder (desk min TBD in W0)
    max_tenor_days: int = 90                            # counterparty tenor cap
    max_open_positions: int = 5                         # concentration cap (single desk)
    desk: str = "SYNTH_DESK"


def check(opp: Opportunity, open_positions: int, caps: ResearchCaps) -> tuple[bool, list[str]]:
    """Return (ok, reasons). An empty reason list with ok=True means PASS."""
    reasons: list[str] = []
    notional = opp.requested_notional_usd
    if notional > caps.max_notional_usd_per_position:
        reasons.append(f"notional {notional:.0f} USD > cap {caps.max_notional_usd_per_position:.0f} USD")
    if opp.horizon_days > caps.max_tenor_days:
        reasons.append(f"tenor {opp.horizon_days:.0f}d > cap {caps.max_tenor_days}d")
    if open_positions >= caps.max_open_positions:
        reasons.append(f"open positions {open_positions} >= cap {caps.max_open_positions} (desk concentration)")
    return (len(reasons) == 0), reasons
