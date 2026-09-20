# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 80 lines · head `7438a1e0da88b234…`
* truncation check: passed (live head == recorded head)
* counts: total 80 · by source {'real': 80, 'synthetic': 0} · by status {'quoted': 79, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 80 records · 79 quoted (79 firm / 0 indicative) · mean -7.5953 bps · p50 -10.0061 · p05 -10.5197 · p95 -5.0061 · n>0 0
    - BTC-USDT: mean -10.1196 bps
    - BTC-USDT-PERP: mean -5.0063 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 178.329, 'p25': 210.5682, 'p50': 227.1065, 'p75': 233.7747, 'p95': 255.3486}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

