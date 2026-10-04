# R27 shared decision implementation sketch

## 1. Keep one source of collective math

Do not duplicate fairness calculations.

Reuse:
- plan_collective_fit_subject
- active_journey_members_with_capabilities
- classify_group_decision
- collective_mutation_decision

Add a helper that builds the proposal-set collective receipt for one:
journey + base_plan + trigger.

Use it from:
- request_replan response;
- list_replans;
- request_collective_decision;
- mutation gate tests.

## 2. Candidate set identity

The collective decision must bind to server proposal rows, not free-form plan IDs from the model.

Option row:
{
  proposal_id,
  proposed_plan_version_id,
  hard_constraints_passed,
  fit_subject,
  member_fits,
  fairness
}

Only PRESENTED, current-base, current-trigger proposals participate.

## 3. request_collective_decision tool

Server derives proposal set.

Reject if:
- fewer than 2 grounded options;
- classification != HUMAN_TRADEOFF_REQUIRED;
- mission/trigger/base stale.

Return:
{
  tool:"request_collective_decision",
  decision:"ALLOW_AUTO",
  mission_status:"WAITING_FOR_MEMBERS",
  clarification:{...}
}

This tool creates decision state only; it does not mutate Journey plan.

## 4. Runtime recognition

Add request_collective_decision to non-domain or clarification tools, not mutation tools.

_server_completion_contract:
successful request_collective_decision with WAITING_FOR_MEMBERS
=> CLARIFICATION_REQUIRED.

_terminal_agent_status should preserve mission WAITING_FOR_MEMBERS.

pending_journey_missions should include it.

## 5. Fingerprint

Function:
collective_decision_epoch(...)

Canonical JSON hash over:
journey id
active plan id
trigger id
sorted candidate proposal/plan ids
candidate fact/mobility fingerprints
sorted in-force member ids
role/capability map
member preferences_json hash

No timestamps that change on reads.

## 6. Member answer

Use clarification_id + proposal_id.

Never accept candidate_plan_id alone if multiple proposals could reference it.

Store:
responses[member_id] = {
  proposal_id,
  candidate_plan_id,
  answered_at
}

The route is member-addressed data scoping, NOT caller identity authentication.

## 7. Resolution child

When aligned:
parent.status = ANSWERED

Create child via create_mission(parent_mission_id=parent.id).

Copy bounds:
max_cost_delta_minor
max_loss_minor
max_schedule_drift_min
requested_autonomy

Store:
resolved_intent_json["collective_decision"] = {
  clarification_id,
  decision_epoch,
  selected_proposal_id,
  selected_candidate_id,
  policy
}

Do not copy one member's answer into current_explicit_mission.

## 8. accept binding

AgentGateway.accept_replan already has request.mission_id.

Pass that mission id into the internal accept implementation.

Internal helper loads server-owned collective resolution and validates:
- child parent matches;
- parent clarification RESOLVED;
- selected proposal == requested proposal;
- epoch fresh.

Then pass only server-derived resolved_decision to collective_mutation_gate.

No public request field for resolved_decision.

## 9. Approval ordering

Collective gate must run before approval can make a rejected target executable.

If selected proposal needs normal confirmation:
approval can be created/consumed only for that selected proposal.

An approval for the wrong proposal must not beat collective governance.

## 10. Final fixture

Use fresh provider-backed facts.

Do not make the final runtime depend on autonomous web-source discovery:
R27 already proved source-truth architecture.

It is acceptable to pre-ground a bounded candidate set through live provider/official-source product paths before Agent run, as long as:
- no fact values are manually injected;
- mission does not name the options;
- Agent discovers them using CityNexus tools.

Focus this strike on collective autonomy.
