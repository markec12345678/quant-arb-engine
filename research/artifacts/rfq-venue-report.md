# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 319 lines · head `327f380b4140865b…`
* truncation check: passed (live head == recorded head)
* counts: total 319 · by source {'real': 319, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 316, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 319 records · 316 quoted (316 firm / 0 indicative) · mean -7.5448 bps · p50 -7.7751 · p05 -10.298 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0786 bps
    - BTC-USDT-PERP: mean -5.011 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 147.6485, 'p25': 183.3565, 'p50': 217.974, 'p75': 233.978, 'p95': 265.323}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

