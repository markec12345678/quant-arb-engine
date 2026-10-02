# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 335 lines · head `15cf59a3383e35a9…`
* truncation check: passed (live head == recorded head)
* counts: total 335 · by source {'real': 335, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 331, 'rejected': 3}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 335 records · 331 quoted (331 firm / 0 indicative) · mean -7.5517 bps · p50 -10.0058 · p05 -10.299 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0774 bps
    - BTC-USDT-PERP: mean -5.0107 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 140.494, 'p25': 183.3565, 'p50': 217.974, 'p75': 234.369, 'p95': 266.7387}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

