# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 291 lines · head `92bf45872159c26f…`
* truncation check: passed (live head == recorded head)
* counts: total 291 · by source {'real': 291, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 288, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 291 records · 288 quoted (288 firm / 0 indicative) · mean -7.5471 bps · p50 -7.7751 · p05 -10.2996 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0827 bps
    - BTC-USDT-PERP: mean -5.0114 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 150.352, 'p25': 183.498, 'p50': 219.889, 'p75': 235.1335, 'p95': 267.6825}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

