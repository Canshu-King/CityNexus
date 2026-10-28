# Beijing: native four-stop candidate, three real routes, published city

Product: `8c18dcd2b99a89b7df2383ff5025b6bd35ded7f6`; integration base: rescue `2542b62135c73b10d80b81ba7874416330e60324`.

The owned classroom database now contains a formally prepared four-stop candidate and three newly measured Amap walking edges. Signed native city publication returned 200. Preflight reports Beijing `110000`, 40 acquired POI, 3 captured routes, `ELIGIBLE_CAPTURED_SNAPSHOT`; the distinct eligible city count is **1** for seeds 17 and 42. The earlier same-database signed result was 40 POI / 0 routes / eligible 0 (`20261026_CITY_NATIVE_BINDING_HTTP.json`). Three-city readiness remains `BLOCKED`.

## Product change

- Existing signed `PUT .../goal-tasks/{task}/draft` accepts optional `reuse_source_task_id`. The server validates the same owner, current source read permission, same internal city, source-task ownership of every selected Place, and exact live materialized provider identity/coordinates. Only the explicitly selected IDs enter the target task. Revision or draft validation failures leave its scope unchanged. Successful reuse emits a source-task/Place audit receipt.
- City publication aggregates only the target owner's Journeys in that city. An unbound new DRAFT cannot erase an existing verified city binding; contradictory verified bindings block publication. Another owner's readable Journey is excluded from publication.
- Preflight and publication retain WGS84 route geometry, geometry provider, fact quality, route provenance and snapshot hash. Public reload rechecks geometry and source markers; legacy empty or malformed snapshots remain blocked. No source coordinates are synthesized.

## Native HTTP run

Owned stack: `14522/60622`; the helper was normally stopped and resumed with the existing database/auth. Backend loaded the product SHA above. Frontend source belongs to Qoder and had independently advanced to `c8adf500e58b`; this report establishes backend HTTP/provider behavior, with no new browser/device acceptance claim.

- New DRAFT Journey: `f884a2b2-bcbc-48b7-8059-4566cd403812`.
- GoalTask: `3ca91376-a2f0-4ec7-b68a-871f0b6ab8bf`.
- Explicit reuse source: existing owner task `1690b9ed-9d00-4c49-986e-85cbd7b3554d`.
- Signed draft PUT: 200; native prepare-plan: 201; PlanVersion `dc1cda13-c5e9-48fe-97f1-c915f11a128d`, `SELECTED_GOAL_DRAFT`, **CANDIDATE**.
- Native freeze-routes: 200, verified 3/3, frozen true, snapshot `d8e78df0-9941-40d2-8a76-aea0162bf3e2`.
- Presenter + owner signed publish on the existing Beijing-bound Journey: 200. Public snapshot hash: `94b6c37704228505d941cf0c866199d69614a000e28bc786340a8404bdf4f9a3`.

| Date | Morning 09:00–12:00 | Afternoon 14:00–17:00 |
| --- | --- | --- |
| 2026-12-03 | 故宫博物院 | 前门大街 |
| 2026-12-04 | 国家自然博物馆（现馆） | 天坛公园 |

These are four distinct canonical Places. Slots remain PLANNED; opening/price unknowns remain unresolved. No reservation, ACTIVE transition or stop completion was fabricated.

## Three new real provider edges

Each pair was measured once by native freeze. ProviderCall count increased **85 → 88**. No old route or POI request was repeated.

| Pair | ProviderCall | HTTP | Seconds / meters | WGS84 points |
| --- | --- | --- | --- | --- |
| 故宫 → 前门大街 | `c909a1e1-9df1-4d8d-be87-3f4b31620445` | 200 | 2950 / 3688 | 139 |
| 前门大街 → 国家自然博物馆（跨日） | `79dc5035-db30-4985-b06c-24748fd8ad22` | 200 | 1398 / 1747 | 58 |
| 国家自然博物馆 → 天坛 | `e0e689a6-5f48-4b95-9896-f8701c11de69` | 200 | 1052 / 1315 | 33 |

All three native snapshot facts are `LIVE_PROVIDER_CAPTURE`, provider/geometry provider `amap-web-service`. The HTTP receipt binds source call IDs, request pairs, response hashes and geometry hashes. Public records retain the geometry and evidence hash; the current TravelEstimateFact schema does not carry a source-call field, so none was invented in the public snapshot.

## Model and history boundaries

One new real `auto:cheapest` attempt timed out: AgentRun `5588dc4b-5812-4d83-8f77-ca99a8dfdeb2`, `FAILED_EXTERNAL`; task `MODEL_TIMEOUT`, one model turn, zero tools. There was no retry. The subsequent four-stop draft is explicitly **signed-owner manual reuse**, not a successful model-generated itinerary. AgentRun count increased 38 → 39.

The old real simulation `5625ed72-9aff-4c87-8bb3-68d9291775e1` remains `SIMULATED_COMPLETED`, sequence 9. Its historical stop completion is not counted toward this new candidate. The new candidate has not been activated or simulated to completion.

## Validation and evidence

Root-only serial pytest, isolated temporary SQLite: city/publication suite 16/16; reuse/date/preparation suite 32/32; final focused workflow scope plus existing city/native regression **251 passed, 5 warnings, exit 0**. Counts overlap and are not additive. The previous empty-public-snapshot fixture was corrected to carry explicit declarative five-POI/three-geometry data; invalid/empty snapshot rejection is tested separately. Test fixtures do not establish live provider acquisition.

- `20261026_BEIJING_NATIVE_CITY_SUPPLY_HTTP.json`: signed HTTP states, exact identities, provider receipts, both seeds and preserved old run.
- `20261026_BEIJING_NATIVE_ROUTE_SNAPSHOT.json`: native PlanVersion frozen evidence with the three WGS84 shapes.
- `20261026_BEIJING_PUBLISHED_CITY_SNAPSHOT.json`: actual published public city payload.
- `20261026_BEIJING_CITY_RESTART_HTTP.json`: after a second normal owned restart, signed HTTP still reads the same public hash and three shapes (139/33/58 points); the old run remains completed sequence 9 / PROPOSAL_ACCEPTED. ProviderCall 88 and AgentRun 39 are unchanged by this reload, with zero new map/model requests. Restart loaded document head `f2a5b60e52`, whose product code is unchanged from `8c18dcd2b9`.
- Owned prewrite consistent backup: `C:/Users/仓鼠王/cn51/classroom-20261026-qa/supply-native-20261026/before-four-stop-native.db`.

Remaining: two more genuinely different eligible cities; classroom same-run two-day/four-stop execution and event chain; Qoder UI integration; physical-device USER_VERIFIED. Beijing eligibility alone does not satisfy those gates.

PR56 document head `f2a5b60e52` checks 40284723978 and 40284714148 both completed SUCCESS. Later document-only heads must be checked independently.
