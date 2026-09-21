# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 108 lines · head `0ec81e01fb764565…`
* truncation check: passed (live head == recorded head)
* counts: total 108 · by source {'real': 108, 'synthetic': 0} · by status {'quoted': 107, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 108 records · 107 quoted (107 firm / 0 indicative) · mean -7.5816 bps · p50 -10.0058 · p05 -10.4992 · p95 -5.0061 · n>0 0
    - BTC-USDT: mean -10.1093 bps
    - BTC-USDT-PERP: mean -5.0062 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 158.0512, 'p25': 204.907, 'p50': 224.343, 'p75': 233.587, 'p95': 256.2097}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

