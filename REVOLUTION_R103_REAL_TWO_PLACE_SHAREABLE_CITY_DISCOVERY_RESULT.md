# Revolution R103 — Real Two-Place Shareable City Discovery

Date: 2026-10-12
Branch: `codex/revolution-r63-planned-parallel-journey`
Scope: R103 only; no R58–R102 historical campaign was rerun.

## Delivered

The ordinary city flow now lets a signed traveler search an explicitly chosen
public city area, perform one deliberate provider-backed discovery, select two
source-linked public candidates, and create a public-only share without first
saving a Pocket Walk. The share contains public names/categories, canonical OSM
source links, provider grade, capture time, and an explicit sample marker for
controlled providers. It does not contain Journey, traveler, member, receipt,
bearer, GPS, raw tag, opening, cost, accessibility, arrival, or ETA claims.

The recipient pastes the share into a separate signed DRAFT Journey. Preview is
local and makes no provider request. A second explicit consent performs exactly
one bounded exact-object lookup containing only the two public OSM identities.
When both identities are freshly verified, one action atomically saves the
recipient's own two private shortlist items and Pocket Walk, preserving the
recipient's order and optional public walking preference. The saved card
survives reload; destination-only and public-to-public map releases remain
separate consented actions.

The atomic save route reuses the existing receipt-scoped shortlist and Pocket
Walk guards. It rejects duplicate stops and commits only after both shortlist
writes and the Pocket Walk write succeed. The share text uses real line breaks
so the strict receiver parser accepts the two canonical links.

## Controlled Chromium evidence

Run: `r103-shared-20261012-d`
Viewport: `390x844`, Chromium, signed A/B backend
Frontend: `:4277`
Backend: `:8277`
Database: `backend/_r103-shared-20261012-d.db`
Python: `C:\Users\仓鼠王\AppData\Local\Programs\Python\Python313\python.exe`
AI: disabled
Result: **2 passed** (authoritative real-seed plus R103 flow)

The controlled city-search and Overpass fixtures were loopback `TEST_PROVIDER`
fixtures. The sender selected a Shanghai public center and received three
source-linked candidates, then shared the museum and gallery directly. The
recipient made no provider request while pasting or previewing; one exact
Overpass request verified both identities. The recipient saved the two places
as its own Pocket Walk, reloaded, authorized destination-only directions, then
authorized the public POI-to-POI walking map. Malicious query text containing a
credential marker was rejected without another provider request.

The exact lookup body contained only `node/103001` and `node/103002`; it did not
contain Journey IDs, member IDs, receipt IDs, bearer tokens, GPS, or private
text. Both sender and recipient remained explore-only:

| Journey record | Sender | Recipient |
| --- | ---: | ---: |
| `places` | 0 | 0 |
| `plan_versions` | 0 | 0 |
| `agent_runs` | 0 | 0 |
| `guardian_runs` | 0 | 0 |
| `bookings` | 0 | 0 |
| physical arrival / route commitments | 0 | 0 |

## Focused checks

- `py -3.13 -m pytest -q backend/tests/test_r102_shared_city_outing.py backend/tests/test_r100_pocket_walk.py backend/tests/test_r101_shared_walk.py` — **28 passed**.
- `npm exec playwright test e2e/r103-real-two-place-shareable-city-discovery.spec.ts --reporter=line` in the fresh authoritative environment — **2 passed**.
- `npm run typecheck:all` — passed.
- `npm run build` — passed; Vite emitted only its existing large-chunk advisory.
- `py -3.13 -m compileall -q backend/app backend/tests` — passed.
- `git diff --check` — passed.

## Bounded external verification

The optional public Overpass attempt was **not made**. R103's controlled
acceptance path used an explicit loopback `TEST_PROVIDER`; no real human-selected
city/object pair and operator-approved public endpoint were supplied for a
single external attempt. The controlled IDs above are not real-world evidence,
and the result makes no live-provider, physical walking, or real visitability
claim.
