"""Strategy interface — every strategy family produces the same opportunity shape."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Protocol

from ..models.market_data import FundingObservation, Instrument, Price, RFQQuote
from ..models.opportunity import Opportunity


@dataclass(frozen=True)
class FamilyEvaluation:
    """v0.3.0 (decision record C5/C6): the ex-ante evaluation of one family on
    one quote day — journaled for EVERY family EVERY quote day, gated or not.

    This is the full decision audit: the ranking layer's inputs, the gates'
    verdicts, and both sigmas (level vs horizon — two different MEANINGS, see
    edge/carry.py) travel together so nothing about the choice is implicit.
    """

    strategy_id: str
    gated: bool
    gates: Mapping[str, bool]
    gross_edge_bps: float
    net_executable_edge_bps: float
    sigma_level_apr: float
    sigma_horizon_apr: float
    signal_z: Optional[float] = None
    detail: Mapping[str, Any] = field(default_factory=dict)


class ScanContext:
    """Everything a strategy may look at. Read-only, sourced, timestamped."""

    def __init__(self, *, ts: int, funding_obs: List[FundingObservation],
                 spot_bid: RFQQuote, spot_ask: RFQQuote,
                 fwd_bid: RFQQuote, fwd_ask: RFQQuote,
                 perp_mark: Price | None = None,
                 perp_instrument: Instrument | None = None,
                 desk_quote_sigma_apr: float = 0.0) -> None:
        self.ts = ts
        self.funding_obs = funding_obs
        self.spot_bid = spot_bid
        self.spot_ask = spot_ask
        self.fwd_bid = fwd_bid
        self.fwd_ask = fwd_ask
        # v0.3.0: the floating-carry instrument (decision record C3). Optional
        # so older feed surfaces keep working; perp_carry_v1 requires both.
        self.perp_mark = perp_mark
        self.perp_instrument = perp_instrument
        self.desk_quote_sigma_apr = desk_quote_sigma_apr


class Strategy(Protocol):
    strategy_id: str

    def evaluate(self, ctx: ScanContext, requested_size_usd: float,
                 tenor_days: float) -> FamilyEvaluation:
        ...

    def scan(self, ctx: ScanContext, requested_size_usd: float,
             tenor_days: float) -> List[Opportunity]:
        ...
