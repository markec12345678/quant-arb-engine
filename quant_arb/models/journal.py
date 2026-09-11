"""Append-only JSONL event journal with write-time invariant enforcement.

The audit's hardest lessons were *silent* defects: prices without provenance,
requested notionals read as executed ones, PnL computed through abs(), fees
counted twice. Here each record type is validated before it is written; a
violation raises ``JournalInvariantError`` and nothing reaches the file.

Enforced invariants (see README):
I-1 price source tag          I-4 all-in cost exactly once
I-2 executed notional per leg I-5 quantity chain exact on settle
I-3 signed PnL only           I-6 requested vs executed distinct fields
"""

from __future__ import annotations

import json
import math
import time
import uuid
from typing import Any, Dict, List

SCHEMA_VERSION = 1

RECORD_TYPES = (
    "run_header",
    "quote",
    "opportunity",
    "family_eval",          # v0.3.0 (decision record C6): per-family ex-ante evaluation
    "funding_daily",        # v0.3.0 (C6): the observation stream, journaled as source of truth
    "decision",
    "position_opened",
    "position_settled",
    "run_summary",
)

EPISTEMIC_NOTE = (
    "SYNTHETIC/paper diagnostic only — on the current sample and reconstruction "
    "there is no proof of a positive edge. Never read as a real-trading forecast."
)


class JournalInvariantError(RuntimeError):
    """Raised when a record would violate a measurement invariant."""


def _require(cond: bool, inv_id: str, msg: str) -> None:
    if not cond:
        raise JournalInvariantError(f"[{inv_id}] {msg}")


def _check_price(d: Dict[str, Any], what: str) -> None:
    _require(isinstance(d, dict) and d.get("source") and d.get("ts", 0) > 0,
             "I-1", f"{what} must carry {'value/source/ts'} with a non-empty source tag")


def _check_legs(legs: List[Dict[str, Any]], what: str) -> None:
    for i, leg in enumerate(legs):
        _require("requested_size_usd" in leg and "executed_size_usd" in leg,
                 "I-6", f"{what} leg[{i}] must carry BOTH requested and executed size fields")
        _check_price(leg["px"], f"{what} leg[{i}] px")
        qty, px = float(leg["qty"]), float(leg["px"]["value"])
        executed = float(leg["executed_size_usd"])
        _require(abs(executed - qty * px) <= 1e-6 * max(1.0, abs(qty * px)),
                 "I-2", f"{what} leg[{i}] executed_size_usd must equal qty * px")


