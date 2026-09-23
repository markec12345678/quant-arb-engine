# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 147 lines · head `196b8725df9911a4…`
* truncation check: passed (live head == recorded head)
* counts: total 147 · by source {'real': 147, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 144, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 147 records · 144 quoted (144 firm / 0 indicative) · mean -7.5529 bps · p50 -7.5062 · p05 -10.4447 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0998 bps
    - BTC-USDT-PERP: mean -5.0061 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 152.6413, 'p25': 199.385, 'p50': 224.063, 'p75': 233.555, 'p95': 256.271}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

