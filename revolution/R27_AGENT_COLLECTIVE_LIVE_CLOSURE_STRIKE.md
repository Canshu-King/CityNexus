# Revolution R27 — Agent Collective Live Closure Strike

## Objective

Close the exact last R27 blocker.

No R27.1.
No R28.
No new planner.
No generic voting framework.
No search-stack project.

The product already has:
- member-aware collective context;
- Truth Mesh;
- plan-delta fairness;
- server collective mutation gate;
- real physical execution.

The last missing machine fact is:

a real Agent on an ACTIVE shared Journey encounters a true collective trade-off, escalates only the human value judgment, resumes after member resolution, and executes only the collectively resolved plan.

## Phase 0 — preserve v3

Do not rewrite the v3 deterministic proof.

Keep:
- Truth Mesh;
- source binding precedence;
- plan_collective_fit_subject;
- collective_mutation_gate;
- select_plan / accept_replan / activate_standby gates.

Add only what the live Agent trade-off path needs.

## Phase 1 — expose collective mediation on replan proposals

A real Agent must be able to see the server classification after request_replan.

After an OPPORTUNITY_WINDOW request creates proposals, return a bounded collective receipt.

For the proposal set sharing:
- journey;
- trigger_event_id;
- base_plan_version_id;

recompute:
- hard-feasible proposed PlanVersions;
- member fit matrix using PLAN_DIFF;
- fairness;
- mediation classification.

Add to request_replan response, and preferably list_replans:

collective_mediation
proposal_collective_decisions

Example:

{
  "collective_mediation": {
    "classification": "HUMAN_TRADEOFF_REQUIRED",
    "candidate_ids": ["plan-a", "plan-b"],
    "decision_relevant_member_ids": ["member-a", "member-b"]
  },
  "proposal_collective_decisions": {
    "proposal-a": {"candidate_plan_id":"plan-a","allowed":false,"code":"COLLECTIVE_TRADEOFF_UNRESOLVED"},
    "proposal-b": {"candidate_plan_id":"plan-b","allowed":false,"code":"COLLECTIVE_TRADEOFF_UNRESOLVED"}
  }
}

Do not make the model infer the authoritative classification from prose.

## Phase 2 — narrow Agent tool: request_collective_decision

Add one narrow tool:

request_collective_decision

Inputs:
- journey_id
- mission_id
- trigger_event_id

No candidate IDs.
No required member IDs.
No question wording from model.

Server derives all of them.

Validation:
- Journey ACTIVE;
- mission belongs to Journey;
- trigger still actionable;
- at least two current hard-feasible proposals exist for same base/trigger;
- current collective classification == HUMAN_TRADEOFF_REQUIRED;
- required members = decision_relevant_member_ids intersect MEMBER_IN_FORCE;
- at least one in-force member can authorize JOURNEY_UPDATE, otherwise AUTHORITY_CONFLICT instead of preference clarification.

Persist one clarification payload in JourneyMission.clarification_json.

## Phase 3 — durable shared decision

Use JourneyMission.clarification_json. Do not create a social-voting subsystem.

Shape:

{
  "kind":"COLLECTIVE_TRADEOFF",
  "policy":"MATERIAL_TRADEOFF_REQUIRES_ALL_RELEVANT_MEMBER_RESPONSES",
  "clarification_id":"...",
  "decision_epoch":"...",
  "trigger_event_id":"...",
  "base_plan_version_id":"...",
  "candidate_options":[
    {"proposal_id":"...","candidate_plan_id":"...","fit_receipt":{...}}
  ],
  "required_member_ids":["...","..."],
  "responses":{},
  "status":"WAITING_FOR_MEMBERS",
  "selected_proposal_id":null,
  "selected_candidate_id":null
}

Set mission.status = WAITING_FOR_MEMBERS.

The Agent does not decide the social policy.

## Phase 4 — collective decision epoch

Fingerprint must include:
- journey id;
- active/base plan id;
- trigger id;
- candidate proposal ids + proposed plan ids;
- authoritative plan/fact fingerprints sufficient to detect plan replacement;
- in-force member ids;
- member role + capability set;
- journey-scoped member preference payload hash.

Any material change makes the decision STALE.

Do not silently reuse old member answers after:
- withdrawal;
- expiry;
- role/capability change;
- preference change;
- active plan change;
- proposal replacement;
- world-fact staleness.

## Phase 5 — member-scoped response route

Add one narrow HTTP route, conceptually:

