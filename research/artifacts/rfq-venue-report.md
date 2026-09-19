# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 44 lines · head `376abf1f82c26983…`
* truncation check: passed (live head == recorded head)
* counts: total 44 · by source {'real': 44, 'synthetic': 0} · by status {'quoted': 44}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 44 records · 44 quoted (44 firm / 0 indicative) · mean -7.5698 bps · p50 -7.5064 · p05 -10.6058 · p95 -5.0062 · n>0 0
    - BTC-USDT: mean -10.1331 bps
    - BTC-USDT-PERP: mean -5.0064 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 165.599, 'p25': 210.802, 'p50': 226.2005, 'p75': 236.593, 'p95': 255.3}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

