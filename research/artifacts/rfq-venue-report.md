# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 8 lines · head `a7e7ddf205938472…`
* truncation check: passed (live head == recorded head)
* counts: total 8 · by source {'real': 8, 'synthetic': 0} · by status {'quoted': 8}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 8 records · 8 quoted (8 firm / 0 indicative) · mean -7.5882 bps · p50 -7.5065 · p05 -10.4315 · p95 -5.0065 · n>0 0
    - BTC-USDT: mean -10.17 bps
    - BTC-USDT-PERP: mean -5.0065 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 153.678, 'p25': 162.6187, 'p50': 189.2545, 'p75': 221.4673, 'p95': 247.139}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

