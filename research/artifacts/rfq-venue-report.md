# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 255 lines · head `99157ea0d8253b28…`
* truncation check: passed (live head == recorded head)
* counts: total 255 · by source {'real': 255, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 252, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 255 records · 252 quoted (252 firm / 0 indicative) · mean -7.5419 bps · p50 -7.7751 · p05 -10.2918 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0736 bps
    - BTC-USDT-PERP: mean -5.0103 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.514, 'p25': 197.837, 'p50': 224.063, 'p75': 237.119, 'p95': 266.7387}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

