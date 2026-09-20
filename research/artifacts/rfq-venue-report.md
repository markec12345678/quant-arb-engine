# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 88 lines · head `ffe14f1dace70606…`
* truncation check: passed (live head == recorded head)
* counts: total 88 · by source {'real': 88, 'synthetic': 0} · by status {'quoted': 87, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 88 records · 87 quoted (87 firm / 0 indicative) · mean -7.5871 bps · p50 -10.0061 · p05 -10.4645 · p95 -5.0061 · n>0 0
    - BTC-USDT: mean -10.1093 bps
    - BTC-USDT-PERP: mean -5.0063 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 178.659, 'p25': 208.694, 'p50': 225.292, 'p75': 233.617, 'p95': 255.3}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

