# Revolution R88 — Real POI exploration without false opening proof

## Review and implementation boundary

- R88 taskbook reviewed at remote GPT HEAD `c73b39719` (`docs(revolution): R88 actionable real POI preview without false opening proof`).
- R87 remains the only live discovery evidence: `LIVE_PROVIDER_SUCCESS` for one bounded, consented Overpass request. R88 made **zero new live provider discovery attempts**.
- R87's strict selection gate is unchanged: `UNKNOWN` and `CLOSED` opening evidence cannot materialize a Place or enter a native plan.
- Implementation commit: `d7d957786` (`feat(revolution): add honest public POI exploration preview`).

## User-visible capability

The signed pre-plan candidate card now supports an explore-first path for a named OSM POI whose opening evidence is incomplete:

1. The card shows the factual opening state, raw `opening_hours` when available, public website/contact tags, source (`OpenStreetMap/Overpass`), and the observation timestamp.
2. `Preview on public map` opens a per-candidate consent step. The copy states that only the public destination is shared; no saved origin, query center, or precise foreground GPS is sent to the map.
3. After consent, the browser receives a destination-only OpenStreetMap URL of the form:
   `https://www.openstreetmap.org/?mlat=<WGS84_LAT>&mlon=<WGS84_LON>#map=18/<WGS84_LAT>/<WGS84_LON>`.
   There is no origin or route parameter.
4. The UI reports `EXTERNAL_NOT_ATTESTED` for an unknown opening claim and links the traveller to the public OSM source. Opening that source is a human verification action only; it never upgrades the candidate to `VERIFIED_PROVIDER`.
5. The post-preview state is explicitly `DRAFT_EXPLORE_ONLY`: the traveller can return to the draft or search another candidate. The unknown candidate remains unselectable for native planning.

## Server release checks

`POST /api/v1/journeys/{journey_id}/bootstrap-discovery/preview` (also available under the existing `real-city/bootstrap/preview` alias) performs a second release-boundary check:

- signed Journey membership and traveler scope,
- exact discovery receipt and expiry,
- DRAFT Journey with no `PlanVersion`,
- candidate still private and unmaterialized,
- explicit `public_map_consent=true`,
- exact WGS84 candidate coordinates.

The failure paths cancel a pending release: stale receipt `BOOTSTRAP_RECEIPT_EXPIRED` (410), member mismatch `BOOTSTRAP_MEMBER_MISMATCH` (403), and coordinate mismatch `BOOTSTRAP_MAP_PREVIEW_COORDINATE_MISMATCH` (409). The response contains only public destination/source data plus explicit shared/withheld field lists. It does not return the search query, private search center, member ID, traveler ID, or a foreground location as an origin.

The preview endpoint is read-only with respect to Journey truth. It creates no `Place`, `PlanVersion`, `Activity`, route, `Agent`, `Guardian`, `Booking`, `Order`, `PaymentTransaction`, or provider discovery call. A cancelled UI consent dialog makes no preview request and opens no window.

## Focused proof

| Check | Result |
| --- | --- |
| `pytest -q backend/tests/test_r88_real_poi_exploration.py` | 1 passed |
| `npm run test:e2e -- e2e/r88-real-poi-exploration.spec.ts --project=chromium` | 2 passed (setup + R88 browser flow) |
| `npm run typecheck` | passed |
| `npm run build` | passed; existing Vite chunk-size warning only |
| `python -m compileall -q backend/app backend/tests/test_r88_real_poi_exploration.py` | passed |
| `git diff --check` | passed |

The focused backend test covers raw source facts, missing consent, successful destination-only release, private member isolation, coordinate mismatch, stale receipt, and zero Place/PlanVersion materialization. The focused browser test covers source evidence, the consent/cancel path with no outbound release, the exact destination map URL, no origin/center parameters, the `EXTERNAL_NOT_ATTESTED` state, and the unchanged native selection gate.

## Evidence grade and next handoff

R88 is **CONTROLLED_PRODUCT_PATH_PROVEN**. It adds useful real-POI exploration around the already-proven R87 live discovery without laundering unknown opening data into a startable Journey. No independent current-opening verifier was available in this pass, so the report deliberately preserves `EXTERNAL_NOT_ATTESTED` and does not claim a live opening, route, physical visit, or Journey start.

The implementation and this report are ready to push to `gpt/revolution-r33-open-world-journey-adaptation` at the same commit lineage.
