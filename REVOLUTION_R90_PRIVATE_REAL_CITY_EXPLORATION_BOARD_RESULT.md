# Revolution R90 — Private real-city exploration board

## Review and implementation boundary

- R90 taskbook reviewed at GPT remote HEAD `1530230fe1b3bc1a3adc026b943266f6aa771d05` (`REVOLUTION_R90_PRIVATE_REAL_CITY_EXPLORATION_BOARD_TASKBOOK.md`).
- R89 remains accepted for the mobile-safe public map release and A/B private candidate scopes. R90 made no new live Overpass request and did not rerun the R58-R88 campaign history.
- Implementation commit: `1ce20b9f1d5cfa3b48b04b7b884d07eb092e6a7a` (`feat(revolution): add private real-city exploration board`).

## User-visible capability

An authenticated member of a DRAFT Journey can now keep a private, persistent exploration board:

1. The candidate card has an intentional `Save to private shortlist` action. The board is capped at three public places and has `Remove`, `Open this public destination`, and source links.
2. The server stores only the saved public identity, WGS84 coordinates, source URL/provenance, capture time, public opening/cost evidence, and a manual-center straight-line distance when that distance came from an expressly manual public center. Foreground GPS, query text, precise search center, other members' receipts, and unsaved candidates are not copied into the member board.
3. The board is restored by a member-scoped GET after reload. A changed bearer identity clears the in-memory viewer state before loading the new member's server-scoped list.
4. Saved cards continue to state `OPENING_UNKNOWN`, `PRICE_UNKNOWN`, and `ROUTE_ETA_UNKNOWN` unless the retained public evidence says otherwise. A saved row never creates a `Place`, `PlanVersion`, visit proof, route ETA, booking, or payment authorization.
5. A saved card requests fresh per-release map consent and calls a separate saved-identity preview endpoint. It never reuses the expired discovery receipt. The response is destination-only and carries no receipt ID.

## Narrow security QA

- A single `RealPlaceCandidate` row still represents one public OSM identity, while each signed member gets an independent `bootstrap_scopes` entry with its own receipt, source kind, distance, and expiry. A compare-and-swap merge prevents concurrent A/B searches from overwriting one another's scopes.
- A member scope is checked before map preview or save. An expired shared row cannot make another member's scope valid; each member's own TTL is authoritative. A legitimately saved public identity remains usable through the separate shortlist preview after the candidate receipt expires.
- `validatedPublicMapUrl` now requires the exact HTTPS OSM origin and root path, one `mlat` and one `mlon`, no credentials, port, or extra query fields, and a numeric `#map=zoom/lat/lon` whose parsed WGS84 coordinates match the server-authorized destination within `1e-6`. Invalid or mismatched releases close the reserved tab and do not navigate.
- Shortlist rows are not included in offline merged/group/Operator projections. The list, save, remove, and preview endpoints resolve the signed Journey member and require a DRAFT Journey with no PlanVersion.

## Controlled Journey and state deltas

- Fresh controlled Chromium Journey used for the R90 browser flow: `79873fef-2cae-43e1-8e29-bb7349ad95f0`.
- The browser test used a controlled `TEST_PROVIDER` response and one named public OSM candidate. It saved the item, reloaded the page, restored the member board, opened the fresh-consent panel, and verified the destination URL.
- The focused backend A/B fixture used separate owner/viewer signed members on the same public OSM identity. Each member saw only its own shortlist. After both private scopes expired, the viewer's saved public identity still opened through fresh consent; the stale receipt endpoint returned `410`.
- Place delta: `0`; PlanVersion delta: `0`; Activity/route delta: `0`; Agent/Guardian/Booking/Order/Payment delta: `0`.
- Provider delta: two bounded controlled `TEST_PROVIDER` discovery calls in the A/B fixture (one per member), zero provider calls for save/list/remove or saved map preview, and zero new external Overpass attempts.
- A real device, current opening state, route feasibility, physical visit, booking, and payment remain **UNVERIFIED**.

## Focused proof

| Check | Result |
| --- | --- |
| `pytest -q backend/tests/test_r90_private_exploration_board.py backend/tests/test_r89_member_shared_osm_identity.py` | 2 passed |
| authoritative `npx playwright test e2e/r90-private-real-city-exploration-board.spec.ts --config=playwright.config.ts --project=chromium --reporter=line` | 2 passed (real seed + mobile R90 flow) |
| `npm run typecheck` | passed |
| `npm run build` | passed; existing Vite chunk-size warning only |
| `python -m compileall -q backend/app backend/tests/test_r90_private_exploration_board.py` | passed |
| `git diff --check` | passed |

The browser evidence covers save, persistence across reload, uncertainty labels, fresh saved-identity consent, destination-only request data, exact authorized coordinates, no receipt leakage, and remove. The backend evidence covers A/B privacy, per-scope expiry, stale receipt refusal, saved identity reauthorization, no materialization, and no extra provider activity.

## Evidence grade and next handoff

R90 is **CONTROLLED_PRODUCT_PATH_PROVEN** for a private three-item real-city exploration board with honest uncertainty and fresh public-map authorization. It does not claim a current opening, arrival, route, booking, or real-world visit. Code and this report are ready to push to `gpt/revolution-r33-open-world-journey-adaptation`.
