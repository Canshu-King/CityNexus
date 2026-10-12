# R54 — Reality Reconciliation / Source Conflict Resolver

> **When CityNexus receives conflicting travel facts from different sources, it no longer silently overwrites reality or follows “last write wins.” It reconciles source authority and freshness, freezes unsafe automation when the truth is genuinely contested, asks the traveller one bounded question only when needed, and resumes the same Journey once reality is resolved.**

## Result

Added a durable, domain-scoped `RealityClaim` and `RealityConflict` path for `RESERVATION_TIME`. R53 pasted schedule changes now pass through reconciliation before changing reservation or Commitment truth. A newer user message can temporarily beat an older replay; a fresh opposite replay opens one material conflict generation and leaves current reservation truth untouched. While unresolved, further schedule updates for that reservation are held, and the unified R52 Needs-you card offers the server-bound claims once.

The traveller’s “Use 18:10” selection resolves that same generation. CityNexus records the selection as `USER_CONFIRMED_REALITY_RESOLUTION`, preserves the underlying source claims, and then continues the existing impact/Guardian path. It does not relabel the selection as provider evidence. The provider-side evidence used here is a server-stored `ProviderObservation` marked `REPLAY` / `CAPTURED_REPLAY`; it is explicitly not live.

## One fresh product experiment

- Started a fresh Journey with a future train `AB123`, Operator enabled, and current Activity `IN_PROGRESS`.
- Stored an older exact 17:40 provider replay, then submitted the R53 pasted 18:10 update. Domain policy selected the newer user claim temporarily and updated the reservation.
- Added a fresh exact provider replay still saying 17:40. Reconciliation returned `UNRESOLVED_MATERIAL_CONFLICT` and opened generation 1. Reservation stayed at 18:10; this conflict added no Event or Guardian run. The Operator exposed one `REALITY_CONFLICT_REQUIRED` item with “Use 18:10” and “Keep 17:40”.
- Selected “Use 18:10” once. The same conflict generation resolved, Reservation/Commitment provenance became `USER_CONFIRMED_REALITY_RESOLUTION`, and the current Activity remained unchanged.
- After resolution, the normal Guardian path ran. The local planning Agent was unavailable, so Guardian reported `PARTIAL / OPERATOR_EXTERNAL_AGENT_BLOCKED`; no recovery completion was fabricated.
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`; estimated-Agent authority is 0.

Machine receipt: [backend/output/r54-reality-reconciliation-v1.json](backend/output/r54-reality-reconciliation-v1.json).

## Focused verification

- `python -m compileall -q backend/app/main.py backend/app/operator_projection.py backend/app/operator_attention.py backend/app/db/models.py backend/app/reality_reconciliation.py backend/app/db/session.py` — passed.
- `pytest -q backend/tests/test_reality_reconciliation.py` — 9 passed.
- `pytest -q backend/tests/test_r54_reality_reconciliation_product.py` — 1 passed.
- `cd frontend && npm run typecheck -- --pretty false` — passed.
- Isolated focused Playwright run (`r54-reality-conflict.spec.ts`, authoritative Python 3.13 server) — 1 passed.
