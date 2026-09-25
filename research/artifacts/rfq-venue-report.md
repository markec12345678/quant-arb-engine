# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 191 lines · head `b3f91e0ceb201599…`
* truncation check: passed (live head == recorded head)
* counts: total 191 · by source {'real': 191, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 188, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 191 records · 188 quoted (188 firm / 0 indicative) · mean -7.5495 bps · p50 -7.7751 · p05 -10.311 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0871 bps
    - BTC-USDT-PERP: mean -5.0118 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.9015, 'p25': 200.085, 'p50': 224.386, 'p75': 236.593, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

