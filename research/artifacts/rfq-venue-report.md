# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 143 lines · head `f27f6b6af022df1e…`
* truncation check: passed (live head == recorded head)
* counts: total 143 · by source {'real': 143, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 140, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 143 records · 140 quoted (140 firm / 0 indicative) · mean -7.5543 bps · p50 -7.5062 · p05 -10.4647 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.1024 bps
    - BTC-USDT-PERP: mean -5.0061 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 152.3451, 'p25': 198.673, 'p50': 221.993, 'p75': 232.962, 'p95': 256.096}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

