# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 307 lines · head `1cd0dfaec1801e06…`
* truncation check: passed (live head == recorded head)
* counts: total 307 · by source {'real': 307, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 304, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 307 records · 304 quoted (304 firm / 0 indicative) · mean -7.5463 bps · p50 -7.7751 · p05 -10.3004 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0815 bps
    - BTC-USDT-PERP: mean -5.0112 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 144.6695, 'p25': 183.215, 'p50': 217.974, 'p75': 233.8425, 'p95': 265.323}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

