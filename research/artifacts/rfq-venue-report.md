# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 119 lines · head `7145dff5614797bb…`
* truncation check: passed (live head == recorded head)
* counts: total 119 · by source {'real': 119, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 117, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 119 records · 117 quoted (117 firm / 0 indicative) · mean -7.533 bps · p50 -5.0065 · p05 -10.4727 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.1033 bps
    - BTC-USDT-PERP: mean -5.0062 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 159.3355, 'p25': 203.744, 'p50': 221.993, 'p75': 233.523, 'p95': 256.271}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

