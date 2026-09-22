# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 123 lines · head `bd3891d564f6004a…`
* truncation check: passed (live head == recorded head)
* counts: total 123 · by source {'real': 123, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 121, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 123 records · 121 quoted (121 firm / 0 indicative) · mean -7.5321 bps · p50 -5.0065 · p05 -10.4621 · p95 -5.0059 · n>0 0
    - BTC-USDT: mean -10.1001 bps
    - BTC-USDT-PERP: mean -5.0062 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 159.569, 'p25': 204.907, 'p50': 224.063, 'p75': 233.555, 'p95': 256.2535}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

