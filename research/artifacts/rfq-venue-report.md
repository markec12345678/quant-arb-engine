# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 96 lines · head `0318a4cf628e5fe6…`
* truncation check: passed (live head == recorded head)
* counts: total 96 · by source {'real': 96, 'synthetic': 0} · by status {'quoted': 95, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 96 records · 95 quoted (95 firm / 0 indicative) · mean -7.5911 bps · p50 -10.0061 · p05 -10.529 · p95 -5.0061 · n>0 0
    - BTC-USDT: mean -10.122 bps
    - BTC-USDT-PERP: mean -5.0063 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 160.089, 'p25': 205.108, 'p50': 224.343, 'p75': 233.539, 'p95': 255.3}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

