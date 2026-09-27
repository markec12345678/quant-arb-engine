# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 243 lines · head `8cdfa09b8dd9eb33…`
* truncation check: passed (live head == recorded head)
* counts: total 243 · by source {'real': 243, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 240, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 243 records · 240 quoted (240 firm / 0 indicative) · mean -7.5433 bps · p50 -7.7751 · p05 -10.2972 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0761 bps
    - BTC-USDT-PERP: mean -5.0105 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.514, 'p25': 197.713, 'p50': 224.386, 'p75': 237.528, 'p95': 269.4035}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

