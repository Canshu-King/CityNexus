# GPT external check — R18 -> R19

Inspected report: `REVOLUTION_R18_ANTICIPATORY_RESILIENCE_RESULT.md`
Verified implementation commit: `7a5f4eced3fb85b5fa98d1a8953078a97c310c37`

## R18 verdict

R18 is a genuine Revolution step.

It proved on a healthy ACTIVE Journey:
- live OpenMeteo + live Valhalla provider observations;
- bounded counterfactual simulation;
- on-demand capture of mobility evidence for hypothetical adjacencies;
- a separate immutable preview snapshot instead of mutating the active plan snapshot;
- deterministic feasibility against the new evidence;
- one persisted non-current shadow PlanVersion;
- no synthetic weather event and no estimate-authority shortcut.

The uploaded report correctly claims REVOLUTION_B, not C/D.

## Source-binding note

The uploaded report names `2fb637920f8799301514ecf6b955b931e289b7a0` as the R18 final SHA. On GitHub, the substantive R18 implementation is `7a5f4eced3fb85b5fa98d1a8953078a97c310c37`; the later `2fb6379...` commit only adjusts report source binding. Keep code SHA and report SHA separate in future reports.

## Critical standby lifecycle gaps

R18's shadow is a strong prototype, but not yet a safe operational reserve.

### 1. Standby is still an ordinary CANDIDATE

The shadow PlanVersion is persisted with:
- `status=CANDIDATE`;
- `explanation.lifecycle=NON_ACTIVE_STANDBY`.

However:
- public `plan_schema` computes `selectable` only from staleness + authority blocker;
- `select_plan` accepts ordinary `CANDIDATE` rows;
- neither path recognizes the standby lifecycle.

Therefore a shadow may be projected as `selectable=true` and may be selected through the normal plan-selection route without its counterfactual trigger.

R19 must make standby a first-class server-enforced lifecycle, not an explanation convention.

### 2. Mobility evidence has no real expiry contract

`MobilitySnapshot.to_evidence()` has no `expires_at`.

R18 shadow evidence writes an `expiry_reason`, but not an actual expiry timestamp. The shadow explanation currently stores `expiry=evidence.captured_at`, which is capture time, not expiry.

The generic staleness/selection path only blocks a plan when a real `expires_at` exists and is in the past.

A standby must therefore receive a real evidence TTL and become non-activatable when stale.

### 3. Activity travel truth can disagree with shadow mobility evidence

The shadow materializer copies each kept Activity's old `travel_from_prev_min` even when dropping an intermediate activity creates a new adjacency.

The feasibility gate itself is safe because it queries the new mobility snapshot, but the persisted Activity rows may still carry the old leg duration. UI/Twin/execution projections can therefore disagree with the plan's own mobility evidence.

R19 must derive persisted activity travel/legs from the shadow snapshot.

### 4. Shadow totals are approximate

Current shadow:
- total cost = active total minus dropped activity costs;
- duration = active duration minus dropped activity durations.

That does not fully account for the new adjacency travel duration/cost or schedule retiming.

R19 must recompute totals from the actual materialized shadow activities + mobility evidence.

### 5. Current standby generation is narrow

The current code materializes at most one shadow and mainly when a scenario produces dropped activities.

A real resilience portfolio needs a small bounded set covering different material failure modes and must be able to represent at least:
- drop;
- reschedule/keep with changed times;
- replacement when a grounded replacement exists.

Do not explode into dozens of plans.

## Test gap

The reported 35-test command is valuable regression coverage, but it is the same focused set used before R18 and does not by itself prove the new standby lifecycle contracts.

R19 should add small direct tests for:
- standby cannot be selected by generic select;
- standby evidence expires;
- parent active-plan change invalidates standby;
- activity travel_from_prev_min matches standby mobility evidence;
- total cost/duration are recomputed;
- preview snapshot does not mutate the base snapshot.

## Revolution frontier

Do not make R19 "more shadow plans".

The next product species is a Living Plan Portfolio:

> one active truth + a small continuously maintained set of evidence-grounded future branches, each with trigger, expiry, authority and activation policy.

Guardian/Agent should be able to see, refresh, prune and choose among those branches instead of recomputing every recovery from zero.
