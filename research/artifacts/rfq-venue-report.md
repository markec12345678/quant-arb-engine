# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 259 lines · head `8cb033b42ac6a064…`
* truncation check: passed (live head == recorded head)
* counts: total 259 · by source {'real': 259, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 256, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 259 records · 256 quoted (256 firm / 0 indicative) · mean -7.5423 bps · p50 -7.7751 · p05 -10.2899 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0725 bps
    - BTC-USDT-PERP: mean -5.012 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.514, 'p25': 197.961, 'p50': 224.063, 'p75': 237.528, 'p95': 270.3611}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

