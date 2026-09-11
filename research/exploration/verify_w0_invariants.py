"""W0 invariant checks — tracked, reproducible audit harness.

Promoted from the ad-hoc ``.scratch`` harness of the v0.6.0 seal run
(commit cd60b3d: 37 checks, 3 harness bugs found/fixed, zero module
defects) so that the "invariant-checked" claim is reproducible from the
repo alone, like ``verify_artifacts_v04/v05.py``. The checks are unchanged;
section 8 adds the v0.6.1 dry-run invariants (writes NOTHING).

Run:   python3 research/exploration/verify_w0_invariants.py
Exit:  number of failures. Every run's result belongs in the worklog trail.
"""
import json, os, sys, tempfile, shutil
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from quant_arb.rfq.schema import ExternalRFQ, RFQSchemaError
from quant_arb.rfq.journal import RawRFQJournal, RFQJournalError
from quant_arb.rfq.providers.synthetic import SyntheticRFQProvider
from quant_arb.rfq.providers.base import FieldMap, normalize
from quant_arb.rfq.edge import RFQEdge, describe

FAILS = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))
    if not cond: FAILS.append(name)

def _raises_notimpl(fn, *a):
    try:
        fn(*a)
        return False
    except NotImplementedError:
        return True

T0 = 1_767_225_600_000  # 2026-01-01Z
def mk(**kw):
    base = dict(rfq_id="X-1", instrument="BTC-USD", venue="DESK-A", ts=T0,
                side="buy", requested_notional=50_000.0, quoted_price=99.5,
                quote_type="firm", quote_expiry_ts=T0+30_000, fees_pct=0.05,
                fees_included_in_price=False, spread_bps=8.0,
                reference_price=100.0, reference_ts=T0-1000, latency_ms=120.0,
                status="quoted", source="real", raw={"id":"X-1"})
    base.update(kw)
    return ExternalRFQ(**base)

