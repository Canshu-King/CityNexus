# Revolution R18 — Anticipatory Resilience OS

## The leap

R15: seek truth.
R16: recover after disruption.
R17: attempted prediction, but the real world was simply not risky enough at the selected activity times.

Do NOT turn R18 into "try more cities until it rains."

R18 must make resilience useful even while the current trip is healthy.

The product target is:

```text
truth-grounded selected/ACTIVE Journey
  -> live provider observations continue
  -> Counterfactual Twin identifies dominant future failure modes
  -> system prepares bounded shadow alternatives BEFORE failure
  -> only high-value missing facts / mobility edges are acquired
  -> every shadow plan is fully evidence-bound and non-active
  -> current plan continues normally while risk is low
  -> if a live provider signal crosses the policy threshold:
       real Agent inspects current state + shadow alternatives
       chooses standby plan or requests a fresh replan
       Gateway validates policy
       new plan activates
  -> revised Journey completes
```

This is not merely predictive alerting.
It is anticipatory operational readiness.

## Hard truth boundaries

- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`;
- no synthetic provider event counted as live;
- no unknown mobility cost silently converted to zero;
- no shadow plan may become active without the normal authority/Gateway boundary;
- a counterfactual is a hypothesis, not a real-world fact;
- active and shadow PlanVersions must remain clearly distinct.

## Phase A — evidence-on-demand mobility for hypothetical plans

Fix the structural R17 blocker first.

Current Trip Studio validates against the active plan's frozen mobility matrix. A new order may introduce new adjacencies that are not in that matrix.

Implement a bounded preview mobility acquisition path:

1. compute the exact adjacency set required by the hypothetical order/plan;
2. reuse still-fresh facts already present in the base snapshot;
3. detect missing/stale pairs;
4. query the existing live mobility provider for ONLY those required pairs;
5. persist a NEW immutable preview mobility snapshot;
6. include:
   - origin/destination;
   - mode;
   - duration;
   - monetary cost status/value;
   - currency;
   - provenance;
   - capture time / expiry;
   - route geometry or provider receipt where available;
7. bind the preview ID to:
   - base PlanVersion;
   - requested order;
   - new preview mobility snapshot;
8. run the deterministic gate against the new snapshot;
9. on accept, revalidate freshness and use the same bound evidence or recapture.

Do not mutate the active plan during preview.

Do not silently extend the old immutable snapshot.

## Phase B — correct mobility cost truth

R17 exposed `UNKNOWN_MOBILITY_COST`.

Keep fail-closed semantics, but make the mode contract explicit.

Rules:
- paid modes with unknown fare: remain UNKNOWN and cannot auto-execute;
- provider-captured known fare: canonical known cost;
- a no-fare mode may be marked KNOWN_FREE only when the mode itself is deterministically no-fare and the provider route confirms that mode;
- do not infer "walking = free" from a missing field unless the selected routing mode contract explicitly says no monetary fare applies.

Add focused regressions for:
- paid unknown remains blocked;
- true known-free mode can pass with explicit provenance;
- stale/missing preview edge cannot pass;
- preview recapture cannot overwrite active-plan evidence.

## Phase C — build shadow contingency plans

Use existing:
- JourneyResilienceSnapshot;
- CounterfactualSimulation;
- CP-SAT V2;
- real-city catalogue;
- live mobility;
- canonical opening/cost facts.

For the ACTIVE Journey, maintain a small bounded set of non-active shadow alternatives for the top material failure modes, e.g.:
- rain affects outdoor activity;
- route delay compresses a protected commitment;
- mutable Place closes;
- replacement disappears.

Each shadow plan must:
- be derived from current truth;
- use canonical Place facts;
- acquire its own required mobility edges;
- pass deterministic feasibility;
- preserve protected commitments;
- record its counterfactual trigger;
- remain explicitly NON_ACTIVE / STANDBY.

Do not generate dozens of plans.
Top 1-3 material contingency plans are enough.

## Phase D — value-of-information readiness

Do not fully hydrate the whole city just because a contingency might happen.

For each counterfactual:
- determine which missing Place fact or mobility edge blocks a viable standby plan;
- estimate whether resolving it changes recovery feasibility;
- acquire only high-value evidence;
- abandon low-value branches.

Persist:
- counterfactual;
- missing evidence;
- acquisition action;
- result;
- whether standby feasibility changed.

This extends the R15 truth-seeking loop into operational resilience.

## Phase E — forecast-aware initial/standby strategy

The planner currently scores actual real-city facts, but predictive weather is mostly consumed later by Guardian.

Add a bounded forecast exposure signal to real-city strategy evaluation WITHOUT making weather a truth override.

For candidate schedules:
- inspect provider forecast at the actual activity place/time;
- compute exposure from provider facts;
- preserve the raw provider values;
- penalize or label weather exposure only when supported;
- never fabricate venue indoor/outdoor status beyond provider/place tags.

The planner may:
- choose a safer initial candidate;
- or retain the preferred candidate while preparing a shadow alternative.

Both are valid if explained.

The user preference still matters; risk does not automatically dominate everything.

## Phase F — safe-state proof must count

R18 does not require bad weather to prove useful capability.

A valid REVOLUTION_A/B run may occur while live conditions are safe, provided the system proves:
- current Journey remains unchanged;
- counterfactuals exist;
- at least one standby plan is fully evidence-grounded;
- new mobility edges were captured on demand;
- no shadow plan was activated without a real trigger.

This avoids weather roulette.

## Phase G — live trigger activation when available

If a real provider signal crosses the predictive threshold during the bounded experiment:

1. Guardian wakes via provider-native pulse;
2. configured real Agent inspects Journey/Twin/current risk;
3. Agent inspects available shadow alternatives;
4. Agent chooses:
   - activate a matching standby proposal;
   - or request a fresh replan if shadows are stale/inadequate;
5. Gateway enforces policy;
6. new PlanVersion becomes active;
7. recompute risk;
8. continue Journey to COMPLETED.

No operator-posted WEATHER/CLOSURE event may count for this stretch success.

## Phase H — measurable benefit

Do not claim "resilience" because a shadow plan exists.

For each standby plan record:
- target failure mode;
- current-plan exposure;
- shadow-plan exposure;
- cost delta;
- schedule drift;
- protected commitment status;
- required new evidence;
- freshness/expiry.

If activated, require deterministic before/after improvement on the provider-linked risk.

## Anti-ORD rules

- one capability branch;
- one main result report;
- inline blocker fixes;
- no R18.1/R18.2 recut carousel;
- no city hopping solely to find rain;
- no new event bus;
- no new mobility framework;
- no giant resilience framework rewrite;
- no spending the majority of time formatting evidence.

## Success levels

### REVOLUTION_A — evidence-on-demand hypothetical planning
A hypothetical reorder/recovery plan acquires its own missing live mobility edges, persists a separate immutable preview snapshot, and passes/fails deterministically without weakening truth gates.

### REVOLUTION_B — anticipatory standby
REVOLUTION_A + an ACTIVE healthy Journey maintains at least one fully evidence-grounded, non-active shadow recovery plan for a material counterfactual.

### REVOLUTION_C — forecast-aware resilience
REVOLUTION_B + real provider forecast materially changes initial/standby strategy in an explainable way while no fake event is introduced.

### REVOLUTION_D — live preemptive activation
REVOLUTION_C + a real provider threshold crossing wakes the configured model, which chooses a grounded standby/fresh replan through Gateway, risk measurably decreases, and Journey COMPLETES.

Target B/C regardless of weather.
Push for D only if live provider conditions genuinely occur.

## Final report

One file:

`REVOLUTION_R18_ANTICIPATORY_RESILIENCE_RESULT.md`

Include:
- base/final SHA;
- fresh Journey/city;
- active plan truth provenance;
- current live weather/mobility state;
- counterfactuals;
- shadow PlanVersion IDs/states;
- evidence-on-demand mobility captures;
- mobility cost statuses/provenance;
- VOI decisions;
- standby feasibility;
- forecast-aware scoring/explanation changes;
- if a real trigger occurs: GuardianRun, real AgentRun/tool sequence, Gateway decision, old/new plan lineage, before/after risk and final Journey state;
- focused tests + candidate-vs-base delta.

## Success sentence

R18 succeeds when this is a machine fact:

> CityNexus no longer waits for a disruption before figuring out how to survive it; while the trip is still healthy, it can build truth-grounded standby plans with on-demand evidence, keep them safely inactive, and use live provider risk to choose or activate the right recovery strategy without weakening authority.
