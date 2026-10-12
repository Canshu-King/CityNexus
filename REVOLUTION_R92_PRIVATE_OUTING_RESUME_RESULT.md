# Revolution R92 — Resume a private outing without inventing movement

## Review and implementation boundary

- R92 taskbook reviewed at GPT remote commit `1444b1b99a65ae36b45089bfefc17f8911338809` (`REVOLUTION_R92_PRIVATE_OUTING_RESUME_TASKBOOK.md`).
- R91 remains accepted as `CONTROLLED_PRODUCT_PATH_PROVEN`; no R58–R91 history was rerun and no new live Overpass request was made.
- Implementation commit: `57efd1b53834ad20e8cf68a9f109624ab49e0b5f` (`feat(revolution): resume private outings safely`).

## User-visible resume experience

- Selecting a saved public POI for map inspection or walking directions writes one member-private `CHOSEN` resume pointer. It stores only the saved shortlist identity and public WGS84/source fields; it never stores a route URL, origin, GPS, ETA, arrival, or external provider state.
- The signed DRAFT shortlist response rehydrates the pointer after reload and after the mobile tab becomes visible again. The top-of-draft `Continue exploring` surface names the last chosen POI, links to its source, offers fresh-consent public-pin and destination-only walking actions, lets the traveler choose another saved place, and returns to the broader Journey draft.
- Every map or walking release still requires fresh one-time consent. A blocked popup shows the authorized manual link and explicitly says the automatic launch did not succeed. The UI distinguishes map opened, app returned, and physical arrival unverified; it never starts tracking, creates an Activity, or claims route feasibility.
- Removing the saved POI deletes its resume pointer. A stale pointer, changed signed member, active Journey, or existing PlanVersion fails closed and cannot restore another member's destination. Consent and transient release state are cleared on member change or a failed/non-DRAFT reload.

## Server, privacy, and transaction boundaries

- Added `member_draft_resume_intents`, unique per `(journey_id, member_id, traveler_id)`, with a cascading FK to the saved shortlist item. `POST /journeys/{journey_id}/bootstrap-shortlist/{shortlist_id}/resume` validates the signed member, exact saved item, DRAFT status, and absence of a PlanVersion.
- Resume projections omit `member_id`, `traveler_id`, receipt data, private query/center data, and navigation URLs. A bystander receives an empty board and no resume intent; cross-member writes return `403`.
- The R91 Journey-row write lock remains the durable three-item bound, but its initial `session.rollback()` was removed. The lock now preserves unrelated pending writes in the caller transaction while the endpoint commits the bounded operation atomically. The race test still yields one save and one `BOOTSTRAP_SHORTLIST_LIMIT` `409`.

## Fresh controlled evidence

- Backend A/B signed flow: owner saves and resumes one controlled `TEST_PROVIDER` POI; bystander cannot read or set the resume pointer; removal leaves no saved item or resume row. No `Place` or `PlanVersion` is materialized by this path.
- Fresh mobile Chromium run `r92-20261010-2` used Journey `2c76c6d5-43f9-49af-9b1d-1453141155f7` for the R92 scenario. It covered save → explicit walking consent → destination-only map → reload/return → resume surface → fresh walking consent → removal and fail-closed UI.
- Place delta: `0`; PlanVersion delta: `0`; Activity/route/arrival delta: `0`; Agent/Guardian/Booking/Order/Payment delta: `0` for the R92 controlled flow.
- Provider delta: controlled `TEST_PROVIDER` fixtures only; no live Overpass retry and no routing/ETA provider call.

## Focused proof

| Check | Result |
| --- | --- |
| `pytest -q backend/tests/test_r90_private_exploration_board.py` | 3 passed (R90 privacy/navigation, R91 concurrency, R92 private resume/removal) |
| authoritative `npx playwright test e2e/r92-private-outing-resume.spec.ts --config=playwright.config.ts --project=chromium --reporter=line` | 2 passed (real seed + R92 mobile return flow) |
| `npm run typecheck` | passed |
| `npm run build` | passed; existing Vite chunk-size warning only |
| `python -m compileall -q backend/app backend/tests/test_r90_private_exploration_board.py` | passed |
| `git diff --check` | passed |

R92 is **CONTROLLED_PRODUCT_PATH_PROVEN** for restoring the signed member's private saved-place context after a mobile return while keeping movement, route, arrival, and opening facts honest. Physical travel, route feasibility, current opening, and real-world arrival remain **UNVERIFIED**.
