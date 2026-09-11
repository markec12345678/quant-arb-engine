"""W0: the first-feed rehearsal — a dress rehearsal for the real-feed day.

Executes the ENTIRE first-feed runbook (docs/runbook-first-feed.md) as one
continuous story, using every real command as a real subprocess — on
**stand-in desk data in a scratch workspace**:

  STEP 1  first contact   rfq_ingest --dry-run      (writes NOTHING; named skips)
  STEP 2  ingest          rfq_ingest --keep-going   (10 appended, 2 named skips)
  STEP 3  push provider   rfq_webhook_recv + POSTs  (200/422/401; live status)
  STEP 4  verify          rfq_replay --verify-only  (chain + truncation bound)
  STEP 5  census          rfq_coverage --json       (families, eligibility, days)
  STEP 6  replay describe JournalReplayFeed          (typed-quote readiness)

Honesty contract: the stand-in export is a DEMO fixture (venue "DEMO-DESK"),
the journal and status artifact live in a scratch temp dir, and the repo's
real artifacts are byte-compared before/after — ZERO pollution, the real
journal is never created. Exit code = number of failed steps.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, REPO)

from quant_arb.rfq.ingest import DEFAULT_JOURNAL, DEFAULT_STATUS  # noqa: E402

FIELD_MAP = os.path.join(REPO, "quant_arb", "rfq", "providers",
                         "example_field_map.json")
INGEST = os.path.join(HERE, "rfq_ingest.py")
WEBHOOK = os.path.join(HERE, "rfq_webhook_recv.py")
REPLAY = os.path.join(HERE, "rfq_replay.py")
COVERAGE = os.path.join(HERE, "rfq_coverage.py")

D1 = "2026-01-01T10:00:00Z"
D1_REF = "2026-01-01T09:59:59Z"
D1_EXP = "2026-01-01T10:00:30Z"
D2 = "2026-01-02T10:00:00Z"
D2_REF = "2026-01-02T09:59:59Z"
D2_EXP = "2026-01-02T10:00:30Z"
FWD_EXP = "2026-01-31T10:00:00Z"

# The stand-in desk export (example-map conventions: created_at ISO,
# fees_bps, side/status synonyms). 12 rows: 10 valid, 1 within-batch
# duplicate, 1 malformed (missing reference_price) — so --dry-run has
# something honest to name. (First rehearsal run caught a fixture bug:
# the expired row initially carried price=0.0 — R-5/6/7/8 require quote-only
# fields to be ABSENT when status != quoted. The machinery was right.)
STAND_IN_EXPORT = [
    dict(id="RD-001", instrument="BTC-USD", venue="DEMO-DESK", created_at=D1,
         side="buy", notional=50_000, price=99.6, quote_type="firm",
         valid_until=D1_EXP, fees_bps=4.0, fees_included_in_price=False,
         spread_bps=5.0, reference_price=100.0, reference_ts=D1_REF,
         latency_ms=90, status="quoted", instrument_kind="spot"),
    dict(id="RD-002", instrument="BTC-USD", venue="DEMO-DESK", created_at=D1,
         side="sell", notional=50_000, price=99.4, quote_type="firm",
         valid_until=D1_EXP, fees_bps=4.0, fees_included_in_price=False,
         spread_bps=5.0, reference_price=100.0, reference_ts=D1_REF,
         latency_ms=85, status="quoted", instrument_kind="spot"),
    dict(id="RD-003", instrument="BTC-USD", venue="DEMO-DESK", created_at=D1,
         side="buy", notional=30_000, price=99.5, quote_type="firm",
         valid_until=D1_EXP, fees_bps=4.0, fees_included_in_price=False,
         spread_bps=6.0, reference_price=100.0, reference_ts=D1_REF,
         latency_ms=95, status="quoted", instrument_kind="spot"),
    dict(id="RD-004", instrument="BTC-USD-FWD-30D", venue="DEMO-DESK",
         created_at=D1, side="buy", notional=50_000, price=101.0,
         quote_type="firm", valid_until=FWD_EXP, fees_bps=4.0,
         fees_included_in_price=False, spread_bps=8.0, reference_price=100.0,
         reference_ts=D1_REF, latency_ms=110, status="quoted",
         instrument_kind="forward"),
    dict(id="RD-005", instrument="BTC-USD-FWD-30D", venue="DEMO-DESK",
         created_at=D1, side="sell", notional=50_000, price=100.9,
         quote_type="firm", valid_until=FWD_EXP, fees_bps=4.0,
         fees_included_in_price=False, spread_bps=8.0, reference_price=100.0,
         reference_ts=D1_REF, latency_ms=105, status="quoted",
         instrument_kind="forward"),
    dict(id="RD-006", instrument="BTC-USD-PERP", venue="DEMO-DESK",
         created_at=D1, side="buy", notional=20_000, price=100.2,
         quote_type="firm", valid_until=D1_EXP, fees_bps=4.0,
         fees_included_in_price=False, spread_bps=7.0, reference_price=100.1,
         reference_ts=D1_REF, latency_ms=100, status="quoted",
         instrument_kind="perp", reference_source="perp_mark"),
    dict(id="RD-007", instrument="BTC-USD", venue="DEMO-DESK", created_at=D2,
         side="buy", notional=50_000, price=100.6, quote_type="firm",
         valid_until=D2_EXP, fees_bps=4.0, fees_included_in_price=False,
         spread_bps=5.0, reference_price=100.5, reference_ts=D2_REF,
         latency_ms=88, status="quoted", instrument_kind="spot"),
    dict(id="RD-008", instrument="BTC-USD", venue="DEMO-DESK", created_at=D2,
         side="sell", notional=50_000, fees_bps=4.0,
         reference_price=100.5, reference_ts=D2_REF,
         latency_ms=5_000, status="expired", reject_reason="desk_timeout",
         instrument_kind="spot"),
    dict(id="RD-009", instrument="BTC-USD", venue="DEMO-DESK", created_at=D2,
         side="buy", notional=25_000, price=98.0, quote_type="indicative",
         valid_until=D2_EXP, fees_bps=4.0, fees_included_in_price=False,
         spread_bps=9.0, reference_price=100.5, reference_ts=D2_REF,
         latency_ms=70, status="quoted", instrument_kind="spot"),
    dict(id="RD-010", instrument="BTC-USD", venue="DEMO-DESK", created_at=D2,
         side="sell", notional=50_000, price=100.4, quote_type="firm",
         valid_until=D2_EXP, fees_bps=4.0, fees_included_in_price=False,
         spread_bps=5.0, reference_price=100.5, reference_ts=D2_REF,
         latency_ms=92, status="quoted", instrument_kind="spot"),
    # within-batch duplicate of RD-001 → the dry-run must name it [R-1]
    dict(id="RD-001", instrument="BTC-USD", venue="DEMO-DESK", created_at=D1,
         side="buy", notional=50_000, price=99.6, quote_type="firm",
         valid_until=D1_EXP, fees_bps=4.0, fees_included_in_price=False,
         spread_bps=5.0, reference_price=100.0, reference_ts=D1_REF,
         latency_ms=90, status="quoted", instrument_kind="spot"),
    # malformed: reference_price missing → the dry-run must name it [MAP]
    dict(id="RD-011", instrument="BTC-USD", venue="DEMO-DESK", created_at=D2,
         side="buy", notional=10_000, price=100.5, quote_type="firm",
         valid_until=D2_EXP, fees_bps=4.0, fees_included_in_price=False,
         spread_bps=5.0, reference_ts=D2_REF, latency_ms=80,
         status="quoted", instrument_kind="spot"),
]

# Webhook payloads use the schema-name surface (no map needed there).
D1_MS = 1_767_261_600_000          # 2026-01-01T10:00:00Z
D2_MS = D1_MS + 86_400_000         # 2026-01-02T10:00:00Z
WH_VALID_SELL = {"rfq_id": "WH-RD-001", "instrument": "BTC-USD",
                 "venue": "DEMO-DESK", "ts": D2_MS + 60_000, "side": "sell",
                 "requested_notional": 40_000, "quoted_price": 100.3,
                 "quote_type": "firm", "quote_expiry_ts": D2_MS + 90_000,
                 "fees_pct": 0.04, "fees_included_in_price": False,
                 "spread_bps": 5.0, "reference_price": 100.5,
                 "reference_ts": D2_MS, "latency_ms": 75.0,
                 "status": "quoted", "reference_source": "spot_book_mid"}
WH_VALID_BUY = {**WH_VALID_SELL, "rfq_id": "WH-RD-002", "side": "buy",
                "quoted_price": 100.7}
WH_DUP = {**WH_VALID_SELL, "rfq_id": "RD-001"}     # duplicate of an ingested id

PORT = 3973
FAILS = []


def step(n: int, name: str, ok: bool, detail: str = "") -> None:
    line = f"[rehearse] STEP {n} {name}: {'PASS' if ok else 'FAIL'}"
    if detail and not ok:
        line += f"  [{detail}]"
    print(line, flush=True)
    if not ok:
        FAILS.append(f"step {n}")


def post(port: int, obj: dict, token: str = "REHEARSAL-TOKEN"):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/rfq", data=json.dumps(obj).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-RFQ-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main() -> int:
    print("[rehearse] FIRST-FEED REHEARSAL — stand-in desk data (DEMO-DESK), "
          "scratch workspace, ZERO writes to the repo", flush=True)
    scratch = tempfile.mkdtemp(prefix="rfq-rehearsal-")
    journal_path = os.path.join(scratch, "journal.jsonl")
    status_path = os.path.join(scratch, "status.json")
    export_path = os.path.join(scratch, "export.json")
    with open(export_path, "w") as f:
        json.dump(STAND_IN_EXPORT, f, indent=1)

    real_status_before = (open(DEFAULT_STATUS, "rb").read()
                          if os.path.exists(DEFAULT_STATUS) else b"")
    real_journal_before = os.path.exists(DEFAULT_JOURNAL)

    try:
        # STEP 1 — first contact: --dry-run writes NOTHING, names every skip
        r = subprocess.run([sys.executable, INGEST, "--provider", "file",
                            "--path", export_path, "--field-map", FIELD_MAP,
                            "--journal", journal_path, "--status", status_path,
                            "--dry-run"], capture_output=True, text=True)
        step(1, "dry-run names the skips, writes nothing",
             r.returncode == 1 and "would-append=10" in r.stdout
             and "would-skip=2" in r.stdout
             and "R-1" in r.stdout and "MAP" in r.stdout
             and not os.path.exists(journal_path)
             and not os.path.exists(status_path),
             r.stdout[-200:] + r.stderr[-200:])

        # STEP 2 — ingest for real (--keep-going: count + report skips)
        r = subprocess.run([sys.executable, INGEST, "--provider", "file",
                            "--path", export_path, "--field-map", FIELD_MAP,
                            "--journal", journal_path, "--status", status_path,
                            "--keep-going"], capture_output=True, text=True)
        st = json.load(open(status_path)) if os.path.exists(status_path) else {}
        n_lines = sum(1 for _ in open(journal_path)) \
            if os.path.exists(journal_path) else 0
        step(2, "ingest appends 10, skips 2, status live",
             r.returncode == 0 and "appended=10" in r.stdout
             and "skipped=2" in r.stdout and n_lines == 10
             and st.get("integrity", {}).get("lines") == 10
             and st.get("integrity", {}).get("sources") == {"real": 10},
             r.stdout[-200:] + r.stderr[-200:])

        # STEP 3 — the push lane: receiver subprocess + honest surfaces
        proc = subprocess.Popen(
            [sys.executable, WEBHOOK, "--journal", journal_path,
             "--status", status_path, "--port", str(PORT),
             "--token", "REHEARSAL-TOKEN"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{PORT}/rfq", timeout=0.2)
                except urllib.error.HTTPError:
                    break
                except Exception:
                    time.sleep(0.1)
            c1, o1 = post(PORT, WH_VALID_SELL)
            c2, o2 = post(PORT, WH_VALID_BUY)
            c3, o3 = post(PORT, WH_DUP)                       # R-1 duplicate
            c4, _ = post(PORT, WH_VALID_SELL, token="WRONG")  # 401
            st = json.load(open(status_path))
            n_lines = sum(1 for _ in open(journal_path))
            step(3, "webhook: 2 accepted (live status), dup 422 R-1, "
                    "bad token 401",
                 c1 == 200 and o1.get("status_refresh") == "ok"
                 and c2 == 200 and o2.get("status_refresh") == "ok"
                 and c3 == 422 and "R-1" in o3.get("error", "")
                 and c4 == 401
                 and n_lines == 12
                 and st["integrity"]["lines"] == 12
                 and st["last_operation"]["op"] == "webhook-append",
                 f"codes {c1}/{c2}/{c3}/{c4}")
        finally:
            proc.terminate()
            proc.wait(timeout=5)

        # STEP 4 — verify integrity (chain + truncation bound vs status head)
        r = subprocess.run([sys.executable, REPLAY, "--journal", journal_path,
                            "--status", status_path, "--verify-only"],
                           capture_output=True, text=True)
        step(4, "verify: chain OK, truncation checked",
             r.returncode == 0 and "OK lines=12" in r.stdout
             and "truncation=checked" in r.stdout,
             r.stdout[-200:] + r.stderr[-200:])

        # STEP 5 — the research-readiness census
        r = subprocess.run([sys.executable, COVERAGE, "--journal",
                            journal_path, "--json"], capture_output=True,
                           text=True)
        cov = json.loads(r.stdout) if r.returncode == 0 else {}
        fam = (cov.get("families") or [{}])[0]
        step(5, "census: 12 records, 10 eligible, ineligible named, 2 days",
             r.returncode == 0 and fam.get("symbol") == "BTC-USD"
             and fam.get("total_records") == 12
             and fam.get("eligible") == 10
             and fam.get("ineligible", {}).get("by_status") == {"expired": 1}
             and fam.get("ineligible", {}).get("indicative") == 1
             and fam.get("quote_days") == 2,
             r.stdout[-200:] + r.stderr[-200:])

        # STEP 6 — replay readiness (typed-quote surface, additive counter)
        from quant_arb.feeds.journal_replay import JournalReplayFeed
        from quant_arb.rfq.journal import RawRFQJournal
        d = JournalReplayFeed(
            RawRFQJournal(journal_path, create_parent=False),
            "BTC-USD").describe()
        step(6, "replay describe: 10 used, 2 ineligible, 2 quote days",
             d["records_used"] == 10 and d["ineligible"] == 2
             and d["quote_days"] == 2 and d["synthetic_mode"] is False,
             json.dumps(d)[:200])
    finally:
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)

    # ZERO-POLLUTION closing invariant: the repo's real artifacts untouched
    real_status_after = (open(DEFAULT_STATUS, "rb").read()
                         if os.path.exists(DEFAULT_STATUS) else b"")
    step(0, "repo untouched (status byte-identical, real journal absent)",
         real_status_after == real_status_before
         and real_journal_before == os.path.exists(DEFAULT_JOURNAL))

    if not FAILS:
        print("\n[rehearse] REHEARSAL COMPLETE — every step PASSed. The same "
              "sequence (docs/runbook-first-feed.md) runs your real feed on "
              "the real journal. Stand-in data only; nothing written to the "
              "repo.", flush=True)
    else:
        print(f"\n[rehearse] REHEARSAL FAILED at: {', '.join(FAILS)}",
              file=sys.stderr, flush=True)
    return len(FAILS)


if __name__ == "__main__":
    raise SystemExit(main())
