# Revolution R89 — Mobile-safe real POI next action

## Review and evidence boundary

- R89 taskbook reviewed at GPT remote HEAD `f64a40a67` (`docs(revolution): R89 mobile-safe POI maps and actionable opening evidence`).
- R88 was accepted at `35fc69dd023acbe2c7263bbbc48b300719926f8e` as `CONTROLLED_PRODUCT_PATH_PROVEN`.
- R87 remains the only genuine live Overpass discovery. R89 made **zero new real provider discovery attempts** and did not rerun R58–R88 archives.
- Implementation commit: `abaa64861` (`feat(revolution): make POI exploration mobile safe`).

## Mobile-safe public map release

`BootstrapDiscoveryPanel.confirmMapPreview` now reserves an `about:blank` tab synchronously while the user click still has activation, immediately clears its opener, and only navigates it after the signed server preview response passes client-side identity checks:

- receipt ID and candidate ID must match the pending card;
- returned WGS84 coordinates must match within `1e-6`;
- URL must be HTTPS on `www.openstreetmap.org`, include only `mlat`/`mlon` plus a `#map=` fragment, and contain no `origin` or `query` parameter.

If a mobile browser blocks the pre-opened tab, the already-authorized destination is rendered as a normal `Open authorized public map` link. A stale response, identity mismatch, invalid URL, or server refusal closes the reserved tab and never navigates to an unvalidated destination. Cancelling the consent panel makes no preview request and opens no window.

The fallback for provider-unavailable/disabled discovery is now limited to a manually supplied public map center. A foreground GPS search never gets a map-center link, so a precise foreground fix cannot escape through an error fallback.

## Evidence and source safety

The card displays the source identity (`OpenStreetMap/Overpass` plus the OSM external ID), captured timestamp, raw `opening_hours`, and the public website/contact tags as untrusted claims. React text rendering escapes the values. Website links are created only for HTTPS URLs without credentials; `javascript:`, `data:`, malformed, and other unsafe schemes remain text. Every website link is labelled as an unverified OSM-provided site. A source-page click never promotes `UNKNOWN` to `VERIFIED_PROVIDER`; the card and preview continue to say `EXTERNAL_NOT_ATTESTED`.

The existing official-facts verifier is a `Place`-scoped flow (`POST /facts/acquire`) and is not a legitimate exact-candidate verifier before the strict unknown-opening selection gate. R89 therefore does not invent a verifier, scrape arbitrary OSM tags, or cross the native PlanVersion gate. The explicit `Continue exploring without committing` action keeps the signed DRAFT Journey useful and offers another search without creating a Place or plan.

## A/B private scope repair

`RealPlaceCandidate` still keeps one deterministic `(Journey, provider, OSM identity)` row, but its evidence now carries independent `bootstrap_scopes` for each signed member/traveller/receipt. A second member receiving the same public OSM identity is no longer dropped. Each response is filtered by its own scope, each preview/selection validates that exact scope, and scoped distance is used so one member's public-center distance cannot leak to another. A member's next search removes only that member's scope; it does not delete another member's private receipt.

## Counts and state deltas

The preview and explore-first paths create no `Place`, `PlanVersion`, `Activity`, route, `Agent`, `Guardian`, `Booking`, `Order`, `PaymentTransaction`, or provider discovery attempt. Controlled tests keep the Journey at zero Places and zero PlanVersions while opening the source-linked public map. The only provider calls in the focused backend fixtures are the single monkeypatched discovery call per test Journey; no network call is made.

## Focused proof

| Check | Result |
| --- | --- |
| `pytest -q backend/tests/test_r88_real_poi_exploration.py backend/tests/test_r89_member_shared_osm_identity.py` | 2 passed |
| `npm run test:e2e -- e2e/r89-mobile-real-poi-next-action.spec.ts --project=chromium` | 2 passed (setup + mobile-sized Chromium flow) |
| `npm run typecheck` | passed |
| `npm run build` | passed; existing Vite chunk-size warning only |
| `python -m compileall -q backend/app backend/tests/test_r88_real_poi_exploration.py backend/tests/test_r89_member_shared_osm_identity.py` | passed |
| `git diff --check` | passed |

The browser proof covers consent cancellation, automatic-tab success, popup rejection with the authorized-link fallback, stale-release refusal, no unsafe website link, `EXTERNAL_NOT_ATTESTED`, and the unchanged native selection gate. The backend proof covers receipt/member/coordinate checks, no materialization, and same-OSM-identity A/B isolation.

## Evidence grade and next handoff

R89 is **CONTROLLED_PRODUCT_PATH_PROVEN** for a signed mobile-safe public POI preview and a useful explore-first next action. It does not claim current opening, route feasibility, physical arrival, booking, or Journey start. Code and this report are ready to push to `gpt/revolution-r33-open-world-journey-adaptation`.
