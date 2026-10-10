# REVOLUTION R52 — Quiet Operator / Decision Inbox

**The traveller can now hand the Journey to CityNexus and stop supervising every subsystem. The Operator works quietly by default and surfaces one unified, prioritized “Needs you” decision only when it cannot safely continue without the traveller; once the traveller responds, the original Journey flow resumes automatically.**

## Delivered

- GET `/api/v1/journeys/{journey_id}/operator` now includes a read-only `attention` projection derived from existing approvals, collective decisions, transaction state, route/milestone state, morning state, and JourneyIntent state. It chooses one primary item by server-owned priority and reports `null` when no source needs the traveller.
- Active and unresolved JourneyIntents are visible only to their creating traveller in the Operator projection. Existing source authority remains responsible for approvals, group responses, route checks, execution transitions, and transaction review.
- Deterministic fallback clarifications persist a question and bounded choices with the original JourneyIntent. The clarification endpoint accepts only a persisted option, updates that same row, preserves its source text and scope, creates one child evaluation mission, and rejects a second answer.
- The Operator UI presents one “Needs you” block with the source action. Repeated approval, collective, route, and execution buttons are suppressed when the same action is promoted there; Now, Looking ahead, and Overnight remain in place. QUIET is the projection default.

## Bounded experiment

With `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`, a fresh demo Journey was started with its Operator enabled. One original request — “I'm tired. Make the rest of today easier and keep walking low.” — entered `NEEDS_CLARIFICATION` through the deterministic fallback. Two Operator GETs returned the same single `INTENT_CLARIFICATION_REQUIRED` item and the same bounded options. One `LESS_WALKING` answer updated the same JourneyIntent id to `ACTIVE`, retained `REST_OF_TODAY`, stored the answer, and created one linked evaluation mission. The current Activity stayed unchanged. The configured runtime boundary raised `AgentRuntimeUnavailable`; the result was reported as `DECISION_INBOX_BRAIN_BLOCKED_AFTER_RESPONSE`. A repeated answer returned HTTP 409. No request was resubmitted and no second JourneyIntent was created.

This is an isolated application-level experiment with a deterministic unavailable-runtime adapter; it does not claim a live external model call.

## Verification

- `backend/.venv/Scripts/python.exe -m pytest tests/test_operator_attention.py tests/test_r52_decision_inbox.py -q` — 11 passed.
- `npm run typecheck` — passed.
- `npm run test:e2e -- e2e/r52-operator-attention.spec.ts --project=chromium --no-deps` — 1 passed with isolated ports and database.
- `git diff --check` and Python `compileall` — passed.

Machine-readable result: `backend/output/r52-quiet-operator-decision-inbox-v1.json`.
