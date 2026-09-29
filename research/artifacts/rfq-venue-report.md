# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 279 lines · head `5e8594d80d0e3cf5…`
* truncation check: passed (live head == recorded head)
* counts: total 279 · by source {'real': 279, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 276, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 279 records · 276 quoted (276 firm / 0 indicative) · mean -7.5474 bps · p50 -7.7751 · p05 -10.3012 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0832 bps
    - BTC-USDT-PERP: mean -5.0116 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.4345, 'p25': 185.311, 'p50': 220.683, 'p75': 236.593, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

