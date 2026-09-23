# GPT external assist — R6.2 -> R6.3

Frozen R6.2 LAB candidate: `fe3369f729c9cd5741e5cc8b4355b8aacbb3e79e`
Pre-patch RED checkpoint: `5dd1fdfd6fda0d9f08e4549eaf0281e812307bf1`
Parent R6.1: `39e028f914240d5421b1304b0dd83c7113705412`

## R6.2 audit

The stale compatibility repair is credible:
- pre-patch: 1 failed / 5 passed;
- final focused: 17 passed / 0 failed;
- external reconstruction of final `real_city.py` from R6 source + R6.1 patch + R6.2 patch is byte-identical;
- UNKNOWN evidence now clears stale compatibility `cost_minor` to 0 while `price_known=false`.

Do not claim planner cost truth closed. The final receipt still reproduces:
`R62_ANCHOR_UNKNOWN_COST_COLLAPSE`
with HTTP 201, one PlanVersion, three Activities, UNKNOWN anchor evidence, anchor Activity cost 0, `price_known=true`, plan total 1000, budget_fit 0.9, synthetic mobility, non-selectable, P7=false.

## Newly traced R6.3 roots

### R63_COMMITMENT_COST_SOURCE_LOST

A C4 anchor starts from a Commitment that already owns `monetary_value_minor`, `monetary_value_status`, and `currency`. But `ResolvedAnchor` discards those facts and later prices the anchor from Place metadata. A locked reservation's actual committed amount must outrank public Place catalogue price.

### R63_GENERIC_ANCHOR_COST_FORCED_ZERO

`_inject_anchors_into_generic()` inserts every anchor row with literal cost `0`. A KNOWN-paid MID_TRIP commitment can therefore have known evidence but Activity/Plan cost zero.

### R63_TEMPLATE_BUDGET_FIT_STATIC

The provider/catalogue template path computes `total_cost` but takes `budget_fit` from the fixed metrics table (0.90 / 0.96 / 0.95). The explicit POI path already derives budget fit as `1 - total_cost / budget`. Prove this with an all-known-cost dynamic catalogue before repair.

## R6.3 required contract

1. Carry Commitment monetary truth through anchor resolution: commitment_id, monetary status, amount, currency.
2. Both template and explicit generic anchor paths consume the same commitment monetary truth.
3. KNOWN positive -> exact amount included exactly once.
4. KNOWN zero -> known-free, not UNKNOWN.
5. UNKNOWN -> current schema cannot represent partial/unknown Plan total or budget_fit, so fail closed for a priced candidate with a named reason (recommended `COMMITMENT_COST_UNVERIFIED`), zero plan/activity persistence, Commitment unchanged.
6. Currency mismatch without verified FX -> fail closed; never relabel.
7. Template Activity metadata must derive `price_known`; never hard-code true.
8. Provider/catalogue template budget_fit must be derived from cost and Journey budget. If sealed CNX-DEMO scores must remain frozen, isolate that envelope explicitly.
9. Recompute utility total after budget-fit change.
10. Keep R6/R6.1/R6.2 regressions and sealed demo controls green.

## Independent Harness

The R6.2 focused suite is not independent Harness evidence. Point the next Harness pass at exact `fe3369f...`. It should independently verify the closed R6/R6.1/R6.2 claims and reproduce the open anchor RED. Also probe a KNOWN-paid explicit anchor for `R63_GENERIC_ANCHOR_COST_FORCED_ZERO`.

## Audit coordinate

At GPT review time, `fe3369f...`, `5dd1fdf...`, and `39e028f...` did not resolve in either connected CityNexus repository. Keep:
`LOCAL-ONLY / NO RESOLVABLE AUDIT COORDINATE`
until the isolated experiment branch is pushed. Do not merge merely to publish a SHA.

P7=false. Mission A not closed. Broad provider enrichment waits.
