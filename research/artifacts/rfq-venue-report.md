# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 175 lines · head `661fa38764d16051…`
* truncation check: passed (live head == recorded head)
* counts: total 175 · by source {'real': 175, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 172, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 175 records · 172 quoted (172 firm / 0 indicative) · mean -7.547 bps · p50 -7.5062 · p05 -10.3192 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0879 bps
    - BTC-USDT-PERP: mean -5.0061 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.606, 'p25': 200.085, 'p50': 224.386, 'p75': 237.119, 'p95': 271.0248}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

