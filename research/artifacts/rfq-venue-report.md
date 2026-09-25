# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 203 lines · head `6b13e6de123e1d8e…`
* truncation check: passed (live head == recorded head)
* counts: total 203 · by source {'real': 203, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 200, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 203 records · 200 quoted (200 firm / 0 indicative) · mean -7.5483 bps · p50 -7.7751 · p05 -10.3019 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0852 bps
    - BTC-USDT-PERP: mean -5.0115 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.514, 'p25': 199.385, 'p50': 225.682, 'p75': 237.528, 'p95': 269.4035}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

