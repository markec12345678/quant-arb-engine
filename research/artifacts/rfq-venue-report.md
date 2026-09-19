# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 64 lines · head `b58f0ff07a02e4e7…`
* truncation check: passed (live head == recorded head)
* counts: total 64 · by source {'real': 64, 'synthetic': 0} · by status {'quoted': 63, 'rejected': 1}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 64 records · 63 quoted (63 firm / 0 indicative) · mean -7.6043 bps · p50 -10.0061 · p05 -10.5349 · p95 -5.0061 · n>0 0
    - BTC-USDT: mean -10.1211 bps
    - BTC-USDT-PERP: mean -5.0063 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 168.2838, 'p25': 212.0012, 'p50': 228.9065, 'p75': 233.7747, 'p95': 256.1254}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

