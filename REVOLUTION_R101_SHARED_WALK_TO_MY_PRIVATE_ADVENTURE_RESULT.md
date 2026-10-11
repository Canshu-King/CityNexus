# Revolution R101 — Shared Walk to My Private Adventure

Date: 2026-10-11
Branch: `codex/revolution-r63-planned-parallel-journey`
Scope: R101 only; no historical R58–R100 campaign was rerun.

## Delivered

The DRAFT bootstrap surface now has **Import a friend's public walk**. The recipient pastes public text, and the browser extracts exactly two canonical HTTPS OpenStreetMap object links locally. The preview exposes only `node|way|relation` plus the canonical source URL and labels both as `UNVERIFIED_SHARED_REFERENCE`.

Names, categories, provider grades, opening data, prices, timing, routes, Journey IDs, member IDs, receipts, GPS, credentials, and sender authority are not accepted from the paste. No pasted text is sent to the backend or persisted. Preview, edit, reload, cancel, and malicious payload rejection perform no provider request.

After a separate checkbox consent, the backend validates the two identities again and makes one bounded Overpass union request containing only the two public IDs. The response is filtered to exact public identities with WGS84 coordinates, a public name, and no explicit private-access tag. Each usable result receives a fresh recipient member/traveler scope and receipt; sender scopes and authority are never copied. A blocked or unavailable provider returns `LOOKUP_BLOCKED` with no synthetic coordinates or save-ready place.

The fresh candidates use the existing member-private shortlist and Pocket Walk gates. The recipient can save up to three candidates, choose two ordered stops, restore the Pocket Walk, and separately authorize a destination-only map or a public-to-public walking map. No route estimate, arrival claim, or foreground origin is created.

## Authoritative browser evidence

Run: `r101-shared-20261011-17`
Frontend: `:4269`
Backend: `:8269`
Database: `backend/_r101-shared-20261011-17.db`
Python: `D:\moodle\CityNexus\.venv\Scripts\python.exe`
AI: disabled
Result: **2 passed (23.3s)**

The controlled Overpass fixture returned one `node/101001` and one `way/101002` in a single union. The sender and recipient used separate travelers and draft Journeys. The recipient's shortlist IDs and fresh receipt differed from the sender's. Paste and preview kept the fixture request count unchanged; the recipient's explicit lookup added exactly one request. The asserted query contained no bearer, Journey, member, receipt, or GPS value.

The same browser run saved and reloaded the recipient Pocket Walk, opened the destination-only map without an origin, opened the separate public-to-public walking map, and verified that the two map consents remain independent. Four hostile payloads (an extra OSM link, credentials in the URL, a query token, and HTML) were rejected without another provider request.

For both R101 journeys in the isolated database, the explore-only boundary remained:

| Record | Count |
| --- | ---: |
| `places` with `provider_key='overpass'` | 0 |
| `plan_versions` | 0 |
| `agent_runs` | 0 |
| `guardian_runs` | 0 |
| `bookings` | 0 |

The expected private draft records were present: two `real_place_candidates`, two shortlist items, and one Pocket Walk per journey.

## Focused checks

- `py -3.13 -m pytest -q backend/tests/test_r101_shared_walk.py backend/tests/test_r100_pocket_walk.py` — **9 passed**.
- `py -3.13 -m compileall -q backend/app backend/tests` — passed.
- `npm run typecheck:all` — passed.
- `npm run build` — passed; Vite emitted only its existing large-chunk warning.
- `git diff --check` — passed.

The provider fixture and map interception are controlled local evidence. This result does not claim a live public Overpass response, a physical walking route, or a real-world arrival ETA; those remain gated by the existing provider and map consents.
