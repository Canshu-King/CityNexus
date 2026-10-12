# Revolution R43 — Autonomous Journey Operator v1

## Product answer

CityNexus newly learns to carry one Journey disruption from normal sensing to a user-facing decision boundary, then continue the exact approved action without asking the user to stitch Guardian, Agent, proposal, and approval screens together.

## Implemented product loop

- `POST /api/v1/journeys/{journey_id}/operator/start` creates or reuses the standing mission, binds the requested autonomy, enables Guardian Autopilot, and returns the Operator projection.
- `GET /api/v1/journeys/{journey_id}/operator` joins durable Journey, mission, enrollment, incident, Guardian, proposal, pending action, approval, active plan, and audit timeline rows.
- `POST /api/v1/journeys/{journey_id}/operator/stop` disables future watch/recovery while preserving history.
- Operator approval has a plain-language approve/reject surface. Approve uses the existing authenticated approval route and `resume_pending_action()`; it does not start another model run.
- Pending approval creates one `NotificationEvent` keyed by the durable approval id.
- Continuation reconciliation updates the linked Guardian run and exposes a short `RECOVERED` transition before the next pulse returns the projection to `WATCHING`.
- Raw Guardian/Agent traces are under `advanced`; the default projection contains ordinary user copy and a durable timeline.
- When Operator is enabled and Hermes/DeepSeek is unavailable, Guardian records `OPERATOR_EXTERNAL_AGENT_BLOCKED` and refuses deterministic fallback.

## Fresh product experiment

The fresh Journey used the normal product paths: plan generation and selection, Journey activation, one Operator start, one `LAB_FIXTURE`-labelled provider disruption through the Guardian fixture endpoint, and one Guardian pulse.

Result: `OPERATOR_EXTERNAL_AGENT_BLOCKED`.

The configured external Agent was not available in this environment (`DeepSeek API key is not configured`). The pulse created exactly one provider-backed closure Event through the normal signal pipeline, retained Autopilot enrollment, created no AgentRun or proposal, and did not fabricate recovery. `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` remained in force.

Machine artifact: `backend/output/r43-autonomous-journey-operator-v1.json`.

## Validation

- `backend/tests/test_r43_operator_loop.py` — 3 passed
- `backend/tests/test_operator_projection.py` — 8 passed
- `backend/tests/test_r28_durable_approval_continuation.py` — 7 passed
- compileall passed
- frontend TypeScript typecheck passed
- Focused `frontend/e2e/r43-journey-operator.spec.ts` was added; execution was blocked before browser assertions because the Playwright backend launcher selected Python 3.10, whose stdlib lacks `enum.StrEnum`.

The focused R43 test set covers one-click start/stop, Operator timeline, normal fixture sensing, external-agent blocking, no deterministic fallback, and rejected approval projection. Existing durable continuation tests remain green after notification/reconciliation integration.
