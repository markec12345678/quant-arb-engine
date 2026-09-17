# W0 — The real venue-book source connection (OKX)

* status: **SEALED 2026-09-17, BEFORE the code it governs** (family discipline:
  every W0 component was sealed before implementation; the poller was shipped
  as a *slot* by the sealed W0 record §3 — "it lands with W1 when the user
  connects a source". This record is that day.)
* version: 0.7.0 · follows runbook-first-feed (v0.6.5) · owner directive
  (2026-09-17): **W0 = real RFQ ingestion only** — no trading, no strategy
  optimization, no research; W1 begins only when a real feed actually exists
  and requires its own pre-registered decision record.

---

## 0. What this is — and is not

This connects a REAL RFQ source to the sealed W0 machinery:

```
OKX public book (real, no credentials)
   → venue_book provider (adapter, normalize-at-the-edge)
   → 15-field ExternalRFQ (validated, fail-closed R-1…R-13)
   → hash-chain journal (append-only, head-hash bounded)
   → descriptive ALL-IN EDGE (accounting, never estimation)
```

It is NOT: trading (no order is ever placed — no API keys exist in this
system by design); an estimator or optimization (the v0.5 STOP RULE,
strategies, ranking and every research module are untouched); W1 (the first
research number on real data still requires its own sealed decision record
written before the number exists); a desk feed (no RFQ desk credentials exist
in this environment — the source is a public venue order book, which is the
real, credential-free quoting surface available today).

## 1. Venue selection — evidence first (2026-09-17)

Requirements: public no-auth API; reachable from BOTH planes (the sandbox AND
GitHub-hosted runners — the durable lane runs on the latter, and they exit
from US IPs where some venues geo-block); spot + perp of the SAME instrument
family (the W1 replay convention C-1/M-6/M-7: family = BASE-QUOTE root, perp
= root + `-PERP`); a published fee schedule; a clean REST surface.

Evidence:

| venue (spot+perp) | sandbox egress | GH runner (probe run 35242813230) | family fit | fees (published taker, regular tier) |
|---|---|---|---|---|
| **OKX** BTC-USDT / BTC-USDT-SWAP | 200 | **200 / 200** | **same family BTC-USDT** | **spot 0.10% + perp 0.05%** |
| Kraken XBT/USD / PF_XBTUSD | 200 | 200 / 200 | same family BTC-USD | spot 0.40% + futures 0.05% (fee-gate dominating on the spot leg) |
| Hyperliquid UBTC-USDC / BTC | 200 | 200 / 200 | **broken** — spot family UBTC-USDC ≠ perp family BTC-USDC (only wrapped-BTC spot exists); the W1 replay cannot pair them |
| Bybit BTCUSDT | 200 | **403 / 403** (geo-blocked) | — | — |
| Binance BTCUSDT | 200 | **451 / 451** (geo-blocked) | — | — |
| Deribit BTC_USD / BTC-PERPETUAL | 400 / 200 | 400 / 200 (spot endpoint anomalous) | partial | — |
| Coinbase BTC-USD | 200 | 200 (spot only, no perp family) | — | — |

**Selection: OKX.** The only GH-runner-reachable venue where a canonical spot
book and its perp live on ONE venue, ONE API, with the lowest combined taker
fees among the coherent candidates (0.10% + 0.05% per leg pair — directly
relevant to the fee-gate question the funding-arb Phase-2 verdict C left
open). The alternatives are documented above so the choice is auditable, not
a preference.

## 2. The RFQ semantics of a venue book (the honest mapping, V-1…V-9)

One poll = **4 RFQ records**: {BTC-USDT spot, BTC-USDT-PERP perp} × {buy,
sell}, requested notional **10,000 USDT** each (notional_ccy == price_ccy ==
USDT — the W1 replay M-4 same-currency requirement, met by construction).

- **V-1 quoted_price = depth VWAP.** Walk the visible book until the
  requested notional is filled (buy → asks ascending, sell → bids
  descending); quoted_price = the notional-weighted average fill price. Swap
  levels are quoted in CONTRACTS: level quote value = px × sz × ctVal
  (ctVal = 0.01 BTC, fetched live from /public/instruments and preserved in
  raw).
- **V-2 quote_type = "firm".** Displayed resting liquidity on a CLOB is
  executable by a taker at the snapshot instant. The honest qualification is
  carried by V-3, not by downgrading to "indicative" (the levels ARE
  tradable, not indications).
- **V-3 quote_expiry_ts = ts — instantaneous validity.** A public book
  carries no hold: the quote is valid AT its snapshot. (R-7 allows equality;
  the W1 replay's ttl_ms = quote_expiry_ts − ts = 0 is then the honest
  statement "no hold granted".)
- **V-4 ts = the venue's book timestamp** (server-side ms, from the books
  response) — not our clock; reference_ts = the same value (reference_age
  exactly 0; R-11 satisfied at equality).
