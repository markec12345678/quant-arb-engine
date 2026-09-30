# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 303 lines · head `930393b718a58283…`
* truncation check: passed (live head == recorded head)
* counts: total 303 · by source {'real': 303, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 300, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 303 records · 300 quoted (300 firm / 0 indicative) · mean -7.5469 bps · p50 -7.7751 · p05 -10.301 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0825 bps
    - BTC-USDT-PERP: mean -5.0112 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 143.6765, 'p25': 182.707, 'p50': 217.974, 'p75': 233.978, 'p95': 265.323}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

