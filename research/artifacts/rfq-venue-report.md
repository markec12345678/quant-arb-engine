# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 111 lines · head `fdfeefba831329a6…`
* truncation check: passed (live head == recorded head)
* counts: total 111 · by source {'real': 111, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 109, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 111 records · 109 quoted (109 firm / 0 indicative) · mean -7.5344 bps · p50 -5.0065 · p05 -10.4939 · p95 -5.0061 · n>0 0
    - BTC-USDT: mean -10.1093 bps
    - BTC-USDT-PERP: mean -5.0062 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 158.4015, 'p25': 204.9095, 'p50': 224.3, 'p75': 233.587, 'p95': 256.271}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

