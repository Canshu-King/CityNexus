# Revolution R80 — Private Buddy Navigation Result

## Delivery

- Implementation commit: `50eeef97fe07a44ed7a3193b7c867df99c0ca637`
- Local working branch: `codex/revolution-r63-planned-parallel-journey`
- Intended remote branch: `gpt/revolution-r33-open-world-journey-adaptation`
- Base: `226619eec63386d0d8b676e7009883b1b1b8e329`

The result report and authoritative Playwright provenance are delivered in the follow-up report commit. No default branch or `commander/control` branch was changed.

## Product behavior

Each signed helper/requester can independently consent to one foreground location sample for the currently accepted R79 handoff, then separately consent to send that precise origin once to a configured routing provider. The sample is marked `BUDDY_HANDOFF_ROUTE_PRIVATE`. It is excluded from shared presence, launch-origin, shared route, transit, stay and offline-snapshot projections. Generic route and side-quest entry points reject reusing this private sample.

The route targets the immutable accepted handoff Place snapshot and supports WALK only. Responses and legacy operation reads are signed-member-bound and omit the observation ID, origin coordinates and geometry. Revocation, expiry, membership or active-plan/cursor changes make the route unavailable. The original shared stop remains unchanged and is named in the private card; route success is not arrival proof and does not trigger Guardian.

Location capture alone contacts no provider and creates no route operation. A missing provider or unsupported evidence produces `UNKNOWN / ROUTE_UNAVAILABLE`; no mock duration is substituted. Captured replay is labelled historical. The UI retains the separately consented public-place pin.

## Verification

- Focused backend group: `52 passed` across R80, R79, grounded presence, grounded launch-origin/setup and in-transit reroute tests.
- `python -m compileall -q app tests`: passed.
- `npm run typecheck:all`: passed.
- `npm run build`: passed. Vite emitted its existing large-chunk advisory.
- Authoritative signed-member Chromium run: `2 passed` (real-seed prerequisite plus the R80 three-context test) in 14.5 seconds, with a fresh SQLite database, AI disabled, and no borrowed server. The R80 test exercised signed A/B/C contexts, independent location and provider consents, current-route reads, shared Operator/offline-snapshot privacy, unchanged plan/cursor, and revocation.
- `git diff --check`: passed.

## Isolated R80 Playwright database

Database: `backend/_r80relay20261009_1750.db`

Run ID: `r80relay20261009_1750`

Captured at: `2026-10-09T02:47:20.805Z`

| Evidence | Count / result |
| --- | ---: |
| R79 handoffs | 1, final status `REVOKED` |
| Location observations | 2, both `BUDDY_HANDOFF_ROUTE_PRIVATE` |
| Route operations | 2, both `UNAVAILABLE / ROUTE_UNAVAILABLE` |
| Provider calls | 0 |
| Shared MobilityFacts | 0 |
| Agent runs | 0 |
| Guardian runs / pulses | 0 / 0 |
| Journey outcome events | 1 `ACTIVITY_STARTED`, created by the demo `/start` setup before R80; none from route acquisition |

The selected public handoff fixture was `Riverside Museum`, evidence grade `DEMO_FIXTURE_NOT_LIVE_VERIFIED`; opening hours, accessibility and route feasibility remain UNKNOWN. No live routing provider was configured, so no LIVE provider result is claimed. A focused backend case verifies `CAPTURED_REPLAY` remains `REPLAY` and that a mock provider with a forged live provenance/receipt still projects as UNKNOWN.

## Test commands

```text
pytest tests/test_r80_private_buddy_route.py tests/test_grounded_presence.py tests/test_grounded_launch_origin.py tests/test_launch_setup_projection.py tests/test_in_transit_reroute.py tests/test_r79_buddy_rescue_handoff.py -q --tb=short
python -m compileall -q app tests
npm run typecheck:all
npm run build
npm run test:e2e -- --project=chromium e2e/r80-private-buddy-route.spec.ts
git diff --check
```
