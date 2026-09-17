# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 16 lines · head `b5fd5c7f9bc519dd…`
* truncation check: passed (live head == recorded head)
* counts: total 16 · by source {'real': 16, 'synthetic': 0} · by status {'quoted': 16}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 16 records · 16 quoted (16 firm / 0 indicative) · mean -7.5528 bps · p50 -7.5065 · p05 -10.2353 · p95 -5.0065 · n>0 0
    - BTC-USDT: mean -10.0991 bps
    - BTC-USDT-PERP: mean -5.0065 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 153.678, 'p25': 193.3355, 'p50': 226.357, 'p75': 247.9793, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

