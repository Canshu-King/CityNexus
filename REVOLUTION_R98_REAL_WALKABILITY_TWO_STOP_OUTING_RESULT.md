# CityNexus Revolution R98 — Real Two-Stop Walkability Result

## Delivery

- Implementation commit: `585650fbfba39e41a97ca72896c012c4b91c1890` (`feat(revolution): add provider-grounded two-stop walkability`).
- Branch: `codex/revolution-r63-planned-parallel-journey`.
- Evidence grade: `CONTROLLED_PRODUCT_PATH_PROVEN`.
- Scope: signed member-owned DRAFT Journey, two saved public OSM identities, explicit public-to-public pedestrian route consent, provider-backed duration/distance when available, and an honest unavailable branch with an external map fallback.

## Fresh isolated Journey and signed members

The authoritative run used a fresh SQLite database and a fresh signed A/B pair:

- Run ID: `r98-20261011-05`.
- Journey: `9811cf9d-64b6-459f-90bb-a2c08fbc5451`, city code `CN-R98-SH-1791651825640`, status `DRAFT`.
- Owner traveler: `cb4e7946-ec35-441a-b0db-300260592ad8`.
- Collaborator traveler: `aaef5e89-77bc-447d-8030-878d575a63aa`.
- Saved pair before the deletion assertion: `0564b5b7-2319-45dd-9999-fc4470569673` (`R98 Shanghai Museum`, `overpass:node/98011`, `31.2304,121.4737`) and `8574efbb-9feb-4445-88d5-68915ad53534` (`R98 Shanghai Gallery`, `overpass:node/98012`, `31.231,121.474`).
- The collaborator session saw zero owner-private shortlist rows. Removing the first stop deleted the pair selection, route result, consent, and fallback state; one saved item remained.

## Controlled provider evidence

The mobile Chromium run was `390x844` and used only loopback fixtures:

- City search: `http://127.0.0.1:8237`, one controlled request, Shanghai centroid `31.2304,121.4737`.
- Overpass: `http://127.0.0.1:8238/api/interpreter`, one controlled request, the two OSM candidates above. The request retained the `museum|gallery` union.
- Valhalla route fixture: `http://127.0.0.1:8239/route`, pedestrian costing, two explicit requests in two user-triggered checks.

The first route response was a valid controlled Valhalla payload (`200`, `time=1080` seconds, `length=1.25` km). The product displayed:

- `18 min` and `1.25 km`;
- provider `valhalla-http`;
- provenance `TEST_PROVIDER_EMULATOR`;
- the provider response `observed_at` timestamp and advisory caveats.

The route request body contained only the two ordered public `{lat,lon}` objects, `costing: pedestrian`, and `units: kilometers`. It contained no Journey ID, member/traveler identity, bearer, GPS, query center, receipt, or private intent. The route preview returned `DRAFT_EXPLORE_ONLY`, with null `plan_version_id` and `selected_place_id`.

The second controlled route response was `503` (fixture unavailable). The API returned `200 ROUTE_UNVERIFIED` with reason `ROUTE_PROVIDER_UNAVAILABLE`, null duration and distance, and an actionable public fallback:

`https://www.google.com/maps/dir/?api=1&origin=31.2304000%2C121.4737000&destination=31.2310000%2C121.4740000&travelmode=walking`

No synthetic duration or distance was shown. The existing separate external two-stop walking handoff still opened with the same public-to-public URL and no foreground origin.

The loopback provider is controlled evidence only. No live external routing request was made; live routing remains `BLOCKED`/unclaimed.

## Explore-only invariants

The browser path and backend unit test kept the target Journey at zero for `Place`, `PlanVersion`, `AgentRun`, `GuardianRun`, `Booking`, `MobilityFact`, `RouteAcquisitionOperation`, and route-related `ProviderCall` rows. The endpoint validates DRAFT status, absence of any PlanVersion, in-force signed membership, two SAVED member-owned OSM identities, distinct IDs, finite WGS84 coordinates, and separate explicit route consent before contacting the configured adapter.

## Verification

- `py -3.13 -m pytest -q backend/tests/test_r95_city_jump_and_provenance.py backend/tests/test_r96_intent_driven_first_outing.py backend/tests/test_r97_two_stop_city_walk.py backend/tests/test_r98_two_stop_walkability.py` — **6 passed**.
- `CITYNEXUS_E2E_AUTHORITATIVE=1 CITYNEXUS_E2E_RUN_ID=r98-20261011-05 npx playwright test e2e/r98-real-walkability-two-stop-outing.spec.ts --project=chromium --reporter=line --timeout=120000` — **2 passed** (real seed + Chromium).
- `npm run typecheck:all` — passed.
- `npm run build` — passed.
- `py -3.13 -m compileall -q backend/app` — passed.
- `git diff --check` — passed.

## Limits

The route result is advisory provider evidence. It does not prove safety, accessibility, opening hours, price, arrival, physical travel, or a guaranteed ETA. No live public router was configured for this proof, and no historical R58–R97 campaign was rerun.
