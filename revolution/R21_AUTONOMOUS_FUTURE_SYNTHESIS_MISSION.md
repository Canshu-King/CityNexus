# Revolution R21 — Autonomous Future Synthesis

## The leap

R20 proved a real model can inspect a truthful standby portfolio and choose a branch.

R21 must prove something harder:

> the Agent can decide whether the existing future portfolio is sufficient at all.

Target behavior:

```text
one ACTIVE reality
  + multiple materially distinct grounded futures
  + one real disruption
        |
        v
real configured Agent
  -> inspect Journey
  -> inspect Twin / portfolio / event
  -> independently choose:
       A. activate an existing compatible standby
       B. request a fresh replan because all standby futures are inadequate
       C. NO_ACTION because current reality remains acceptable
        |
        v
if B:
  deterministic replan / truth acquisition / live mobility
  -> new candidate future
  -> Agent evaluates it
  -> Gateway governs mutation
        |
        v
execution continues to COMPLETED
```

The wrapper supplies tools and authority.
It must not supply the strategy.

## Phase 0 — remove strategy-order leakage from the mission plan

Current `build_mission_plan()` inserts a fixed step:

`arbitrate_standby -> activate_standby`

before `request_replan`.

For R21-style recovery missions, replace ordered mutation steps with a neutral decision stage.

Preferred shape:

```text
inspect_journey
inspect_twin
evaluate_recovery_options
authority_boundary
```

where:
- `evaluate_recovery_options` has no preselected mutating tool;
- allowed tools still include `activate_standby`, `request_replan`, and other policy-valid actions;
- system prompt may explain authority rules, but does not prescribe which action to try first.

Do not remove deterministic allowed-tool restrictions.

Do not remove approval boundaries.

The mission plan is an envelope, not a script.

## Phase A — stop counting equivalent branches as multiple futures

R20's route_plus_20 and route_plus_30 materially overlapped.

For R21 final proof, prepare at least two truly different executable futures.

They must differ in actual product state, for example:
- different activity set;
- different order;
- different replacement Place;
- materially different schedule;
- materially different travel burden.

Valid examples:
1. DROP one optional visit;
2. RETIME/KEEP the visit with changed downstream schedule;
3. REPLACE with a canonical grounded Place;
4. one existing standby plus one fresh replan candidate.

Do not count:
- two risk labels over the same itinerary;
- two snapshots whose activities/order/times are materially identical.

Expose a deterministic `material_difference_fingerprint` or equivalent summary if useful.

## Phase B — final mission must be natural, not a hidden multiple-choice exam

Final user/event mission should state the real problem, for example:

"The traveler reports a major delay affecting the current route. Preserve the important commitments and recover the trip safely."

Do NOT put in the final mission:
- correct standby plan ID;
- "activate standby";
- "request replan";
- "choose A/B/C";
- expected tool order.

The model can learn available tools from the server tool catalog and authority envelope.

The system prompt may still say:
- inspect before mutation;
- Gateway is authoritative;
- never invent IDs/facts;
- use tools, not prose, for mutations.

## Phase C — prove the existing portfolio is sometimes insufficient

Design one bounded disruption where:
- at least one standby exists;
- no existing standby fully satisfies the current event + traveler constraints.

Examples:
- closure affects a Place not covered by mobility-only standby;
- user reduces walking tolerance;
- new commitment makes every prepared branch invalid;
- concurrent mobility + closure constraint makes single-mode standbys inadequate.

Do not hardcode the answer.

The deterministic trigger matcher should mark incompatible branches as NO_MATCH/STALE/INSUFFICIENT.

The Agent must then be free to choose `request_replan`.

## Phase D — fresh future synthesis

When the Agent requests a replan, the resulting new future must satisfy the same truth boundaries as previous Revolution work:

- exact provider-backed Place identity;
- canonical opening/cost facts;
- estimate authority OFF;
- live/provider-backed mobility;
- deterministic feasibility;
- protected commitment preservation;
- explicit cost/schedule deltas;
- old/new lineage.

If the first new proposal lacks facts:
- the Agent may acquire facts;
- search a replacement;
- request another bounded replan;
- or abandon that strategy.

Do not let the wrapper perform those strategy choices.

