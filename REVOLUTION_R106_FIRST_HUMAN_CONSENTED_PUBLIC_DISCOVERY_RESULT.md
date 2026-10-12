# Revolution R106 — First Human-Consented Public Discovery

Date: 2026-10-12  
Branch: `codex/revolution-r63-planned-parallel-journey`  
Implementation commit: `21d27dc94c`  
Scope: R106 only; no R58–R105 historical campaign was rerun.

## Delivered

R106 makes the public discovery action a one-use, human-consented operation
with a truthful readiness boundary:

- readiness is configuration capability only. A valid approved public endpoint
  reports `LIVE_CAPABLE`; it never reports `LIVE_VERIFIED` before a provider
  response;
- ordinary discovery accepts only `MANUAL_PUBLIC_CENTER`. The visible GPS
  action is removed and the signed API rejects `FOREGROUND_GPS` before any
  provider construction;
- the traveler must explicitly confirm the Journey city label, choose a
  public map center, choose an outing category, review the disclosure, and
  grant one-use provider consent;
- changing the source, city confirmation, public coordinates, or category
  revokes the previous discovery consent. Launching a discovery request
  consumes it. City-search disclosure is also one-use and is consumed when its
  request starts or when its query changes;
- live Overpass requests require the approved HTTPS host/path, no credentials,
  query, or fragment, and a DNS result containing only globally routable
  addresses. The DNS check runs only after signed identity, manual center, and
  consent gates pass. Readiness GETs, mount, typing, and invalid centers do not
  construct a provider or perform resolver/provider I/O;
- Nominatim, Photon, and Overpass clients do not follow redirects, so an
  approved request cannot silently move to another host;
- result states remain truthful (`FOUND_2+`, `PARTIAL_1`, `ZERO`,
  `UNAVAILABLE`, `DISABLED`). No synthetic OSM identity is created when the
  provider is blocked or unavailable;
- provider audit requests continue to omit the exact center, accuracy,
  member ID, and traveler ID.

## Controlled signed A/B evidence

Run: `r106-human-consent-20261012-c`  
Viewport: `390x844`, Chromium, signed sender and recipient  
Frontend: `:4288`  
Backend: `:8288`  
Database: `frontend/../backend/_r106-human-consent-20261012-c.db`  
Python: `C:\Users\仓鼠王\AppData\Local\Programs\Python\Python313\python.exe`  
AI: disabled  
Result: **2 passed** (authoritative real-seed plus the signed R105/R106 flow)

The sender selected Shanghai through the explicit city-search disclosure,
chose a validated OpenStreetMap map center, confirmed the city label, selected
`ART_HISTORY`, and granted one discovery consent. The browser proved the
controlled Overpass fixture was untouched on mount, readiness, typing, and an
invalid latitude. The GPS source control is absent. City search made one
explicit request and its disclosure checkbox was cleared after the request.
The sender's single discovery returned two source-linked fixtures and the UI
reported `FOUND_2+` with `TEST_PROVIDER`.

The recipient used a separate signed DRAFT Journey, the same public center,
and `QUIET_BOOKS`. Its controlled provider response was empty, so the UI
reported `ZERO` and created no invented place or two-place share. The
Overpass fixture was called exactly twice: once for each signed member after
fresh consent.

The persisted sender and recipient discovery audit rows were checked during
the run. Neither row contained `center`, `accuracy_m`, `member_id`, or
`traveler_id`.

## Focused checks

- `py -3.13 -m pytest -q backend/tests/test_r105_provider_readiness.py backend/tests/test_r106_human_consented_public_discovery.py` — **6 passed**.
- `npm exec playwright test e2e/r105-provider-readiness-city-discovery.spec.ts --project=chromium --reporter=line --timeout=120000` in the fresh authoritative environment — **2 passed**.
- `npm run typecheck:all` — passed.
- `npm run build` — passed; Vite emitted only its existing large-chunk advisory.
- `py -3.13 -m compileall -q backend/app backend/tests` — passed.
- `git diff --check` — passed.

## Real-provider outcome

`LIVE_BLOCKED`: this evidence run used the declared loopback `TEST_PROVIDER`
boundary (`http://127.0.0.1:8262/api`). No operator-approved real public city,
center, and live-query authorization were supplied for this run, so no public
Overpass request was made. The controlled response stayed `TEST_PROVIDER` and
was never promoted to `LIVE_PROVIDER`; no real-world OSM identity or travel
arrival is claimed.

当前:CityNexus R106 human-consented public discovery / signed mobile A/B, provider safety, capability labeling, and privacy checks passed; live public provider remains intentionally blocked / push the implementation and report, then request the next GPT review
