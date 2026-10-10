# CityNexus Revolution R97 — Two-stop first city walk result

## Delivery

- Implementation commit: `d98599496c` (`feat(revolution): add signed two-stop city walk`)
- Branch: `codex/revolution-r63-planned-parallel-journey`
- Scope: private signed DRAFT Journey, two owner-saved public POIs, explicit order, destination-only first leg, then a separate public-POI-to-public-POI walking release.
- Evidence grade: `CONTROLLED_PRODUCT_PATH_PROVEN`.

## Fresh isolated Journey and signed members

The authoritative browser run created a fresh isolated Journey and two signed members:

- Journey `76cd3901-8562-48d6-9565-7d961c3f3f11`, city code `CN-R97-SH-1791640858969`, status `DRAFT`.
- Owner traveler `f6da7c38-c413-4862-9ca3-1e1ce6c3ba9e`.
- Collaborator traveler `3fd710f3-c75b-4e18-9f70-40a6bab09881`.
- Owner saved shortlist IDs, in order: `23f512ee-e269-4bc6-a085-170b012d6480` (`overpass:node/97011`, R97 Shanghai Museum) and `64aeb572-69ee-4b49-b84f-9376a4779364` (`overpass:node/97012`, R97 Shanghai Gallery).

The collaborator view saw zero owner-private shortlist records. The release endpoint rechecked both IDs, the current signed member, same DRAFT Journey, absence of every PlanVersion, distinct public identities, and finite WGS84 coordinates.

## Controlled provider and browser evidence

- Run ID: `r97-20261010-09`.
- Mobile Chromium viewport: `390x844`.
- Controlled city provider: `http://127.0.0.1:8237`, one request, returned Shanghai centroid `31.2304,121.4737`.
- Controlled Overpass provider: `http://127.0.0.1:8238`, one request, returned OSM fixtures `97011` (museum) and `97012` (gallery).
- The Overpass request preserved the compound `museum|gallery` union.
- First-stop release is destination-only walking navigation. It contains the selected public destination and `travelmode=walking`, with no `origin`.
- Second-stop release URL, after a distinct consent, was:
  `https://www.google.com/maps/dir/?api=1&origin=31.2304000%2C121.4737000&destination=31.2310000%2C121.4740000&travelmode=walking`
- Frontend validation requires HTTPS, `www.google.com`, `/maps/dir/`, exactly `api`, `origin`, `destination`, and `travelmode`, `walking`, and exact match to the ordered saved WGS84 coordinates. Any other URL is rejected.
- The external URL receives only the two public POI coordinates. Foreground GPS, current location, query center, bearer/member/traveler identity, receipt, private intent, arrival, ETA, booking, and payment are withheld.
- UI states route time, opening, price, arrival, and feasibility as `UNKNOWN`; the Journey remains `DRAFT_EXPLORE_ONLY` and no arrival is inferred.

The isolated database assertions stayed at zero for the R97 Journey's `PlanVersion`, `AgentRun`, `GuardianRun`, and `Booking` rows and for Places in its city code. The second-leg endpoint is ephemeral and performs no durable plan or arrival mutation.

## Verification

- `py -3.13 -m pytest -q backend/tests/test_r97_two_stop_city_walk.py backend/tests/test_r96_intent_driven_first_outing.py backend/tests/test_r95_city_jump_and_provenance.py` — **5 passed**.
- `py -3.13 -m compileall -q backend/app` — passed.
- `git diff --check` — passed.
- `npm run typecheck:all` — passed.
- `npm run build` — passed.
- `CITYNEXUS_E2E_AUTHORITATIVE=1 CITYNEXUS_E2E_RUN_ID=r97-20261010-09 npx playwright test e2e/r97-two-stop-first-city-walk.spec.ts --project=chromium --reporter=line` — **passed** with the isolated real backend and controlled city/Overpass fixtures.

## Live-provider boundary and limits

No fresh external Nominatim or Overpass call was made in this run. The live portion is therefore `BLOCKED`/not claimed as live success; the recorded provider calls are controlled loopback fixtures only. The result does not verify current opening hours, prices, walking time, route feasibility, physical arrival, or a real trip. A later live run must retain the same consent and provenance boundaries and must not turn this explore action into an authoritative plan.
