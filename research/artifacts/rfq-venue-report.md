# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 151 lines · head `4bc90678617914e0…`
* truncation check: passed (live head == recorded head)
* counts: total 151 · by source {'real': 151, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 148, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 151 records · 148 quoted (148 firm / 0 indicative) · mean -7.553 bps · p50 -7.5062 · p05 -10.4216 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0998 bps
    - BTC-USDT-PERP: mean -5.0061 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 152.9375, 'p25': 200.983, 'p50': 224.3, 'p75': 233.707, 'p95': 256.366}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

