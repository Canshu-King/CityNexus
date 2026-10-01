# R19 implementation sketch — shortest path

## 1. Use STANDBY status before inventing a new table

PlanVersion.status is stored as a string and the public schema currently allows:
CANDIDATE / SELECTED / ACTIVE / SUPERSEDED / REJECTED.

Smallest safe first step:
- add STANDBY to the public Literal;
- persist R18 shadows as STANDBY;
- plan_schema => selectable=false for STANDBY;
- select_plan => explicit refusal for STANDBY.

This turns the current explanation convention into a server invariant.

## 2. Add real expiry to mobility evidence

R18 shadow/preview evidence needs:
`expires_at = captured_at + configured TTL`

Use one helper so:
- Trip Studio preview;
- Shadow Plan;
- future contingency refresh
all compute the same expiry contract.

Selection/activation already knows how to fail on expired evidence when the field exists.

## 3. Fix Activity/leg consistency at materialization

When creating a standby:
- iterate the final kept/replaced activities in order;
- read the exact edge fact from shadow evidence;
- write current Activity.travel_from_prev_min = fact.minutes;
- write/update JourneyLeg rows from the same fact shape if candidate plan legs are persisted elsewhere.

Regression:
for every consecutive standby pair:
`Activity.travel_from_prev_min == shadow_snapshot.estimate_minutes(prev, current)`.

## 4. Recompute totals from materialized truth

After materialization:
- total activity cost;
- total mobility known cost;
- actual first-start / last-end span;
- route duration;
- cost delta vs active;
- schedule drift.

Never derive these by subtracting one dropped activity from the active aggregate.

## 5. Generalize the existing one-shadow flag

Current `simulate_counterfactuals` uses one boolean `shadow_materialized`.

Replace it with a bounded portfolio accumulator:
- max 3;
- one best branch per materially distinct scenario/failure mode;
- only persist if feasible + truth-complete + non-dominated.

Do not create every counterfactual as a PlanVersion.

## 6. Reuse existing recovery materialization for REPLACE/reschedule

The normal replan path already knows how to:
- map solver assignments;
- materialize replacements;
- recapture mobility;
- retime rows;
- preserve semantic keys.

Extract/reuse the smallest helper rather than duplicating that logic inside predictive.py.

R18's drop-only code should become a consumer of the common materializer.

## 7. Portfolio refresh loop

Add one bounded function such as:
`maintain_standby_portfolio(session, journey, snapshot, simulations)`

Responsibilities only:
- validate parent == current active plan;
- expire stale evidence;
- prune obsolete/dominated standby;
- refresh high-value missing/stale evidence;
- create missing top branches.

Call it from the existing Autopilot pulse after resilience/counterfactual computation.

## 8. Compact Agent view

Add a compact summary:
- plan_id;
- trigger;
- readiness;
- expires_at;
- key changes;
- cost_delta;
- schedule_drift;
- protected commitments.

Prefer embedding this in inspect_twin unless a separate read-only tool is cleaner.

## 9. Activation path

Do not call generic select_plan on STANDBY.

Preferred shape:
`activate_standby(journey, standby_plan, trigger_event, policy_context)`

It should:
- verify trigger match;
- verify parent/current relationship;
- verify not expired;
- revalidate feasibility/authority;
- route through Gateway policy;
- atomically supersede/activate.

If existing replan proposal acceptance can represent this cleanly, wrap standby into a proposal and reuse it.

## 10. Direct regression set

Add focused tests for:
1. STANDBY is projected non-selectable.
2. generic select refuses STANDBY.
3. expired standby refuses activation.
4. parent active-plan change invalidates standby.
5. activity travel matches standby snapshot.
6. cost/duration recompute includes new edges.
7. preview snapshot does not mutate base evidence.
8. portfolio max bound and distinct-scenario pruning.
9. Agent/Twin summary exposes readiness without raw evidence dump.

Then run the existing R15-R18 focused suite once.
Do not create another audit harness.
