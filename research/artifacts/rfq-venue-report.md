# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 24 lines · head `7320ed736be453e7…`
* truncation check: passed (live head == recorded head)
* counts: total 24 · by source {'real': 24, 'synthetic': 0} · by status {'quoted': 24}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 24 records · 24 quoted (24 firm / 0 indicative) · mean -7.5754 bps · p50 -7.5065 · p05 -10.5753 · p95 -5.0065 · n>0 0
    - BTC-USDT: mean -10.1443 bps
    - BTC-USDT-PERP: mean -5.0065 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 155.4661, 'p25': 208.0455, 'p50': 230.4465, 'p75': 247.9793, 'p95': 267.8307}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

