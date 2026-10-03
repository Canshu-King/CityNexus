# R26 implementation sketch — shortest path

## 1. Tighten horizon feasibility with existing primitives

Do not keep `GROUNDED` as a proxy for feasible.

Reuse:
- OpportunityWindow;
- evaluate_window_replacement / existing deterministic feasibility;
- canonical cost/opening;
- frozen route evidence for planning-only inspection.

Add compact fields per horizon item:
- `grounding_status`;
- `hard_feasibility.passed`;
- `hard_feasibility.failures`;
- `commitment_slack_min`;
- `opening_fit`;
- `resource_fit`.

Gateway DEFER must require hard_feasibility.passed on both options.

## 2. Reserve only unavoidable future monetary obligations

Add helper:

`reserved_future_commitment_cost_minor(session, journey, activities)`

Include only:
- locked/protected paid activity cost;
- active C3/C4 commitment monetary obligations;
- confirmed booking/payment amounts that are unavoidable.

Avoid double counting.

Expose the total and component IDs in optional_budget_basis.

## 3. Decision sensitivity can be deterministic

For two actions A/B:
- compute current effective soft preference;
- identify differentiating canonical categories/tags;
- recompute ranking under bounded explicit preference A and explicit preference B;
- if top action flips => decision_sensitive.

The counterfactual preference is analysis only.
Do not persist it as user truth.

## 4. Add a tiny clarification persistence seam

Preferred minimal schema addition to JourneyMission:
- `clarification_json` Text default `{}`;
or one tiny `JourneyClarification` table if migration cleanliness is clearly better.

Do NOT overload `unresolved_references_json`; that field means entity grounding failure.

Mission statuses:
- CREATED
- RUNNING
- WAITING_FOR_USER
- COMPLETED / existing terminal states

Additive only.

## 5. Extend conclude_recovery

Add typed outcome:
`CLARIFICATION_REQUIRED`.

Arguments:
- question;
- option_keys;
- preference_dimension.

Server fills/validates the actual option/action mapping from decision sensitivity.

Model cannot invent authoritative candidate IDs in the clarification.

Completion contract:
- valid persisted clarification => CLARIFICATION_REQUIRED;
- prose without persisted server validation => UNRESOLVED.

## 6. Answer endpoint

Small endpoint, conceptually:

`POST /api/v1/journeys/{journey_id}/missions/{mission_id}/clarification`

Body:
- clarification_id;
- option_key;
- scope: THIS_JOURNEY | REMEMBER_FOR_FUTURE_TRIPS.

Server:
- validates traveler/journey ownership;
- checks clarification not stale;
- maps option to explicit preference;
- stores journey-scoped explicit mission preference;
- optionally persists explicit cross-Journey preference only when scope says remember;
- creates a child JourneyMission with parent_mission_id;
- carries original authority bounds;
- starts/returns the resumed mission through existing runtime.

No free-form authority expansion.

## 7. User answer should not widen mission bounds

Child mission resolved_intent:
- max_cost_delta <= parent;
- max_loss <= parent;
- max_schedule_drift <= parent;
- autonomy <= parent;
- protected IDs preserved.

The answer influences preference/ranking only.

## 8. Clarification staleness fingerprint

Store:
- active_plan_version_id;
- current_activity_id;
- decision option IDs;
- snapshot/fact freshness IDs.

On answer:
- if fingerprint changed materially, reject with `CLARIFICATION_STALE_RECOMPUTE_REQUIRED`.

## 9. Real-model proof

Mission text should NOT tell the model to ask.

Natural instruction:
"Use the remaining trip well while preserving commitments and budget. Act only when the decision is grounded."

The model sees:
- two options;
- sensitivity receipt;
- weak/conflicted learned context.

It should choose the clarification tool/outcome.

If it guesses TAKE/DEFER despite decision-critical uncertainty, server may refuse autonomous value-sensitive mutation and return `HUMAN_VALUE_CLARIFICATION_REQUIRED`.

This keeps the authority invariant even if the model is overconfident.

## 10. Do-not-bother control

If `decision_sensitive=false`, server rejects CLARIFICATION_REQUIRED.

The model then proceeds with normal action/no-action.

## 11. Focused regressions

1. horizon grounded but opening-infeasible => DEFER rejected.
2. horizon grounded but slack-infeasible => DEFER rejected.
3. unavoidable future commitment cost reduces optional budget.
4. optional future activity cost is not pre-reserved.
5. explicit mission already resolves choice => no clarification.
6. learned conflict + action flips under explicit A/B => sensitivity true.
7. same action under both answers => sensitivity false.
8. factual unknown => provider acquisition path, not clarification.
9. valid clarification persists WAITING_FOR_USER.
10. prose-only clarification is not machine completion.
11. stale clarification answer rejected.
12. child mission authority <= parent authority.
13. THIS_JOURNEY answer does not write cross-Journey memory.
14. REMEMBER scope may persist explicit preference.
15. opposite answers flip strategy under same hard facts.
16. R20-R25 focused lineage passes once after implementation.

No new harness.
