# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 76 lines · head `a47ba411a5a4b3ca…`
* truncation check: passed (live head == recorded head)
* counts: total 76 · by source {'real': 76, 'synthetic': 0} · by status {'quoted': 75, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 76 records · 75 quoted (75 firm / 0 indicative) · mean -7.6001 bps · p50 -10.0061 · p05 -10.529 · p95 -5.0061 · n>0 0
    - BTC-USDT: mean -10.1256 bps
    - BTC-USDT-PERP: mean -5.0063 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 175.649, 'p25': 209.867, 'p50': 227.1065, 'p75': 233.707, 'p95': 255.5428}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

