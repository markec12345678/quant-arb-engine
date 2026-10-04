# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 371 lines · head `a308aef3ad542de8…`
* truncation check: passed (live head == recorded head)
* counts: total 371 · by source {'real': 371, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 367, 'rejected': 3}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 371 records · 367 quoted (367 firm / 0 indicative) · mean -7.5475 bps · p50 -10.0058 · p05 -10.2917 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0709 bps
    - BTC-USDT-PERP: mean -5.0103 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 143.18, 'p25': 187.124, 'p50': 217.047, 'p75': 234.1735, 'p95': 267.6825}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