tmp = tempfile.mkdtemp(prefix="w0-")
try:
    # --- 1. schema invariants (fail-closed) -------------------------------
    for name, kw, inv in [
        ("future reference_ts rejected", dict(reference_ts=T0+5000), "R-11"),
        ("negative latency rejected", dict(latency_ms=-1.0), "R-12"),
        ("quoted without price rejected", dict(quoted_price=None), "R-5"),
        ("quoted without quote_type rejected", dict(quote_type=None), "R-6"),
        ("expiry < ts rejected", dict(quote_expiry_ts=T0-1), "R-7"),
        ("quoted without fees_included flag rejected", dict(fees_included_in_price=None), "R-8"),
        ("bad side rejected", dict(side="bid"), "R-4"),
        ("bad source rejected", dict(source="mixed"), "W0"),
        ("naked reference without provenance default", dict(reference_source="made_up"), "R-10"),
    ]:
        try:
            mk(**kw); check(name, False, "no exception raised")
        except RFQSchemaError as e:
            check(name, inv in str(e), str(e))
    # rejected status must NOT carry quote-only fields
    try:
        mk(status="rejected"); check("rejected carries no quote fields rejected", False, "no exception")
    except RFQSchemaError as e:
        check("rejected carries no quote fields rejected", "R-5" in str(e), str(e))
    # valid non-quoted record passes
    r = mk(status="rejected", quoted_price=None, quote_type=None, quote_expiry_ts=None,
           fees_included_in_price=None, spread_bps=None, reject_reason="size_over_limit")
    check("valid rejected record passes", r.status == "rejected")

    # --- 2. hash chain ------------------------------------------------------
    jp = os.path.join(tmp, "j.jsonl")
    j = RawRFQJournal(jp)
    prov = SyntheticRFQProvider(n=50, seed=7)
    fm = FieldMap()
    recs = list(prov.records(fm))
    check("synthetic provider source wall", all(x.source == "synthetic" for x in recs))
    lines = [j.append(r) for r in recs]
    check("seq monotone 1..n", [l["seq"] for l in lines] == list(range(1, 51)))
    check("chain links", lines[0]["prev_hash"] == "0"*64 and
          all(lines[i]["prev_hash"] == lines[i-1]["hash"] for i in range(1, 50)))
    s = j.verify()
    check("verify clean", s["ok"] and s["lines"] == 50)
    # duplicate rfq_id rejected
    try:
        j.append(recs[0]); check("duplicate rfq_id rejected", False, "no exception")
    except RFQSchemaError as e:
        check("duplicate rfq_id rejected", "R-1" in str(e))
    # determinism: same provider seed → bit-identical payloads
    recs2 = list(SyntheticRFQProvider(n=50, seed=7).records(fm))
    check("synthetic determinism", [r.to_payload() for r in recs] == [r.to_payload() for r in recs2])

    # --- 3. tamper detection --------------------------------------------------
    # 3a: modify a middle record's price
    with open(jp) as f: raw_lines = f.read().splitlines()
    tampered = json.loads(raw_lines[24]); tampered["rfq"]["quoted_price"] = 123.0
    raw_lines[24] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
    tp = os.path.join(tmp, "tampered.jsonl")
    with open(tp, "w") as f: f.write("\n".join(raw_lines) + "\n")
    try:
        RawRFQJournal(tp, create_parent=False).verify()
        check("tampered middle record detected", False, "verify passed!")
    except RFQJournalError as e:
        check("tampered middle record detected", "line 25" in str(e), str(e))
    # 3b: reorder two lines (pristine copy)
    with open(jp) as f: pristine_lines = f.read().splitlines()
    rl = list(pristine_lines); rl[10], rl[11] = rl[11], rl[10]
    rp = os.path.join(tmp, "reordered.jsonl")
    with open(rp, "w") as f: f.write("\n".join(rl) + "\n")
    try:
        RawRFQJournal(rp, create_parent=False).verify()
        check("reordered lines detected", False, "verify passed!")
    except RFQJournalError as e:
        check("reordered lines detected", "seq" in str(e) or "prev_hash" in str(e), str(e))
    # 3c: insertion of a forged line (pristine copy)
    il = list(pristine_lines); forged = json.loads(il[5]); forged["rfq"]["rfq_id"] = "FORGED"
    il.insert(30, json.dumps(forged, sort_keys=True, separators=(",", ":")))
    ip = os.path.join(tmp, "inserted.jsonl")
    with open(ip, "w") as f: f.write("\n".join(il) + "\n")
    try:
        RawRFQJournal(ip, create_parent=False).verify()
        check("inserted forged line detected", False, "verify passed!")
    except RFQJournalError as e:
        check("inserted forged line detected", "seq" in str(e) or "prev_hash" in str(e), str(e))
    # 3d: tail truncation detected via recorded head (the honest-limitation bound)
    head = j.head_hash()
    cutp = os.path.join(tmp, "cut.jsonl")
    with open(cutp, "w") as f: f.write("\n".join(pristine_lines[:44]) + "\n")
    try:
        RawRFQJournal(cutp, create_parent=False).verify(expect_head=head)
        check("tail truncation detected vs recorded head", False, "verify passed!")
    except RFQJournalError as e:
        check("tail truncation detected vs recorded head", "head" in str(e), str(e))
    # and WITHOUT a recorded head, truncation is honestly not detectable (documented)
    s2 = RawRFQJournal(cutp, create_parent=False).verify()
    check("truncation undetectable without head (documented limit)", s2["lines"] == 44)

    # --- 4. all-in edge accounting -------------------------------------------
    e1 = RFQEdge.of(mk(side="buy", quoted_price=99.5, reference_price=100.0,
                       fees_pct=0.05, fees_included_in_price=False))
    # buy below ref: +50bps price edge; fees 5bps on top when NOT included → +45
    check("buy edge accounting", abs(e1.price_edge_bps - 50.0) < 1e-9 and
          abs(e1.fee_cost_bps - 5.0) < 1e-9 and abs(e1.all_in_edge_bps - 45.0) < 1e-9,
          f"{e1}")
    e2 = RFQEdge.of(mk(side="sell", quoted_price=100.4, reference_price=100.0,
                       fees_pct=0.05, fees_included_in_price=True))
    # sell above ref: +40bps; fees INCLUDED in price → not charged again (I-4)
    check("sell edge + fees-included counted once", abs(e2.price_edge_bps - 40.0) < 1e-9
          and abs(e2.fee_cost_bps - 0.0) < 1e-9 and abs(e2.all_in_edge_bps - 40.0) < 1e-9,
          f"{e2}")
    e3 = RFQEdge.of(mk(status="no_response", quoted_price=None, quote_type=None,
                       quote_expiry_ts=None, fees_included_in_price=None, spread_bps=None))
    check("non-quoted has no edge", e3.all_in_edge_bps is None)

    # --- 5. round-trip + source wall in describe() -----------------------------
    p = mk().to_payload(); r2 = ExternalRFQ.from_payload(p)
    check("payload round-trip", r2.to_payload() == p)
    rep = describe(list(j.iter_records()))
    check("source wall in report (split, no pooling)",
          rep["edges"]["real"]["records"] == 0 and
          rep["edges"]["synthetic"]["records"] == 50 and
          rep["edges"]["pooled"] is None)
    check("counts sane", rep["counts"]["total"] == 50)

    # --- 6. file provider (real) + field map ------------------------------------
    export = os.path.join(tmp, "export.jsonl")
    with open(export, "w") as f:
        for k in range(3):
            f.write(json.dumps({"id": f"R{k}", "instrument": "ETH-USD", "venue": "DESK-X",
                "created_at": "2026-03-01T10:00:00Z", "side": "ask", "notional": 25000,
                "price": 2000.5, "quote_type": "executable", "valid_until": "2026-03-01T10:00:30Z",
                "fees_bps": 7.5, "fees_included_in_price": "false", "spread_bps": 5.0,
                "reference_price": 2000.0, "reference_ts": "2026-03-01T09:59:59Z",
                "latency_ms": 250.0, "status": "filled"}) + "\n")
    fm2 = FieldMap(rfq_id="id", ts="created_at", requested_notional="notional",
                   quoted_price="price", quote_expiry_ts="valid_until",
                   fees_pct="fees_bps", fees_in_bps=True,
                   fees_included_in_price="fees_included_in_price",
                   reference_ts="reference_ts")
    from quant_arb.rfq.providers.file_ingest import FileRFQProvider
    frecs = list(FileRFQProvider(export).records(fm2))
    check("file provider maps ISO ts → epoch", frecs[0].ts == 1_772_359_200_000)  # 2026-03-01T10:00:00Z
    check("file provider side synonym ask→sell", frecs[0].side == "sell")
    check("file provider status synonym filled→quoted", frecs[0].status == "quoted")
    check("file provider quote_type executable→firm", frecs[0].quote_type == "firm")
    check("file provider bps→pct fees", abs(frecs[0].fees_pct - 0.075) < 1e-12)
    check("file provider source=real", all(x.source == "real" for x in frecs))
    check("file provider raw verbatim", frecs[0].raw["id"] == "R0")
    # research eligibility wall
    check("research eligibility wall", frecs[0].is_research_eligible and not recs[0].is_research_eligible)

    # --- 7. real journal cannot receive synthetic via CLI guard (simulated) ----
    # (guard logic is in scripts/rfq_ingest.py; here: normalize enforces provider source)
    syn_map = FieldMap(rfq_id="id", requested_notional="notional",
                       fees_pct="fees_bps", fees_in_bps=True,
                       quoted_price="price", quote_expiry_ts="expiry")
    syn_norm = normalize({"id":"S","instrument":"X","venue":"V","ts":T0,"side":"buy",
        "notional":100,"reference_price":10,"reference_ts":T0-100,"status":"quoted",
        "price":10,"quote_type":"firm","expiry":T0+1,"fees_bps":0,
        "fees_included_in_price":True}, syn_map, provider_source="synthetic")
    check("normalize keeps provider source tag", syn_norm.source == "synthetic")

    # --- 8. dry-run writes NOTHING (v0.6.1 first-contact validation) -----------
    from quant_arb.rfq.ingest import dry_run
    # 8a: fresh non-existent path (dir does not exist) — nothing created
    fresh = os.path.join(tmp, "freshdir", "journal.jsonl")
    rep_d = dry_run(prov, RawRFQJournal(fresh, create_parent=False), fm)
    check("dry-run fresh: all would-append", rep_d["would_append"] == 50 and rep_d["would_skip"] == 0)
    check("dry-run fresh: would-be sources census", rep_d["would_be_sources"] == {"synthetic": 50})
    check("dry-run writes no journal/lock/dir",
          not os.path.exists(fresh) and not os.path.exists(fresh + ".lock")
          and not os.path.isdir(os.path.dirname(fresh)))
    # 8b: against the populated journal — every record a journal duplicate
    import hashlib as _hl
    _before = _hl.sha256(open(jp, "rb").read()).hexdigest()
    _lock_before = os.path.exists(jp + ".lock")  # the section-2 appends own this file
    rep_d2 = dry_run(prov, RawRFQJournal(jp, create_parent=False), fm)
    check("dry-run detects journal duplicates",
          rep_d2["would_append"] == 0 and rep_d2["would_skip"] == 50
          and all("R-1" in e["error"] and "already journaled" in e["error"]
                  for e in rep_d2["skip_errors"]))
    check("dry-run leaves journal byte-identical + lock untouched",
          _hl.sha256(open(jp, "rb").read()).hexdigest() == _before
          and RawRFQJournal(jp, create_parent=False).verify()["lines"] == 50
          and os.path.exists(jp + ".lock") == _lock_before)
    # 8c: within-batch duplicate (via the provider interface: iter_raw)
    from quant_arb.rfq.providers.base import RFQProvider as _RP
    class DupProvider(_RP):
        name = "dup-test"
        def iter_raw(self):
            base = {"rfq_id": "X-1", "instrument": "BTC-USD", "venue": "DESK-A",
                    "ts": T0, "side": "buy", "requested_notional": 50_000,
                    "quoted_price": 99.5, "quote_type": "firm",
                    "quote_expiry_ts": T0 + 30_000, "fees_pct": 0.05,
                    "fees_included_in_price": False, "spread_bps": 8.0,
                    "reference_price": 100.0, "reference_ts": T0 - 1000,
                    "latency_ms": 120.0, "status": "quoted"}
            yield dict(base)
            yield dict(base)  # same rfq_id "X-1" within the batch
    rep_d3 = dry_run(DupProvider(),
                     RawRFQJournal(os.path.join(tmp, "none.jsonl"), create_parent=False),
                     FieldMap())
    check("dry-run detects in-batch duplicate",
          rep_d3["would_append"] == 1 and rep_d3["would_skip"] == 1
          and "within this batch" in rep_d3["skip_errors"][0]["error"])
    # 8d: malformed-row isolation (the e2e-discovered defect, now an invariant)
    #     2 valid rows + 1 row missing reference_price/reference_ts
    mixed = os.path.join(tmp, "mixed.jsonl")
    with open(mixed, "w") as f:
        for k in range(2):
            f.write(json.dumps({"id": f"M{k}", "instrument": "BTC-USD", "venue": "DESK-M",
                "ts": T0 + k, "side": "buy", "notional": 1000,
                "reference_price": 100.0, "reference_ts": T0 - 1000,
                "status": "quoted", "price": 99.9, "quote_type": "firm",
                "expiry": T0 + 30000, "fees_bps": 1.0,
                "fees_included_in_price": True}) + "\n")
        f.write(json.dumps({"id": "M-BAD", "instrument": "ETH-USD", "venue": "DESK-M",
            "ts": T0 + 2, "side": "buy", "notional": 1000, "status": "no_response"}) + "\n")
    from quant_arb.rfq.ingest import ingest as _ingest
    fm_m = FieldMap(rfq_id="id", requested_notional="notional", quoted_price="price",
                    quote_expiry_ts="expiry", fees_pct="fees_bps", fees_in_bps=True,
                    fees_included_in_price="fees_included_in_price")
    rep_m = dry_run(FileRFQProvider(mixed),
                    RawRFQJournal(os.path.join(tmp, "m.jsonl"), create_parent=False), fm_m)
    check("dry-run isolates malformed rows (walk continues)",
          rep_m["would_append"] == 2 and rep_m["would_skip"] == 1
          and "[MAP]" in rep_m["skip_errors"][0]["error"]
          and rep_m["skip_errors"][0]["index"] == 2)
    jm = RawRFQJournal(os.path.join(tmp, "mj.jsonl"))
    run_m = _ingest(FileRFQProvider(mixed), jm, fm_m, stop_on_error=False)
    check("keep-going ingest isolates malformed rows",
          run_m["appended"] == 2 and run_m["skipped"] == 1
          and jm.verify()["lines"] == 2)
    try:
        _ingest(FileRFQProvider(mixed),
                RawRFQJournal(os.path.join(tmp, "fj.jsonl")), fm_m, stop_on_error=True)
        check("fail-closed ingest still raises on malformed row", False, "no exception")
    except RFQSchemaError as e:
        check("fail-closed ingest still raises on malformed row", "[MAP]" in str(e))

    # --- 9. webhook receiver (real HTTP, ephemeral port, in-process) -----------
    #     Promotes the ad-hoc Task-27 e2e (200/422/422) to a tracked invariant:
    #     token gate, duplicate/future-ts rejection, malformed JSON, path check,
    #     and NOTHING journaled except the one valid payload.
    import threading, urllib.request, urllib.error
    from http.server import ThreadingHTTPServer
    from quant_arb.rfq.providers.webhook import WebhookReceiver
    wh_journal_path = os.path.join(tmp, "wh.jsonl")
    wh_recv = WebhookReceiver(RawRFQJournal(wh_journal_path), FieldMap(),
                              token="SECRET-TOKEN")
    wh_srv = ThreadingHTTPServer(("127.0.0.1", 0), wh_recv.handler())
    wh_port = wh_srv.server_address[1]
    threading.Thread(target=wh_srv.serve_forever, daemon=True).start()
    try:
        def wh_post(path="/rfq", body=None, token="SECRET-TOKEN", raw_body=None):
            data = raw_body if raw_body is not None else json.dumps(body).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{wh_port}{path}", data=data, method="POST",
                headers={"Content-Type": "application/json",
                         **({"X-RFQ-Token": token} if token is not None else {})})
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return resp.status, json.loads(resp.read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read())

        valid = {"rfq_id": "WH-1", "instrument": "BTC-USD", "venue": "DESK-W",
                 "ts": T0, "side": "buy", "requested_notional": 25000,
                 "quoted_price": 99.5, "quote_type": "firm",
                 "quote_expiry_ts": T0 + 30000, "fees_pct": 0.04,
                 "fees_included_in_price": False, "spread_bps": 6.0,
                 "reference_price": 100.0, "reference_ts": T0 - 1000,
                 "latency_ms": 80.0, "status": "quoted"}
        code, obj = wh_post(body=valid)
        check("webhook valid payload accepted (200, seq=1)",
              code == 200 and obj.get("ok") is True and obj.get("seq") == 1
              and obj.get("rfq_id") == "WH-1")
        code, _ = wh_post(body=valid, token="WRONG")
        check("webhook wrong token rejected (401)", code == 401)
        code, _ = wh_post(body=valid, token=None)
        check("webhook missing token rejected (401)", code == 401)
        code, obj = wh_post(body=valid)
        check("webhook duplicate rfq_id rejected (422, R-1)",
              code == 422 and "R-1" in obj.get("error", ""))
        code, obj = wh_post(body={**valid, "rfq_id": "WH-2",
                                  "reference_ts": T0 + 5000})
        check("webhook future reference_ts rejected (422, R-11)",
              code == 422 and "R-11" in obj.get("error", ""))
        code, _ = wh_post(raw_body=b"{not json")
        check("webhook malformed JSON rejected (400)", code == 400)
        code, _ = wh_post(path="/other", body=valid)
        check("webhook unknown path rejected (404)", code == 404)
        wh_j = RawRFQJournal(wh_journal_path, create_parent=False)
        s_wh = wh_j.verify()
        check("webhook: only the valid payload journaled (source=real)",
              s_wh["lines"] == 1 and s_wh["sources"] == {"real": 1}
              and next(wh_j.iter_records()).rfq_id == "WH-1")
    finally:
        wh_srv.shutdown(); wh_srv.server_close()

    # --- 10. W1-INFRA journal replay feed (v0.6.2, sealed docs/w1-replay-adapter.md) ---
    import hashlib as _h2
    from quant_arb.feeds.journal_replay import JournalReplayFeed, ReplayError
    from quant_arb.models.market_data import PriceSource

    # 10a: source wall — the smoke journal is synthetic; default constructor refuses
    smoke_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "artifacts", "rfq",
        "journal-synthetic-smoke.jsonl"))
    smoke = RawRFQJournal(smoke_path, create_parent=False)
    try:
        JournalReplayFeed(smoke, "BTC-USD")
        check("replay source wall refuses synthetic journal", False, "no exception")
    except ReplayError as e:
        check("replay source wall refuses synthetic journal", "M-8" in str(e))
    # 10b: machinery-test mode constructs, quotes carry SYNTHETIC_MOCK provenance
    import hashlib as _hsm
    _sm_before = _hsm.sha256(open(smoke_path, "rb").read()).hexdigest()
    rf_syn = JournalReplayFeed(smoke, "BTC-USD", allow_synthetic=True)
    d_syn = rf_syn.describe()
    check("replay smoke: describe is honest (sources, synthetic_mode)",
          d_syn["sources"] == {"synthetic": 200} and d_syn["synthetic_mode"] is True
          and d_syn["quote_days"] >= 1 and d_syn["chain"]["lines"] == 200)
    saw_syn_quote = False
    try:
        while True:
            rf_syn.advance_day()
            try:
                b, a = rf_syn.spot_quotes()
                saw_syn_quote = (a.px.source == PriceSource.SYNTHETIC_MOCK
                                 and b.px.source == PriceSource.SYNTHETIC_MOCK)
                break
            except ReplayError:
                continue   # day without a full pair — keep walking
    except ReplayError:
        pass            # exhausted without a pair — acceptable; determinism is what matters
    check("replay smoke: synthetic quotes carry SYNTHETIC_MOCK (I-1 wall travels)",
          saw_syn_quote)
    check("replay leaves journal byte-identical (M-9)",
          _hsm.sha256(open(smoke_path, "rb").read()).hexdigest() == _sm_before)

    # 10c: hand-built REAL journal — the full mapping surface
    def mk2(**kw):
        base = dict(rfq_id="R-1", instrument="BTC-USD", venue="DESK-R", ts=T0,
                    side="buy", requested_notional=50_000.0, quoted_price=99.6,
                    quote_type="firm", quote_expiry_ts=T0 + 30_000, fees_pct=0.04,
                    fees_included_in_price=False, spread_bps=5.0,
                    reference_price=100.0, reference_ts=T0 - 1000,
                    reference_source="spot_book_mid", latency_ms=90.0,
                    status="quoted", source="real",
                    instrument_kind="spot", raw={})
        base.update(kw)
        return ExternalRFQ(**base)

    DAY2 = T0 + 86_400_000
    rj = RawRFQJournal(os.path.join(tmp, "real.jsonl"))
    for rec in [
        mk2(rfq_id="RB-1", side="buy", quoted_price=99.6),
        mk2(rfq_id="RS-1", side="sell", quoted_price=99.4),
        mk2(rfq_id="FB-1", instrument="BTC-USD-FWD-30D", instrument_kind="forward",
            side="buy", quoted_price=101.0, quote_expiry_ts=T0 + 30 * 86_400_000),
        mk2(rfq_id="FS-1", instrument="BTC-USD-FWD-30D", instrument_kind="forward",
            side="sell", quoted_price=100.9, quote_expiry_ts=T0 + 30 * 86_400_000),
        mk2(rfq_id="PP-1", instrument="BTC-USD-PERP", instrument_kind="perp",
            side="buy", quoted_price=100.2, reference_price=100.1,
            reference_source="perp_mark"),
        mk2(rfq_id="IN-1", quote_type="indicative", side="buy", quoted_price=98.0),
        mk2(rfq_id="CC-1", notional_ccy="EUR", side="sell", quoted_price=99.4),
        mk2(rfq_id="WU-1", side="sell", quoted_price=99.4,
            reference_source="composite_index"),
        mk2(rfq_id="RB-2", ts=DAY2, quote_expiry_ts=DAY2 + 30_000,
            reference_ts=DAY2 - 1000, side="buy", quoted_price=100.6),
        mk2(rfq_id="RS-2", ts=DAY2, quote_expiry_ts=DAY2 + 30_000,
            reference_ts=DAY2 - 1000, side="sell", quoted_price=100.4),
    ]:
        rj.append(rec)
    rf = JournalReplayFeed(rj, "BTC-USD")
    d = rf.describe()
    check("replay real: describe counts (2 days, 8 used, 1 unusable ccy)",
          d["quote_days"] == 2 and d["records_used"] == 8 and len(d["unusable"]) == 1
          and "CC-1" in d["unusable"][0])
    check("replay real: not started surfaces raise (M-7)",
          rf.day() == 0)
    try:
        rf.now_ms(); check("replay real: now_ms before start raises", False, "no exception")
    except ReplayError:
        check("replay real: now_ms before start raises", True)
    rf.advance_day()
    check("replay real: day 1 + now_ms = day's last eligible ts",
          rf.day() == 1 and rf.now_ms() == T0)
    bid, ask = rf.spot_quotes()
    check("replay M-2 sides: sell→bid 99.4, buy→ask 99.6 (indicative NOT surfaced)",
          bid.px.value == 99.4 and ask.px.value == 99.6
          and ask.instrument.symbol == "BTC-USD")
    check("replay M-3 provenance: px=DESK_RFQ_QUOTE; ask ref=SPOT_BOOK_MID; "
          "latest sell (composite_index) → REFERENCE_OTHER — never naked",
          ask.px.source == PriceSource.DESK_RFQ_QUOTE
          and bid.px.source == PriceSource.DESK_RFQ_QUOTE
          and ask.ref_mid.source == PriceSource.SPOT_BOOK_MID
          and bid.ref_mid.source == PriceSource.REFERENCE_OTHER)
    check("replay M-4/M-5: size=notional/px, ttl=expiry−ts",
          abs(ask.size_quote - 50_000.0 / 99.6) < 1e-9
          and ask.ttl_ms == 30_000)
    fb, fa = rf.forward_quotes(30)
    check("replay M-6: forward pair surfaced with tenor parsed",
          fa.px.value == 101.0 and fb.px.value == 100.9
          and fa.instrument.kind == "forward"
          and fa.instrument.symbol == "BTC-USD-FWD-30D")
    pm = rf.perp_mark()
    check("replay perp_mark from perp-kind reference (PERP_MARK source)",
          pm.value == 100.1 and pm.source == PriceSource.PERP_MARK)
    check("replay M-10 refused surfaces raise NotImplementedError",
          _raises_notimpl(lambda: rf.funding_obs)
          and _raises_notimpl(rf.settlement_print)
          and _raises_notimpl(rf.printed_funding_between, T0, T0 + 1)
          and _raises_notimpl(rf.true_apr))
    rf.advance_day()
    check("replay real: day 2 surfaces the later pair",
          rf.day() == 2 and rf.spot_quotes()[0].px.value == 100.4)
    try:
        rf.advance_day()
        check("replay M-7 exhaustion raises", False, "no exception")
    except ReplayError as e:
        check("replay M-7 exhaustion raises", "exhausted" in str(e))

    # 10d: M-6 fail-closed on unparseable forward symbol
    bj = RawRFQJournal(os.path.join(tmp, "badfwd.jsonl"))
    bj.append(mk2(rfq_id="BF-1", instrument="BTC-USD-FWD-XX", instrument_kind="forward"))
    try:
        JournalReplayFeed(bj, "BTC-USD")
        check("replay M-6 bad forward symbol refused", False, "no exception")
    except ReplayError as e:
        check("replay M-6 bad forward symbol refused", "M-6" in str(e))

    # --- 11. W1-INFRA coverage report (v0.6.3, sealed docs/w1-coverage-report.md) ---
    import hashlib as _h3
    import subprocess as _sp
    from quant_arb.feeds.coverage import (CoverageError, journal_coverage,
                                          render_report)

    # 11a: source wall — the smoke journal is synthetic; default census refuses (C-7)
    try:
        journal_coverage(smoke)
        check("coverage source wall refuses synthetic journal (C-7)",
              False, "no exception")
    except CoverageError as e:
        check("coverage source wall refuses synthetic journal (C-7)", "C-7" in str(e))

    # 11b: machinery mode works on the smoke journal; read-only (C-8)
    _sm_before2 = _h3.sha256(open(smoke_path, "rb").read()).hexdigest()
    cov_syn = journal_coverage(smoke, allow_synthetic=True)
    check("coverage machinery mode: families census + byte-identical (C-8)",
          cov_syn["synthetic_mode"] is True and len(cov_syn["families"]) >= 1
          and _h3.sha256(open(smoke_path, "rb").read()).hexdigest() == _sm_before2)

    # 11c: hand-built REAL journal — the full census surface
    DAY3 = T0 + 2 * 86_400_000
    cj = RawRFQJournal(os.path.join(tmp, "cov.jsonl"))
    for rec in [
        mk2(rfq_id="RB-C1", side="buy", quoted_price=99.6),
        mk2(rfq_id="RS-C1", side="sell", quoted_price=99.4),
        mk2(rfq_id="FB-C1", instrument="BTC-USD-FWD-30D", instrument_kind="forward",
            side="buy", quoted_price=101.0, quote_expiry_ts=T0 + 30 * 86_400_000),
        mk2(rfq_id="FS-C1", instrument="BTC-USD-FWD-30D", instrument_kind="forward",
            side="sell", quoted_price=100.9, quote_expiry_ts=T0 + 30 * 86_400_000),
        mk2(rfq_id="PP-C1", instrument="BTC-USD-PERP", instrument_kind="perp",
            side="buy", quoted_price=100.2, reference_price=100.1,
            reference_source="perp_mark"),
        mk2(rfq_id="RB-C2", ts=DAY2, quote_expiry_ts=DAY2 + 30_000,
            reference_ts=DAY2 - 1000, side="buy", quoted_price=100.6),
        mk2(rfq_id="RS-C2", ts=DAY2, quote_expiry_ts=DAY2 + 30_000,
            reference_ts=DAY2 - 1000, side="sell", quoted_price=100.4),
        mk2(rfq_id="RB-C3", ts=DAY3, quote_expiry_ts=DAY3 + 30_000,
            reference_ts=DAY3 - 1000, side="buy", quoted_price=101.6),
        mk2(rfq_id="EX-C1", status="expired", quoted_price=None, quote_type=None,
            quote_expiry_ts=None, fees_included_in_price=None, spread_bps=None,
            reject_reason="desk_timeout"),
        mk2(rfq_id="NR-C1", status="no_response", quoted_price=None, quote_type=None,
            quote_expiry_ts=None, fees_included_in_price=None, spread_bps=None),
        mk2(rfq_id="IN-C1", quote_type="indicative", side="buy", quoted_price=98.0),
        mk2(rfq_id="CC-C1", notional_ccy="EUR", side="sell", quoted_price=99.4),
        mk2(rfq_id="BF-C1", instrument="BTC-USD-FWD-30", instrument_kind="forward"),
        mk2(rfq_id="CF-C1", instrument_kind="cfd"),
        mk2(rfq_id="EB-C1", instrument="ETH-USD", side="buy", quoted_price=3.6),
        mk2(rfq_id="ES-C1", instrument="ETH-USD", side="sell", quoted_price=3.59),
    ]:
        cj.append(rec)
    _cj_before = _h3.sha256(open(cj.path, "rb").read()).hexdigest()
    cov = journal_coverage(cj)
    btc = next(f for f in cov["families"] if f["symbol"] == "BTC-USD")
    eth = next(f for f in cov["families"] if f["symbol"] == "ETH-USD")

    check("coverage: two families, sorted (C-1/C-9)",
          [f["symbol"] for f in cov["families"]] == ["BTC-USD", "ETH-USD"])
    check("coverage BTC: eligibility breakdown exact (C-3: 12 family records, "
          "8 eligible, 1 expired + 1 no_response + 1 indicative — bad-symbol "
          "and other-kind records stay unclassified)",
          btc["total_records"] == 12 and btc["eligible"] == 8
          and btc["ineligible"]["by_status"] == {"expired": 1, "no_response": 1}
          and btc["ineligible"]["indicative"] == 1)
    check("coverage BTC: unusable named with M-4 shape",
          len(btc["unusable"]) == 1 and "CC-C1" in btc["unusable"][0]
          and "M-4" in btc["unusable"][0])
    check("coverage BTC: day coverage (3 quote days, 2026-01-01…03) (C-5)",
          btc["quote_days"] == 3 and btc["first_day"] == "2026-01-01"
          and btc["last_day"] == "2026-01-03")
    check("coverage BTC: spot 2 full pair + partial day [3] (C-6)",
          btc["spot_days"] == 3 and btc["spot_full_pair_days"] == 2
          and btc["partial_spot_days"] == [3])
    check("coverage BTC: tenor census 30D — 2 rec, 1 full pair (C-6)",
          btc["tenors"] == {"30": {"records": 2, "full_pair_days": 1}})
    check("coverage BTC: perp days + venues census",
          btc["perp_days"] == 1 and btc["venues"] == ["DESK-R"])
    check("coverage: unclassified buckets — report-don't-refuse (C-2)",
          len(cov["unclassified"]["bad_symbols"]) == 1
          and "BF-C1" in cov["unclassified"]["bad_symbols"][0]
          and len(cov["unclassified"]["other_kinds"]) == 1
          and "CF-C1" in cov["unclassified"]["other_kinds"][0])
    check("coverage ETH: minimal family (2 eligible, 1 full-pair day)",
          eth["total_records"] == 2 and eth["eligible"] == 2
          and eth["spot_full_pair_days"] == 1 and eth["quote_days"] == 1)
    check("coverage: read-only — journal byte-identical (C-8)",
          _h3.sha256(open(cj.path, "rb").read()).hexdigest() == _cj_before)

    # 11d: family filter + determinism + JSON contract (C-9)
    cov_eth = journal_coverage(cj, family="ETH-USD")
    check("coverage: --family filter restricts to one family (C-9)",
          [f["symbol"] for f in cov_eth["families"]] == ["ETH-USD"])
    check("coverage: deterministic — same journal, same report (C-9)",
          journal_coverage(cj) == cov)
    check("coverage: JSON-serializable contract (C-9)",
          json.loads(json.dumps(cov))["kind"] == "rfq-journal-coverage")

    # 11e: the additive replay-feed observability fix (describe()['ineligible'])
    rf_c = JournalReplayFeed(rj, "BTC-USD")
    check("replay describe(): ineligible counter counts M-1 drops (C-3 additive)",
          rf_c.describe()["ineligible"] == 1)     # IN-1 (indicative) in the 10c journal

    # 11f: empty journal — a valid honest report, never an error (sealed decision 6)
    ej = RawRFQJournal(os.path.join(tmp, "empty.jsonl"))
    cov_e = journal_coverage(ej)
    check("coverage: empty journal → 0 families, honest render",
          cov_e["families"] == [] and "no classifiable records" in render_report(cov_e))

    # 11g: CLI end-to-end (scripts/rfq_coverage.py) — real subprocesses
    cli = os.path.join(os.path.dirname(__file__), "..", "..", "scripts",
                       "rfq_coverage.py")
    r1 = _sp.run([sys.executable, cli, "--journal", cj.path, "--json"],
                 capture_output=True, text=True)
    ok1 = (r1.returncode == 0 and json.loads(r1.stdout)["chain"]["lines"] == 16
           and len(json.loads(r1.stdout)["families"]) == 2)
    check("coverage CLI: --json report, exit 0, census matches", ok1, r1.stderr[-200:])
    r2 = _sp.run([sys.executable, cli, "--smoke-journal"],
                 capture_output=True, text=True)
    check("coverage CLI: smoke journal walled without --allow-synthetic (exit 1)",
          r2.returncode == 1 and "C-7" in r2.stderr)
    r3 = _sp.run([sys.executable, cli, "--journal", cj.path],
                 capture_output=True, text=True)
    check("coverage CLI: human render contains the family + census-only line",
          r3.returncode == 0 and "BTC-USD" in r3.stdout
          and "no research number" in r3.stdout)
    r4 = _sp.run([sys.executable, cli, "--journal", cj.path, "--family", "BTC"],
                 capture_output=True, text=True)
    check("coverage CLI: bad family symbol refused (C-1 BASE-QUOTE form)",
          r4.returncode == 1 and "C-1" in r4.stderr)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{'ALL CHECKS PASSED' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
sys.exit(len(FAILS))
