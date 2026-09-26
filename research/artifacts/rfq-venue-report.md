# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 211 lines · head `90ad27e11c1052cf…`
* truncation check: passed (live head == recorded head)
* counts: total 211 · by source {'real': 211, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 208, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 211 records · 208 quoted (208 firm / 0 indicative) · mean -7.5467 bps · p50 -7.7751 · p05 -10.2996 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0821 bps
    - BTC-USDT-PERP: mean -5.0112 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.514, 'p25': 200.785, 'p50': 225.682, 'p75': 238.362, 'p95': 271.6375}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

