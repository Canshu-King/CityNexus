# Revolution R93 — Search my city and keep private sessions isolated

## Review and implementation boundary

- R93 taskbook reviewed from GPT remote commit `2ca21731e18192a4ba2402e51ad50403761a5b4f` (`REVOLUTION_R93_EXPLICIT_CITY_CENTER_AND_PRIVATE_SESSION_TASKBOOK.md`).
- R92 remains accepted as `CONTROLLED_PRODUCT_PATH_PROVEN`; no R58–R92 history was rerun and no new live Overpass request was made.
- The implementation stays on `codex/revolution-r63-planned-parallel-journey`.

## User-visible changes

- A new Journey no longer starts with a Tianjin coordinate. Manual latitude and longitude fields start blank and preserve blank input instead of coercing `Number("")` to `0`.
- Searching is disabled until the traveler provides a finite WGS84 center or deliberately grants foreground GPS. Switching between manual center and GPS clears the old coordinates, accuracy, and discovery result before the new source is used.
- Before a provider request, the screen shows the selected center, source kind, optional GPS accuracy, and the explicit limitation that the center does not prove city relation, route origin, presence, or arrival. Provider disclosure consent remains a separate checkbox.
- The manual fallback map uses only the validated selected center. No empty or invalid field can produce an external provider request or fallback URL.

## Same-tab identity boundary

- Added a `subscribeTravelerBearer` signal that observes the opaque signed bearer through explicit helper events, the browser storage event, and a short same-tab poll. `storeTravelerBearer` and `clearTravelerBearer` emit the signal.
- Every shortlist load, discovery, selection, save, remove, resume, and map-release continuation is scoped to the bearer and an identity generation captured at request start. A delayed response from an older generation is ignored.
- A bearer change immediately clears the discovery receipt and candidates, private shortlist/resume state, provider and map consent, selected center/query, fallback URL, navigation notice, busy flags, and selection state. Any pre-opened map window is closed. The next signed member receives a clean board and performs its own signed load.

## Fresh controlled evidence

- Backend uses two signed traveler principals, a non-Tianjin Shanghai Journey, an explicit `31.2304, 121.4737` public center, and a controlled `TEST_PROVIDER` discovery response. The saved shortlist remains empty for the second signed member.
- Browser uses a fresh authoritative backend/database and real traveler/Journey creation with a sufficiently long `CITYNEXUS_TRAVELER_AUTH_SECRET`. The provider discovery and delayed private-board responses are deterministic route fixtures so the test can hold A's save response, switch the same tab to B, and release the stale response. B never sees A's candidate, receipt, center, consent, or shortlist; switching back to A restores only A's own board.
- No live Overpass, routing, ETA, GPS, physical travel, opening-hours verification, arrival, booking, payment, or formal PlanVersion claim is made by this controlled path.

## Focused proof

| Check | Result |
| --- | --- |
| `pytest -q backend/tests/test_r93_explicit_city_center_and_private_session.py` | 1 passed |
| authoritative `npm run test:e2e -- --project=chromium e2e/r93-explicit-city-center-private-session.spec.ts` (run `r93-20261010-10`) | 2 passed (real seed + R93 browser scenario) |
| `npm run typecheck` | passed |
| `npm run typecheck:all` | passed |
| `npm run build` | passed; existing Vite chunk-size warning only |
| `python -m compileall -q backend/app backend/tests/test_r93_explicit_city_center_and_private_session.py` | passed |
| `git diff --check` | passed |

R93 is **CONTROLLED_PRODUCT_PATH_PROVEN** for explicit public-center onboarding and same-tab signed-session fail-closed behavior. Real provider availability, mobile OS GPS prompts, physical travel, current opening, route feasibility, and arrival remain **UNVERIFIED**.
