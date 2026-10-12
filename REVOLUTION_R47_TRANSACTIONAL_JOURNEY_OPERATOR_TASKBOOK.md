# REVOLUTION R47 — Transactional Journey Operator

## Product-direction gate

This task is governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

The required product answer is:

> **CityNexus newly learns to finish the external work behind an approved trip recovery: execute the required booking/commitment actions through explicit sandbox/provider tools, track partial completion, stop safely on failure, and return to Journey monitoring only when the operational work is actually done.**

If implementation becomes “add a real Booking.com integration” or “prove old booking APIs”, stop and correct course.

## Starting truth

R46 is complete at `31ffac622003f3337dd8ca89c2d7a088b415dacf`.

R46 proved the Agent can expand a narrow recovery surface through bounded open-world discovery and feed normal server planning.

Do not rerun R33-R46 historical closures.

## Existing capabilities to connect — do not reimplement

The repository already has:
- AgentAction CREATE_BOOKING / CANCEL_REFUNDABLE_BOOKING / PAYMENT / REFUND vocabulary;
- Booking, PaymentTransaction, Commitment and ProviderCall;
- commerce service functions for booking creation/cancellation and payment capture;
- Agent policy / ActionApproval / AgentPendingAction;
- R43 approval continuation;
- R44 resilient Operator brain;
- R46 open-world discovery;
- mock/sandbox booking providers.

Today Agent booking actions still route through `_mock_booking_provider()`.

That is acceptable for this lab slice only if the product labels it honestly as SANDBOX/LAB execution.

R47 is not a claim of live merchant connectivity.

## 1. Recovery execution plan

After the Agent chooses a recovery and before external transaction execution, create one server-owned **RecoveryExecutionPlan** / semantic equivalent.

It should describe an ordered set of operational actions required to make the approved recovery real.

Example:

```json
{
  "actions": [
    {"kind": "CANCEL_BOOKING", "booking_id": "..."},
    {"kind": "CREATE_BOOKING", "activity_id": "..."}
  ]
}
```

The model may propose intent, but the server resolves exact ids and action facts.

Do not accept model-supplied external refs, prices, cancellation guarantees, or provider success claims.

## 2. Saga semantics

Transaction execution is not one boolean mutation.

Suggested execution states:
- PLANNED
- WAITING_FOR_APPROVAL
- EXECUTING
- PARTIALLY_APPLIED
- COMPLETED
- FAILED_SAFE
- NEEDS_ATTENTION

Each action should have:
- semantic idempotency key;
- target;
- authority decision;
- status;
- provider/sandbox provenance;
- result reference;
- error classification.

Repeated continuation must not double-book or double-cancel.

## 3. Authority

External booking/payment actions use the existing policy/approval gates.

Do not let approval of a PlanVersion automatically authorize every commerce side effect unless the server-owned approval scope explicitly covers them.

Preferred v1:
- recovery proposal approval authorizes the plan change;
- each material commerce action is compiled into the frozen pending execution plan;
- if current AgentPolicy requires confirmation/step-up for the booking action, Operator presents one combined operational approval only when existing approval semantics permit a single scoped receipt;
- otherwise preserve separate required approvals.

Do not weaken current ActionApproval rules to make the demo smoother.

## 4. Sandbox provider boundary

R47 may use the existing mock provider as an explicit:

`LAB_SANDBOX_PROVIDER`

or equivalent provenance.

User copy must say:
> “Sandbox booking confirmed.”

Never:
> “Your real reservation is confirmed.”

ProviderCall / Booking rows must preserve sandbox identity.

Do not rename mock external refs into live merchant refs.

## 5. Plan vs operational completion

Critical product rule:

`active PlanVersion changed` does not mean `recovery fully executed`.

Operator needs an operational state.

Examples:
- Plan updated, booking pending -> APPLYING
- Old booking cancelled, new booking failed -> PARTIALLY_APPLIED / NEEDS_ATTENTION
- New booking confirmed -> RECOVERED / WATCHING

Do not close the recovery epoch simply because the plan switched if required commerce actions remain incomplete.

## 6. Compensation / safe failure

For v1, keep compensation bounded and honest.

Example:
- cancelling old refundable booking succeeds;
- creating new sandbox booking fails.

Do not silently restore a fake old booking.

Instead:
- execution state = PARTIALLY_APPLIED;
- Operator says what succeeded and what still needs attention;
- Agent may propose a new recovery under a new server-owned recovery decision if appropriate.

