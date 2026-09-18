# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 32 lines · head `e94805948835a410…`
* truncation check: passed (live head == recorded head)
* counts: total 32 · by source {'real': 32, 'synthetic': 0} · by status {'quoted': 32}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 32 records · 32 quoted (32 firm / 0 indicative) · mean -7.5672 bps · p50 -7.5064 · p05 -10.4605 · p95 -5.0063 · n>0 0
    - BTC-USDT: mean -10.128 bps
    - BTC-USDT-PERP: mean -5.0065 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 160.2346, 'p25': 210.5682, 'p50': 232.04, 'p75': 241.6378, 'p95': 261.9339}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

