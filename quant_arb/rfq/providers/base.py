"""Provider surface — normalize-at-the-edge (W0 §3).

An ``RFQProvider`` yields raw payloads; a declarative ``FieldMap`` maps
provider key names to schema fields with small value transforms
(ISO-8601 → unix ms, bps → pct, side synonyms). Normalization is
provider-side; the journal stores the verbatim raw payload alongside the
normalized record (§1: never lose what the desk actually sent).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from ..schema import ExternalRFQ, RFQSchemaError

_ISO_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
)

_SIDE_SYNONYMS = {
    "buy": "buy", "bid": "buy", "ask": "sell", "sell": "sell",
    "b": "buy", "s": "sell", "long": "buy", "short": "sell",
}


def iso_to_unix_ms(v: Any) -> int:
    """Parse an ISO-8601-ish timestamp to unix ms (UTC when naive)."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return int(v) if v > 1e11 else int(float(v) * 1000.0)
    s = str(v).strip().replace("Z", "+0000").replace("+00:00", "+0000")
    for fmt in _ISO_FORMATS:
        try:
            d = _dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
        if d.tzinfo is None:
            d = d.replace(tzinfo=_dt.timezone.utc)
        return int(d.timestamp() * 1000)
    raise RFQSchemaError(f"[MAP] cannot parse timestamp: {v!r}")


def bps_to_pct(v: Any) -> float:
    return float(v) / 100.0


def side_normalize(v: Any) -> str:
    s = _SIDE_SYNONYMS.get(str(v).strip().lower())
    if s is None:
        raise RFQSchemaError(f"[MAP] unknown side: {v!r}")
    return s


@dataclass
class FieldMap:
    """Declarative mapping: schema field ← provider key (+ transform).

    ``required`` fields must be present after mapping; optional ones may be
    missing (status-dependent requirements are enforced by the schema itself).
    """
    rfq_id: str = "rfq_id"
    instrument: str = "instrument"
    venue: str = "venue"
    ts: str = "ts"
    side: str = "side"
    requested_notional: str = "requested_notional"
    quoted_price: Optional[str] = "quoted_price"
    quote_type: Optional[str] = "quote_type"
    quote_expiry_ts: Optional[str] = "quote_expiry_ts"
    fees_pct: Optional[str] = "fees_pct"
    fees_included_in_price: Optional[str] = "fees_included_in_price"
    spread_bps: Optional[str] = "spread_bps"
    reference_price: str = "reference_price"
    reference_ts: str = "reference_ts"
    latency_ms: Optional[str] = "latency_ms"
    status: str = "status"
    reject_reason: Optional[str] = "reject_reason"
    instrument_kind: Optional[str] = "instrument_kind"
    notional_ccy: Optional[str] = "notional_ccy"
    price_ccy: Optional[str] = "price_ccy"
    reference_source: Optional[str] = "reference_source"
    # transforms: timestamp fields parsed as ISO-or-epoch; fees may arrive in bps
    ts_is_epoch: bool = False
    expiry_is_epoch: bool = False
    reference_ts_is_epoch: bool = False
    fees_in_bps: bool = False

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "FieldMap":
        base = FieldMap()
        for k, v in d.items():
            if k.startswith("_"):
                continue          # underscore-prefixed keys are comments (e.g. "_comment")
            if not hasattr(base, k):
                raise RFQSchemaError(f"[MAP] unknown field-map key: {k!r}")
            setattr(base, k, v)
        return base


class RFQProvider:
    """Base class. Subclasses implement ``iter_raw`` and declare ``source``.

    ``source`` MUST be "real" for anything that relays actual desk/provider
    payloads; only the shipped synthetic test generator may say "synthetic".
    This is the epistemic wall's single point of enforcement on ingest.
    """

    name: str = "base"
    source: str = "real"

    def effective_map(self, field_map: FieldMap) -> FieldMap:
        """The map this provider actually speaks (dialect hook).

        Default: the caller-supplied map. Dialect providers that ship their
        own canonical key names (the synthetic test generator) override this
        so ``records``/``safe_records`` both speak the dialect consistently.
        """
        return field_map

    def iter_raw(self) -> Iterator[Dict[str, Any]]:
        raise NotImplementedError

    def records(self, field_map: FieldMap) -> Iterator[ExternalRFQ]:
        fm = self.effective_map(field_map)
        for raw in self.iter_raw():
            yield normalize(raw, fm, provider_source=self.source)

    def safe_records(self, field_map: FieldMap
                     ) -> Iterator[Tuple[int, Optional[ExternalRFQ],
                                         Optional[RFQSchemaError]]]:
        """Yield ``(index, record, error)`` — exactly one of record/error set.

        Per-record isolation: a payload that fails normalization (missing
        mapped field, unparseable timestamp, unknown status/side) is reported
        at its index and the walk CONTINUES — this is the ``--keep-going`` /
        ``--dry-run`` contract (one malformed row never aborts the report).
        The strict ``records()`` generator above still dies at the first bad
        payload (fail-closed single-shot flows).
        """
        fm = self.effective_map(field_map)
        for i, raw in enumerate(self.iter_raw()):
            try:
                yield i, normalize(raw, fm, provider_source=self.source), None
            except RFQSchemaError as e:
                yield i, None, e

    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "source": self.source}


