# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 311 lines · head `2725b13103292740…`
* truncation check: passed (live head == recorded head)
* counts: total 311 · by source {'real': 311, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 308, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 311 records · 308 quoted (308 firm / 0 indicative) · mean -7.5458 bps · p50 -7.7751 · p05 -10.2996 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0805 bps
    - BTC-USDT-PERP: mean -5.0111 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 145.6625, 'p25': 183.3565, 'p50': 217.974, 'p75': 233.707, 'p95': 265.323}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

