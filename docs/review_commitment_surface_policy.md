# CityNexus Review / Commitment Surface Consolidation Policy

Status: arbiter contract note for the user review -> confirm -> commitment experience.

## 1. Corrected problem statement

Do **not** describe the backend as having no approval/commitment capability at all.

Existing server-owned primitives already include, on the currently reviewed code line:

- a reservation draft confirmation route:
  `POST /api/v1/journeys/{journey_id}/inbox/{draft_id}/confirm`
  which creates/returns the authoritative reservation and its commitment; and
- an Agent action approval route:
  `POST /api/v1/journeys/{journey_id}/agent/approvals/{approval_id}/approve`
  which approves a scoped ActionApproval.

These are real backend capabilities.

The product gap is narrower:

> CityNexus lacks one coherent, discoverable, server-owned review surface that lets the UI list
> pending review items, understand allowed actions, execute the correct existing confirmation /
> approval primitive, and receive a canonical post-action state without the frontend guessing.

Therefore the remediation should reuse/consolidate existing server truth rather than invent a
parallel review state machine.

## 2. Ownership decision

Preferred product direction: **Option A**, implemented as a product/backend P1.

Recommended order:

    ORD-0178 — Canonical Review and Commitment Surface

Owner: backend/product lane C.

The frontend may consume the surface, but must not own business-state transitions.

## 3. Required model

Conceptually:

    pending review source
        -> server-owned review projection
        -> allowed_actions from server policy/state
        -> user chooses action
        -> existing canonical mutation primitive
        -> canonical resulting state

Candidate review sources may include:

- reservation/inbox drafts needing confirmation;
- Agent ActionApproval items requiring user confirmation/step-up;
- other commitment-management review items only if they already have a valid server mutation
  primitive and ownership model.

Do not collapse unlike review items into one database entity merely for UI convenience.

A unified surface can be a projection/facade over existing domain owners.

## 4. Canonical review projection

Each review item should expose machine-readable fields such as:

    review_id
    review_kind
    source_entity_type
    source_entity_id
    journey_id
    state
    reason_codes
    allowed_actions
    requires_step_up
    commitment_impact
    c4_affected
    created_at
    expires_at
    version / etag

Equivalent repository-native names are acceptable.

The UI must render enabled/disabled actions from this server projection rather than infer them.

## 5. Mutation routing

The review facade must delegate to existing authoritative mutation paths when they exist.

Examples:

- reservation draft CONFIRM -> existing inbox confirm path/domain service;
- Agent approval APPROVE -> existing ActionApproval approval service;
- commitment-changing action -> existing guarded Agent/domain operation if one exists.

Do not duplicate commitment creation logic inside a new review endpoint.

If an action has no real server mutation primitive, expose it as unavailable/not-implemented rather
than fabricating a successful review action.

## 6. Reject / dismiss semantics

Do not add a generic REJECT action unless its domain effect is defined.

For each review_kind, REJECT/DISMISS must specify whether it means:

- decline proposal/action;
- keep draft but mark reviewed;
- delete/cancel draft;
- leave underlying domain object unchanged;
- expire an approval.

These are not interchangeable.

The server must own the transition and audit it.

## 7. Commitment safety

Any path that creates, changes, or removes commitments must preserve existing commitment rules.

Hard requirements:

- C4/protected commitment rules cannot be bypassed;
- step-up remains required where policy says so;
- one ACTIVE-plan invariant remains intact;
- authorization principal remains server-resolved;
- idempotency prevents duplicate commitment/reservation creation;
- concurrent review actions resolve deterministically;
- resulting commitment is bound to the intended Journey/Activity/PlanVersion;
- audit records before/after, actor, review item, action, and correlation/idempotency identity.

## 8. R14 integration

The review surface is an R14 boundary.

It must distinguish at least:

- review item not found;
- review item already consumed/resolved;
- confirmation required;
- step-up required;
- action not allowed in current state;
- domain conflict;
- successful confirmation/approval;
- retryable runtime failure.

The UI may not translate all failures into "review unavailable" or "network unavailable".

Screen copy, aria-live, telemetry, and recovery action must consume the same machine reason.

## 9. Minimum acceptance gates

1. GET/list review surface returns only items belonging to the Journey/traveler scope.
2. Each item exposes server-owned allowed_actions.
3. Reservation draft CONFIRM routes to the existing authoritative confirm behavior and returns the
   resulting commitment.
4. Agent ActionApproval APPROVE routes to the existing approval behavior and preserves
   confirmation/step-up semantics.
5. Frontend does not enable an action absent from allowed_actions.
6. C4/protected commitment mutation without required step-up is rejected.
7. One ACTIVE-plan invariant remains unchanged by review actions.
8. Duplicate/replayed confirm is idempotent or returns the defined deterministic conflict, never a
   second commitment.
9. Stale/replayed approval cannot mutate a different target.
10. Review result includes a stable machine state/reason consumed consistently by UI/aria/telemetry.
11. Audit records actor, review kind, source entity, action, before/after, and correlation.
12. Mutation: frontend hard-codes an action not returned by server -> UI contract gate RED.
13. Mutation: bypass step-up/C4 protection -> server gate RED.
14. Mutation: duplicate confirm creates a second commitment -> idempotency gate RED.
15. Mutation: facade reimplements commitment creation instead of delegating to authoritative
    service -> ownership/architecture gate RED.

## 10. Non-goal

This order is not a license to create a broad new workflow engine.

The goal is to make existing server-owned confirmation/approval capabilities coherent,
discoverable, and consumable without frontend guesswork.

## 11. Freeze sentence

**One review surface, existing domain owners, server-owned allowed actions, no frontend guessing.**
