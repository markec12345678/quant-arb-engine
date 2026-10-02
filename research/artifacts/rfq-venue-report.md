# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 331 lines · head `4ad2b5ef8e578482…`
* truncation check: passed (live head == recorded head)
* counts: total 331 · by source {'real': 331, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 327, 'rejected': 3}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 331 records · 327 quoted (327 firm / 0 indicative) · mean -7.5523 bps · p50 -10.0058 · p05 -10.2998 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0782 bps
    - BTC-USDT-PERP: mean -5.0108 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 140.494, 'p25': 183.215, 'p50': 217.974, 'p75': 234.1735, 'p95': 264.49}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

