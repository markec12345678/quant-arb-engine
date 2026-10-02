# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 339 lines · head `fbbc646787ad285d…`
* truncation check: passed (live head == recorded head)
* counts: total 339 · by source {'real': 339, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 335, 'rejected': 3}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 339 records · 335 quoted (335 firm / 0 indicative) · mean -7.5512 bps · p50 -10.0058 · p05 -10.2982 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0766 bps
    - BTC-USDT-PERP: mean -5.0107 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 140.494, 'p25': 183.498, 'p50': 217.974, 'p75': 234.1735, 'p95': 265.7949}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

