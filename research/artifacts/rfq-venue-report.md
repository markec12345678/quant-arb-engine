# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 139 lines · head `60a599528c018e46…`
* truncation check: passed (live head == recorded head)
* counts: total 139 · by source {'real': 139, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 137, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 139 records · 137 quoted (137 firm / 0 indicative) · mean -7.5371 bps · p50 -5.0065 · p05 -10.4727 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.1053 bps
    - BTC-USDT-PERP: mean -5.0061 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 152.197, 'p25': 197.961, 'p50': 221.741, 'p75': 231.966, 'p95': 256.1135}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

