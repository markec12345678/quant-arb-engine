# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 60 lines · head `459427de2cc977cd…`
* truncation check: passed (live head == recorded head)
* counts: total 60 · by source {'real': 60, 'synthetic': 0} · by status {'quoted': 59, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 60 records · 59 quoted (59 firm / 0 indicative) · mean -7.6101 bps · p50 -10.0061 · p05 -10.5713 · p95 -5.0062 · n>0 0
    - BTC-USDT: mean -10.1271 bps
    - BTC-USDT-PERP: mean -5.0063 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 165.599, 'p25': 210.802, 'p50': 228.9065, 'p75': 233.978, 'p95': 256.271}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

