# Revolution R102 — First Real Shared City Outing

Date: 2026-10-11
Branch: `codex/revolution-r63-planned-parallel-journey`
Scope: R102 only; no R58–R101 historical campaign was rerun.

## Delivered

R102 now keeps one public OSM identity as one shared row while storing a fresh,
member-private observation for every signed member. Each scope carries its own
name, category, finite WGS84 coordinates, observation time, exact canonical
source URL, access classification, and provider grade. A later member cannot
read the first member's coordinates, captured time, or `LIVE_PROVIDER` grade.
Legacy scopes without a member grade remain `UNVERIFIED` instead of inheriting
the shared row's grade.

Provider candidates and saved observations reject malformed, non-finite, or
out-of-range latitude/longitude and invalid distances before receipt, map, or
shortlist release. Explicit private/restricted/public=no signals are excluded.
Indoor-only signals remain usable only with the honest
`INDOOR_ACCESS_UNVERIFIED` state; they are never presented as unquestionably
visitable.

The Python and browser shared-walk parsers enforce the same boundary: exactly
two distinct canonical HTTPS OSM object URLs, no credentials, query, fragment,
encoded path separator, control/HTML text, or sensitive member data. Pasting,
previewing, cancelling, or rejecting a link does not call Overpass. Only the
separate provider-consent action sends the two public identities.

## Controlled Chromium evidence

Run: `r102-shared-20261011-d`
Viewport: `390x844`, Chromium, signed backend
Frontend: `:4273`
Backend: `:8273`
Database: `backend/_r102-shared-20261011-d.db`
Python: `C:\Users\仓鼠王\AppData\Local\Programs\Python\Python313\python.exe`
AI: disabled
Result: **2 passed** (authoritative seed plus R102 flow)

The local controlled fixture returned the same `node/102001` and `way/102002`
identities twice. The owner observation used `31.2304,121.4737` and the
collaborator observation used `31.2404,121.4837`; both scopes received
`TEST_PROVIDER`, different capture times, and their own names. The gallery was
marked `indoor=only` and remained `INDOOR_ACCESS_UNVERIFIED`. The second member
saved two private shortlist items, and the malformed encoded-separator paste
was rejected without a third provider request.

The controlled boundary made exactly two exact-object Overpass requests, one
per signed member. The request body contained only the two public identities;
no Journey ID, member ID, receipt, bearer token, GPS, or private text was sent.

| R102 Journey record | Count |
| --- | ---: |
| `real_place_candidates` | 2 |
| member-private shortlist items | 2 |
| `MemberDraftPocketWalk` | 0 (not created by this focused flow) |
| `places` | 0 |
| `plan_versions` | 0 |
| `agent_runs` | 0 |
| `guardian_runs` | 0 |
| `bookings` | 0 |
| arrivals / route commitments | 0 |

## Focused checks

- `py -3.13 -m pytest -q backend/tests/test_r102_shared_city_outing.py backend/tests/test_r101_shared_walk.py backend/tests/test_r89_member_shared_osm_identity.py` — **27 passed**.
- `./node_modules/.bin/playwright.cmd test e2e/r102-shared-city-outing.spec.ts --project=chromium --reporter=line` in the authoritative environment — **2 passed**.
- `npm run typecheck:all` — passed.
- `npm run build` — passed; Vite emitted only its existing large-chunk advisory.
- `py -3.13 -m compileall -q backend/app backend/tests` — passed.
- `git diff --check` — passed.

## Bounded real-world gate

The one allowed public Overpass attempt was **not attempted**. R102 requires a
genuine named city plus two known real OSM object URLs independently selected
as a pair by the user. Those prerequisites were not supplied, so the status is
`BLOCKED_MISSING_USER_SELECTED_CITY_AND_OBJECTS`. The synthetic IDs above are
controlled test fixtures only and are not real-city evidence. No public
network query, physical walking route, arrival, or real-world visitability
claim is made.
