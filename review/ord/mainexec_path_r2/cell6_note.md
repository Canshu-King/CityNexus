# ORD main-exec-path, cell 6 — swept every gateway handler for the fake-gate shape; none left

Domain ownership rule, rule three: when a cell finds nothing new, widen the coverage instead of stopping.
Cell 5 found and removed a fake gate in my own tool (a DENY branch that could never fire). Cell 6 asks the
same question of every handler in the gateway, so the answer is a sweep, not a spot check.

## The sweep

Instrument: `handler_refusal_reachability_r2.py` (read-only). For each of the twelve dispatch handlers it
reads which `AgentAction` the handler evaluates and what refusal branches it has, then **runs the policy** with
the tightest envelope the product can express (auto-accept off, zero cost/loss/drift, no allowed types) to get
the decision that action resolves to in each mode. Receipt: `handler_refusal_reachability_r2.txt`.

| handler | policy action | decision (ADVISORY/ASSISTED/AUTONOMOUS) | other refusals |
|---|---|---|---|
| inspect_journey / inspect_twin / list_replans | (read, no policy) | — | none (pure reads) |
| search_city_services | (read, no policy) | — | 422 |
| request_replan | REQUEST_REPLAN | ALLOW_AUTO ×3 | 404, 422 |
| report_disruption | REPORT_DISRUPTION | ALLOW_AUTO ×3 | 422 |
| accept_replan | ACCEPT_REPLAN | DENY ×3 (tight) | 403, 404, 409, 422 |
| replace_activity | REPLACE_ACTIVITY | DENY ×3 | 404, 409, 422 |
| reschedule_activity | RESCHEDULE_ACTIVITY | DENY ×3 | 422 |
| create_booking | CREATE_BOOKING | DENY ×3 | (via shared path) |
| cancel_refundable_booking | CANCEL_REFUNDABLE_BOOKING | DENY ×3 | 404, 422 |
| request_commitment_change | REQUEST_COMMITMENT_CHANGE | DENY ×3 | 404, 422 |

## What it decides

The fake-gate shape is: the handler's *only* refusal is an unreachable policy DENY. No handler has that shape
now.

- The two actions that resolve ALLOW_AUTO in every mode — `REQUEST_REPLAN` and `REPORT_DISRUPTION` — cannot be
  refused by policy. `request_replan`'s refusals are 404/422 (a missing journey, a missing trigger event); they
  are reachable argument validation, not a fake policy gate. `report_disruption`'s only refusal is the 422 for
  a missing type/reason; also reachable. Both are gated by the allowlist, which is real.
- The typed mutations resolve DENY under the tight envelope, so their policy refusals are reachable; they also
  carry their own argument/target refusals. No dead branch.

So `report_disruption` was the only same-shape defect, and cell 5 already removed it. Cell 6's finding is the
negative result with a full denominator: **12 of 12 handlers swept, 0 further fake gates.**

## Two instrument fixes made in this cell (recorded, not hidden)

- First pass attributed 5 typed handlers to `(none)`: their action reaches the policy through
  `_run_typed_mutation(..., action=AgentAction.X)`, not a literal `evaluate_action(...)` in the body. The
  scanner now reads that form too.
- Second pass still missed them because `body_of` stopped at the *nested* `def execute()` inside a handler. It
  now stops only at method-level `def`s. Both were blind spots that would have let the sweep claim "all clear"
  while seeing 7 of 12 — the exact failure mode this domain guards against.

## Next cell (self-assigned, widen again)

The sweep reads refusals in the handler bodies. The next layer out is the refusals that live *outside* the
bodies: the shared `_run_typed_mutation` / `_bound_authorization` path and the `_require_journey` / `_typed_*`
helpers. Cell 7 asks whether any refusal in that shared layer is unreachable — a dead gate there would affect
every typed tool at once.

## Boundary

Read-only in this cell (no product bytes). Branch only; no authority moved.