def validate_record(rec: Dict[str, Any]) -> None:
    rtype = rec.get("type")
    _require(rtype in RECORD_TYPES, "SCHEMA", f"unknown record type: {rtype!r}")
    p = rec.get("payload", {})
    _require(isinstance(p, dict), "SCHEMA", "payload must be an object")

    if rtype == "quote":
        _check_price(p["price"], "quote price")
        _check_price(p["ref_mid"], "quote ref_mid")
        _require("all_in_cost_bps" in p, "I-4",
                 "quote must record its all-in cost exactly once (embedded in the spread)")

    elif rtype in ("opportunity", "position_opened"):
        _check_legs(p["legs"], rtype)
        if rtype == "position_opened":
            _require(p.get("settle_ts", 0) > 0, "SCHEMA", "position_opened requires settle_ts")

    elif rtype == "family_eval":
        # v0.3.0 (C6): the full ex-ante decision audit — every family, every
        # quote day, gated or not. Nothing is silently dropped.
        _require(isinstance(p.get("strategy_id"), str) and p.get("strategy_id"),
                 "SCHEMA", "family_eval requires a non-empty strategy_id")
        _require(isinstance(p.get("day"), int) and p["day"] > 0,
                 "SCHEMA", "family_eval requires day (int > 0)")
        _require(isinstance(p.get("gated"), bool), "SCHEMA", "family_eval gated must be bool")
        _require(isinstance(p.get("selected"), bool), "SCHEMA", "family_eval selected must be bool")
        _require(isinstance(p.get("gates"), dict)
                 and all(isinstance(v, bool) for v in p["gates"].values()),
                 "SCHEMA", "family_eval gates must be a bool-valued dict")
        for k in ("gross_edge_bps", "net_executable_edge_bps", "sigma_level_apr", "sigma_horizon_apr"):
            v = p.get(k)
            _require(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v),
                     "SCHEMA", f"family_eval {k} must be a finite number")
        sz = p.get("signal_z")
        _require(sz is None or (isinstance(sz, (int, float)) and math.isfinite(sz)),
                 "SCHEMA", "family_eval signal_z must be finite or null")
        _require(isinstance(p.get("detail"), dict), "SCHEMA", "family_eval detail must be an object")

    elif rtype == "funding_daily":
        # v0.3.0 (C6): daily mean printed APR — signed by nature (funding can
        # be negative); finite is the only shape requirement.
        _require(isinstance(p.get("day"), int) and p["day"] > 0,
                 "SCHEMA", "funding_daily requires day (int > 0)")
        apr = p.get("apr_printed")
        _require(isinstance(apr, (int, float)) and not isinstance(apr, bool) and math.isfinite(apr),
                 "SCHEMA", "funding_daily apr_printed must be finite (funding is signed — may be negative)")
        _require(isinstance(p.get("n_prints"), int) and p["n_prints"] >= 1,
                 "SCHEMA", "funding_daily n_prints must be >= 1")

    elif rtype == "decision":
        _require(p.get("action") in ("open", "reject"), "SCHEMA", "decision action must be open|reject")
        _require(isinstance(p.get("reasons"), list), "SCHEMA", "decision requires reasons[]")

    elif rtype == "position_settled":
        _require("signed_pnl_usd" in p, "I-3", "settlement requires signed_pnl_usd")
        _require("abs_pnl_usd" not in p and "pnl_usd" not in p,
                 "I-3", "settlement must not carry unsigned/ambiguous pnl field names")
        fa = p.get("funding_accrual_usd")
        _require("abs_funding_accrual_usd" not in p,
                 "I-3", "funding accrual must be signed (no abs_ variant)")
        _require(fa is None or (isinstance(fa, (int, float)) and math.isfinite(fa)),
                 "I-3", "funding_accrual_usd must be a finite signed number")
        _require(not (p.get("strategy_id") == "perp_carry_v1") or fa is not None,
                 "I-3", "perp_carry_v1 settlements require funding_accrual_usd (the floating carry leg)")
        _require(p.get("quantity_chain_ok") is True, "I-5",
                 "settlement must verify the quantity chain quote→fill→settlement")
        _check_legs(p.get("entry_legs", []), "settled entry_legs")
        for leg in p.get("legs_pnl", []):
            _require("signed_pnl_usd" in leg and leg.get("direction") in (1, -1),
                     "I-3", "per-leg pnl must be signed and carry leg direction")

    elif rtype == "run_summary":
        _require(p.get("epistemic_note") == EPISTEMIC_NOTE, "EPI",
                 "run summary must carry the canonical epistemic note verbatim")
        _require("aggregate_pct_of_notional" in p and "mean_per_position_pct" in p,
                 "UNIT", "summary must report the aggregate AND the per-position mean (unit discipline)")


class Journal:
    """Append-only JSONL journal. One run = one file = one audit trail."""

    def __init__(self, path: str, run_id: str | None = None, mode: str = "research_paper") -> None:
        self._fh = open(path, "a", encoding="utf-8")
        self._seq = 0
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.append("run_header", {"mode": mode, "engine": "quant-arb-engine", "schema_note": RECORD_TYPES})

    def append(self, rec_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._seq += 1
        rec = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "seq": self._seq,
            "ts": int(time.time() * 1000),
            "type": rec_type,
            "payload": payload,
        }
        validate_record(rec)
        self._fh.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        self._fh.flush()
        return rec

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "Journal":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def read_all(path: str) -> List[Dict[str, Any]]:
    records = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
