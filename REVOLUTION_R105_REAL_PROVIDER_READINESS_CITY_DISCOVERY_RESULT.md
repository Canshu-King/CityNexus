# Revolution R105 — Real Provider Readiness and City Discovery

Date: 2026-10-12  
Branch: `codex/revolution-r63-planned-parallel-journey`  
Scope: R105 only; no R58–R104 historical campaign was rerun.

## Delivered

The signed first-place city flow now exposes a nonsecret readiness projection
before any public-provider operation. It reports only the provider recipient,
safe reason code, source grade, and whether the configuration is test-only. It
does not reveal an endpoint, proxy, user agent, credential, bearer token, or
selected center.

The Overpass gate is strict:

- live requests require `CITYNEXUS_REAL_CITY_ENABLED=true`, live mode, HTTPS,
  an approved public Overpass host, no credentials/query/fragment, and the
  `/api` path;
- loopback HTTP is accepted only for the declared controlled test boundary and
  remains `TEST_PROVIDER` with `external_request_allowed=false`;
- disabled, replay, malformed, plaintext public, private, or unknown endpoints
  return a stable nonsecret reason and do not construct or call a provider;
- both ordinary discovery and exact shared-object lookup use the same gate and
  remain limited to one provider attempt.

Provider audit requests no longer persist exact center, accuracy, member ID, or
traveler ID. The response adds truthful `FOUND_2+`, `PARTIAL_1`, `ZERO`,
`UNAVAILABLE`, and `DISABLED` result states without changing the existing
compatibility status values.

The 390px panel now fetches readiness only after signed identity is available,
fences stale responses on identity/Journey changes, displays the expected
recipient and test grade, requires a named city label, a manual public map
center, a fixed outing category, and explicit consent, and releases the exact
public coordinates in the consent text. Foreground GPS cannot start this
public discovery action. One candidate remains reviewable/saveable, while
two-place sharing stays disabled.

## Controlled signed A/B evidence

Run: `r105-readiness-20261012-k`  
Viewport: `390x844`, Chromium, signed sender/recipient  
Frontend: `:4284`  
Backend: `:8284`  
Database: `backend/_r105-readiness-20261012-k.db`  
Python: `C:\Users\仓鼠王\AppData\Local\Programs\Python\Python313\python.exe`  
AI: disabled  
Result: **2 passed** (authoritative real-seed plus the R105 flow)

The sender used an explicit Shanghai city search, a strict OpenStreetMap map
link followed by a public-area confirmation, the `ART_HISTORY` category, and
one consented discovery click. The browser proved zero Overpass calls on mount,
while typing, and with an invalid latitude; the readiness card moved through
`USER_CATEGORY_REQUIRED`, `CONSENT_REQUIRED`, and `READY`. The controlled
loopback fixture returned two source-linked candidates and the UI reported
`FOUND_2+` with `TEST_PROVIDER`.

The signed recipient used a separate DRAFT Journey and the same public center,
selected `QUIET_BOOKS`, and received an empty controlled response. The UI
reported `ZERO`, with no invented place or two-place share. The provider call
counter was exactly two: one sender discovery and one recipient discovery,
plus the explicitly consented city-camera lookup.

The run also queried the persisted discovery audit rows. Both rows omitted
`center`, `accuracy_m`, `member_id`, and `traveler_id`; only public operation
metadata remained.

## Focused checks

- `py -3.13 -m pytest -q backend/tests/test_r105_provider_readiness.py` — **2 passed**.
- `npm exec playwright test e2e/r105-provider-readiness-city-discovery.spec.ts --reporter=line` in the fresh authoritative environment — **2 passed**.
- `npm run typecheck:all` — passed.
- `npm run build` — passed; Vite emitted only its existing large-chunk advisory.
- `py -3.13 -m compileall -q backend/app backend/tests` — passed.
- `git diff --check` — passed.

## Real-provider outcome

`LIVE_BLOCKED`: the optional public Overpass operation was not made. This run
had no human-selected real city/center plus separate live-query authorization,
and the configured evidence boundary was loopback HTTP. Network recovery alone
is not user consent. The fixture returned `TEST_PROVIDER` and was never
promoted to `LIVE_PROVIDER`; no OSM identity in this report is real-world
evidence.

当前:CityNexus R105 readiness / focused signed A/B and configuration gates passed; live public provider intentionally not called / push this result and request GPT review