def _map_get(raw: Dict[str, Any], key: Optional[str]) -> Any:
    if key is None:
        return None
    # allow dotted paths into nested provider payloads
    cur: Any = raw
    for part in str(key).split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def normalize(raw: Dict[str, Any], fm: FieldMap, provider_source: str) -> ExternalRFQ:
    """Provider payload → ExternalRFQ. Raw is preserved verbatim."""
    missing = [f for f in ("rfq_id", "instrument", "venue", "ts", "side",
                           "requested_notional", "reference_price",
                           "reference_ts", "status")
               if _map_get(raw, getattr(fm, f)) is None]
    if missing:
        raise RFQSchemaError(f"[MAP] provider payload missing required field(s): {missing}")

    ts = iso_to_unix_ms(_map_get(raw, fm.ts)) if not fm.ts_is_epoch else int(_map_get(raw, fm.ts))
    reference_ts = (iso_to_unix_ms(_map_get(raw, fm.reference_ts))
                    if not fm.reference_ts_is_epoch else int(_map_get(raw, fm.reference_ts)))
    expiry_raw = _map_get(raw, fm.quote_expiry_ts)
    expiry = (None if expiry_raw is None else
              (int(expiry_raw) if fm.expiry_is_epoch else iso_to_unix_ms(expiry_raw)))

    fees_raw = _map_get(raw, fm.fees_pct)
    fees_pct = 0.0 if fees_raw is None else float(fees_raw)
    if fm.fees_in_bps:
        fees_pct = fees_pct / 100.0

    quoted_price_raw = _map_get(raw, fm.quoted_price)
    spread_raw = _map_get(raw, fm.spread_bps)

    # status synonyms → canonical statuses
    status_raw = str(_map_get(raw, fm.status)).strip().lower()
    status_map = {"quoted": "quoted", "filled": "quoted", "answered": "quoted",
                  "rejected": "rejected", "reject": "rejected", "declined": "rejected",
                  "expired": "expired", "expired_awaiting_cancel": "expired",
                  "no_response": "no_response", "timeout": "no_response",
                  "canceled": "rejected"}
    if status_raw not in status_map:
        raise RFQSchemaError(f"[MAP] unknown status: {status_raw!r}")
    status = status_map[status_raw]

    qt_raw = _map_get(raw, fm.quote_type)
    if qt_raw is not None:
        qt = str(qt_raw).strip().lower()
        qt_map = {"firm": "firm", "executable": "firm", "tradable": "firm",
                  "indicative": "indicative", "indication": "indicative"}
        if qt not in qt_map:
            raise RFQSchemaError(f"[MAP] unknown quote_type: {qt_raw!r}")
        quote_type: Optional[str] = qt_map[qt]
    else:
        quote_type = None

    fip_raw = _map_get(raw, fm.fees_included_in_price)
    if fip_raw is None:
        fip: Optional[bool] = None
    elif isinstance(fip_raw, bool):
        fip = fip_raw
    else:
        s = str(fip_raw).strip().lower()
        if s in ("true", "yes", "1", "y"):
            fip = True
        elif s in ("false", "no", "0", "n"):
            fip = False
        else:
            raise RFQSchemaError(f"[MAP] unknown fees_included_in_price: {fip_raw!r}")

    latency_raw = _map_get(raw, fm.latency_ms)
    latency_ms = 0.0 if latency_raw is None else float(latency_raw)

    ref_src_raw = _map_get(raw, fm.reference_source)
    reference_source = ("other_reported" if ref_src_raw is None
                        else str(ref_src_raw).strip().lower())

    return ExternalRFQ(
        rfq_id=str(_map_get(raw, fm.rfq_id)),
        instrument=str(_map_get(raw, fm.instrument)),
        venue=str(_map_get(raw, fm.venue)),
        ts=ts,
        side=side_normalize(_map_get(raw, fm.side)),
        requested_notional=float(_map_get(raw, fm.requested_notional)),
        quoted_price=None if quoted_price_raw is None else float(quoted_price_raw),
        quote_type=quote_type,
        quote_expiry_ts=expiry,
        fees_pct=fees_pct,
        fees_included_in_price=fip,
        spread_bps=None if spread_raw is None else float(spread_raw),
        reference_price=float(_map_get(raw, fm.reference_price)),
        reference_ts=reference_ts,
        latency_ms=latency_ms,
        status=status,
        source=provider_source,
        instrument_kind=str(_map_get(raw, fm.instrument_kind) or "spot").strip().lower(),
        notional_ccy=str(_map_get(raw, fm.notional_ccy) or "USD"),
        price_ccy=str(_map_get(raw, fm.price_ccy) or "USD"),
        reference_source=reference_source,
        reject_reason=(None if _map_get(raw, fm.reject_reason) is None
                       else str(_map_get(raw, fm.reject_reason))),
        raw=raw,
    )
