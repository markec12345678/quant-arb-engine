# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 327 lines · head `81822eb03693b0da…`
* truncation check: passed (live head == recorded head)
* counts: total 327 · by source {'real': 327, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 324, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 327 records · 324 quoted (324 firm / 0 indicative) · mean -7.5438 bps · p50 -7.7751 · p05 -10.2964 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0768 bps
    - BTC-USDT-PERP: mean -5.0108 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 148.145, 'p25': 185.311, 'p50': 218.34, 'p75': 234.369, 'p95': 264.8232}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

