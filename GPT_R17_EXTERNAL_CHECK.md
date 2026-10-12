# GPT external check — R17 -> R18

Inspected report: `REVOLUTION_R17_PREDICTIVE_SELF_HEALING_RESULT.md`
Verified code commits:
- `b2ce28211d0c9d4a17cf56795372388797078679`
- `cfd21eb052711851cee91b217c6df65490a7c051`

## R17 verdict

R17 is an honest non-closure, and that honesty is valuable.

The clean live run did NOT fabricate a predictive event:
- fresh Nara Journeys remained `STABLE`;
- actual scheduled outdoor windows did not exceed the configured live OpenMeteo predictive threshold;
- no WEATHER/CLOSURE event was manually posted;
- no synthetic forecast was injected;
- no preventive AgentRun/replan was claimed.

The cost-contract cleanup is good:
- Guardian budget checks now consume canonical cost evidence;
- legacy `metadata_json.cost_minor` can no longer override explicit canonical UNKNOWN;
- focused suite reported 35 passed.

## Structural blocker discovered

The R17 experiment exposed two architectural limitations that should not be solved by weather roulette.

### 1. Predictive capability currently waits for a threshold coincidence

The Guardian predictive path only becomes interesting when a live provider risk overlaps the already-selected schedule.

If the weather is benign at the scheduled outdoor windows, the product correctly remains STABLE. Re-running cities until rain happens is not a product capability.

The next step should make resilience valuable even before any threshold is crossed:
- maintain evidence-backed standby alternatives;
- continuously evaluate counterfactual weakness;
- pre-acquire only the facts/edges needed by high-value recovery paths;
- keep all alternatives inactive until policy/provider evidence warrants mutation.

### 2. Trip Studio cannot validate a genuinely new adjacency from the active plan snapshot

Current Trip Studio reads the active PlanVersion's immutable `mobility_evidence_json`.

For a reordered itinerary:
- if the new `from -> to` pair is absent from the frozen matrix, it is a route evidence gap;
- the preview does not capture that new pair on demand;
- the new order can therefore be rejected even when a live mobility provider could answer the route.

This is correct fail-closed behavior, but incomplete product behavior.

A new hypothetical plan should be able to acquire a NEW immutable preview mobility snapshot for its own adjacency set before authority evaluation.

Do not weaken the gate. Supply the missing truth.

## Mobility-cost caveat

The R17 report hit `UNKNOWN_MOBILITY_COST`.

Do not fix this by coercing unknown to zero.

Required semantics:
- paid modes with unknown fare remain blocking / confirmation-required;
- a mode may be known-free only if the deterministic mode contract and provider evidence genuinely establish zero monetary cost;
- every preview/replan edge keeps explicit cost status and provenance.

## Revolution frontier

R17 attempted:
live forecast -> predictive weakness -> prevention.

R18 should become:
continuous counterfactual twin -> prevalidated shadow plans -> evidence-on-demand mobility/facts -> provider-aware initial/standby strategy -> instant governed activation when real risk materializes.

This removes dependence on lucky bad weather while preserving truth.
