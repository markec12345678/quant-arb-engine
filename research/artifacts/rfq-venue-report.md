# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 92 lines · head `8518caecba14384d…`
* truncation check: passed (live head == recorded head)
* counts: total 92 · by source {'real': 92, 'synthetic': 0} · by status {'quoted': 91, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 92 records · 91 quoted (91 firm / 0 indicative) · mean -7.5898 bps · p50 -10.0061 · p05 -10.5382 · p95 -5.0061 · n>0 0
    - BTC-USDT: mean -10.1172 bps
    - BTC-USDT-PERP: mean -5.0063 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 160.089, 'p25': 204.907, 'p50': 224.343, 'p75': 233.587, 'p95': 255.3}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