## Phase E — Agent must compare old portfolio vs newly synthesized future

After fresh candidate creation:
- expose compact deltas;
- expose compatibility/readiness;
- expose cost/time/travel burden;
- expose protected commitment result.

The model then decides:
- activate an existing standby;
- accept the newly synthesized proposal;
- request another replan;
- or no-action.

Do not automatically accept the new proposal merely because `request_replan` produced one.

## Phase F — deterministic authority remains absolute

Existing standby activation:
- shared trigger matcher;
- parent/current equality;
- evidence TTL;
- canonical feasibility;
- Gateway policy.

Fresh replan acceptance:
- deterministic proposal;
- Gateway policy;
- approval as required.

The model cannot:
- mark a branch compatible;
- mark evidence fresh;
- mint provider facts;
- write active plan pointer;
- self-approve.

## Phase G — negative strategy controls

R21 needs at least two negative proofs.

### Control 1 — existing branch exists but is inadequate

Agent must NOT activate it merely because it is MATCH on event type if:
- it violates a new commitment;
- it fails current traveler constraints;
- it is dominated by a materially safer grounded option;
- or server readiness says INSUFFICIENT.

### Control 2 — no material intervention required

Give the same strategy surface a low-severity/irrelevant event.

The model should be allowed to return NO_ACTION after inspection.

This proves R21 is not "always mutate".

## Phase H — complete the synthesized future

For the main success path:
- selected/accepted future becomes active through Gateway;
- sibling/pre-parent branches reconcile;
- execute the real HTTP state machine;
- Journey reaches `COMPLETED`;
- final Twin agrees with active plan;
- all actual used edges retain hard-eligible provider truth.

## Phase I — small runtime hygiene

Fix inline only:
1. `ai_state` should not say `DISABLED_BY_OPS` while Hermes-compatible runtime is actively executing.
2. stale orphaned RUNNING AgentRun/JourneyMission rows from crashed/restarted processes should reconcile to `INTERRUPTED` / `ABORTED` with a named reason after a bounded timeout/startup sweep.

Do not turn either into a runtime refactor project.

## Anti-ORD rules

- one capability branch;
- one result report;
- no R21.1/R21.2 recut;
- no new solver;
- no new event bus;
- no new Agent framework;
- no branch-count vanity metric;
- no prompt containing the correct recovery action;
- no spending most of the round polishing observability.

## Success levels

### REVOLUTION_A — strategy freedom
Mission plan no longer pre-orders standby activation vs replan; final natural-language mission does not name the recovery strategy.

### REVOLUTION_B — materially different future arbitration
REVOLUTION_A + real model compares at least two materially different grounded futures and independently chooses an existing branch, fresh replan, or NO_ACTION.

### REVOLUTION_C — autonomous future synthesis
REVOLUTION_B + existing portfolio is intentionally insufficient for one real/user-observed disruption, the model independently calls `request_replan`, a new truth-grounded future is created, and the model chooses/accepts it through Gateway.

### REVOLUTION_D — full adaptive completion
REVOLUTION_C + revised Journey executes to `COMPLETED`; a second control run demonstrates NO_ACTION or existing-standby reuse without wrapper strategy hints.

Target C/D.

## Final report

One file:

`REVOLUTION_R21_AUTONOMOUS_FUTURE_SYNTHESIS_RESULT.md`

Include:
- base/final code SHA;
- report SHA separately;
- final natural-language mission text;
- proof that mission plan contains no ordered `activate_standby` strategy step;
- active Journey/event;
- materially different pre-existing futures;
- material difference summaries;
- real Agent provider/model;
- ordered model-selected tools;
- reason existing portfolio was sufficient/insufficient;
- fresh replan/fact/mobility receipts when synthesized;
- Gateway/approval;
- old/new plan lineage;
- final Journey/Twin;
- NO_ACTION or existing-standby control run;
- focused R21 regressions + prior focused-suite delta.

## Success sentence

R21 closes when this is a machine fact:

> CityNexus did not merely choose from futures prepared for it; a real model independently recognized when those futures were inadequate, created a new truth-grounded future through the existing planning and evidence machinery, crossed the same deterministic authority boundary, and completed the trip without the wrapper telling it which recovery strategy to use.
