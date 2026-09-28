# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 263 lines · head `ee60bd25799cb94f…`
* truncation check: passed (live head == recorded head)
* counts: total 263 · by source {'real': 263, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 260, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 263 records · 260 quoted (260 firm / 0 indicative) · mean -7.5417 bps · p50 -7.7751 · p05 -10.288 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0715 bps
    - BTC-USDT-PERP: mean -5.0119 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.5232, 'p25': 195.9155, 'p50': 222.421, 'p75': 237.119, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

