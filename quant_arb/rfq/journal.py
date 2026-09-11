"""Immutable raw RFQ journal — append-only, hash-chained (W0 §2).

Every line is:

    {"seq": k, "received_ts": ..., "source": ..., "rfq": {...},
     "prev_hash": "...", "hash": "sha256(canonical(seq, prev_hash,
                                            received_ts, source, rfq))"}

The chain makes tampering, reordering and insertion detectable anywhere in
the file: ``verify()`` recomputes the walk and names the first bad line.
There is no update/delete API — immutability by construction.

Honest limitation (stated in the design record §2): pure tail truncation is
not detectable from the file alone, so every ingest persists the chain head
hash in the derived status artifact; ``verify()`` re-checks the live head
against it when one is supplied. Truncation is then caught at the next
verification, not silently accepted.

Single-writer discipline: an advisory lockfile guards concurrent appends
(``fcntl.flock``); the journal is one-writer by design.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .schema import ExternalRFQ, RFQSchemaError

GENESIS = "0" * 64


class RFQJournalError(RuntimeError):
    """Raised on journal integrity violations (chain, sequence, truncation)."""


def _canonical(obj: Any) -> str:
    """Deterministic JSON (sorted keys, no whitespace) for hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _line_hash(seq: int, prev_hash: str, received_ts: int, source: str,
               rfq_payload: Dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update(_canonical({
        "seq": seq,
        "prev_hash": prev_hash,
        "received_ts": received_ts,
        "source": source,
        "rfq": rfq_payload,
    }).encode("utf-8"))
    return h.hexdigest()


class RawRFQJournal:
    """Append-only JSONL journal for raw external RFQ records."""

    def __init__(self, path: str, create_parent: bool = True) -> None:
        self.path = path
        if create_parent:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
        self._lock_path = path + ".lock"

    # ------------------------------------------------------------------ read

    def _iter_lines(self) -> Iterator[Tuple[int, str]]:
        """Yield (line_no, line) for every complete line; an unterminated
        trailing fragment (concurrent append) is ignored, mirroring the
        funding-arb phase2 analyzer's tolerance."""
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                s = line.strip()
                if not s:
                    continue
                yield i, s

    def tail(self, n: int = 5) -> List[Dict[str, Any]]:
        """Last n journal lines as parsed dicts (for status reporting)."""
        lines = [s for _, s in self._iter_lines()]
        out: List[Dict[str, Any]] = []
        for s in lines[-n:]:
            try:
                out.append(json.loads(s))
            except json.JSONDecodeError:
                out.append({"unparseable": True})
        return out

    def head_hash(self) -> Optional[str]:
        """Hash of the last valid line, or None for an empty journal."""
        last: Optional[str] = None
        for _, s in self._iter_lines():
            try:
                rec = json.loads(s)
            except json.JSONDecodeError:
                break
            last = rec.get("hash")
        return last

    def count(self) -> int:
        return sum(1 for _ in self._iter_lines())

    def iter_records(self) -> Iterator[ExternalRFQ]:
        """Yield every journaled ExternalRFQ (after full-chain verification)."""
        for rec in self._iter_verified():
            yield ExternalRFQ.from_payload(rec["rfq"])

    def _iter_verified(self) -> Iterator[Dict[str, Any]]:
        prev = GENESIS
        seq_expected = 1
        for line_no, s in self._iter_lines():
            try:
                rec = json.loads(s)
            except json.JSONDecodeError as e:
                raise RFQJournalError(f"line {line_no}: unparseable JSON ({e})") from e
            if rec.get("seq") != seq_expected:
                raise RFQJournalError(
                    f"line {line_no}: seq {rec.get('seq')!r} != expected {seq_expected} "
                    "(inserted, removed or reordered lines)")
            if rec.get("prev_hash") != prev:
                raise RFQJournalError(f"line {line_no}: prev_hash mismatch (chain broken)")
            want = _line_hash(rec["seq"], rec["prev_hash"], rec["received_ts"],
                              rec["source"], rec["rfq"])
            if rec.get("hash") != want:
                raise RFQJournalError(f"line {line_no}: hash mismatch (record tampered)")
            prev = rec["hash"]
            seq_expected += 1
            yield rec

    # ------------------------------------------------------------------ verify

    def verify(self, expect_head: Optional[str] = None) -> Dict[str, Any]:
        """Walk the chain, re-validate every record, check the head.

        Returns a summary dict; raises RFQJournalError on any violation.
        """
        n = 0
        sources: Dict[str, int] = {}
        first_ts: Optional[int] = None
        last_ts: Optional[int] = None
        live_head = GENESIS
        for rec in self._iter_verified():
            n += 1
            # re-validate the schema on read (defence in depth: the journal
            # is only as honest as its weakest historical line)
            ExternalRFQ.from_payload(rec["rfq"])
            sources[rec["source"]] = sources.get(rec["source"], 0) + 1
            ts = rec["rfq"]["ts"]
            first_ts = ts if first_ts is None else min(first_ts, ts)
            last_ts = ts if last_ts is None else max(last_ts, ts)
            live_head = rec["hash"]
        if expect_head is not None and live_head != expect_head:
            raise RFQJournalError(
                f"chain head {live_head[:12]}… != recorded head {expect_head[:12]}… "
                "(tail truncation or append after last status artifact)")
        return {
            "ok": True,
            "lines": n,
            "sources": sources,
            "first_ts": first_ts,
            "last_ts": last_ts,
            "head_hash": live_head if n else GENESIS,
        }

    # ------------------------------------------------------------------ append

    def append(self, rfq: ExternalRFQ, received_ts: Optional[int] = None) -> Dict[str, Any]:
        """Validate + append one record. Returns the journal line written.

        Fails closed: schema violation (RFQSchemaError) or duplicate rfq_id
        (R-1) → nothing is written.
        """
        # validate first (write-time invariants, fail-closed)
        payload = rfq.to_payload()
        if received_ts is None:
            received_ts = int(time.time() * 1000)

        lock_dir = os.path.dirname(self._lock_path) or "."
        os.makedirs(lock_dir, exist_ok=True)
        with open(self._lock_path, "a+", encoding="utf-8") as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                prev = GENESIS
                seq = 0
                seen_ids = set()
                for line_no, s in self._iter_lines():
                    try:
                        rec = json.loads(s)
                    except json.JSONDecodeError as e:
                        raise RFQJournalError(
                            f"line {line_no}: unparseable JSON ({e}) — refusing to append "
                            "onto a broken journal") from e
                    prev = rec.get("hash", GENESIS)
                    seq = rec.get("seq", 0)
                    rid = (rec.get("rfq") or {}).get("rfq_id")
                    if rid is not None:
                        seen_ids.add(rid)
                seq += 1
                if rfq.rfq_id in seen_ids:
                    raise RFQSchemaError(
                        f"[R-1] duplicate rfq_id {rfq.rfq_id!r} — already journaled")
                h = _line_hash(seq, prev, received_ts, rfq.source, payload)
                line = {
                    "seq": seq,
                    "received_ts": received_ts,
                    "source": rfq.source,
                    "rfq": payload,
                    "prev_hash": prev,
                    "hash": h,
                }
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(line, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                return line
            finally:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
