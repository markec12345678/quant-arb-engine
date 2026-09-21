# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 115 lines · head `81485b6ce2b1b2fe…`
* truncation check: passed (live head == recorded head)
* counts: total 115 · by source {'real': 115, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 113, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 115 records · 113 quoted (113 firm / 0 indicative) · mean -7.5333 bps · p50 -5.0065 · p05 -10.4833 · p95 -5.006 · n>0 0
    - BTC-USDT: mean -10.1056 bps
    - BTC-USDT-PERP: mean -5.0062 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 158.8685, 'p25': 202.581, 'p50': 221.993, 'p75': 233.555, 'p95': 256.271}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

