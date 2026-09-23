# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 159 lines · head `611f943f740d5db9…`
* truncation check: passed (live head == recorded head)
* counts: total 159 · by source {'real': 159, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 156, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 159 records · 156 quoted (156 firm / 0 indicative) · mean -7.5505 bps · p50 -7.5062 · p05 -10.3753 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.095 bps
    - BTC-USDT-PERP: mean -5.0061 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 153.5299, 'p25': 201.683, 'p50': 224.386, 'p75': 235.898, 'p95': 263.657}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

