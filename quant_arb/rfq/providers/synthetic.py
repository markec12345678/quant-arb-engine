"""Synthetic RFQ generator — TEST ONLY, source="synthetic" hardwired (W0 §3).

Exists for exactly one purpose: exercising every schema path (quoted firm,
quoted indicative, rejected, expired, no_response; stale references; latency
jitter; optional spread) so the ingestion machinery is reviewable BEFORE any
real data arrives — the same purpose the mock feed serves for the pipeline
(README epistemics). Seeded and deterministic; every record carries
source="synthetic" and is structurally excluded from research aggregation.
"""

from __future__ import annotations

import random
from typing import Any, Dict, Iterator

from .base import FieldMap, RFQProvider, normalize

_DAY_MS = 86_400_000


class SyntheticRFQProvider(RFQProvider):
    """TEST ONLY. ``source`` is hardwired to 'synthetic' and cannot be changed."""

    name = "synthetic-test-generator"
    source = "synthetic"          # hardwired — the epistemic wall

    def __init__(self, n: int = 200, seed: int = 7, t0_ms: int = 1_767_225_600_000) -> None:
        # 2026-01-01T00:00:00Z fixed epoch, matching the mock feed convention
        self.n = n
        self.seed = seed
        self.t0_ms = t0_ms

    def iter_raw(self) -> Iterator[Dict[str, Any]]:
        rng = random.Random(self.seed)
        instruments = [("BTC-USD", "spot"), ("ETH-USD", "spot"),
                       ("BTC-USD-FWD-30D", "forward"), ("SOL-USD", "spot")]
        venues = ["DESK-A", "DESK-B", "DESK-C"]
        for i in range(self.n):
            sym, kind = instruments[rng.randrange(len(instruments))]
            venue = venues[rng.randrange(len(venues))]
            ts = self.t0_ms + int(i * 60_000 * (1.0 + rng.random() * 3.0))
            # reference market data is 50 ms .. 4 s old — never from the future
            reference_ts = ts - int(rng.uniform(50, 4000))
            ref_px = 100.0 * (1.0 + rng.gauss(0.0, 0.02)) * (10 if "BTC" in sym else 1)
            side = "buy" if rng.random() < 0.5 else "sell"
            notional = float(rng.choice([10_000, 25_000, 50_000, 100_000]))
            latency = round(rng.uniform(40, 900), 1)
            u = rng.random()
            payload: Dict[str, Any] = {
                "id": f"SYN-{i:06d}",
                "instrument": sym,
                "kind": kind,
                "venue": venue,
                "ts": ts,
                "side": side,
                "notional": notional,
                "reference_price": round(ref_px, 6),
                "reference_ts": reference_ts,
                "reference_source": rng.choice(["spot_book_mid", "composite_index"]),
                "latency_ms": latency,
            }
            if u < 0.70:      # quoted, mostly firm
                spread = round(rng.uniform(2, 18), 2)
                # desk quotes around the reference with a real edge distribution
                skew_bps = rng.gauss(0.0, 9.0) - (spread / 2.0) * (1 if side == "buy" else -1)
                px = ref_px * (1.0 + (skew_bps / 1e4) * (1 if side == "buy" else -1))
                payload.update({
                    "status": "quoted",
                    "price": round(px, 6),
                    "quote_type": "firm" if rng.random() < 0.8 else "indicative",
                    "expiry": ts + int(rng.uniform(5_000, 45_000)),
                    "fees_bps": round(rng.uniform(0, 12), 2),
                    "fees_included_in_price": rng.random() < 0.5,
                    "spread_bps": spread,
                    "notional_ccy": "USD", "price_ccy": "USD",
                })
            elif u < 0.85:    # rejected
                payload.update({"status": "rejected",
                                "reject_reason": rng.choice(
                                    ["size_over_limit", "instrument_not_supported",
                                     "risk_limit"])})
            elif u < 0.95:    # expired before answering
                payload.update({"status": "expired"})
            else:             # no response at all
                payload.update({"status": "timeout"})
            yield payload

    def records(self, field_map: FieldMap) -> Iterator[Any]:
        # The synthetic provider speaks its own canonical dialect, so it ships
        # its own map; the CLI-supplied one is accepted and ignored (documented
        # behaviour, not silent surprise).
        syn_map = FieldMap(
            rfq_id="id", instrument="instrument", venue="venue", ts="ts",
            side="side", requested_notional="notional", quoted_price="price",
            quote_type="quote_type", quote_expiry_ts="expiry",
            fees_pct="fees_bps", fees_in_bps=True,
            fees_included_in_price="fees_included_in_price",
            spread_bps="spread_bps", reference_price="reference_price",
            reference_ts="reference_ts", latency_ms="latency_ms",
            status="status", reject_reason="reject_reason",
            instrument_kind="kind", notional_ccy="notional_ccy",
            price_ccy="price_ccy", reference_source="reference_source",
            ts_is_epoch=True, expiry_is_epoch=True, reference_ts_is_epoch=True,
        )
        for raw in self.iter_raw():
            yield normalize(raw, syn_map, provider_source=self.source)
