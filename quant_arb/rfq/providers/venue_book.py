"""OKX venue-book RFQ provider — the connected REAL source (W0 v0.7.0).

Design record: docs/w0-venue-source-connection.md (SEALED 2026-09-17 before
this code). The W0 record §3 shipped the REST-poller as a *slot* — "it lands
with W1 when the user connects a source". The source is now connected: OKX's
public order books (no credentials, public REST), the real, credential-free
quoting surface available in this environment.

One poll = 4 RFQ records: {BTC-USDT spot, BTC-USDT-PERP perp} × {buy, sell},
requested notional 10,000 USDT each. The mapping V-1…V-9 (sealed):

  quoted_price    depth VWAP of the levels that fill the notional
                  (buy walks asks, sell walks bids; swap levels are
                  contracts × ctVal — ctVal fetched live, preserved in raw)
  quote_type      "firm" — displayed resting liquidity is executable by a
                  taker at the snapshot instant
  quote_expiry    == ts — a public book carries no hold (instant validity)
  ts              the venue's own book timestamp (server ms)
  reference       the SAME book's mid (spot_book_mid / perp_book_mid),
                  reference_ts == ts (reference age exactly 0)
  spread_bps      (best ask − best bid) / mid × 1e4, same book
  fees_pct        the venue's published standard-tier taker fee (spot 0.10,
                  perp 0.05), fees_included_in_price=false, full provenance
                  (URLs + verification date) embedded in raw
  status          quoted | rejected(insufficient_depth) | no_response
                  (fetch failure — reference = freshest available: in-process
                  prior book, else the journal-supplied prior reference)
  rfq_id          okx:{instrument}:{side}:{book_ts} — deterministic on the
                  observation, so a retry of the SAME payload is refused by
                  R-1 instead of double-journaled

Instrument naming follows the W1 replay convention (C-1): spot "BTC-USDT",
perp "BTC-USDT-PERP" — the family root BTC-USDT is shared. venue tag "okx".

``source = "real"`` — the epistemic wall's single point of enforcement on
ingest. This provider NEVER places orders; it reads public market data only.
"""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from .base import FieldMap, RFQProvider

VENUE_TAG = "okx"
_BASE = "https://www.okx.com"
_USER_AGENT = "quant-arb-engine-w0-venue-poll/0.7.0 (public book reader; no orders)"

#: fees as reported by the venue's published schedule — verified 2026-09-17
#: from the live okx.com/fees schedule (spot regular taker 0.001) and OKX's
#: "Advance Notice: Spot and Futures Trading Fee Adjustment" announcement
#: (futures standard regular maker 0.0200% / taker 0.0500%; spot standard
#: regular maker 0.0800% / taker 0.1000%). Sealed V-7.
FEE_PROVENANCE = {
    "venue": "okx",
    "tier": "Regular user — Standard fee pairs",
    "spot_taker_pct": 0.10,
    "perp_taker_pct": 0.05,
    "verified_utc": "2026-09-17",
    "sources": [
        "https://www.okx.com/fees",
        "https://www.okx.com/help/advance-notice-spot-and-futures-trading-fee-adjustment",
    ],
    "note": "taker fees charged on top of the quoted price (not included)",
}


class VenueInstrument:
    """One quoted instrument of the connected venue (sealed §2)."""

    def __init__(self, symbol: str, kind: str, inst_id: str, reference_tag: str,
                 taker_fee_pct: float, needs_ctval: bool) -> None:
        self.symbol = symbol            # W1 convention symbol (C-1)
        self.kind = kind                # instrument_kind
        self.inst_id = inst_id          # OKX instId
        self.reference_tag = reference_tag
        self.taker_fee_pct = taker_fee_pct
        self.needs_ctval = needs_ctval  # swap: sizes are contracts × ctVal


#: the connected universe: one family (BTC-USDT), spot + perp, both quoted
#: every poll (sealed §2 / §7-2).
INSTRUMENTS: Tuple[VenueInstrument, ...] = (
    VenueInstrument(symbol="BTC-USDT", kind="spot", inst_id="BTC-USDT",
                    reference_tag="spot_book_mid", taker_fee_pct=0.10,
                    needs_ctval=False),
    VenueInstrument(symbol="BTC-USDT-PERP", kind="perp", inst_id="BTC-USDT-SWAP",
                    reference_tag="perp_book_mid", taker_fee_pct=0.05,
                    needs_ctval=True),
)


