"""Strategy interface — every strategy family produces the same opportunity shape."""

from __future__ import annotations

from typing import List, Protocol

from ..models.market_data import FundingObservation, RFQQuote
from ..models.opportunity import Opportunity


class ScanContext:
    """Everything a strategy may look at. Read-only, sourced, timestamped."""

    def __init__(self, *, ts: int, funding_obs: List[FundingObservation],
                 spot_bid: RFQQuote, spot_ask: RFQQuote,
                 fwd_bid: RFQQuote, fwd_ask: RFQQuote,
                 desk_quote_sigma_apr: float = 0.0) -> None:
        self.ts = ts
        self.funding_obs = funding_obs
        self.spot_bid = spot_bid
        self.spot_ask = spot_ask
        self.fwd_bid = fwd_bid
        self.fwd_ask = fwd_ask
        self.desk_quote_sigma_apr = desk_quote_sigma_apr


class Strategy(Protocol):
    strategy_id: str

    def scan(self, ctx: ScanContext, requested_size_usd: float,
             tenor_days: float) -> List[Opportunity]:
        ...
