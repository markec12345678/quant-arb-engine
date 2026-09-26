# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 231 lines · head `5dbb8a9a3149feb6…`
* truncation check: passed (live head == recorded head)
* counts: total 231 · by source {'real': 231, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 228, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 231 records · 228 quoted (228 firm / 0 indicative) · mean -7.544 bps · p50 -7.7751 · p05 -10.2937 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0772 bps
    - BTC-USDT-PERP: mean -5.0108 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.1165, 'p25': 193.602, 'p50': 224.063, 'p75': 237.119, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

