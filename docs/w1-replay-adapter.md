# W1-INFRA: the RFQ journal replay adapter (v0.6.2)

* status: SEALED design record — written 2026-09-11, BEFORE implementation
* version: 0.6.2 · follows W0 (docs/w0-rfq-ingestion.md, sealed 0.6.0)
* discipline: same as W0 — infrastructure, not research. **No research number
  is produced by anything in this document.** The first real-data research
  round (uncertainty → ranking → GO/NO-GO) remains W1-proper and requires its
  own sealed decision record before any number exists.

## 0. What this is — and is not

Architecture extension point 2 names two halves: the **journal replayer** (the
adapter that feeds W0 records into the engine's typed quote model) and the
**W1 research round** (sealed separately, later, when real data exists). This
document seals ONLY the first half. The replayer is the bridge:

```
W0 raw journal (immutable, hash-chained, 15-field ExternalRFQ)
        │  verify chain (read-only) → source wall → mapping rules M-1…M-10
        ▼
RFQQuote / Price / Instrument        ← the engine's typed vocabulary
        │                               (I-1 provenance travels on every Price)
        ▼
W1 research design record (LATER, user-gated, sealed before any number)
```

## 1. The honest capability map (the structural finding)

The user-specified 15-field schema captures **quote events**. What it can and
cannot feed — stated now, so the W1 research record inherits the constraint:

| pipeline surface | replayable from RFQ journal? | why |
|---|---|---|
| `spot_quotes()` (bid/ask pair) | **YES** | quoted+firm spot RFQs, both requesting sides |
| `forward_quotes(tenor)` | **YES** | forward-kind RFQs, sealed tenor convention |
| `perp_mark()` | **YES** | perp-kind references (provenance carried) |
| `spot()` / reference mid | **YES** | latest eligible spot reference price |
| `funding_obs` / `printed_funding_between` | **NO — refused** | CEX funding settlements are not RFQ fields; synthesizing them from forwards would be an estimator smuggled in through infrastructure |
| `settlement_print()` / `true_apr()` | **NO — refused** | final fixings and ground-truth APR are market data beyond the schema |

Consequence (honest): RFQ-only real data supports **entry-side evaluation**
(quote-day ALL-IN EDGE accounting, family edges, ranking inputs) and
forward-implied carry. The perp-carry family's float-carry settlement needs
funding data the schema does not carry. Resolving that — a schema extension
(user-owned: the 15 fields are user-specified) or a separate CEX market-data
lane — belongs to the W1 research design record, not here.

## 2. The mapping (sealed rules M-1…M-10)

- **M-1 eligibility.** A record surfaces as an executable quote only if
  `status == "quoted"` AND `quote_type == "firm"`. Indicative, rejected,
  expired and no-response records never become executable quotes.
- **M-2 sides.** `ExternalRFQ.side` is the *requesting* side: a user **buy**
  RFQ yields the desk's **ask**; a user **sell** RFQ yields the desk's **bid**.
- **M-3 price provenance (I-1 travels).** `px = Price(quoted_price,
  DESK_RFQ_QUOTE|SYNTHETIC_MOCK per record source, ts)`; `ref_mid =
  Price(reference_price, PriceSource(reference_source) if a valid enum name
  else REFERENCE_OTHER, reference_ts)`. A new enum value `REFERENCE_OTHER`
  is added to `PriceSource` (additive; unknown desk provenance stays explicit,
  never naked).
- **M-4 size.** `size_quote = requested_notional / quoted_price`, valid only
  when `notional_ccy == price_ccy` (documented same-currency assumption);
  otherwise the record is unusable for replay and counted loudly.
- **M-5 ttl.** `ttl_ms = quote_expiry_ts − ts` (positive by R-7).
- **M-6 forward tenor convention.** Forward-kind symbols carry the tenor as a
  `-FWD-{n}D` suffix. A forward-kind record whose symbol does not parse → the
  replay refuses (fail-closed, record named).
- **M-7 timeline.** One feed instance serves ONE instrument family (a spot
  symbol, its forwards, its perp — multiple symbols = multiple instances, the
  W1 design's business). A quote day = a UTC calendar day with ≥1 eligible
  record for the family; `day()` is the 1-based index over those days;
  `now_ms()` = the day's last eligible ts; `advance_day()` iterates them in
  order. Deterministic: same journal → same replay, always.
- **M-8 the source wall, replay edition.** The constructor REFUSES any
  synthetic record by default (research posture). `allow_synthetic=True` is
  the machinery-test mode and maps `px.source = SYNTHETIC_MOCK` — the wall
  then travels inside every quote (I-1 enforces it downstream; a synthetic
  quote can never masquerade as real because its Price says so).
- **M-9 read-only.** The replayer verifies the whole chain at load
  (`journal.verify()`) and never writes; the journal is byte-identical after
  any replay.
- **M-10 refused surfaces.** `funding_obs`, `printed_funding_between`,
  `realized_funding_apr_between`, `settlement_print`, `true_apr` raise
  `NotImplementedError` naming the missing data class (§1) — loud and honest,
  never silently empty.

## 3. Sealed decisions

1. Scope = the adapter only; W1 research (any uncertainty/ranking/GO-NO-GO
   number) requires a NEW sealed decision record — unchanged from W0 §6.
2. Mapping = M-1…M-10 exactly as §2; eligibility and fail-closed posture
   follow the W0 invariants (R-1…R-13 descendants where applicable).
3. The source wall doubles at the Price layer (M-8): real → `DESK_RFQ_QUOTE`,
   synthetic → `SYNTHETIC_MOCK`; no replay output exists without provenance.
4. `REFERENCE_OTHER` added to `PriceSource` — additive enum value, no existing
   semantics touched.
5. Refused surfaces (M-10) are permanent until a sealed record adds the data
   class they need; the replayer never fabricates funding or fixings.
6. funding-arb untouched @ `0373f5d` throughout; no live trading anywhere.
