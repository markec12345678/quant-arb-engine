# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 195 lines · head `512740ae287dd53e…`
* truncation check: passed (live head == recorded head)
* counts: total 195 · by source {'real': 195, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 192, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 195 records · 192 quoted (192 firm / 0 indicative) · mean -7.5501 bps · p50 -7.7751 · p05 -10.3089 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0885 bps
    - BTC-USDT-PERP: mean -5.0117 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 152.0197, 'p25': 200.785, 'p50': 225.682, 'p75': 236.856, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

