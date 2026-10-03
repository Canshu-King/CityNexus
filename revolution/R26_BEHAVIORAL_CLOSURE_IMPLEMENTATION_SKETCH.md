# R26 behavioral closure — implementation sketch

## 1. Shared skip helper

Extract the mutation core of `skip_activity()` into one helper.

Suggested inputs:
- Session
- Journey
- Activity
- actor_type
- reason
- mission_id optional
- clarification_id optional

Keep the HTTP route as a thin wrapper.

## 2. Agent tool is clarification-scoped, not arbitrary

Add `apply_clarified_horizon_choice` to:
- tool catalog;
- runtime allowlist;
- Gateway dispatch.

Do NOT accept arbitrary activity_id.

Server resolves W1 from:
- child mission -> parent;
- parent.clarification_json;
- option_windows;
- current horizon.

## 3. Only mutate at W1-current epoch

For final proof, require:
- journey.current_activity_id == W1 activity;
- W1 status ACTIVE/NOT_STARTED before departure.

If W1 is already EN_ROUTE/ARRIVED, either refuse as stale or require explicit stronger user confirmation; do not silently teleport a traveler out of an activity.

## 4. Live direct edge after skip

Before commit:
- determine actual origin from latest completed/current execution location;
- determine next non-skipped activity routing key;
- if adjacency differs from frozen plan, use `capture_runtime_mobility_snapshot`;
- require LIVE_PROVIDER_CAPTURE/hard eligibility;
- persist compact execution override on the next activity metadata or another existing bounded evidence surface;
- store snapshot/provider/captured_at/origin/destination/minutes/cost semantics.

Do not edit PlanVersion.mobility_evidence_json.

## 5. Depart guard

When current activity has an execution mobility override caused by a skipped predecessor:
- verify override matches current plan + origin/destination;
- verify freshness/provider/hard eligibility;
- refuse depart if missing/stale.

This makes the actual used route authoritative.

## 6. Completion contract

Tool result should include:
- executed: true;
- mutation: ACTIVITY_SKIPPED;
- skipped_activity_id;
- next_activity_id;
- execution_mobility_snapshot_id;
- clarification_id.

Runtime completion contract should classify this as MUTATION_EXECUTED.

If child explicit strategy is DEFER and no such executed tool appears, mission cannot count as resolved.

## 7. Budget semantics

After W1 skip:
- W1 is not included in consumed-cost basis;
- optional budget remains available for W2.

After TAKE_NOW and W1 completion:
- W1 cost enters consumed-cost basis;
- horizon recomputes.

Add explicit receipts to prove this.

## 8. Learning semantics

A clarified strategic skip is not evidence that the traveler dislikes W1's category.

Keep/extend the R23 suppression rule using the skip reason/provenance.

## 9. Focused test sequence

Write tests before the rerun:
- shared helper parity;
- clarification-scoped mutation;
- route recapture;
- rollback on mobility failure;
- DEFER-without-mutation refused;
- TAKE_LATER vs TAKE_NOW execution divergence.

Then run one live closure.

No broad repeated reruns.
