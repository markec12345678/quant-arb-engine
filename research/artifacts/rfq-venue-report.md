# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 52 lines · head `c96e507377f43fac…`
* truncation check: passed (live head == recorded head)
* counts: total 52 · by source {'real': 52, 'synthetic': 0} · by status {'quoted': 52}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 52 records · 52 quoted (52 firm / 0 indicative) · mean -7.56 bps · p50 -7.5063 · p05 -10.4605 · p95 -5.0062 · n>0 0
    - BTC-USDT: mean -10.1136 bps
    - BTC-USDT-PERP: mean -5.0063 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 165.599, 'p25': 212.401, 'p50': 228.9065, 'p75': 233.978, 'p95': 255.3}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

