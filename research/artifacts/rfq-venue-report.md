# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 283 lines · head `000ac84f0ac7aa5e…`
* truncation check: passed (live head == recorded head)
* counts: total 283 · by source {'real': 283, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 280, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 283 records · 280 quoted (280 firm / 0 indicative) · mean -7.5472 bps · p50 -7.7751 · p05 -10.301 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0828 bps
    - BTC-USDT-PERP: mean -5.0116 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.514, 'p25': 187.124, 'p50': 220.46, 'p75': 236.2455, 'p95': 269.5701}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