def venue_field_map() -> FieldMap:
    """The identity map with epoch flags — this provider speaks canonical
    schema keys with unix-ms timestamps (normalize-at-the-edge, W0 §3)."""
    return FieldMap(ts_is_epoch=True, reference_ts_is_epoch=True,
                    expiry_is_epoch=True)


def _urllib_fetch(url: str, timeout_s: float) -> Tuple[Dict[str, Any], float]:
    """Default fetcher: GET → parsed JSON + measured latency (stdlib only)."""
    t0 = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout_s) as r:
        body = r.read().decode("utf-8")
    latency_ms = (time.monotonic() - t0) * 1000.0
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError(f"unexpected non-object response from {url}")
    return data, latency_ms


def _book_url(inst: VenueInstrument, depth: int) -> str:
    return f"{_BASE}/api/v5/market/books?instId={inst.inst_id}&sz={depth}"


def _instruments_url(inst: VenueInstrument) -> str:
    inst_type = "SWAP" if inst.kind == "perp" else "SPOT"
    return (f"{_BASE}/api/v5/public/instruments?instType={inst_type}"
            f"&instId={inst.inst_id}")


def _vwap_fill(levels: List[List[Any]], notional: float,
               size_mult: float) -> Optional[Tuple[float, int]]:
    """Walk the book until `notional` (quote ccy) is filled.

    Returns (vwap_price, levels_consumed) or None when the visible depth
    cannot fill the requested notional (→ rejected / insufficient_depth).
    """
    remaining = notional
    quote_spent = 0.0
    base_filled = 0.0
    consumed = 0
    for lv in levels:
        if not lv:
            continue
        px = float(lv[0])
        sz = float(lv[1]) * size_mult
        if px <= 0 or sz < 0:
            continue
        avail_quote = px * sz
        use = min(remaining, avail_quote)
        base_filled += use / px
        quote_spent += use
        remaining -= use
        consumed += 1
        if remaining <= 1e-9:
            return quote_spent / base_filled, consumed
    return None


