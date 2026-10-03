# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 359 lines · head `e2705d9ffe9bb1dc…`
* truncation check: passed (live head == recorded head)
* counts: total 359 · by source {'real': 359, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 355, 'rejected': 3}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 359 records · 355 quoted (355 firm / 0 indicative) · mean -7.5487 bps · p50 -10.0058 · p05 -10.2945 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0727 bps
    - BTC-USDT-PERP: mean -5.0104 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 142.9114, 'p25': 188.3075, 'p50': 217.047, 'p75': 234.369, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

