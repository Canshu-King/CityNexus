# R27 final implementation delta — shortest safe path

## 1. Runtime preflight assertions

Add a small experiment helper or explicit checks:
- two MEMBER_IN_FORCE rows;
- owner preference non-empty;
- second-member preference non-empty;
- preferences differ;
- Journey ACTIVE before mediation;
- active PlanVersion exists.

Abort final run otherwise.

## 2. Refactor fact acquisition provider ordering

Current:
Overpass -> Nominatim -> official.

Required:
exact ref
-> attempt Overpass
-> attempt Nominatim independently
-> establish identity evidence set
-> official source acquisition if at least one exact identity path survives.

Do not turn provider failure into fact success.
Separate identity authority from fact authority.

Recommended receipt fields:
identity_evidence
identity_authority
degraded_providers
fact_sources

## 3. Strong source precedence

Pseudo:

candidate_binding = requested candidate
stored_binding = validated stored strong binding

if stored strong:
    final_binding = stored_binding
else:
    final_binding = candidate_binding

source_url = final_binding.url if final_binding else provider-tag URL

For agent_observation:
server may upgrade candidate only after corroboration.

Never compute source_url before precedence resolution.

## 4. Collective fit subject

Helper:

plan_collective_fit_subject(base_plan, candidate_plan)

Return changed optional Place IDs and tags.

If multiple changed optional experiences:
include all changed optional IDs, but exclude unchanged shared places.

If no meaningful delta:
mark NO_COLLECTIVE_DECISION_SUBJECT rather than pretending the full plan is the choice.

## 5. Persist or reconstruct candidate set

collective mutation gate must know the exact candidate set that produced mediation.

Use one of:
- current sibling candidate PlanVersions from same parent/solve epoch;
- server-persisted candidate IDs in mission decision receipt.

Do not accept model-supplied arbitrary comparison set at mutation time.

## 6. Shared decision in JourneyMission

Prefer reusing clarification_json.

Example:

{
  "kind": "COLLECTIVE_TRADEOFF",
  "policy": "MATERIAL_TRADEOFF_REQUIRES_ALL_RELEVANT_MEMBER_RESPONSES",
  "decision_epoch": "...",
  "candidate_plan_ids": ["p1", "p2"],
  "required_member_ids": ["m1", "m2"],
  "responses": {
     "m1": {"candidate_plan_id": "p1", "answered_at": "..."}
  },
  "status": "WAITING_FOR_MEMBERS",
  "selected_candidate_id": null
}

No second social framework.

## 7. Epoch fingerprint

Include:
- journey_id
- active_plan_version_id
- candidate plan IDs + authoritative fingerprints
- in-force member IDs
- role names/capabilities
- member preference payload hashes

If any changes:
STALE.

## 8. Mutation gate location

Call collective gate BEFORE:
- creating/consuming action approval for an unacceptable target where possible;
- _accept_replan_impl;
- _switch_active_plan_atomically.

A normal approval must not override unresolved collective tradeoff.
Approval authorizes mutation authority, not preference truth.

## 9. Agent runtime contract

If generate_plans returns HUMAN_TRADEOFF_REQUIRED:
Agent can call one bounded tool:
request_collective_decision

Server derives candidate IDs / members.

If COMPROMISE_AVAILABLE:
Agent should not ask members; it should act on acceptable compromise or explain blocker.

If INSUFFICIENT_WORLD_FACTS:
acquire facts.

If AUTHORITY_CONFLICT:
do not ask preference questions; surface authority conflict.

## 10. Report correction

Update existing R27 report:
- correct the owner-preference claim from the failed checkpoint;
- name the SQLite machine state;
- distinguish failed checkpoint from final closure.

Do not erase the failure; preserve it as provenance.
