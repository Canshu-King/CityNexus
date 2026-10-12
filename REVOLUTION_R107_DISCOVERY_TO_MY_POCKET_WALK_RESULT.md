# Revolution R107 — Discovery to My Private Pocket Walk

Date: 2026-10-12  
Branch: `codex/revolution-r63-planned-parallel-journey`  
Implementation commit: `c8ef0f1fc6d9abb1680125183ebdd3029a7c6dc3`  
Scope: R107 only; no R58–R106 historical campaign was rerun.

## Delivered

R107 adds a native path from the current signed manual-center discovery result to
one member-private ordered Pocket Walk:

- the frontend lets a traveler choose exactly two current result candidates,
  set stop order, review source links and provenance, see `UNKNOWN` opening,
  price, access, and walking ETA fields, declare an optional 15/20/30/45-minute
  preference, and explicitly confirm the private save;
- the signed API endpoint is separate from friend import:
  `POST /api/v1/journeys/{journey_id}/bootstrap-discovery/pocket-walk`;
- the server requires one unexpired receipt shared by both candidates, the same
  signed member and traveler, `MANUAL_PUBLIC_CENTER` source scopes, valid OSM
  identities, finite WGS84 coordinates, non-restricted access, a DRAFT Journey,
  and no active PlanVersion;
- both candidates, the three-item private shortlist quota, and all authority
  checks are validated before either shortlist row is created. The two shortlist
  rows and ordered Pocket Walk commit in one transaction, with rollback leaving
  no partial private state;
- `SHARED_PUBLIC_REFERENCE` and foreign-member candidates are rejected by this
  endpoint and remain available only to the existing friend-import route;
- the saved response rehydrates the existing private Pocket Walk card and
  ordered shortlist after refresh. Existing stop-1 destination consent and
  stop-1-to-stop-2 walking consent remain separate; no receipt, member, Journey,
  or private center is placed in map URLs;
- bearer, Journey, discovery, source, order, and response-generation fences
  clear the new selection and reject stale responses after identity or Journey
  changes.

## Controlled signed A/B evidence

Run: `r107-discovery-pocket-20261012-d`  
Viewport: `390x844`, Chromium, signed owner and collaborator  
Frontend: `:4292`  
Backend: `:8292`  
Database: `frontend/../backend/_r107-discovery-pocket-20261012-d.db`  
Python: `C:\Users\仓鼠王\AppData\Local\Programs\Python\Python313\python.exe`  
AI: disabled  
Result: **2 passed** (authoritative real-seed plus the fresh R107 flow)

The owner selected Shanghai through the explicit city-search disclosure,
confirmed the manual public center and city label, selected `ART_HISTORY`, and
granted one discovery consent. The controlled Overpass fixture returned three
source-linked OSM candidates labeled `TEST_PROVIDER`. The owner selected two in
an explicit order and saved them directly through the new endpoint without a
friend import or intermediate shortlist clicks.

The browser then restored the ordered Pocket Walk after reload, opened stop 1
with its own destination-only map consent, and opened the stop-1-to-stop-2
walking map with a separate consent. A collaborator's signed page saw an empty
private board. A second owner save response was held in the browser, the same
tab switched to the collaborator bearer, and the late owner response did not
repopulate the collaborator's state. Restoring the owner bearer reloaded the
owner's persisted Pocket Walk from the signed server read.

The controlled fixture was used only as a declared `TEST_PROVIDER` boundary;
the run made no real public Overpass request.

## Focused checks

- `py -3.13 -m pytest -q backend/tests/test_r107_discovery_to_my_pocket_walk.py backend/tests/test_r102_shared_city_outing.py backend/tests/test_r106_human_consented_public_discovery.py` — **28 passed**.
- `npm run test:e2e -- e2e/r107-discovery-to-my-pocket-walk.spec.ts --project=chromium` in the fresh authoritative environment — **2 passed**.
- `npm run typecheck:all` — passed.
- `npm run build` — passed; Vite emitted only its existing large-chunk advisory.
- `py -3.13 -m compileall -q backend/app backend/tests` — passed.
- `git diff --check` — passed.

## Real-provider outcome

`LIVE_BLOCKED`: this evidence run used the declared loopback controlled fixture
(`http://127.0.0.1:8262/api`). No operator-approved real public city, center, and
live-query authorization were supplied, so no public Overpass request was made.
The response stayed `TEST_PROVIDER` and was never promoted to `LIVE_PROVIDER`.

当前:CityNexus R107 discovery-to-my-private-Pocket-Walk / direct signed two-stop save, atomic persistence, map-consent separation, A/B isolation, reload, and stale-response checks passed / push this implementation and result report, then request the next GPT review
