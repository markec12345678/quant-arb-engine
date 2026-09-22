# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 131 lines · head `842b55e22184687c…`
* truncation check: passed (live head == recorded head)
* counts: total 131 · by source {'real': 131, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 129, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 131 records · 129 quoted (129 firm / 0 indicative) · mean -7.5389 bps · p50 -5.0065 · p05 -10.4939 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.1111 bps
    - BTC-USDT-PERP: mean -5.0062 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 152.197, 'p25': 197.961, 'p50': 221.741, 'p75': 232.9765, 'p95': 256.1835}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

