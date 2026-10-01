# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 323 lines · head `544fec72468b4fe8…`
* truncation check: passed (live head == recorded head)
* counts: total 323 · by source {'real': 323, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 320, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 323 records · 320 quoted (320 firm / 0 indicative) · mean -7.5443 bps · p50 -7.7751 · p05 -10.2972 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0777 bps
    - BTC-USDT-PERP: mean -5.0109 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 148.145, 'p25': 183.498, 'p50': 218.34, 'p75': 234.1735, 'p95': 265.1564}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

