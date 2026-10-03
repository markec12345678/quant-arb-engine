# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 355 lines · head `bca95ab382c96453…`
* truncation check: passed (live head == recorded head)
* counts: total 355 · by source {'real': 355, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 351, 'rejected': 3}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 355 records · 351 quoted (351 firm / 0 indicative) · mean -7.5492 bps · p50 -10.0058 · p05 -10.2952 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0734 bps
    - BTC-USDT-PERP: mean -5.0105 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 142.3742, 'p25': 187.124, 'p50': 216.315, 'p75': 234.1735, 'p95': 265.323}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

