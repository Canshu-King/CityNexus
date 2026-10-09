# Revolution R86 — First startable real-city Journey

## Outcome

**PROVEN in the isolated signed backend flow and Chromium product path; live external Overpass remains BLOCKED by the current deployment flag.**

The R86 path now supports a newly created DRAFT Journey whose city starts with zero Places:

1. signed owner gives explicit OpenStreetMap/Overpass consent and discovers source-bound candidates;
2. exactly the selected candidate is materialized as one `overpass:` Place;
3. native planning accepts an explicit `allow_unknown_cost` acknowledgement only for that selected bootstrap Place;
4. the persisted plan exposes a known subtotal with `total_cost_status=PARTIAL_UNKNOWN`, records `COST_UNKNOWN_ACCEPTED` and `USER_ACCEPTS_UNKNOWN_PRICE_NOT_INCLUDED`, and marks the admission price as not included and not bookable;
5. the owner selects and starts the Journey through the ordinary native plan gates.

Unknown price is never presented as FREE.  Selection and start still require grounded opening facts, and the booking path refuses an activity whose price remains UNKNOWN.  No AgentRun, GuardianRun, Booking, Order, PaymentTransaction, or provider charge is created by the bootstrap-to-start path.

## Evidence

- Backend: `backend/tests/test_r86_first_startable_real_city_journey.py`
  - zero Places before discovery and one materialized Place after selection;
  - invalid, expired, and member-mismatch candidate selection;
  - durable Journey/member/traveler rate claim and `max_attempts=1`;
  - default unknown-cost refusal, explicit acknowledgement, idempotent replay, selection/start, and zero side effects.
- Browser: `frontend/e2e/r86-first-startable-real-city-journey.spec.ts`
  - Chromium exercises consent, selection, explicit price-unknown acknowledgement, generate/select/start, and verifies no Agent or booking request.
- Existing R85 regression and generic refusal/claim-lease checks remain green.

## Validation

- `pytest -q backend/tests/test_r86_first_startable_real_city_journey.py` — passed
- `pytest -q backend/tests/test_r85_zero_catalog_bootstrap.py backend/tests/test_qoder_generic_compose_reason_codes.py backend/tests/test_qoder_ord0340_claim_lease.py` — 16 passed
- `npm run typecheck` — passed
- `npm run build` — passed
- `npm run test:e2e -- e2e/r86-first-startable-real-city-journey.spec.ts --project=chromium` — 2 passed (real-seed setup + Chromium)
- `python -m compileall -q backend/app` and `git diff --check` — passed

## Honest limitation

The current process reports `real_city_enabled=False` and `real_city_mode=replay`, so no live Overpass request was attempted.  The provider trial is therefore **BLOCKED by configuration**, while the provider-backed semantics are covered by the isolated signed test and browser contract.

