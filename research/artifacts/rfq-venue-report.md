# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 104 lines · head `c080b622f5fb804a…`
* truncation check: passed (live head == recorded head)
* counts: total 104 · by source {'real': 104, 'synthetic': 0} · by status {'quoted': 103, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 104 records · 103 quoted (103 firm / 0 indicative) · mean -7.5845 bps · p50 -10.0061 · p05 -10.5098 · p95 -5.0061 · n>0 0
    - BTC-USDT: mean -10.1131 bps
    - BTC-USDT-PERP: mean -5.0063 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 160.9155, 'p25': 205.1093, 'p50': 225.292, 'p75': 233.617, 'p95': 256.2448}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

