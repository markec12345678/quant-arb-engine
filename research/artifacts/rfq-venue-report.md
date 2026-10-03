# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 363 lines · head `abf0620e83637afd…`
* truncation check: passed (live head == recorded head)
* counts: total 363 · by source {'real': 363, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 359, 'rejected': 3}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 363 records · 359 quoted (359 firm / 0 indicative) · mean -7.5484 bps · p50 -10.0058 · p05 -10.2938 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0723 bps
    - BTC-USDT-PERP: mean -5.0104 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 143.18, 'p25': 189.491, 'p50': 217.974, 'p75': 235.1335, 'p95': 269.5701}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

