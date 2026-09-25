# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 207 lines · head `503c84d4266a35dc…`
* truncation check: passed (live head == recorded head)
* counts: total 207 · by source {'real': 207, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 204, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 207 records · 204 quoted (204 firm / 0 indicative) · mean -7.5475 bps · p50 -7.7751 · p05 -10.3004 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0836 bps
    - BTC-USDT-PERP: mean -5.0113 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.514, 'p25': 200.085, 'p50': 225.297, 'p75': 237.119, 'p95': 268.1265}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

