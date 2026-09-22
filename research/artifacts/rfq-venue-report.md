# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 127 lines · head `efa3b2accdecf7b4…`
* truncation check: passed (live head == recorded head)
* counts: total 127 · by source {'real': 127, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 125, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 127 records · 125 quoted (125 firm / 0 indicative) · mean -7.5331 bps · p50 -5.0065 · p05 -10.4389 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.1008 bps
    - BTC-USDT-PERP: mean -5.0062 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 153.678, 'p25': 200.983, 'p50': 221.993, 'p75': 233.523, 'p95': 256.2185}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

