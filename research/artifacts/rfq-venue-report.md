# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 227 lines · head `c3122c06d5327fb1…`
* truncation check: passed (live head == recorded head)
* counts: total 227 · by source {'real': 227, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 224, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 227 records · 224 quoted (224 firm / 0 indicative) · mean -7.5445 bps · p50 -7.7751 · p05 -10.2955 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0782 bps
    - BTC-USDT-PERP: mean -5.0109 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 150.9575, 'p25': 197.961, 'p50': 224.3, 'p75': 237.528, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