class OKXBookRFQProvider(RFQProvider):
    """REAL source: OKX public order books, polled (ingestion only)."""

    name = "okx-venue-book"
    source = "real"   # the epistemic wall — enforced at the provider base

    def __init__(self, notional: float = 10_000.0, depth: int = 25,
                 timeout_s: float = 10.0,
                 fetcher: Optional[Callable[[str, float],
                                            Tuple[Dict[str, Any], float]]] = None,
                 prior_references: Optional[Dict[str, Tuple[float, int]]] = None,
                 instruments: Tuple[VenueInstrument, ...] = INSTRUMENTS) -> None:
        self.notional = notional
        self.depth = depth
        self.timeout_s = timeout_s
        self._fetch = fetcher or _urllib_fetch
        # instrument symbol → (reference_price, reference_ts): the freshest
        # known reference, used for no_response records (V-8). The poll
        # script seeds this from the journal tail; the provider refreshes it
        # after every successful fetch.
        self.prior_references: Dict[str, Tuple[float, int]] = dict(prior_references or {})
        self.instruments = instruments
        self._meta_cache: Dict[str, Dict[str, Any]] = {}
        self._cold_failures: List[str] = []

    # ------------------------------------------------------------------ api

    def cold_failures(self) -> List[str]:
        """Instruments that produced NO record this run (a fetch failed and
        no prior reference existed — R-10 could not be satisfied honestly).
        The poll CLI turns this into a red run AFTER partial data is pushed."""
        return list(self._cold_failures)

    def iter_raw(self) -> Iterator[Dict[str, Any]]:
        for inst in self.instruments:
            try:
                book, latency_ms, meta = self._fetch_book(inst)
            except Exception as e:                      # noqa: BLE001 — honest
                prior = self.prior_references.get(inst.symbol)
                if prior is None:
                    # Cold failure: nothing can be journaled honestly for
                    # this instrument (reference_price is REQUIRED, R-10).
                    self._cold_failures.append(
                        f"{inst.inst_id}: fetch failed with no prior reference "
                        f"({type(e).__name__}: {e})")
                    continue
                ref_px, ref_ts = prior
                yield self._payload_no_response(inst, ref_px, ref_ts, e)
                continue
            ts = int(book["ts"])
            bids = book.get("bids") or []
            asks = book.get("asks") or []
            if not bids or not asks:
                # An empty side is a degenerate book: treat like a fetch
                # failure (no honest quote, but the book ts + prior may
                # still give a reference).
                prior = self.prior_references.get(inst.symbol)
                if prior is None:
                    self._cold_failures.append(
                        f"{inst.inst_id}: empty book side with no prior reference")
                    continue
                ref_px, ref_ts = prior
                yield self._payload_no_response(
                    inst, ref_px, ref_ts,
                    ValueError("empty book side (bids/asks missing)"))
                continue
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid = (best_bid + best_ask) / 2.0
            spread_bps = (best_ask - best_bid) / mid * 1e4
            # refresh the prior reference (freshest book for this instrument)
            self.prior_references[inst.symbol] = (mid, ts)
            size_mult = float(meta.get("ctVal", 1.0) or 1.0) if inst.needs_ctval else 1.0
            for side in ("buy", "sell"):
                levels = asks if side == "buy" else bids   # M-2: buy→ask, sell→bid
                fill = _vwap_fill(levels, self.notional, size_mult)
                if fill is None:
                    yield self._payload_rejected(inst, side, ts, mid, book,
                                                 meta, latency_ms, size_mult)
                else:
                    vwap_px, consumed = fill
                    yield self._payload_quoted(inst, side, ts, mid, book, meta,
                                               latency_ms, size_mult, vwap_px,
                                               consumed, spread_bps)

    # ------------------------------------------------------------- fetching

    def _instrument_meta(self, inst: VenueInstrument) -> Dict[str, Any]:
        if inst.inst_id not in self._meta_cache:
            data, _lat = self._fetch(_instruments_url(inst), self.timeout_s)
            if data.get("code") != "0" or not data.get("data"):
                raise ValueError(f"instruments meta: bad envelope for {inst.inst_id}")
            row = data["data"][0]
            if str(row.get("state", "live")) != "live":
                raise ValueError(f"instrument {inst.inst_id} not live "
                                 f"(state={row.get('state')!r})")
            self._meta_cache[inst.inst_id] = row
        return self._meta_cache[inst.inst_id]

    def _fetch_book(self, inst: VenueInstrument
                    ) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        meta = self._instrument_meta(inst)
        data, latency_ms = self._fetch(_book_url(inst, self.depth), self.timeout_s)
        if data.get("code") != "0" or not data.get("data"):
            raise ValueError(f"books: bad envelope for {inst.inst_id}")
        book = data["data"][0]
        if not book.get("ts"):
            raise ValueError(f"books: no ts in response for {inst.inst_id}")
        return book, latency_ms, meta

    # ------------------------------------------------------------ payloads

    def _raw_block(self, inst: VenueInstrument, book: Optional[Dict[str, Any]],
                   meta: Optional[Dict[str, Any]], latency_ms: float,
                   extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """The verbatim/provenance block stored under `venue_raw` (§1: never
        lose what the venue actually sent; the fee provenance travels with
        every record)."""
        raw: Dict[str, Any] = {
            "venue": VENUE_TAG,
            "endpoint": _book_url(inst, self.depth),
            "okx_response": book,          # verbatim books response
            "instrument_meta": meta,       # verbatim instruments row (ctVal…)
            "fee_schedule": FEE_PROVENANCE,
            "poll": {
                "requested_notional": self.notional,
                "notional_ccy": "USDT",
                "depth_requested": self.depth,
                "timeout_s": self.timeout_s,
                "latency_ms": round(latency_ms, 3),
            },
        }
        if extra:
            raw["poll"].update(extra)
        return raw

    def _payload_quoted(self, inst: VenueInstrument, side: str, ts: int,
                        mid: float, book: Dict[str, Any], meta: Dict[str, Any],
                        latency_ms: float, size_mult: float, vwap_px: float,
                        levels_consumed: int, spread_bps: float
                        ) -> Dict[str, Any]:
        return {
            "rfq_id": f"{VENUE_TAG}:{inst.symbol}:{side}:{ts}",
            "instrument": inst.symbol,
            "instrument_kind": inst.kind,
            "venue": VENUE_TAG,
            "ts": ts,
            "side": side,
            "requested_notional": self.notional,
            "notional_ccy": "USDT",
            "quoted_price": vwap_px,
            "quote_type": "firm",
            "quote_expiry_ts": ts,          # V-3: instant validity
            "fees_pct": inst.taker_fee_pct,
            "fees_included_in_price": False,
            "spread_bps": spread_bps,
            "reference_price": mid,
            "price_ccy": "USDT",
            "reference_source": inst.reference_tag,
            "reference_ts": ts,
            "latency_ms": latency_ms,
            "status": "quoted",
            "reject_reason": None,
            "venue_raw": self._raw_block(inst, book, meta, latency_ms, {
                "side_quoted_against": "asks" if side == "buy" else "bids",
                "size_multiplier": size_mult,
                "levels_consumed": levels_consumed,
            }),
        }

    def _payload_rejected(self, inst: VenueInstrument, side: str, ts: int,
                          mid: float, book: Dict[str, Any], meta: Dict[str, Any],
                          latency_ms: float, size_mult: float
                          ) -> Dict[str, Any]:
        # R-5/6/7/8: quote-only fields null when not quoted; R-9: spread only
        # on quoted records. fees_pct keeps the schedule value (V-7: the
        # schedule is a fact about the venue, documented in raw).
        return {
            "rfq_id": f"{VENUE_TAG}:{inst.symbol}:{side}:{ts}",
            "instrument": inst.symbol,
            "instrument_kind": inst.kind,
            "venue": VENUE_TAG,
            "ts": ts,
            "side": side,
            "requested_notional": self.notional,
            "notional_ccy": "USDT",
            "quoted_price": None,
            "quote_type": None,
            "quote_expiry_ts": None,
            "fees_pct": inst.taker_fee_pct,
            "fees_included_in_price": None,
            "spread_bps": None,
            "reference_price": mid,
            "price_ccy": "USDT",
            "reference_source": inst.reference_tag,
            "reference_ts": ts,
            "latency_ms": latency_ms,
            "status": "rejected",
            "reject_reason": "insufficient_depth",
            "venue_raw": self._raw_block(inst, book, meta, latency_ms, {
                "side_quoted_against": "asks" if side == "buy" else "bids",
                "size_multiplier": size_mult,
                "levels_consumed": self.depth,
            }),
        }

    def _payload_no_response(self, inst: VenueInstrument, ref_px: float,
                             ref_ts: int, err: Exception) -> Dict[str, Any]:
        # V-8: the venue did not answer; the reference is the freshest
        # available for this instrument (reference_age carries the honest
        # staleness; R-11 holds — ref_ts is in the past by construction).
        # The failed unit is the BOOK FETCH, which serves both sides — one
        # no_response record per instrument poll (side carries the first
        # requested side; sides_requested in raw carries the truth). Unlike
        # quoted records (deterministic on the venue's book ts), a retry that
        # fails again is a genuinely NEW failed request → wall-clock id.
        now_ms = int(time.time() * 1000)
        return {
            "rfq_id": f"{VENUE_TAG}:{inst.symbol}:poll:{now_ms}:no_response",
            "instrument": inst.symbol,
            "instrument_kind": inst.kind,
            "venue": VENUE_TAG,
            "ts": now_ms,
            "side": "buy",
            "requested_notional": self.notional,
            "notional_ccy": "USDT",
            "quoted_price": None,
            "quote_type": None,
            "quote_expiry_ts": None,
            "fees_pct": inst.taker_fee_pct,
            "fees_included_in_price": None,
            "spread_bps": None,
            "reference_price": ref_px,
            "price_ccy": "USDT",
            "reference_source": inst.reference_tag,
            "reference_ts": ref_ts,
            "latency_ms": self.timeout_s * 1000.0,
            "status": "no_response",
            "reject_reason": None,
            "venue_raw": {
                "venue": VENUE_TAG,
                "endpoint": _book_url(inst, self.depth),
                "okx_response": None,
                "instrument_meta": self._meta_cache.get(inst.inst_id),
                "fee_schedule": FEE_PROVENANCE,
                "poll": {
                    "requested_notional": self.notional,
                    "notional_ccy": "USDT",
                    "depth_requested": self.depth,
                    "timeout_s": self.timeout_s,
                    "sides_requested": ["buy", "sell"],
                    "error": f"{type(err).__name__}: {err}",
                },
            },
        }
