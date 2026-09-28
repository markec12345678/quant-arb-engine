# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 267 lines · head `548210e3c88b0e3f…`
* truncation check: passed (live head == recorded head)
* counts: total 267 · by source {'real': 267, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 264, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 267 records · 264 quoted (264 firm / 0 indicative) · mean -7.5455 bps · p50 -7.7751 · p05 -10.2955 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0791 bps
    - BTC-USDT-PERP: mean -5.0118 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.5416, 'p25': 194.118, 'p50': 221.993, 'p75': 236.856, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

