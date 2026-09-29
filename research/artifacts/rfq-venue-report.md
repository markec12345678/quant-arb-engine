# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 287 lines · head `213ecd63728da535…`
* truncation check: passed (live head == recorded head)
* counts: total 287 · by source {'real': 287, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 284, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 287 records · 284 quoted (284 firm / 0 indicative) · mean -7.5466 bps · p50 -7.7751 · p05 -10.3004 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0817 bps
    - BTC-USDT-PERP: mean -5.0115 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.514, 'p25': 188.3075, 'p50': 220.46, 'p75': 235.898, 'p95': 268.6263}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

