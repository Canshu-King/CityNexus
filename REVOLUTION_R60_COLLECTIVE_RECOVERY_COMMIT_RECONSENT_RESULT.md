# Revolution R60 — Collective Recovery Commit + Re-consent

## Result

**The server can now spend the current, server-selected collective recovery once through an authenticated Journey editor, and refuses stale consent by opening one fresh member decision round.** The traveler-facing recovery panel exposes that same narrow action and removes generic acceptance controls for proposals belonging to the collective incident.

This is a local server/domain and UI closure, not a fresh provider-backed Journey run. No external Agent or model was called, and no live-provider facts are claimed.

## Implementation

- Code commit: `a3549f91eab04790bb3eda4bb6411a70b299fb7e`
- Branch: `gpt/revolution-r33-open-world-journey-adaptation`
- Apply endpoint: `POST /api/v1/journeys/{journey_id}/group-recovery/apply`
- The request body is strict and empty. The server resolves the signed Traveler principal, current in-force JourneyMember, and `JOURNEY_UPDATE`; it derives the incident, current room, selected proposal, receipt, and RecoveryEpoch itself.
- Generic proposal acceptance refuses collective-recovery proposals. Successful apply goes through the existing replan acceptance path and writes an authenticated spend audit with member/role, receipt, epochs, and before/after PlanVersion IDs.
- An idempotency key is scoped to Journey and authenticated Traveler. Replay returns the durable original result and does not create a second plan transition.
- If decision/member/material authority is stale before spend, the old clarification is retained as `STALE` with its responses, its receipt is invalidated, and the server creates or reuses one successor round with a new clarification/epoch and empty responses. Current required signers are recomputed from in-force members and `JourneyRoleCapability`.

## User-visible behavior

- The current selected shared recovery is shown once; its sibling proposals are not exposed as ordinary individual “Accept” actions.
- A current `JOURNEY_UPDATE` viewer sees **Apply shared recovery**. A read-only member sees that the group agreed and the Journey editor must apply it.
- After successful apply, the panel reports completion only from the persisted spend audit whose after-plan is still active.
- After stale consent, the panel says the previous choice expired, shows the fresh round and its unanswered options, and does not offer the old apply action.

## Verification

- Focused backend lineage: **49 passed** across R60 apply/re-consent, R59 collective recovery room, R29 disagreement/authority, and R27 collective mediation tests.
- Python `compileall`: passed.
- Frontend TypeScript check: passed.
- Frontend production build: passed. Vite emitted the existing large-chunk advisory; no build failure.
- R60 two-context Playwright: **2 passed** (authorized apply/shared refreshed state; stale choice/fresh round). The UI API is mocked in these browser tests; signed principal and database behavior are exercised in backend tests.
- `git diff --check`: passed.

The backend route tests use the real HTTP endpoint, signed-principal resolution, database rows, and replan mutation path. The focused successful apply fixture substitutes the collective receipt/preflight and feasibility seam to isolate the commit transition. The stale capability-loss case calls the real `_collective_resolution_for_child` and derives a new round after the ADMIN `JOURNEY_UPDATE` capability is removed; its bounded proposal-surface fixture is seeded. These tests do not replace live provider evidence.

## Live-provider / Agent evidence

- Fresh provider-backed Journey ID: **none created in this checkpoint**.
- Live member IDs/roles, selected proposal, clarification, receipt, and before/after active PlanVersion: **not applicable to a product run**. Backend tests create disposable randomized rows only; no live-run identifiers are reported as product evidence.
- Provider provenance: **none**. Candidate rows in the backend fixtures are deterministic seeded test data; mobility/feasibility are not represented as live provider truth.
- External Agent status: **not invoked**, as required for this relay validation.
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY`: shell override unset; application configuration defaults it to `false`.

## Boundary

R60's authenticated, exactly-once apply and stale re-consent seams are implemented and locally exercised. A fresh provider-grounded shared Journey and real-Agent mediation-to-apply run remain unclaimed; this result does not say that a real-world group trip was executed.
