# Revolution R45 — Collective Journey Operator

## Product result

CityNexus now exposes one Journey-level Operator with a viewer-specific collective projection. A signed traveler principal is resolved to the exact in-force `JourneyMember`; the URL member id is never trusted as identity. Each affected member sees the same durable recovery context and only their own response affordance.

The Operator now renders grounded recovery options, response progress, waiting members, mediation state, stale state, authority state, and collective timeline entries. Responses continue through the existing `/collective-clarification/{member_id}` path. The server still owns candidate facts, decision epochs, role capabilities, `CollectiveAuthorityReceipt`, and the final Gateway/continuation mutation preflight.

There is still one standing mission and one Autopilot enrollment per Journey. Starting the Operator from another in-force member reuses that Journey-level mission rather than creating a second control plane. Member notifications use `journey + decision_epoch + member` dedupe keys. R44 recovery rows remain durable, so an external brain outage does not discard a collective clarification or member responses.

## Focused implementation

- `backend/app/collective_operator.py` now builds the collective state projection, exact active-member checks, stale capability/epoch handling, mediation child linkage, and durable collective timeline.
- `backend/app/operator_projection.py` includes the projection and merges collective audit moments into the normal Operator timeline.
- `backend/app/main.py` resolves signed viewer identity for `GET /operator`, allows an in-force capable member to reuse the shared Operator, and records authority issuance in the timeline.
- `backend/app/agent/gateway.py` records one deduped notification per relevant member and decision epoch when a server-derived collective decision opens.
- `frontend/src/api/citynexus.ts` and `frontend/src/features/execution/LiveRecovery.tsx` make the Operator the normal member response surface.

## Fresh product experiment

The machine artifact is [`backend/output/r45-collective-journey-operator-v1.json`](backend/output/r45-collective-journey-operator-v1.json).

Experiment facts:

- fresh demo Journey with the normal plan generation, World Context fixture, Guardian pulse, one OWNER, and one in-force ADMIN member;
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`;
- Guardian observed one `LAB_FIXTURE` closure and preserved one Journey-level standing mission;
- server-derived replan surface contained only one grounded feasible candidate, so the existing Gateway correctly refused to open a collective trade-off with `COLLECTIVE_TRADEOFF_NOT_REQUIRED`;
- no candidate, receipt, mediation output, active plan, or majority decision was hand-written;
- active plan mutation count remained zero.

The honest product result is `COLLECTIVE_OPERATOR_NO_COMPROMISE`. The code path is ready for a multi-option grounded trade-off; this fixture's candidate surface did not supply one, so the experiment stopped at the server-owned boundary rather than manufacturing a group choice.

## Validation

- Backend focused suites: 20 passed for collective/operator/brain helpers, plus the isolated R44 resilient-resume file (3 passed).
- Python compileall: passed.
- Frontend TypeScript check: passed (`npm run typecheck`).
- Playwright collective UI was attempted; the existing environment's system Python 3.10 launcher is missing `enum.StrEnum`, so the backend web server stopped before browser assertions.

## Commit

Pending final R45 commit and push on `gpt/revolution-r33-open-world-journey-adaptation`.
