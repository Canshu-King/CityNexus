# CityNexus Revolution R96 — One-Tap First Outing Result

## Delivered slice

R96 adds a deliberate first-outing preference choice to the fresh zero-catalog Journey surface:

| User choice | Bounded provider query | Result explanation |
| --- | --- | --- |
| Art and history | `museum/gallery` | museum, gallery, or arts centre |
| Quiet green walk | `park/garden` | park or garden |
| Coffee and a short stroll | `cafe` | cafe or coffee stop |
| Books and quiet | `library` | library |

The browser sends only the selected fixed category. It does not accept an arbitrary free-text POI query or infer a preference. Each returned candidate shows why it fits the declared choice, source identity, provider grade, observation time, opening uncertainty, price `UNKNOWN`, and ETA `UNKNOWN`. Existing private shortlist, per-release map consent, destination-only walking, and resume paths remain in the same panel.

The Overpass adapter now treats the two compound categories as explicit unions. `museum/gallery` cannot silently become only `museum`, and `park/garden` cannot silently become only `park`.

## Controlled Chromium receipt

- Authoritative run: `r96-20261010-06`
- Browser: Chromium, viewport `390x844`
- Database: fresh `_r96-20261010-06.db`
- Providers: loopback city and Overpass fixtures only; no public external request
- Calls: exactly one city lookup and exactly one Overpass discovery
- City receipt: `nominatim:relation/95001`, `Shanghai`, `TEST_PROVIDER`, observed `2026-10-10T12:59:22.997793+00:00`, first lookup `cache_hit=false`; the durable cache expiry was seven days later
- Public-area receipt: manual WGS84 center `31.230400,121.473700` after separate city and map-tile consent
- Overpass receipt: one `POST /interpreter` at `2026-10-10T12:59:23.797141+00:00`, `TEST_PROVIDER`, two source identities: `overpass:node/96011` (`R96 Shanghai Museum`) and `overpass:node/96012` (`R96 Shanghai Gallery`)
- Candidate observations: opening `UNKNOWN`, cost `UNKNOWN`, and no live physical/travel proof

The owner selected the explicit `ART_HISTORY` choice, saw the bounded `museum/gallery` request and per-result reason, privately saved `R96 Shanghai Museum`, opened destination-only walking directions, and returned to the exploration board. The generated URL contained only the public destination and `travelmode=walking`; the browser assertion found no `origin` or receipt.

The collaborator session saw `Saved 0 of 3`, no owner candidate, no owner intent selection, and no `museum/gallery` query text. Direct database assertions for the owner Journey remained `Place=0`, `PlanVersion=0`, `AgentRun=0`, `GuardianRun=0`, and `Booking=0` both after saving and after walking/resume.

## Verification

- `py -3.13 -m pytest -q backend/tests/test_r95_city_jump_and_provenance.py backend/tests/test_r96_intent_driven_first_outing.py` — **3 passed**
- `npx playwright test e2e/r96-one-tap-first-outing.spec.ts --project=chromium` in the authoritative environment — **2 passed** (real-seed dependency + R96 scenario)
- `npm run typecheck:all` — passed
- `npm run build` — passed
- `py -3.13 -m compileall -q backend/app` — passed
- `git diff --check` — passed

## Boundary and remaining uncertainty

The controlled receipts prove the product path and isolation boundary only. They do not claim a fresh public Nominatim/Photon/Overpass response, current opening status, price, route ETA, or physical arrival. Those remain `UNVERIFIED` until a separately consented, policy-compliant live trial is possible.

GPT's review base was `00ffb457c1` (R96 taskbook), with the narrow review fixes `9dd5b3896a`, `250b4a111c`, `9b7a8fa7d4`, and `76903ed41e`; the focused R95 regression passed after those fixes.
