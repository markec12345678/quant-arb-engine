# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 20 lines · head `7a5f6ced9186ada9…`
* truncation check: passed (live head == recorded head)
* counts: total 20 · by source {'real': 20, 'synthetic': 0} · by status {'quoted': 20}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 20 records · 20 quoted (20 firm / 0 indicative) · mean -7.5892 bps · p50 -7.5065 · p05 -10.6732 · p95 -5.0065 · n>0 0
    - BTC-USDT: mean -10.1718 bps
    - BTC-USDT-PERP: mean -5.0065 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 153.678, 'p25': 202.581, 'p50': 218.605, 'p75': 247.139, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

