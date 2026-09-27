# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 247 lines · head `3010b88fd1a4860e…`
* truncation check: passed (live head == recorded head)
* counts: total 247 · by source {'real': 247, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 244, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 247 records · 244 quoted (244 firm / 0 indicative) · mean -7.5427 bps · p50 -7.7751 · p05 -10.2955 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0749 bps
    - BTC-USDT-PERP: mean -5.0105 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.514, 'p25': 195.9155, 'p50': 224.3, 'p75': 237.119, 'p95': 268.1265}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

