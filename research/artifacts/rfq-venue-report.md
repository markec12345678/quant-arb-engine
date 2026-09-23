# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 155 lines · head `004ce01c04239aa6…`
* truncation check: passed (live head == recorded head)
* counts: total 155 · by source {'real': 155, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 152, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 155 records · 152 quoted (152 firm / 0 indicative) · mean -7.5517 bps · p50 -7.5062 · p05 -10.3984 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0973 bps
    - BTC-USDT-PERP: mean -5.0061 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 153.2337, 'p25': 202.581, 'p50': 224.386, 'p75': 234.938, 'p95': 263.657}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

