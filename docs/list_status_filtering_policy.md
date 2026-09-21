# CityNexus Server-Side Status Filtering Policy

Status: arbiter contract note for Journey-scoped PlanVersion and ReplanProposal collection endpoints.

## 1. Ownership decision

Create **one backend/product order owned by lane C** for the two sibling list endpoints:

    GET /api/v1/journeys/{journey_id}/replans
    GET /api/v1/journeys/{journey_id}/plans

Recommended order:

    ORD-0181 — Server-Side Status Filtering for Plans and Replans

This is one contract gap expressed on two closely related collection endpoints.

Do not split it into two unrelated tickets unless implementation evidence later shows different owners or incompatible semantics.

## 2. Backend owns the filter contract

Frontend filtering may be used only as a temporary compatibility bridge.

It is NOT sufficient as the final fix because:

- other consumers (Hermes, Agent flows, tests, future clients) also need the same query semantics;
- actionability/state truth already lives on the server;
- client-only filtering requires downloading historical/non-actionable rows and re-encoding state vocabulary in each consumer;
- server-side filtering makes the requested collection semantics replayable and testable at the API boundary.

Therefore acceptance requires the backend endpoint itself to honor the status filter.

## 3. Backward-compatible query shape

Preferred shape:

    ?status=PRESENTED
    ?status=PRESENTED&status=GENERATED

and, for plans:

    ?status=CANDIDATE
    ?status=ACTIVE&status=SELECTED

Equivalent framework-native repeated-query syntax is acceptable.

Rules:

- status omitted -> preserve current behavior and return all Journey-scoped rows;
- one status -> return only that status;
- multiple statuses -> OR semantics within the same entity type;
- valid status with zero rows -> 200 + empty list;
- invalid status -> typed validation failure (normally 422), never silently ignored;
- status filtering happens in the database query, not after fetching all rows;
- Journey ownership/scope predicate remains mandatory and is combined with status using AND.

## 4. Entity-specific status vocabularies

Do not invent one fake shared enum.

### ReplanProposal

Allowed values are the existing ReplanProposal API states:

    GENERATED
    PRESENTED
    ACCEPTED
    REJECTED
    EXPIRED
    INVALIDATED

### PlanVersion

Allowed values are the existing PlanVersion API states:

    CANDIDATE
    SELECTED
    ACTIVE
    SUPERSEDED
    REJECTED

The two endpoints share filtering behavior, not one status vocabulary.

## 5. Ordering must remain deterministic

Filtering must not alter the existing deterministic ordering contract.

- replans: preserve the endpoint's current created-at ordering unless a separately approved contract changes it;
- plans: preserve current version_no ordering.

A status filter narrows a collection; it does not silently redefine ordering.

## 6. Actionability and UI use

For the review panel / ORD-0180:

- request actionable replan rows from the server, e.g. status=PRESENTED;
- do not treat client-side status filtering as the authoritative queue contract once ORD-0181 is available;
- mutation actions still revalidate state at the mutation endpoint. A filtered list is a view, not an authorization token.

For plans:

- UI surfaces should request the server-side subset they actually mean (for example CANDIDATE, ACTIVE, or a deliberate union);
- the list filter must never replace select/accept feasibility and state-transition guards.

## 7. R14 interaction

Status filtering itself is primarily a collection/query contract, not a new causal-attribution system.

However:

- invalid filter input must not be silently discarded;
- if the server ignores an unsupported status and returns 200/all rows, that is the same forbidden family as "parameter discarded is not boundary honoured";
- the response or validation layer must make the effective query semantics observable.

## 8. Minimum acceptance gates

1. Replans with no status query preserve the current full-list behavior.
2. Replans status=PRESENTED returns only PRESENTED rows.
3. Replans repeated status query returns the union of requested valid states.
4. Plans with no status query preserve the current full-list behavior.
5. Plans status=CANDIDATE returns only CANDIDATE rows.
6. Plans repeated status query returns the union of requested valid states.
7. Valid status with no matches -> 200 [].
8. Invalid status -> typed validation error; no silent fallback to all rows.
9. Cross-Journey rows are never returned even when status matches.
10. Existing deterministic ordering is preserved inside the filtered subset.
11. Accept/reject transition: after a PRESENTED replan is accepted/rejected, a fresh status=PRESENTED query no longer returns it.
12. Plan transition: after a plan changes status, filtered queries reflect the persisted current status on the next request.
13. Mutation: ignore/remove the replan status predicate while returning 200 -> replan filter gate RED.
14. Mutation: ignore/remove the plan status predicate while returning 200 -> plan filter gate RED.
15. Mutation: accept an invalid status but silently return the unfiltered list -> validation gate RED.

## 9. Non-goals

This order does not:

- add new PlanVersion/ReplanProposal states;
- replace state-transition validation;
- add pagination unless separately justified;
- create a generic repository-wide query DSL;
- force the frontend to stop rendering historical rows where a historical view is intended.

## 10. Freeze sentence

**Filter collection state at the server boundary; let clients choose the view, not redefine the truth.**
