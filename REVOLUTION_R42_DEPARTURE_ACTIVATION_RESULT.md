# CityNexus Revolution R42 — Departure Activation & Confirmed Journey Launch

## Fresh closure

- Source HEAD: `273b8c5a641ad561c85af15fe6e76945c3614794`
- Fresh Journey: `77eb5360-5fba-4b45-a647-e9235ca7eab4`
- Active plan before/after: unchanged
- Closure: `DEPARTURE_CONFIRMED_EN_ROUTE`
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`

The setup used one real Valhalla-backed R41 Route Session. The execution clock was frozen only for deterministic activation timing; the provider was not called again.

## Activation and confirmation

- Target activity: `9727d527-1f2d-5caa-8979-81128751319e` (`依水園`)
- R41 exact route: `real-place-b47a20314c81d5a81381d4a4 → real-place-22cf72809897ff4c7f312fcf`, WALK, 22 minutes
- Provider/provenance: `valhalla-http` / `LIVE_PROVIDER_CAPTURE`
- `must_leave_by`: `2026-10-07T08:39:00+08:00`
- Activation: `DUE_NOW`, `minutes_to_leave=-5.0`
- Cue: one `DEPARTURE_ACTIVATION` notification, one dedupe key, occurrence `1`
- Authenticated principal: signed HMAC bearer, OWNER JourneyMember
- Departure action count: exactly `1`
- Request truth: `OPERATOR_CONFIRMED_EXECUTION`, `operator_confirmed=true`
- Activity: `ACTIVE → EN_ROUTE`
- Execution truth actor: `AUTHENTICATED_TRAVELER`; physical presence was not asserted
- Journey phase: `APPROACHING_NEXT → IN_TRANSIT`
- Outcome history: `ACTIVITY_DEPARTED` recorded; material `Event` rows remain `0`

The offline snapshot records `departure_activation`, confirmed departure, EN_ROUTE execution truth, and captured-at metadata. After departure, the old planned launch origin is no longer used as the active execution context; the R41 route fact remains byte-for-byte equivalent in the receipt before/after comparison.

## Safeguards and verification

- Activation bands, blocked CTA suppression, cue dedupe, and band change: passed.
- Authenticated strong execution, missing confirmation, unauthenticated confirmation, and simulation boundary regressions: passed.
- R41 route/session, launch-origin, readiness, presence, adaptive watch, Guardian phase, R28 truth/auth, and V12 execution regression: **90 passed**.
- Python compileall: passed.
- Frontend TypeScript: passed.
- Focused Playwright attempt was blocked before tests by the local Python 3.10 backend launcher (`enum.StrEnum` unavailable); no product assertion was recorded as passing.
- Event / AgentRun / proposal / plan-mutation counts after departure: `0 / 0 / 0 / 0`.

Machine receipt: [backend/output/r42-departure-activation-v1.json](D:/moodle/CityNexus-Revolution-RealTrip-Recovery/backend/output/r42-departure-activation-v1.json)
