# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 223 lines · head `369803861ff36c69…`
* truncation check: passed (live head == recorded head)
* counts: total 223 · by source {'real': 223, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 220, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 223 records · 220 quoted (220 firm / 0 indicative) · mean -7.5445 bps · p50 -7.7751 · p05 -10.2972 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.078 bps
    - BTC-USDT-PERP: mean -5.011 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.5232, 'p25': 198.9365, 'p50': 224.386, 'p75': 237.937, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

