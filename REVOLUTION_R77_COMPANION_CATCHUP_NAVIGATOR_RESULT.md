# Revolution R77 — Companion Catch-Up Navigator Result

**Implementation/result SHA:** `1d1eb251aa6875666f3a0fa2b3c394f1b1b26174`

**Local branch:** `codex/revolution-r63-planned-parallel-journey`

**Push target:** `origin/gpt/revolution-r33-open-world-journey-adaptation`

## Delivered

The active Journey catch-up card now lets an in-force member explicitly request a one-time foreground location sample and a route to the current shared-plan stop. The consent explains that the observation is retained, may change companions' coarse group-presence view, and may send the exact origin to the configured routing provider. It also states the Guardian/risk possibility, no background sampling, no plan mutation, and that a route is not an arrival report. Cancel leaves the public map fallback available.

The route endpoint and UI bind the response to the signed member's fresh, accurate Journey observation, active PlanVersion, execution cursor, exact public Place and validated WGS84 coordinates. Unknown or invalid destination CRS fails before route acquisition. The response carries the target binding, provider provenance and receipt time; the UI rechecks the plan and destination before location capture, after capture, and after routing. A changed projection discards the old result and prevents stale map release.

Grounded captured replays are labelled historical and are not presented as current traffic. Untrusted, stale, fixture, mock or otherwise unknown evidence is shown as `UNKNOWN / ROUTE_UNAVAILABLE` with no duration. The result includes route source, evidence, receipt time, location authority and the actual returned risk/Guardian status. It distinguishes the planned destination from the group's physical location.

The R62 followthrough edge is covered: accepting a new member during an in-force recovery leaves the original required-member set and PlanVersion intact, requires explicit membership reconfirmation, and does not count the newcomer as an arrival or close the recovery.

## Focused verification

All commands below completed with exit code 0.

- Backend: `backend\.venv\Scripts\python.exe -m pytest tests\test_r76_journey_membership_invitation.py -q` — **8 passed**. Covers R76 acceptance, R77 route identity/freshness/target binding, fail-closed unknown CRS, privacy projection, and R62 recovery followthrough.
- Frontend: `npm run typecheck:all` — passed.
- Frontend: `npm run build` — passed. Vite emitted its existing large-chunk advisory; it did not fail the build.
- Python: `backend\.venv\Scripts\python.exe -m compileall -q app` — passed.
- Diff: `git diff --check` — passed.
- R76 regression: `e2e/r76-companion-join-catchup.spec.ts`, Chromium, `--no-deps --grep 'R76 lets a signed nonmember'` — **1 passed** in an isolated authoritative run (`r77_r76_regression_20261009`).
- R77 closure: `e2e/r76-companion-join-catchup.spec.ts`, Chromium, `--no-deps --grep R77` — **1 passed** in an isolated authoritative run (`r77_companion_20261009h`, AI disabled, fresh SQLite database, owned frontend/backend ports).

The R77 browser test used three signed test contexts (owner, existing companion and newly invited companion). It verified C's own UI acceptance, no location/route request before consent or after cancel, two explicit observation-to-route-ID bindings, historical `CAPTURED_REPLAY` display, and a `SYNTHETIC_FIXTURE` result with a supplied 999-minute duration displayed only as UNKNOWN with no minutes. A and B's operator projections contained neither C's observation IDs nor the test origin coordinates; their views did not report C as arrived.

The freshness UI test supplied a changed PlanVersion/cursor through a controlled operator-projection response while consent was open. It verified that routing captured no third location and that map release closed its blank popup instead of opening the stale Place. This part is a projection fixture: direct active shared-plan selection correctly returned `409 COLLECTIVE_TRADEOFF_UNRESOLVED`, so the test did not bypass collective mediation or claim a real plan mutation.

## Isolated run evidence

For `r77_companion_20261009h`, the database recorded exactly **2** Journey-bound location observations. The initial and final database values were identical:

- PlanVersion: `55523d40-cafe-5bd2-b30a-de057ec7a839`
- Execution cursor: `3a58c470-524c-5854-aa39-6c37a350eb80`

Database counts: `RouteAcquisitionOperation=0`, `ProviderCall=0`, `ProviderObservation=0`, `AgentRun=0`, `AgentRunStep=0`, `GuardianRun=0`, `GuardianPulse=0`, and `Event=0`. The two browser route replies were controlled fixtures; the real provider route endpoint was not called in the browser run. The backend route endpoint's binding behavior was separately exercised by the focused backend regression with a frozen route-operation stub.

The location was a Playwright geolocation fixture in the isolated local test. The signers are per-run test HMAC identities, not production identity-provider evidence. No live GPS, real external route provider, traffic freshness, physical co-location, or arrival was verified.

## Follow-up boundary

The optional coarse “I'm coming” status remains **BLOCKED / separate follow-up**. Existing R62 arrival reports and R69 meetup handshakes have different meaning and authority; the inspected APIs do not provide a Journey-wide current-stop `ON_MY_WAY` signal with member binding, idempotency and withdrawal. R77 therefore completes the consented own-location route path and does not infer or write a heading or arrival report.
