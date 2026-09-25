# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 187 lines · head `bfca16e6c9313f31…`
* truncation check: passed (live head == recorded head)
* counts: total 187 · by source {'real': 187, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 184, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 187 records · 184 quoted (184 firm / 0 indicative) · mean -7.549 bps · p50 -7.7751 · p05 -10.3154 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.086 bps
    - BTC-USDT-PERP: mean -5.0119 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.7833, 'p25': 199.385, 'p50': 224.3, 'p75': 236.2455, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

