# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 271 lines · head `27d7067f4562a942…`
* truncation check: passed (live head == recorded head)
* counts: total 271 · by source {'real': 271, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 268, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 271 records · 268 quoted (268 firm / 0 indicative) · mean -7.5473 bps · p50 -7.7751 · p05 -10.2996 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0829 bps
    - BTC-USDT-PERP: mean -5.0118 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.1165, 'p25': 188.3075, 'p50': 221.741, 'p75': 236.593, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

