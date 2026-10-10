# Revolution R85 — zero-catalogue Journey bootstrap

## Delivered

- Added signed-member `POST /api/v1/journeys/{journey_id}/bootstrap-discovery` for a new `DRAFT` Journey with no `PlanVersion` and no public Place.
- The request requires an explicit `FOREGROUND_GPS` or `MANUAL_PUBLIC_CENTER` source and provider disclosure consent. WGS84 bounds, radius, query length, candidate count, and one bounded Overpass attempt are enforced.
- Repeated bootstrap requests for the same Journey are rate-limited for five seconds before any provider call.
- Foreground GPS is transient provider input. The audit request stores only a coarse center and the candidate row does not persist a GPS-derived distance. No `LocationObservation`, presence signal, or route origin is written.
- Results are source-linked, named OSM candidates with opening, price, availability, and ETA states explicitly `UNKNOWN`. Candidate rows remain private (`BOOTSTRAP_PRIVATE`) until the signed member selects one.
- Added `POST .../bootstrap-discovery/select` with receipt/member checks, expiry, compare-and-set selection, deterministic OSM identity, and exactly one `Place` materialization. Repeating the same selection is idempotent; selecting another candidate after the first is refused.
- Provider mesh now exposes only materialized candidates, so another Journey member cannot read the private pre-selection set.
- New travelers receive a server-issued bearer when traveler auth is configured, allowing the browser onboarding flow to enter the signed bootstrap route.
- V8 onboarding detects a new empty catalogue, skips stay/plan generation, and shows the consented discovery panel. Cancel performs no provider request. Native plan generation accepts the explicit one-place request and reports the existing `PLACE_COST_UNVERIFIED` blocker when OSM has no price evidence; no provisional plan is fabricated.

## Evidence

Backend proof in `backend/tests/test_r85_zero_catalog_bootstrap.py` covers:

- fresh signed owner Journey and empty public catalogue;
- consent refusal with zero provider calls;
- one bounded provider attempt;
- private candidates hidden from a second signed member;
- one selected candidate producing exactly one Place;
- repeat selection returning the same Place;
- no plan, location observation, live scout receipt, or agent run;
- native single-place generation returning `PLACE_COST_UNVERIFIED`.

Browser proof in `frontend/e2e/r85-zero-catalog-bootstrap.spec.ts` covers cancellation with no search, disclosure gating, one search request, source-linked result rendering, UNKNOWN fact labels, and one selection request. The provider response is a browser fixture; the backend test is the materialization authority.

## Verification

- `pytest -q backend/tests/test_r85_zero_catalog_bootstrap.py` — passed.
- `pytest -q backend/tests/test_r84_empty_catalog_entry.py` — passed.
- `pytest -q backend/tests/test_real_city_overpass_union.py backend/tests/test_foundation_discovery_pipeline.py` — passed.
- `npm run -s typecheck` — passed.
- `npm run -s build` — passed.
- `python -m compileall -q backend/app` — passed.
- `git diff --check` — passed.
- Playwright R85 browser spec with an isolated backend/database — 2 passed (seed project plus R85 spec).

The existing `test_v6_predictive_real_city.py` remains an unrelated baseline failure in this checkout (`run_once(enrolled_only=True)` returns zero); the R85 focused tests and real-city discovery tests pass independently.