- **V-5 reference_price = the same book's mid**, provenance-tagged per R-10:
  spot records `spot_book_mid`, perp records `perp_book_mid` (a NEW tag — the
  schema's provenance list is explicitly extensible; `perp_mark`/`perp_last`
  would be dishonest for a book mid, `other_reported` needlessly vague).
  reference_ts ≤ ts by construction (same fetch).
- **V-6 spread_bps = (best ask − best bid) / mid × 1e4** from the same book.
- **V-7 fees = the venue's published standard-tier taker fee, verbatim from
  the schedule**: spot 0.1000%, perp 0.0500% — verified 2026-09-17 from (a)
  the live okx.com/fees schedule (spot regular taker 0.001) and (b) OKX's
  announcement "Advance Notice: Spot and Futures Trading Fee Adjustment"
  (futures standard regular maker 0.0200% / taker 0.0500%; spot standard
  regular maker 0.0800% / taker 0.1000%). fees_included_in_price = false
  (OKX charges fees on top). The full provenance (URLs, tier, verification
  date) travels inside every record's raw.
- **V-8 status semantics.** `quoted` when the visible depth fills the
  notional; `rejected` with reject_reason="insufficient_depth" when it
  cannot (quote-only fields null — R-5/6/7/8); `no_response` when the venue
  does not answer (non-200, bad envelope, or timeout) — with the freshest
  available reference for that instrument (in-process prior book, else the
  journal tail's last reference for it, honest reference_age). A cold process
  whose FIRST fetch for an instrument fails has no reference at all — then
  NOTHING is journaled for it (R-10 cannot be satisfied honestly) and the
  poll exits red. Collection friction must be visible in the census (C-3),
  never invented away.
- **V-9 rfq_id = okx:{instrument}:{side}:{book_ts}** — deterministic on the
  observation. A retry carrying the same payload yields the same id → R-1
  refuses the duplicate (retry-SAFE: re-running a poll never double-journals
  the same quote; a fresh fetch has a fresh book_ts → a genuinely new
  observation).

Instrument naming follows the W1 convention exactly: `BTC-USDT` (kind spot),
`BTC-USDT-PERP` (kind perp) — C-1 strips `-PERP` to the same family root.
venue tag: `okx`.

## 3. Journal path governance (the honest amendment to W0 §2)

The sealed W0 record gitignores `research/artifacts/rfq/journal.jsonl`
because "raw desk data may be proprietary; size unbounded". The venue-book
journal is **public market data at a bounded cadence**, and this environment
has proven — twice, via container reclamation — that data not on GitHub is
data lost (the funding-arb `paper-data` branch is the precedent: the ONLY
plane that survived both recyclings).

Amendment (additive; the sealed default path is untouched and stays
gitignored for any future desk feed):

| artifact (all on the dedicated `rfq-data` branch) | role |
|---|---|
| `research/artifacts/rfq/journal-venue.jsonl` | the venue journal (hash-chained, append-only, tracked) |
| `research/artifacts/rfq-status-venue.json` | its derived status (chain head, census, tail) — the tower's W0 card reads this |
| `research/artifacts/rfq-venue-report.json` / `.md` | the descriptive replay report (verify + ALL-IN EDGE accounting) |
| `research/artifacts/coverage-venue-latest.json` | the coverage census (the future W1 record's inclusion-criteria input) |

`main` stays code-only (CI runs on code pushes, not on data appends); the
data plane is the branch, exactly like `paper-data`.

## 4. The durable lane (single writer = GitHub Actions)

`.github/workflows/rfq-venue-poll.yml` on the engine repo:

* triggers: schedule every 30 min (`:07`/`:37`), `workflow_dispatch`, and a
  `repository_dispatch` bridge (`rfq-venue-poll`) mirroring the proven
  paper-collector pattern — any machine can fire a poll on demand;
* each run: checkout main (code, stdlib only — no pip install) → restore the
  accumulated journal from `origin/rfq-data` → **one poll** (4 records via
  scripts/rfq_poll.py) → `rfq_replay.py --verify-only` (chain + truncation
  bound checked IN-RUN; a broken chain fails the run before any push) →
  coverage census + descriptive report regenerated → commit + push the four
  artifacts to `rfq-data` with the default `GITHUB_TOKEN` (no secrets);
* **single-writer discipline**: the GitHub workflow is the ONLY writer of the
  venue journal. The sandbox reads (fetch + `git show`), never writes. R-1
  plus the concurrency group make an accidental double-run safe (duplicate
  ids refused; worst case the push loses a race and the next run re-appends);
* honest throttle expectation: GitHub schedules on quiet repos fire slower
  than nominal (paper-data observed 25 cycles over ~4 days). The census
  records ACTUAL ts coverage — the nominal cron is a ceiling, never a claim.

## 5. The no-optimization boundary (owner directive, 2026-09-17)

funding-arb stays LOCKED @ 0373f5d (Phase-2 verdict C executed: standdown,
results locked, root cause = fees 2.46× gross edge). This connection changes
NO estimator, NO strategy, NO ranking, NO research module, produces NO
research verdict, and places NO orders. Additive surface only:
`quant_arb/rfq/providers/venue_book.py` (+ `scripts/rfq_poll.py`, the
workflow, one schema provenance tag, harness checks, docs, version).

## 6. The W1 handoff (what the real data will and will not support)

* Supports, per the sealed W1-INFRA bridge: entry-side ALL-IN EDGE accounting
  on real quotes (family BTC-USDT: spot + perp, both sides, every poll);
  family detection (C-1) and day coverage (C-5/C-6) — both sides are quoted
  every poll, so pair days are complete by construction (barring fetch
  failures, which the census counts honestly);
* Still refuses (M-10): funding observations — the 15-field schema carries
  quote events only. OKX exposes a public funding-rate endpoint; whether W1
  consumes it (schema extension or a separate lane) is the W1 record's
  decision to make, not this one's;
* The W1 sealed record MUST cite the coverage census
  (`coverage-venue-latest.json`) as its inclusion criteria — runbook §4's
  contract, unchanged.

## 7. Sealed decisions

1. Venue = OKX per §1's evidence table (both planes verified; same-family
   spot+perp; published fees).
2. RFQ semantics = V-1…V-9 exactly; instrument symbols `BTC-USDT` /
   `BTC-USDT-PERP`; venue tag `okx`; notional 10,000 USDT per record.
3. Fees = published standard-tier taker fees (spot 0.10%, perp 0.05%),
   fees_included_in_price=false, provenance embedded in raw (§ V-7).
4. Schema: `REFERENCE_SOURCES` gains `perp_book_mid` (additive; the list is
   explicitly extensible; the W1 replay maps unknown-but-valid tags to
   REFERENCE_OTHER gracefully — no replay change).
5. Journal governance amendment per §3: tracked venue journal + derived
   artifacts on the `rfq-data` branch; the sealed `journal.jsonl` path stays
   gitignored for desk feeds; nothing sealed is edited.
6. The durable lane per §4: GitHub Actions, single writer, in-run
   verification, GITHUB_TOKEN push, no secrets.
7. No trading, no optimization, no research number — anywhere in this
   connection. W1 remains gated on its own sealed record.
