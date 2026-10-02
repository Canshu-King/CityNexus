# GPT external check — R21 -> R22

Inspected:
- uploaded `CityNexus-Revolution-R21-Delivery-20261002.zip`
- raw R21 AgentRun / approval / execution / Twin receipts from that package
- remote R21 report `REVOLUTION_R21_AUTONOMOUS_FUTURE_SYNTHESIS_RESULT.md`
- current remote experiment head `cd1e5dd214f3ea7e52198674487ffa7d1cbf66e7`

## R21 verdict

R21 is a genuine Revolution closure.

The remote primary run proves:
- neutral mission plan: no ordered activate_standby/request_replan mutation script;
- no event/proposal/standby/plan ID answer leakage in mission text;
- materially distinct prepared futures (DROP vs RETIME/KEEP);
- USER_REPORTED closure outside existing trigger contracts;
- real configured Hermes-compatible GLM runtime;
- model independently selected `request_replan`;
- deterministic solver produced a new grounded future;
- model inspected and selected `accept_replan`;
- Gateway/deterministic feasibility remained authoritative;
- live Valhalla actual edges were hard eligible;
- revised Journey completed.

The remote NO_ACTION control is also meaningful:
- ACTIVE Journey;
- user-reported closure;
- model acquired provider-backed official facts;
- official facts contradicted the user report;
- model chose no mutation and preserved the active reality.

This is stronger than the later supplemental ZIP control, which was run after completion.

## Supplemental R21 hardening after the primary report

The delivery ZIP binds a later code head:
`cd1e5dd214f3ea7e52198674487ffa7d1cbf66e7`

and proves additional repairs:
- multiple actionable events now require explicit event selection;
- Agent selected the relevant event after Twin inspection;
- no trigger ID was supplied by the mission;
- machine-visible `conclude_recovery` contract exists;
- a frozen mobility structural-anchor case mismatch was repaired through shared snapshot lookup;
- final Twin exposes the accepted plan's live Valhalla edge.

These later fixes strengthen R21; they do not invalidate the earlier primary C/D run.

## Source-binding cleanup required, but timebox it

Two R21 result narratives now exist:
1. the published canonical report `REVOLUTION_R21_AUTONOMOUS_FUTURE_SYNTHESIS_RESULT.md`;
2. the supplemental ZIP report `REVOLUTION_R21_AUTONOMOUS_FUTURE_RESULT.md`.

The canonical remote report still names an earlier final experimental SHA while current code head is `cd1e5dd...`.

Before R22 product work, spend at most a few minutes:
- append a "post-closure hardening" note to the canonical SYNTHESIS report;
- name current final code head `cd1e5dd...`;
- reference the later accepted AgentRun(s) only as supplemental hardening evidence;
- keep one official R21 report filename.

Do not create a report-reconciliation project.

## Remaining R21 product boundaries

### 1. Future synthesis is still defensive/subtractive

The successful synthesized future is an F1 optional removal:
- closed Place removed;
- protected commitment preserved;
- travel/cost reduced;
- Journey survives.

That is real synthesis, but it improves survivability by subtraction.

R21 does not yet prove CityNexus can use newly available slack to create a better trip by adding a new real-world opportunity.

### 2. OpportunityWindow already exists but is not yet an autonomous positive-action loop

Current Twin already computes a bounded opportunity window before the next protected commitment.

Current replan code already contains:
- `OpportunityWindow`;
- `evaluate_window_replacement`;
- F3 opportunity-window evidence;
- real candidate Place facts;
- runtime mobility capture.

The next product leap should use those existing pieces proactively.

### 3. Direct Agent `replace_activity` is NOT a safe shortcut for R22

Current `AgentToolGateway.replace_activity` has legacy behavior for a replacement Place:
- reads `metadata.cost_minor` with a default zero;
- estimates travel through `MockMobilityProvider`.

That would regress the truth boundary if used for a real-city opportunity insertion.

R22 must NOT use this path for final success unless it is first upgraded to canonical cost truth + live provider mobility.

Preferred path:
- reuse the replan/opportunity-window materialization and live mobility capture.

### 4. Event lifecycle remains sticky after recovery

Accepted replans currently move a DETECTED trigger only to ACKNOWLEDGED.

The later R21 NO_ACTION receipt still sees old MAJOR closure events as actionable after the trip was already recovered/completed.

That pollutes the Agent world model.

R22 should add a small journey-impact lifecycle:
- when a replan/standby activation definitively adapts the Journey to a trigger, mark the trigger RESOLVED (or equivalent handled state) with resolved_at and a resolution reason such as JOURNEY_ADAPTED;
- preserve the original event/provenance; resolution means "no longer actionable for this Journey", not "the external world condition ceased";
- completed Journey may close remaining Journey-actionable events.

Do not turn this into an event-system rewrite.

### 5. conclude_recovery argument hygiene

The supplemental main run emitted two oversized conclude_recovery calls rejected by schema before a valid compact call.

Fix narrowly:
- server/tool description should advertise the 500-char reason bound clearly;
- runtime may compact/truncate model reason before tool dispatch, preserving the full prose only in final assistant text if needed.

No separate runtime project.

## Revolution frontier

Do not make R22 "better recovery".

The next capability should be positive autonomy:

> When the active trip gains a real usable window, CityNexus notices the opportunity, autonomously searches the open world for a new experience, acquires only the facts needed to prove it fits, captures live inbound/outbound mobility, creates an additive governed plan that preserves commitments and budget, and either inserts the opportunity or deliberately leaves the window empty.

This changes the Agent from a defensive recovery operator into an opportunity-seeking trip operator.
