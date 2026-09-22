# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 135 lines · head `2e450b6f62b79628…`
* truncation check: passed (live head == recorded head)
* counts: total 135 · by source {'real': 135, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 133, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 135 records · 133 quoted (133 firm / 0 indicative) · mean -7.538 bps · p50 -5.0065 · p05 -10.4833 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.1083 bps
    - BTC-USDT-PERP: mean -5.0062 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 152.197, 'p25': 198.673, 'p50': 221.741, 'p75': 232.43, 'p95': 256.1485}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

