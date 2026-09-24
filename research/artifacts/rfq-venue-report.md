# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 171 lines · head `b727ff66270b1eaf…`
* truncation check: passed (live head == recorded head)
* counts: total 171 · by source {'real': 171, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 168, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 171 records · 168 quoted (168 firm / 0 indicative) · mean -7.548 bps · p50 -7.5062 · p05 -10.329 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0898 bps
    - BTC-USDT-PERP: mean -5.0061 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.606, 'p25': 199.385, 'p50': 224.386, 'p75': 236.856, 'p95': 271.68}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

