# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 215 lines · head `404915651e3419a2…`
* truncation check: passed (live head == recorded head)
* counts: total 215 · by source {'real': 215, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 212, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 215 records · 212 quoted (212 firm / 0 indicative) · mean -7.5459 bps · p50 -7.7751 · p05 -10.2988 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0807 bps
    - BTC-USDT-PERP: mean -5.0111 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.514, 'p25': 198.9365, 'p50': 225.297, 'p75': 237.937, 'p95': 270.9993}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

