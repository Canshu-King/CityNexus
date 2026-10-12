# Revolution R40 — Launch Setup & Origin Clarification

## Closure

- Source branch: `gpt/revolution-r33-open-world-journey-adaptation`
- Source HEAD before live closure: `72441e3b52a39bb7dfaa67185db2d963e7cc8e16`
- R39 remains immutable at `cd83eaea4746ea866f446c2de835b1a9199f125b`.
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.
- R33–R39 live closures were not rerun.
- One fresh R40 live closure was completed through the real API with no database injection.

## Live result

- Result: `LAUNCH_SETUP_GROUNDED_EDGE_UNAVAILABLE`
- Fresh Journey: `1bd72996-3da5-4cce-8e92-1d4eeae10582`
- Initial GET `/api/v1/journeys/{id}/launch-setup`:
  - `NEEDS_ORIGIN`
  - actions: `SHARE_LOCATION`, `CHOOSE_PLACE`
  - no candidates
  - `read_only=true`, `provider_capture=false`
- POST `/api/v1/journeys/{id}/launch-origin`:
  - source: exact existing `PLACE`
  - Place: `real-place-b47a20314c81d5a81381d4a4`
  - provider: `overpass`
  - external id: `overpass:node/2465643503`
  - coordinates: WGS84 `34.678661, 135.8281897`
  - authority: `USER_CONFIRMED_PLANNED_ORIGIN`
  - physical presence asserted: `false`
  - audit action: `journey.launch_origin.confirmed`
- The persisted launch contract is bound to the first target activity and has a validity window around its start.
- R39 recomputation returned a grounded origin with the exact Place key.
- No exact launch edge existed for the confirmed Place to the first target. No provider retry or GET-triggered capture occurred.
- Readiness remained `READY_WITH_UNCERTAINTY` with `must_leave_by=null` and reason `LAUNCH_EDGE_UNAVAILABLE`.

## Authority and mutation checks

The live receipt shows:

- active plan id unchanged before/after;
- zero material Events;
- zero AgentRuns;
- zero proposals;
- zero mutations;
- zero notifications;
- zero location observations;
- no device-attested execution truth;
- offline snapshot contains the confirmed planned origin, validity window, launch edge state, and captured-read-model timestamps.

## Implementation

- Added persisted `JourneyLaunchContext` model and schema.
- Added read-only launch setup projection and controlled confirmation endpoint.
- Accepted source kinds are limited to `PLACE`, `SELECTED_STAY`, and `ARRIVAL_ANCHOR`.
- Exact Place confirmation validates existence, coordinates, Journey city binding, and server-owned provider provenance.
- Request schema forbids arbitrary fields, caller-supplied authority, and caller-supplied coordinates.
- Updated launch precedence so previous/current execution context wins, followed by fresh location, valid confirmed launch contract, selected stay, arrival anchor, then unknown.
- Added offline/UI handling for “Where will you start from?” and explicit confirmation copy that never claims physical presence.
- Added provenance visibility for persisted exact Place/stay contracts when read through the launch setup API.

## Verification

- Backend focused R40/R38/R39 regression: **37 passed**.
- Python compileall: **passed**.
- Frontend TypeScript: **passed**.
- Playwright `qoder-live-recovery-cursor.spec.ts`: server startup succeeded with the repository Python, but all four product cases stopped at the existing `/api/v1/demo/reset` 403 `RESET_TOKEN_REQUIRED` precondition; one seed setup test passed. No R40 assertion was reached.
- Full legacy `test_v14_trial_readiness.py` was not treated as an R40 regression: its unrelated environment-sensitive assertion expected `nominatim=UNAVAILABLE` but observed `NOT_CALLED`.

## Artifacts

- Machine receipt: `backend/output/r40-launch-setup-v1.json`
- Live harness: `backend/run_r40_live.py`
- Focused projection/origin tests: `backend/tests/test_launch_setup_projection.py`, `backend/tests/test_grounded_launch_origin.py`
