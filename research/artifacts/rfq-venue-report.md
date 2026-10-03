# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 367 lines · head `049bebf90c660ea4…`
* truncation check: passed (live head == recorded head)
* counts: total 367 · by source {'real': 367, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 363, 'rejected': 3}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 367 records · 363 quoted (363 firm / 0 indicative) · mean -7.5479 bps · p50 -10.0058 · p05 -10.2928 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0716 bps
    - BTC-USDT-PERP: mean -5.0103 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 143.18, 'p25': 189.84, 'p50': 217.974, 'p75': 234.369, 'p95': 268.6263}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

