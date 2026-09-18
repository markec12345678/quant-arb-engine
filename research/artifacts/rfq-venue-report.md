# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 40 lines · head `c1b113ef76c5cfca…`
* truncation check: passed (live head == recorded head)
* counts: total 40 · by source {'real': 40, 'synthetic': 0} · by status {'quoted': 40}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 40 records · 40 quoted (40 firm / 0 indicative) · mean -7.5733 bps · p50 -7.5064 · p05 -10.6611 · p95 -5.0062 · n>0 0
    - BTC-USDT: mean -10.1401 bps
    - BTC-USDT-PERP: mean -5.0064 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 165.0029, 'p25': 210.5682, 'p50': 228.9065, 'p75': 237.3957, 'p95': 256.0371}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

