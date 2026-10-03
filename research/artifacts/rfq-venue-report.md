# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 347 lines · head `8c9f353f5daeb257…`
* truncation check: passed (live head == recorded head)
* counts: total 347 · by source {'real': 347, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 343, 'rejected': 3}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 347 records · 343 quoted (343 firm / 0 indicative) · mean -7.5502 bps · p50 -10.0058 · p05 -10.2966 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.075 bps
    - BTC-USDT-PERP: mean -5.0106 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 141.2998, 'p25': 183.498, 'p50': 217.047, 'p75': 234.1735, 'p95': 265.323}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

