# R53 — Journey Inbox / Live Reservation Change Intake

> **The traveller can now forward a booking confirmation, schedule-change message, cancellation notice, or reservation screenshot to the running Journey, and CityNexus turns it into grounded Journey reality: it binds the message to the right reservation/activity, updates Commitment truth only when sufficiently grounded, asks one clear question when ambiguous, and automatically hands any material impact to the existing Journey Operator for recovery.**

## Result

Shipped a first-class durable Journey Inbox item and an authenticated Operator intake route for pasted reservation updates. The server fingerprints normalized text for replay safety, extracts a bounded confirmation reference and explicit departure times, and only mutates a confirmed reservation after exact reference matching and an old-value check. The update preserves provenance as `USER_PASTED_TEXT`, syncs the linked Commitment, records a user-reported `SCHEDULE_DELAY` event for material impact, and hands that event to the existing Guardian. Weak matches are kept for review and offered as server-owned reservation choices in the single Needs-you card. The Operator now shows the latest inbox update and provides a booking-message input.

The implementation does not claim live email ingestion. Screenshot upload and cancellation parsing remain represented by source/provenance and v1 semantics, but the bounded proof is the taskbook's exact structured pasted schedule-change path.

## Bounded product experiment

- Fresh Journey with Operator enabled and current Activity `IN_PROGRESS`.
- Imported a future train reservation (`AB123`) through the existing reservation import/confirmation API, with a linked protected Commitment at 17:40.
- Submitted once: `Booking ZX42 update: departure changed from 17:40 to 18:10. Confirmation AB123.`
- Exact `AB123` binding updated both reservation and Commitment to 18:10; current Activity ID and execution status remained unchanged.
- The 30-minute protected schedule change became `RECOVERY_REQUIRED`, created one `USER_REPORTED` event, and entered the normal Guardian path. Guardian recorded `OPERATOR_EXTERNAL_AGENT_BLOCKED` because the external planning Agent was unavailable in this environment; no recovery AgentRun was fabricated.
- Replayed the same message once. It returned the same inbox item and created no additional inbox row, event, reservation, or commitment.
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.

Machine receipt: [backend/output/r53-journey-inbox-v1.json](backend/output/r53-journey-inbox-v1.json).

## Focused verification

- `python -m compileall -q backend/app/main.py backend/app/operator_projection.py backend/app/operator_attention.py backend/app/db/models.py backend/app/journey_inbox.py` — passed.
- `pytest -q backend/tests/test_journey_inbox.py` — 8 passed.
- `pytest -q backend/tests/test_r53_journey_inbox_product.py` — 1 passed.
- `cd frontend && npm run typecheck -- --pretty false` — passed.
- Isolated focused Playwright run (`r53-journey-inbox.spec.ts`, authoritative Python 3.13 server) — 1 passed.
