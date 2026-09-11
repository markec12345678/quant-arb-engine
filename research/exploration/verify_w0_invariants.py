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
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{'ALL CHECKS PASSED' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
sys.exit(len(FAILS))