If an action is safely compensatable using an existing idempotent provider operation, allow it only through an explicit server-owned compensation step.

No improvised rollback.

## 7. Action order

The server should choose order based on reversibility / risk.

Prefer:
- secure replacement first when feasible before cancelling old booking;
- or cancel first only when provider/business constraints make that necessary and the user was told the risk.

Do not hard-code one universal order.

The Agent can express desired recovery; server commerce facts decide safe sequencing.

## 8. Commitment convergence

Successful booking/payment execution must update the existing Commitment truth through the existing commerce service.

Do not create a second “Operator commitment” layer.

After completion:
- new booking/commitment exists;
- cancelled booking's commitment is cancelled;
- Journey/Readiness sees the updated commitment truth.

## 9. Operator UX

Add an operational execution section.

Examples:

Before approval:
> “I found a recovery. It requires cancelling your old reservation and booking the new option.”

Executing:
> “Updating the trip and handling the reservation…”

Sandbox success:
> “Sandbox reservation confirmed. I’m watching the trip again.”

Partial:
> “I updated the plan and cancelled the old sandbox booking, but the replacement booking failed. I stopped before doing anything else.”

Show:
- what will be done;
- what needs approval;
- which actions completed;
- sandbox/live provenance;
- what failed.

Do not show raw ProviderCall payloads by default.

## 10. External Agent role

The external Agent owns:
- deciding that a booking action is useful for the recovery;
- selecting which approved recovery to pursue.

The server owns:
- exact Booking/Activity ids;
- provider availability;
- cancellation policy;
- price truth;
- action order safety;
- authority;
- idempotency;
- execution.

Do not let the model directly write Booking rows.

## 11. R44 continuity

If the model brain fails before execution plan is frozen:
- R44 resume applies.

Once a frozen operational execution plan exists and tool actions begin:
- do not hand the saga to another model to reinterpret mid-flight.
- server-owned executor continues/halts based on durable action state.

This is an important separation:
AI decides; server executes the approved frozen work.

## 12. Focused tests

Only tests needed for the new capability:

1. approved recovery can compile an exact operational action plan.
2. model cannot inject external refs/provider success.
3. same execution action is idempotent.
4. sandbox provenance is explicit.
5. plan mutation alone does not mark operational completion.
6. create booking success produces Booking + Commitment.
7. refundable cancellation updates Booking + Commitment.
8. failed replacement after successful prior action -> PARTIALLY_APPLIED.
9. partial failure does not fabricate rollback.
10. approval scope is enforced for each commerce action.
11. continuation after approval executes frozen plan without second model reasoning.
12. completed saga returns Operator to WATCHING.
13. R44 cross-model handoff is blocked once transaction tool steps exist.
14. TypeScript + focused Transactional Operator Playwright.

Do not rerun old commerce verifier campaigns unless a concrete defect blocks this loop.

## 13. One bounded R47 product experiment

Use one fresh Journey.

Use explicit LAB/SANDBOX commerce.

Product flow:

1. Operator ON.
2. one material LAB_FIXTURE disruption.
3. Agent chooses a recovery that changes a bookable activity.
4. server creates a recovery proposal and exact operational execution plan.
5. Operator shows what external work is required.
6. authenticated user grants required approval once where existing policy allows.
7. continuation executes the frozen plan.
8. sandbox booking/cancellation provider is called through normal commerce service.
9. Booking/Commitment truth changes.
10. Operator reaches COMPLETED/WATCHING or honest PARTIALLY_APPLIED/NEEDS_ATTENTION.
11. stop.

Do not:
- call commerce service directly from the harness;
- hand-write Booking rows;
- call sandbox results LIVE;
- retry a failed provider action to force success;
- run a second model after approval.

Valid outcomes:
- `TRANSACTIONAL_OPERATOR_SANDBOX_RECOVERED`
- `TRANSACTIONAL_OPERATOR_PARTIALLY_APPLIED`
- `TRANSACTIONAL_OPERATOR_BLOCKED_AUTHORITY`
- `TRANSACTIONAL_OPERATOR_PROVIDER_FAILED`
- `TRANSACTIONAL_OPERATOR_NO_ACTIONABLE_COMMERCE`

## Stop condition

Stop after one visible operational recovery experiment.

The user-visible capability must be obvious:

> **“CityNexus no longer stops after changing my itinerary. When an approved recovery requires a booking action, it can actually carry out the sandbox transaction through its tools, tell me exactly what succeeded, and keep managing the Journey.”**
