# GPT external check — R22 -> R23

Inspected:
- uploaded `CityNexus-Revolution-R22-GPT-Assist-20261003.zip`;
- raw machine receipt + focused-test record;
- bundled R22 source snapshot;
- remote implementation commits:
  - `01b1a5f7c17115308fa2ced16cc3a99916b6cf41`
  - `c9fb37f9d1c20b7341cf2a3bc2f004408ba494f3`
- remote experiment head `8a7856a98ca32bcfdcc53959fc3db1405a0cebd1`.

## R22 verdict

R22 closes the primary positive-autonomy milestone.

The machine path is materially new:
- ACTIVE truth-grounded Journey;
- server-derived `OPPORTUNITY_WINDOW`;
- real Hermes-compatible model `cn:deepseek-v4.1-flash`;
- model inspected Journey/Twin, searched the live city catalogue, acquired facts, generated candidates and requested replan;
- exact provider-backed new Place not already on the active plan;
- official opening/cost truth;
- estimate authority OFF;
- two directed live Valhalla legs;
- `F4_OPPORTUNITY_INSERTION` increased activity count from 2 to 3;
- full deterministic feasibility passed;
- Gateway required user confirmation;
- accepted plan executed the inserted activity and preserved the protected commitment;
- Journey reached COMPLETED;
- opportunity Event was resolved as `OPPORTUNITY_CONSUMED`.

This is genuine self-improving-trip behavior, not another recovery-only round.

## Source binding

Current remote experiment head is:

`8a7856a98ca32bcfdcc53959fc3db1405a0cebd1`

That head pins the R22 delivery artifacts. The substantive final R22 code is:

`c9fb37f9d1c20b7341cf2a3bc2f004408ba494f3`

Keep code SHA and delivery/report SHA distinct.

## R22 boundary 1 — positive signal threshold is too permissive

Current `_ensure_opportunity_window_event()` creates an event for any positive:

`available_minutes > 0`

There is no configured minimum opportunity size.

Therefore a 1-minute or 8-minute theoretical window can wake the Agent even though no worthwhile visit could fit.

R23 should add a small bounded minimum-opportunity policy:
- configurable or clearly named constant;
- applies before creating `OPPORTUNITY_WINDOW`;
- short windows remain ordinary slack, not Agent missions.

Do not create a separate opportunity service.

## R22 boundary 2 — selective positive autonomy is not yet the primary closure

The R22 report explicitly closes at REVOLUTION_C. It does not use the ACTIVE NO_ACTION control as the primary proof.

Do not reopen R22.

R23 should include one ACTIVE small/poor opportunity control and prove:
- no bad insertion;
- no forced search loop;
- machine-visible NO_ACTION or no opportunity event;
- active plan unchanged.

This is a control, not the next product species.

## R22 boundary 3 — direct replace_activity remains a truth-regression shortcut

The old `replace_activity(replacement_place_id=...)` path still contains legacy behavior:
- metadata cost fallback;
- mock mobility.

R22 correctly avoided it for the final success.

R23 must not route learned preference adaptation through that shortcut unless the path is first upgraded to canonical cost + live mobility.

Preferred: keep using grounded replan/F4 paths.

## New opportunity: a learning engine already exists

The repository already contains:
- `JourneyOutcomeEvent`;
- `TravelerPreferenceEvidence`;
- `TravelerTwinSnapshot`;
- `learn_from_journey()`;
- `planning_preference_items()`;
- `LEARNED_SOFT` context injected into the real Agent system prompt;
- planner scoring that can consume interest preferences.

This means R23 should NOT build a new memory framework.

The next leap is to make the existing TravelerTwin learning loop trustworthy and product-causal.

## Critical learning flaw in current implementation

Current `_event_signal()` can interpret:

`ACTIVITY_COMPLETED at indoor Place -> learned indoor preference`

and:

`ACTIVITY_SKIPPED at indoor Place -> learned outdoor preference`.

That is too strong.

Completion does not prove liking:
- it may be a protected commitment;
- prepaid/locked;
- required by companions;
- simply completed because it was already scheduled.

Skip does not prove dislike:
- closure;
- weather;
- mobility failure;
- time pressure;
- recovery logic.

R23 must treat behavior as evidence, not preference truth.

Hard rule:
- explicit user preference/feedback wins;
- learned evidence is soft ranking context only;
- capability/health/accessibility facts are NEVER inferred from behavioral learning;
- learned evidence can never expand authority, budget, payment, commitment or autonomy bounds.

## Revolution frontier

R22 proved:
> CityNexus can autonomously make a live trip better.

R23 should prove:
> CityNexus can learn, cautiously and reversibly, what "better" means for this traveler, and that learning materially changes the next real opportunity decision without overriding explicit human intent.

That is the first full:

`Sense -> Act -> Observe -> Learn -> Act Better`

loop.
