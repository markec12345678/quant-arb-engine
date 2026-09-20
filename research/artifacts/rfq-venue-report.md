# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 84 lines · head `48329edcbd7af6b5…`
* truncation check: passed (live head == recorded head)
* counts: total 84 · by source {'real': 84, 'synthetic': 0} · by status {'quoted': 83, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 84 records · 83 quoted (83 firm / 0 indicative) · mean -7.591 bps · p50 -10.0061 · p05 -10.4982 · p95 -5.0061 · n>0 0
    - BTC-USDT: mean -10.1142 bps
    - BTC-USDT-PERP: mean -5.0063 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 178.659, 'p25': 205.175, 'p50': 225.292, 'p75': 233.707, 'p95': 255.3}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

