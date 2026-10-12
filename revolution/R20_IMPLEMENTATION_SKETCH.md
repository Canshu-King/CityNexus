# R20 implementation sketch — shortest path

## 1. Do not rewrite R19 lifecycle if it is already server-enforced

The uploaded R19 report says `PlanVersion.lifecycle` is explicit and generic select refuses STANDBY.

If the local implementation genuinely enforces this with a real column/server contract, keep it.
Do not churn schema merely because R19 used lifecycle + CANDIDATE instead of putting STANDBY in status.

The R20 codebase is the local R19 head, not the stale remote branch.

## 2. Trigger contract storage

Smallest path:
- add `trigger_contract_json` to PlanVersion if schema migration is cheap;
- otherwise use an existing explicit structured lifecycle/portfolio field, but not free-form explanation prose.

A trigger contract should be stable enough for deterministic matching.

## 3. Shared matcher

Implement one matcher used by:
- portfolio projection;
- Agent tool;
- activation Gateway precondition;
- tests.

Possible result:
```text
MATCH
NO_EVENT
TYPE_MISMATCH
SCOPE_MISMATCH
PROVENANCE_MISMATCH
THRESHOLD_NOT_MET
PARENT_STALE
EVIDENCE_EXPIRED
```

Do not have the model infer these authority codes.

## 4. Build the second branch before the final event

Use current counterfactuals.

Prefer one weather + one closure branch.

For a closure branch:
- choose a mutable future activity;
- materialize the existing PLACE_CLOSURE simulation;
- retain/recompute live mobility as R19 already does;
- store trigger scope against the dropped/replaced Place.

If current counterfactual output only produces one materializable branch, generalize the bounded materializer; do not create bespoke scenario code for the chosen Nara run.

## 5. Agent context

Extend the existing compact `standby_portfolio` with:
- trigger family;
- readiness;
- expires_at;
- current-event match state;
- key diff;
- cost/schedule deltas.

The Agent should be able to discover the correct branch by inspection.

Do not send raw evidence matrices into the model.

## 6. Agent tool contract

`activate_standby` arguments should include:
- standby plan ID;
- trigger Event ID;
- normal approval context as already required.

The tool must not accept an Event ID that fails the shared matcher.

If no standby matches, the Agent should retain access to `request_replan`.

## 7. Negative control before the Agent run

Direct deterministic test/runtime call:
- choose the weather standby;
- pass the closure Event;
- assert named mismatch refusal and zero mutation.

This is not the main success path.
Run it once, then move on.

## 8. Real model run

Use a generic disruption-recovery mission.

Do not include the correct plan ID in:
- mission user text;
- system prompt customization;
- hidden wrapper metadata supplied to the model.

Persist the exact mission input or its safe structured summary so the report can prove no answer leakage.

## 9. Continue to completion

After activation:
- use existing execution endpoints;
- do not invent a special R20 fast path;
- walk the product state machine to COMPLETED in the disposable DB.

## 10. Focused tests

Add direct R20 tests for:
1. weather standby + closure => mismatch;
2. matching closure branch => eligible;
3. stale/expired/parent-invalid => refused;
4. generic select still refuses standby;
5. real Agent tool cannot bypass matcher/Gateway;
6. sibling standby parent invalidated after activation;
7. only one active/current plan after activation.

Then run the existing 35-test focused suite once.

No new harness.
