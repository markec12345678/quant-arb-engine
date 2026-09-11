# Decision record — 2026-09-11: build the parallel engine

## Context

The funding-arb audit is closed (43 findings, 8 rounds) and the Phase-2 A/B/C
paper validation is still collecting evidence on the locked baseline `0373f5d`.
A Wintermute NODE research plan (W0–W4) was pre-registered in funding-arb-tower
(`docs/wintermute-node-analysis.md`), with Route B (implied carry vs priced
forward) elevated to the primary research direction.

Question on the table: **what do we build while the old system measures?**

## The two options

1. **Wait** for the day-5–7 Phase-2 verdict before writing anything new.
2. **Build a parallel research engine** (new repo, paper/research only) that
   transfers the audit's conceptual knowledge — market-data model, universal
   opportunity model, ALL-IN EDGE, forward-basis strategy — without touching
   the measured baseline.

## Decision

**Option 2 — the parallel engine — adopted.** The user proposed exactly this
structure (new repo `quant-arb-engine`, module list, strategy families, an
explicit NOT-building list) and explicitly delegated the final call. My call:
the proposal is correct, and it is adopted with the refinements below.

### Architectural principle (user's, binding)

**The measurement system is strictly separated from new development.**

```
funding-arb @ 0373f5d   ← LOCKED, Phase-2 runner, measurement only
quant-arb-engine        ← new development, paper/research only
funding-arb-tower       ← read-only observation of both worlds
```

### Refinements (my additions, binding)

1. **Language: Python, stdlib-only.** funding-arb is Python; the conceptual
   transfer (venue adapters, scanner semantics, journal discipline) stays
   native. Zero dependencies keeps the engine auditable and runnable anywhere
   the runner already runs.
2. **Invariant-first, enforced in code.** The audit lessons (NEW-16/17/18/20,
   fee double-counting, quantity chain) are not documentation — they are
   write-time checks in the journal and constructors (I-1…I-6). A record that
   violates an invariant raises and is never written.
3. **Deterministic mock world before real data.** The forward-basis strategy is
   fully exercisable today on a seeded synthetic feed (CEX funding prints +
   desk RFQ quotes). When W1 delivers real quotes, a real feed class implements
   the same interface — the strategy code does not change.
4. **Epistemic and unit rules travel with the code.** Every run summary carries
   the canonical phrasing rule and reports aggregates together with
   per-position means.
5. **The pre-registered gates are constants.** `min_z = 2.0`,
   `min_net_edge_bps = 10` mirror the W2 decision matrix — changed only by a
   recorded decision, never per-trade discretion.

### Scope guards (user's list, preserved verbatim)

Not building now: live trading · NODE automatic trading · real capital · FIX
production execution · ML models that decide about money · portfolio allocator ·
complex strategies without data. The engine works paper/research only.

## Next steps

1. W0 (user-owned): onboarding on trade.wintermute.com → capability sheet
   (products × minimums × credit × API).
2. W1 (zero capital): real RFQ quote journal (30–60 days) — the feed interface
   defined here is the attachment point.
3. funding-arb Phase-2 verdict (day-5–7): decides the fate of the *measured*
   system — independently of this engine.

## Relation to prior decision records

- funding-arb-tower `docs/wintermute-node-analysis.md` §0 — W0–W4 adopted,
  Route B primary. **This record implements the research arm of that decision.**
