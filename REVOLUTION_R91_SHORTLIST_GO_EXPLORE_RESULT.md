# Revolution R91 — Turn a private shortlist into an actionable outing

## Review and implementation boundary

- R91 taskbook reviewed at GPT remote HEAD `b07041debde96a7448fd5280fc57f36001288e74` (`REVOLUTION_R91_SHORTLIST_GO_EXPLORE_TASKBOOK.md`).
- R90 was accepted as `CONTROLLED_PRODUCT_PATH_PROVEN` for the three-item member-private board. R91 made no new live Overpass request and did not rerun the R58-R90 campaign history.
- Implementation commit: `461718e429449cb68ee6861170338b3ec807603b` (`feat(revolution): make saved places actionable`).

## User-visible action

Each saved public POI now exposes two distinct actions:

1. `Inspect public map` keeps the R90 destination-only public pin release.
2. `Go explore this public place` shows the saved source and `OPENING_UNKNOWN`, `PRICE_UNKNOWN`, and `ROUTE_ETA_UNKNOWN` warnings, asks for fresh one-time consent, and launches a mobile-safe destination-only walking URL. The provider receives no stored origin, query, discovery receipt, or foreground GPS. The URL is validated as the exact saved WGS84 destination and contains `travelmode=walking` without `origin`.

The browser pre-opens a tab while the click still has activation, clears its opener, and falls back to the authorized destination link if the tab is blocked. The UI explicitly says that a navigation URL is not route feasibility, route duration, arrival, a visit, a booking, or a Journey start. `Back to exploration board` returns to the persisted shortlist without writing arrival or return state.

If the navigation URL is not safe, client validation rejects it and closes the pending tab. The existing public-pin action remains available as the honest map fallback. No external route calculation or provider request is made by CityNexus.

## Server authorization and privacy

- `POST /journeys/{journey_id}/bootstrap-shortlist/{shortlist_id}/navigate` is bound to the current signed member, the exact saved public identity and WGS84 coordinates, a DRAFT Journey, no PlanVersion, and fresh `public_map_consent=true`.
- The saved row survives discovery-receipt expiry, but no expired receipt is reused. A cross-member release is rejected with `403`; a Journey that becomes active or gains a PlanVersion is rejected before any external release.
- The walking response includes a destination-only Google Maps URL of the form `https://www.google.com/maps/dir/?api=1&destination=<LAT>%2C<LON>&travelmode=walking` and no origin. The public source and map pin remain available for inspection.
- The three-item limit is now serialized by a durable Journey-row write lock before the count and insert. Two concurrent saves cannot both observe slot three as free. The focused race test produced one success and one `BOOTSTRAP_SHORTLIST_LIMIT` `409`, with exactly three saved rows.
- Shortlist rows remain member-scoped and are absent from Operator/group/offline projections. No private query, precise location, center, unsaved candidate, or other member receipt is introduced into the release.

## Controlled Journey and deltas

- Fresh mobile Chromium Journey: `398933dd-ec11-4857-9151-5a877c99377c`.
- The browser scenario used a controlled `TEST_PROVIDER` candidate, saved it, launched walking directions after consent, checked the exact destination-only URL, and returned to the board.
- Focused backend coverage used separate signed members for privacy and a separate concurrent-save fixture. It verified cross-member rejection, expired-receipt-safe saved navigation, exact walking URL, and bounded concurrency.
- Place delta: `0`; PlanVersion delta: `0`; Activity/route/arrival delta: `0`; Agent/Guardian/Booking/Order/Payment delta: `0`.
- Provider delta: controlled `TEST_PROVIDER` discovery only (no live Overpass or routing calls); navigation and map releases perform no provider discovery attempt.
- Production mobile behavior, route feasibility, current opening, physical arrival, booking, payment, and real-world site visit remain **UNVERIFIED**.

## Focused proof

| Check | Result |
| --- | --- |
| `pytest -q backend/tests/test_r90_private_exploration_board.py` | 2 passed (privacy/expiry/navigation + concurrent three-item bound) |
| authoritative `npx playwright test e2e/r91-shortlist-go-explore.spec.ts --config=playwright.config.ts --project=chromium --reporter=line` | 2 passed (real seed + mobile R91 flow) |
| `npm run typecheck` | passed |
| `npm run build` | passed; existing Vite chunk-size warning only |
| `python -m compileall -q backend/app backend/tests/test_r90_private_exploration_board.py` | passed |
| `git diff --check` | passed |

R91 is **CONTROLLED_PRODUCT_PATH_PROVEN** for a saved public destination becoming an explicitly authorized, destination-only walking action while preserving uncertainty, privacy, and DRAFT Journey truth. Code and this report are ready to push to `gpt/revolution-r33-open-world-journey-adaptation`.
