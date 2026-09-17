# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 12 lines · head `74dcff80cb85deb3…`
* truncation check: passed (live head == recorded head)
* counts: total 12 · by source {'real': 12, 'synthetic': 0} · by status {'quoted': 12}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 12 records · 12 quoted (12 firm / 0 indicative) · mean -7.561 bps · p50 -7.5065 · p05 -10.3007 · p95 -5.0065 · n>0 0
    - BTC-USDT: mean -10.1155 bps
    - BTC-USDT-PERP: mean -5.0065 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 153.678, 'p25': 165.599, 'p50': 226.357, 'p75': 247.139, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

