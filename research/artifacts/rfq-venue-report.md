# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 28 lines · head `8bc56b9900def800…`
* truncation check: passed (live head == recorded head)
* counts: total 28 · by source {'real': 28, 'synthetic': 0} · by status {'quoted': 28}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 28 records · 28 quoted (28 firm / 0 indicative) · mean -7.5656 bps · p50 -7.5065 · p05 -10.462 · p95 -5.0064 · n>0 0
    - BTC-USDT: mean -10.1246 bps
    - BTC-USDT-PERP: mean -5.0065 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 157.8503, 'p25': 209.867, 'p50': 233.555, 'p75': 247.139, 'p95': 264.8823}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

