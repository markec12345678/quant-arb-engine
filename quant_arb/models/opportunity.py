"""Universal opportunity model — one shape for every strategy family.

I-2: every leg records its notional **as executed** (qty × actual fill price).
I-6: ``requested_size_usd`` and ``executed_size_usd`` are distinct fields and
both are always present (NEW-17/NEW-18 lessons).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple

from .market_data import Instrument, Price


@dataclass(frozen=True)
class LegSpec:
    """A desired leg before execution."""

    instrument: Instrument
    direction: int                 # +1 long, -1 short

    def __post_init__(self) -> None:
        if self.direction not in (1, -1):
            raise ValueError("direction must be +1 or -1")


@dataclass(frozen=True)
class ExecutableLeg:
    """A leg as it would actually be executed (paper or real).

    ``qty`` is the executed quantity in base units (already rounded to the
    instrument's qty_precision); the executed notional is *derived* from
    qty × px so the two can never disagree.
    """

    instrument: Instrument
    direction: int
    qty: float                     # base units, rounded to qty_precision
    px: Price                      # the actual executable price (quote / fill)
    requested_size_usd: float      # I-6: what was asked for

    def __post_init__(self) -> None:
        if self.direction not in (1, -1):
            raise ValueError("direction must be +1 or -1")
        if not math.isfinite(self.qty) or self.qty <= 0:
            raise ValueError("qty must be positive")
        if self.requested_size_usd <= 0:
            raise ValueError("requested_size_usd must be positive")

    @property
    def executed_size_usd(self) -> float:   # I-2
        return self.qty * self.px.value

    def to_payload(self) -> dict:
        return {
            "instrument": self.instrument.symbol,
            "kind": self.instrument.kind,
            "venue": self.instrument.venue,
            "direction": self.direction,
            "qty": self.qty,
            "px": self.px.to_payload(),
            "requested_size_usd": self.requested_size_usd,          # I-6
            "executed_size_usd": round(self.executed_size_usd, 6),  # I-2
        }


@dataclass(frozen=True)
class CarryEstimate:
    """Expected carry (funding / premium income) over the horizon.

    ``locked`` is True when carry is a contract term (dated forward), in which
    case ``sigma_usd`` reflects only benchmark/early-exit uncertainty.
    """

    locked: bool
    expected_usd: float
    sigma_usd: float
    description: str

    def __post_init__(self) -> None:
        if self.sigma_usd < 0:
            raise ValueError("sigma_usd must be non-negative")

    def to_payload(self) -> dict:
        return {
            "locked": self.locked,
            "expected_usd": round(self.expected_usd, 6),
            "sigma_usd": round(self.sigma_usd, 6),
            "description": self.description,
        }


@dataclass(frozen=True)
class Opportunity:
    """Strategy-agnostic opportunity: what to trade, at what executable terms,
    with what expected net edge and confidence."""

    strategy_id: str
    ts: int
    legs: Tuple[ExecutableLeg, ...]
    carry: CarryEstimate
    gross_edge_bps: float
    net_executable_edge_bps: float
    horizon_days: float
    signal_z: Optional[float] = None
    confidence: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.legs:
            raise ValueError("opportunity requires at least one leg")
        if self.horizon_days <= 0:
            raise ValueError("horizon_days must be positive")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in [0, 1]")

    @property
    def requested_notional_usd(self) -> float:
        return sum(l.requested_size_usd for l in self.legs) / 2.0   # per-side notional

    def to_payload(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "ts": self.ts,
            "legs": [l.to_payload() for l in self.legs],
            "carry": self.carry.to_payload(),
            "gross_edge_bps": round(self.gross_edge_bps, 6),
            "net_executable_edge_bps": round(self.net_executable_edge_bps, 6),
            "horizon_days": self.horizon_days,
            "signal_z": None if self.signal_z is None else round(self.signal_z, 4),
            "confidence": round(self.confidence, 4),
            "requested_notional_usd": round(self.requested_notional_usd, 2),
            "metadata": dict(self.metadata),
        }
