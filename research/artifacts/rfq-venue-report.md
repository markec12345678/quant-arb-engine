[rfq-replay] journal=research/artifacts/rfq/journal-venue.jsonl
# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 4 lines · head `ee68683dda1570d6…`
* truncation check: passed (live head == recorded head)
* counts: total 4 · by source {'real': 4, 'synthetic': 0} · by status {'quoted': 4}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 4 records · 4 quoted (4 firm / 0 indicative) · mean -7.67 bps · p50 -7.5065 · p05 -10.5622 · p95 -5.0065 · n>0 0
    - BTC-USDT: mean -10.3334 bps
    - BTC-USDT-PERP: mean -5.0065 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 153.678, 'p25': 153.678, 'p50': 159.6385, 'p75': 165.599, 'p95': 165.599}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

