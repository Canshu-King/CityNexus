# Revolution R19 — Living Plan Portfolio

## The leap

R18 proved CityNexus can create one evidence-grounded standby branch while the current trip is still healthy.

R19 must turn that prototype into a living portfolio of future options.

The product target is:

```text
one ACTIVE Journey
  -> one active PlanVersion = current reality
  -> bounded counterfactual engine identifies material future failure modes
  -> 1-3 grounded STANDBY PlanVersions represent survivable futures
  -> every standby has:
       trigger contract
       canonical Place truth
       its own mobility evidence
       true TTL / expiry
       deterministic feasibility
       exact cost/time deltas
       protected commitment result
       authority policy
  -> Autopilot continuously:
       refreshes expiring high-value evidence
       prunes invalid/dominated branches
       rebuilds only what changed
  -> Guardian/Agent can inspect the portfolio
  -> when a real trigger arrives:
       choose a valid standby or fresh replan
       Gateway revalidates and activates
  -> stale/untriggered standby can never be selected accidentally
```

This is not a backup-plan feature.
It is a branching operational model of the Journey.

## Hard invariants

- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`;
- exactly one active/current plan truth;
- STANDBY is never current;
- ordinary user plan selection cannot activate STANDBY;
- counterfactual trigger is not a real event;
- provider evidence has explicit freshness/expiry;
- activation always revalidates canonical facts, mobility and policy;
- stale standby fails closed;
- no shadow evidence may overwrite the active plan's frozen evidence.

## Phase 0 — make STANDBY a first-class lifecycle

Do not keep lifecycle only in `explanation_json`.

Use the smallest explicit server contract.

Preferred minimal path:
- extend PlanVersion public/status contract with `STANDBY`;
- persist standby rows with `status=STANDBY`;
- `plan_schema.selectable=false` for STANDBY;
- generic `select_plan` refuses STANDBY by status;
- list/get APIs expose lifecycle truth explicitly.

If an explicit contingency table is genuinely cleaner, keep it small. Do not build a new workflow framework.

Required regression:
- a fully authoritative STANDBY plan cannot be selected through the ordinary plan-select endpoint.

## Phase A — real evidence TTL

Every preview/standby mobility snapshot must carry a real `expires_at`.

Use the existing configured provider/cache TTL unless the provider supplies a stricter expiry.

Persist:
- captured_at;
- expires_at;
- provider;
- snapshot ID;
- parent/base plan ID;
- trigger/scenario.

Staleness rules:
- expired evidence => STANDBY becomes stale/non-activatable;
- active parent PlanVersion changed => standby invalid;
- relevant commitment/fact truth changed => revalidation required;
- stale evidence is refreshed on demand, never silently trusted.

Do not write capture time into a field named expiry.

## Phase B — one mobility truth everywhere

When materializing a standby:
- derive each adjacency from the standby mobility snapshot;
- set Activity.travel_from_prev_min from that exact edge;
- persist JourneyLegs if the current plan model expects them;
- preserve mode, duration, cost status, distance, geometry and provenance.

No dual truth:
- gate says 18 min;
- Activity says 7 min
is forbidden.

Add a consistency assertion/regression.

## Phase C — recompute plan economics and timing

Do not compute a standby as "active minus dropped activity".

Recompute from the materialized branch:
- activity costs;
- mobility costs;
- route duration;
- total duration;
- schedule drift;
- budget delta;
- commitment slack.

Paid mobility with unknown cost remains blocking/confirmation-required.

Known-free remains explicit provider/mode-backed truth.

## Phase D — portfolio, not one shadow

Maintain at most 1-3 useful STANDBY plans.

Aim to cover distinct material failure modes, not cosmetic variants:
- weather exposure;
- mobility-delay / commitment-buffer compression;
- Place closure / unavailable stop.

For each branch persist:
- counterfactual/simulation ID;
- trigger contract;
- covered failure mode;
- base active PlanVersion;
- evidence snapshot;
- expires_at;
- change summary;
- cost/time delta;
- protected commitment result;
- readiness state.

Do not create multiple branches whose effective outcome is the same.

## Phase E — support richer counterfactual materialization

R18 mainly materializes drop-based branches.

R19 should support at least:
- DROP;
- KEEP with counterfactual rescheduling;
- grounded REPLACE when the solver selected a real replacement.

Reuse existing replan/CP-SAT materialization logic where possible.

Do not fork another solver.

If REPLACE requires new Place truth/mobility:
- reuse R15 value-of-information acquisition;
- acquire only the evidence that changes readiness.

## Phase F — continuous portfolio maintenance

Hook portfolio maintenance into Guardian/Autopilot pulses, but keep it bounded.

On each due pulse:
1. inspect active PlanVersion;
2. inspect current resilience/counterfactuals;
3. inspect existing standby portfolio;
4. invalidate branches whose parent/truth/evidence is stale;
5. refresh only high-value expiring evidence;
6. prune dominated or no-longer-material branches;
7. create at most the missing top branches.

Persist why each branch was:
- kept;
- refreshed;
- invalidated;
- pruned;
- created.

No bulk crawling. No continuous full-city replanning.

## Phase G — give the Agent portfolio awareness

The real model should be able to inspect standby options before requesting a fresh replan.

Preferred minimal interface:
- include a compact `standby_portfolio` summary in `inspect_twin` or a small read-only tool;
- expose trigger, freshness, key changes, cost/time delta, commitments and readiness;
- do not dump raw megabyte evidence.

When an actionable provider event occurs, the Agent may:
- choose a matching fresh standby;
- request a new replan if portfolio options are stale/inadequate;
- choose NO_ACTION if the event is irrelevant.

## Phase H — activation is a governed operation

Do not activate standby through ordinary `select_plan`.

Add/reuse a Gateway-controlled activation path.

Before activation:
- require a real persisted trigger Event or provider condition matching the standby trigger contract;
- verify parent plan is still current;
- verify evidence freshness;
- re-run canonical authority + deterministic feasibility;
- re-check policy/autonomy bounds.

Then:
- turn old active plan SUPERSEDED;
- turn chosen STANDBY ACTIVE;
- remap commitments/current cursor safely;
- preserve lineage and trigger event.

If policy requires confirmation, stop there and request it.

## Phase I — safe-state proof is valid

R19 does not need nature to produce a disruption.

A healthy live Journey can close the main milestone if it proves:
- active truth unchanged;
- 2+ distinct material failure modes have grounded standby branches, when genuinely feasible;
- standby plans have real TTL;
- portfolio maintenance prunes/refreshes correctly;
- generic select cannot activate standby;
- Agent/Twin can see the portfolio.

If a real provider trigger naturally occurs, push through governed activation.

## Anti-ORD rules

- one capability branch;
- one result report;
- direct inline fixes;
- no branch-per-standby;
- no R19.1/R19.2 recut;
- no new solver;
- no new event bus;
- no generic orchestration rewrite;
- no spending most time proving safe weather again.

## Success levels

### REVOLUTION_A — first-class standby truth
STANDBY lifecycle is server-enforced, expiring, non-selectable through generic select, and internally consistent with its mobility evidence.

### REVOLUTION_B — living portfolio
An ACTIVE healthy Journey maintains multiple distinct evidence-grounded standby branches, refreshes/prunes them as truth changes, and leaves the active plan untouched.

### REVOLUTION_C — agent-aware mission control
REVOLUTION_B + real configured Agent can inspect the portfolio and choose standby-vs-fresh-replan strategy from live Journey state.

### REVOLUTION_D — governed branch activation
REVOLUTION_C + a real provider/user-observed event matches a trigger, Gateway activates a fresh validated standby, and the Journey continues to COMPLETED.

Target B/C without waiting for bad weather.
Push for D only if a truthful trigger occurs.

## Final report

One file:

`REVOLUTION_R19_LIVING_PLAN_PORTFOLIO_RESULT.md`

Include:
- code final SHA and report SHA separately;
- Journey/city;
- active PlanVersion;
- standby portfolio rows;
- trigger contracts;
- evidence captured_at/expires_at;
- activity/leg mobility consistency;
- recomputed cost/time deltas;
- portfolio keep/refresh/prune decisions;
- Agent-visible portfolio summary;
- generic-select refusal proof;
- if activated: trigger Event, AgentRun, Gateway decision, lineage and final Journey/Twin;
- focused R19 regressions + candidate-vs-base delta.

## Success sentence

R19 closes when this is a machine fact:

> CityNexus no longer has one plan and one ad-hoc backup; it continuously maintains a small, truthful portfolio of executable future branches, knows when each branch expires or stops applying, prevents accidental activation, and can let the Agent choose the right branch when reality changes.
