# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 351 lines · head `0b336fc50b0ec32a…`
* truncation check: passed (live head == recorded head)
* counts: total 351 · by source {'real': 351, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 347, 'rejected': 3}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 351 records · 347 quoted (347 firm / 0 indicative) · mean -7.5497 bps · p50 -10.0058 · p05 -10.2959 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0742 bps
    - BTC-USDT-PERP: mean -5.0105 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 141.837, 'p25': 185.311, 'p50': 216.315, 'p75': 233.978, 'p95': 265.323}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

