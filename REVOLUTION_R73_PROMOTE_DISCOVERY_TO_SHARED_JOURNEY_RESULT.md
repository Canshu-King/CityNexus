# Revolution R73 Result — Promote a Discovery Into the Shared Journey

## Delivery

- Implementation commit: `47918f514c4b93398e9f33e9f3b34c7ab63d7845`
- Source branch: `codex/revolution-r63-planned-parallel-journey`
- Push target: `gpt/revolution-r33-open-world-journey-adaptation`
- Result report commit: the commit adding this file; its SHA is reported in the relay handoff.

R73 adds an explicit shared-stop proposal to the accepted-place board. The server derives the canonical Place, active Journey plan, current rendezvous, and required member set; members choose a 10/20/30-minute dwell, review one candidate, and decide independently. Members outside the temporary invitation group are included. Declines leave the active plan unchanged. A fully approved proposal still requires an explicit authenticated apply, which uses the existing authoritative replan acceptance path to create one successor PlanVersion.

The flow revalidates the plan, membership, cursor, proposal epoch, route evidence, and protected commitments before apply. It adds exactly one shared Place activity and carries the C4 rendezvous commitment to the successor plan. The R72 progress-share race is also closed: each confirmation is bound to a server-derived accepted-member audience token; a changed audience returns a conflict and requires renewed consent.

## Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_r64_member_side_quest.py -k "r72 or r73" -q --tb=short` — **5 passed, 39 deselected**.
- `npx playwright test --config=playwright.r73.config.ts` from `frontend` — **1 passed** in a fresh isolated signed A/B/C browser flow; run `46fd429e7f9f41ce8950edca08c9ecc6`.
- `npm run typecheck:all` — passed.
- `npm run build` — passed; Vite emitted its existing large-chunk advisory.
- `backend\.venv\Scripts\python.exe -m compileall -q backend/app backend/tests` — passed.
- `git diff --check` — passed.

The browser run used an isolated SQLite database, AI disabled, and no server reuse. Its dedicated loopback-only fixture server labels route facts `R73-TEST-REPLAY-EXPLICIT-FIXTURE` / `EXPLICIT_FROZEN_FIXTURE`. The UI acceptance path used three signed test identities; the test shim grants them `OWNER` so the existing `JOURNEY_UPDATE` authority can be exercised. Normal `COLLABORATOR` permissions are unchanged.

## Persisted browser evidence

Database: `frontend/_r73_46fd429e7f9f41ce8950edca08c9ecc6.db`.

- Plan `55523d40-cafe-5bd2-b30a-de057ec7a839` (v1) is `SUPERSEDED`.
- Plan `526f3940-ab14-403d-b7d2-6d748ecaf924` (v2) is the sole `ACTIVE` plan.
- Promotion `cd8c7314-274d-41df-a75c-8a1b92601343` is `APPLIED`; the exact catalog Place `place-city-park` appears once as a visit in v2.
- The active C4 rendezvous commitment remains attached to an activity in v2.
- The active plan records only explicit frozen replay facts for this promotion. AgentRuns: 0; ProviderCalls: 0; route-acquisition operations: 0.

## Evidence boundary

This is a controlled `TEST_REPLAY` acceptance of the local CityNexus public Place catalog entry `place-city-park` (`mock-city`), not a live OSM lookup or live route-provider result. No device GPS permission or physical-presence proof was used. The result demonstrates the governed code path and persisted PlanVersion transition; it does not claim live navigation or real-world arrival validation.
