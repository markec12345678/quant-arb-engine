# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 68 lines · head `2baa5987984c692a…`
* truncation check: passed (live head == recorded head)
* counts: total 68 · by source {'real': 68, 'synthetic': 0} · by status {'quoted': 67, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 68 records · 67 quoted (67 firm / 0 indicative) · mean -7.6035 bps · p50 -10.0061 · p05 -10.4969 · p95 -5.0061 · n>0 0
    - BTC-USDT: mean -10.1244 bps
    - BTC-USDT-PERP: mean -5.0063 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 171.0237, 'p25': 209.867, 'p50': 226.2005, 'p75': 233.707, 'p95': 255.9312}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