POST /api/v1/journeys/{journey_id}/missions/{mission_id}/collective-clarification/{member_id}

Payload:
{
  "clarification_id":"...",
  "proposal_id":"..."
}

Server validates:
- clarification kind is COLLECTIVE_TRADEOFF;
- status is WAITING_FOR_MEMBERS;
- epoch fresh;
- member is MEMBER_IN_FORCE;
- member_id is in required_member_ids;
- proposal is one of server-derived options.

A response writes only responses[member_id].

It never rewrites JourneyMember.preferences_json.
It never writes TravelerTwin memory.
It is a decision-specific answer, not a preference-profile overwrite.

No caller-authentication claim.

## Phase 6 — resolution policy

Policy:
MATERIAL_TRADEOFF_REQUIRES_ALL_RELEVANT_MEMBER_RESPONSES

Rules:

Missing any required response:
WAITING_FOR_MEMBERS.

All required responses exist and all select the same proposal:
RESOLVED.

Set:
selected_proposal_id
selected_candidate_id

If all required members responded but disagree:
UNRESOLVED_DISAGREEMENT.

No majority vote.
No OWNER tie-break.
No LLM tie-break.

OWNER mutation authority remains separate from member preference voice.

## Phase 7 — child mission continuation

When a collective decision becomes RESOLVED:

- parent mission -> ANSWERED;
- create one child JourneyMission with parent_mission_id;
- inherit parent authority envelope;
- put the collective resolution in child.resolved_intent_json;
- do NOT convert the answer into permanent TravelerTwin preference.

Child command should be neutral and machine-derived, e.g.:

"Continue the pending shared-Journey recovery using the current resolved collective decision. Re-inspect server state and execute only if the Gateway confirms the decision remains current."

Do not put the selected proposal ID in user prose if the Agent can discover it through server tools.
It may be present in resolved_intent_json as server-owned machine state.

Reuse the existing /missions/{mission_id}/resume endpoint if possible.

## Phase 8 — runtime completion contract

A successful request_collective_decision must be a typed clarification completion, not PARTIAL.

Generalize runtime completion semantics:

request_collective_decision
with mission_status=WAITING_FOR_MEMBERS
and clarification_id
=> completion_contract.kind = CLARIFICATION_REQUIRED
=> AgentRun may complete cleanly
=> mission stays WAITING_FOR_MEMBERS.

Pending missions endpoint must include WAITING_FOR_MEMBERS.

Do not force the model to call the R26 TAKE_NOW/DEFER conclude_recovery contract.

## Phase 9 — bind resolved decision into mutation

Currently collective_mutation_gate supports resolved_decision, but production call sites do not supply it.

For Agent accept_replan:
- load the child mission via request.mission_id;
- derive server-owned collective resolution from child.resolved_intent_json / parent clarification;
- verify selected proposal and selected candidate;
- pass this resolution through the internal accept path to collective_mutation_gate.

Do not let model supply arbitrary resolved_decision JSON.

Public/manual accept without a matching fresh resolved decision remains blocked when classification is HUMAN_TRADEOFF_REQUIRED.

Normal approval does not override unresolved tradeoff.

## Phase 10 — final live fixture

Fresh disposable DB.

Create a real ACTIVE Nara Journey using ordinary product paths.

Recommended truthful shape:
- current Activity: a grounded real Place, ARRIVED or IN_PROGRESS;
- future next Activity: real protected C4 anchor;
- live frozen mobility current -> anchor;
- enough slack for at least one opportunity insertion.

Use the already-proven R22 opportunity architecture.

Useful setup lead, not Agent mission content:
- current can be a grounded Nara museum such as Nara Craft Museum;
- candidate garden can be Isuien;
- candidate museum can be the grounded Calligraphy Museum;
- next C4 anchor may reuse a real R22-style protected Nara anchor if facts remain current.

Do not hardcode these into production logic.

## Phase 11 — member truth

Two MEMBER_IN_FORCE rows:

OWNER:
interest/garden

ADMIN or COLLABORATOR:
interest/museum

Both non-empty.
Read back before Agent start.

Do not change these preferences during the experiment.

## Phase 12 — opportunity signal

Advance current activity to ARRIVED or IN_PROGRESS.

inspect_twin must create a real:

SYSTEM_DERIVED
OPPORTUNITY_WINDOW

using:
- live active-plan mobility;
- real current activity;
- future C4 anchor;
- >=30 minute actionable window.

No synthetic Event insertion.

## Phase 13 — real Agent first run

