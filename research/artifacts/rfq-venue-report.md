# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 299 lines · head `62d233f3955cb296…`
* truncation check: passed (live head == recorded head)
* counts: total 299 · by source {'real': 299, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 296, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 299 records · 296 quoted (296 firm / 0 indicative) · mean -7.546 bps · p50 -7.7751 · p05 -10.298 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0806 bps
    - BTC-USDT-PERP: mean -5.0113 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 143.18, 'p25': 182.199, 'p50': 217.974, 'p75': 234.1735, 'p95': 265.7949}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

