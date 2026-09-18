# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 36 lines · head `f91cb1d83ea15e71…`
* truncation check: passed (live head == recorded head)
* counts: total 36 · by source {'real': 36, 'synthetic': 0} · by status {'quoted': 36}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 36 records · 36 quoted (36 firm / 0 indicative) · mean -7.5621 bps · p50 -7.5064 · p05 -10.3878 · p95 -5.0062 · n>0 0
    - BTC-USDT: mean -10.1177 bps
    - BTC-USDT-PERP: mean -5.0064 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 162.6187, 'p25': 210.802, 'p50': 230.1775, 'p75': 239.804, 'p95': 258.9855}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

