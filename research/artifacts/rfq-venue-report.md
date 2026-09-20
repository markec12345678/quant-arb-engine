# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 72 lines · head `69044ed9dcbf3d4b…`
* truncation check: passed (live head == recorded head)
* counts: total 72 · by source {'real': 72, 'synthetic': 0} · by status {'quoted': 71, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 72 records · 71 quoted (71 firm / 0 indicative) · mean -7.598 bps · p50 -10.0061 · p05 -10.4539 · p95 -5.0061 · n>0 0
    - BTC-USDT: mean -10.1178 bps
    - BTC-USDT-PERP: mean -5.0063 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 172.969, 'p25': 208.694, 'p50': 225.292, 'p75': 233.617, 'p95': 255.737}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

