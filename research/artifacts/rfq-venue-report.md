# W0 — raw RFQ journal replay (descriptive accounting)

* journal: `research/artifacts/rfq/journal-venue.jsonl` · 275 lines · head `5650855d2fbe630c…`
* truncation check: passed (live head == recorded head)
* counts: total 275 · by source {'real': 275, 'synthetic': 0} · by status {'no_response': 1, 'quoted': 272, 'rejected': 2}

## ALL-IN EDGE (bps of reference; source-split, never pooled)

* **real**: 275 records · 272 quoted (272 firm / 0 indicative) · mean -7.5467 bps · p50 -7.7751 · p05 -10.2988 · p95 -5.0058 · n>0 0
    - BTC-USDT: mean -10.0818 bps
    - BTC-USDT-PERP: mean -5.0117 bps
* **synthetic**: 0 records

## Data quality

* reference age (ms): {'p05': 0.0, 'p25': 0.0, 'p50': 0.0, 'p75': 0.0, 'p95': 0.0}
* latency (ms): {'p05': 151.2755, 'p25': 183.498, 'p50': 220.683, 'p75': 236.2455, 'p95': 270.042}

> Descriptive accounting over journaled RFQ records only — no research conclusions, no GO/NO-GO, until a W1 decision record is sealed on real data.

