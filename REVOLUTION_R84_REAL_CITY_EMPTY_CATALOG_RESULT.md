# CityNexus Revolution R84 — Real City, Empty Catalog, One Action

## Verdict

**PARTIAL.** R84 ships a truthful recovery action for browsers that cannot provide a
foreground location and records the fresh empty-catalog blocker. The full
`LIVE_CITY_SUCCESS` path remains **BLOCKED/UNVERIFIED** because this run had
`real_city_enabled=false`, made no Overpass request, and could not create a plan for
a fresh Journey whose public Place catalog is empty.

## Delivered behavior

- `MomentScoutCard` keeps the authenticated foreground-location flow unchanged.
- When foreground location is unavailable, the card remains in
  `LOCATION_UNAVAILABLE` and offers a public map action for the current shared
  rendezvous when, and only when, its coordinates are explicitly WGS84.
- The Google action is destination-only walking navigation (`origin` is omitted);
  the OpenStreetMap action is an exact public pin. Unknown or non-WGS84
  coordinates open no map.
- The fallback copy states that only public shared-stop coordinates are sent,
  that the current location is not sent, and that no nearby provider request is
  made. No candidate or receipt is materialized by this fallback.
- A fresh product-created Journey in `CN-R84-EMPTY` starts with zero public
  Places. Plan generation returns `422` with `error.reason_code=CATALOG_EMPTY`,
  `places_in_catalog=0`, and the city code. No fake plan or seeded venue was
  introduced to bypass this precondition.

## Evidence and provenance

### Fresh empty-catalog slice

`backend/tests/test_r84_empty_catalog_entry.py` creates a new traveler and
Journey, asserts `GET /api/v1/places?city_code=CN-R84-EMPTY` is `[]`, then asserts
plan generation refuses the Journey with the server-grounded `CATALOG_EMPTY`
error. This is the precise entry blocker required by the taskbook.

### Authoritative browser run

- Run ID: `r84fallback20261009221103`
- Database: `sqlite:///D:/moodle/backend/_r84fallback20261009221103.db`
- Frontend/backend: `4175` / `8015`
- AI: disabled; one Chromium worker; no reused server
- Scenario: signed owner starts the existing demo Journey, opens `/v8/live`
  without geolocation, opts into live search, receives
  `LOCATION_UNAVAILABLE`, and uses the shared-stop Google action.
- The popup contained `/maps/dir/`, `travelmode=walking`,
  `dir_action=navigate`, and no `origin` parameter. Google was intercepted as a
  navigation fixture; this proves URL construction and consent behavior, not
  physical travel or external map availability.
- Isolated database counts after the scenario: `provider_calls=0`,
  `real_place_candidates=0`, `member_live_moment_scout_receipts=0`,
  `member_side_quests=0`, `agent_runs=0`, `guardian_runs=1`.
  The demo baseline contained `journeys=1`, `plan_versions=1`, and `places=16`;
  those are not R84 live-provider results.

### Real-city/provider status

The run used `CITYNEXUS_REAL_CITY_ENABLED=false` and replay mode. Therefore the
bounded actual Overpass request count is **0**; there are no real OSM IDs,
sanitized Overpass request/response, live candidate materializations, route ETA,
opening, price, or physical arrival/return evidence to report. No TEST_PROVIDER
result is relabeled as a LIVE_PROVIDER result.

## Verification run

- `backend`: `python -m pytest tests/test_r84_empty_catalog_entry.py -q` — **1 passed**
- `frontend`: `npm exec playwright -- test e2e/r84-real-city-empty-catalog.spec.ts --project=chromium --no-deps` — **1 passed** (authoritative isolated run)
- `frontend`: `npm run typecheck` — **passed**
- `frontend`: `npm run build` — **passed** (only existing chunk-size warnings)
- `backend`: `python -m compileall -q app` — **passed**
- `git diff --check` — **passed**

No R58–R83 historical strike suites were rerun.

## Remaining work

To move from PARTIAL to a real-city proof, the next pass needs a valid public
center selected with explicit consent, `real_city_enabled=true`, one bounded
Overpass attempt with sanitized provenance and real OSM IDs, and a fresh
product-created Journey that can reach the choice-gated discovery path without
inventing a PlanVersion. Route feasibility, device movement, opening, price, and
ETA must remain unknown until independently evidenced.