Use actual configured Hermes-compatible runtime.

Preferred primary:
cn:glm-5.3-flash

If a bounded recorded primary external failure occurs, the already-configured real fallback:
cn:deepseek-v4.1-flash
is acceptable.

No deterministic fake Agent fallback.

Neutral mission:

"Use the current shared Journey well. Inspect the current members separately and respect the server's collective mediation. If a real opportunity exists, compare a small number of grounded city options. If one option is jointly acceptable, use the governed recovery path. If the grounded choices leave a true human value trade-off, request the shared decision instead of choosing for the members. Do not invent facts or social authority."

Do not provide:
- candidate names;
- candidate IDs;
- desired proposal;
- correct classification;
- fixed tool sequence.

Expected autonomous shape may include:
inspect_journey
inspect_twin
search_city_services
acquire_place_facts
request_replan

The model should discover at least two real feasible options before requesting people.

Server should return:
HUMAN_TRADEOFF_REQUIRED.

Then Agent calls:
request_collective_decision.

Mission:
WAITING_FOR_MEMBERS.

## Phase 14 — member responses

Use the member response API.

For the closure experiment, both relevant members may explicitly align on either grounded proposal.

This is a decision-specific current choice and may differ from their baseline profile.

Do not change their stored garden/museum preferences.

Machine proof:
before responses = distinct preferences
after responses = same distinct preferences
collective clarification = aligned decision

This demonstrates that a person can choose a specific compromise without rewriting who they generally are.

## Phase 15 — resume real Agent

Resume the server-created child mission through the configured real Agent runtime.

It must re-inspect current state.

It should discover:
- same active base;
- same trigger;
- current proposals;
- RESOLVED collective decision.

Then it may call accept_replan only for the selected proposal.

Server collective gate must reject the other proposal even now.

If normal policy returns REQUIRE_CONFIRMATION:
use the existing product approval path.
Do not bypass it.

If existing explicit autonomy policy legitimately allows auto execution, ALLOW_AUTO is also acceptable.

## Phase 16 — physical execution

After accepted replan:

- opportunity proposal becomes active;
- execute inserted activity through HTTP state machine;
- preserve C4 anchor;
- actual mobility edges must be hard-eligible live provider captures;
- resolve opportunity event;
- complete remaining Journey.

Final Journey must be COMPLETED or reach the truthful terminal state dictated by the active schedule.

## Mandatory controls

1. Before member responses:
accept either tradeoff proposal -> 409 COLLECTIVE_TRADEOFF_UNRESOLVED.

2. One required member response missing:
WAITING_FOR_MEMBERS.

3. Both responses disagree:
UNRESOLVED_DISAGREEMENT; mutation blocked.

4. Both align:
RESOLVED.

5. Try accepting non-selected proposal after RESOLVED:
reject.

6. Withdraw one member before second response:
decision becomes STALE and recomputes.

7. Change one member preference before accept:
decision becomes STALE.

8. Change role/capability basis:
decision becomes STALE if authority basis changes.

9. World facts/mobility stale before accept:
normal feasibility/truth gate rejects.

10. Member response does not alter JourneyMember baseline preferences or TravelerTwin memory.

## Tests

Add focused tests for:
- collective replan receipt;
- request_collective_decision server derivation;
- decision epoch;
- member response isolation;
- missing/disagree/aligned responses;
- child mission inheritance;
- runtime WAITING_FOR_MEMBERS completion;
- resolved decision binding into accept_replan;
- stale decision controls.

At the end run the full R20-R27 focused lineage once, including the v3 Truth Mesh/gate tests.

Do not reduce from the previous broad focused set merely because the new tests are green.

## Closure bar

R27-C closes only when the real Agent trace itself contains the collective handoff and continuation.

Required machine chain:

AgentRun #1
-> sees two members
-> sees real opportunity
-> obtains at least two grounded proposals
-> sees HUMAN_TRADEOFF_REQUIRED
-> request_collective_decision
-> WAITING_FOR_MEMBERS

member responses
-> RESOLVED

AgentRun #2 child
-> re-inspects
-> accepts only selected proposal
-> Gateway executes

physical Journey
-> inserted activity executed
-> protected anchor preserved
-> final completion

## Success sentence

CityNexus did not resolve a human disagreement by averaging it away or letting the model pick a winner. The real Agent discovered the grounded trade-off, handed only the value judgment to the relevant members, preserved each person's underlying preference truth, resumed after their decision, and the server allowed only the collectively resolved plan to change the real Journey.
