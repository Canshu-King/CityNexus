# Revolution R81 — Real Buddy Route and Safe Return Result

Implementation commit: `6ce1273296b3201ad42f6ee78b047359dd736716`  
Result checkpoint SHA: pending report-record commit  
Branch: `codex/revolution-r63-planned-parallel-journey`  
Prior and pushed base: `1d86111108f04c622b38098d1fc58292408e57a2`  
Remote destination: `origin/gpt/revolution-r33-open-world-journey-adaptation`

## Delivered

- Every R80 private location capture now gets an immutable database binding to its exact accepted handoff, signed member and traveler, active plan and cursor, destination snapshot hash, audience, acceptance time, capture time, and expiry. Legacy observations without that receipt fail closed. Coordinates and observation IDs stay out of group audit and Operator projections.
- Each consented route action records separate private legs from the caller to the accepted handoff and from that public handoff to the current shared-plan stop. Both legs retain their own operation and provider receipt. Reads revalidate the exact capture and current context; an expired binding returns typed `STALE`, not `NOT_REQUESTED`.
- The route path rechecks the accepted handoff, member, plan, cursor, destination, and capture after outbound provider work and before releasing the return request. A separate-session revocation test confirms that revocation after the first operation prevents the second provider request and returns no ETA.
- Protected-commitment risk stays `UNKNOWN` unless both required legs are credible, except where one fresh, receipt-verified `LIVE` leg alone already proves the commitment cannot be met. In that case the UI keeps the risk visible and offers return to the shared stop or authorized group recovery. Reads do not mutate the plan or invoke Guardian.
- The accepted handoff card offers a separate, per-person consent for destination-only Google Maps walking directions. It sends the exact current public WGS84 destination, not CityNexus's stored origin. The UI refreshes both the pair handoff and shared-plan cursor immediately before release; stale consent closes the blank popup without sending a destination. The existing static public pin remains separate.
- Loopback and reserved Valhalla test endpoints, plus deployments explicitly configured with `CITYNEXUS_LIVE_VALHALLA_TEST_PROVIDER=true`, are classified as `TEST_PROVIDER_EMULATOR`. This provenance cannot enter live readiness or be promoted to `LIVE` by a successful-looking receipt.

## Verification

### Focused backend

- `pytest tests/test_r80_private_buddy_route.py tests/test_r81_private_location_binding.py -q --tb=short` — **14 passed** on a new isolated SQLite database.
- `pytest tests/test_provider_runtime_gate.py -k 'prt08 or loopback_and_reserved' -q --tb=short` — **3 passed**. The tests cover `.test` and loopback emulator classification and rejection from live readiness.
- The controlled two-leg C4 case used test-only durations of 8 and 10 minutes against a commitment 15 minutes away with a 5-minute buffer. It returned `COMMITMENT_AT_RISK` with `evidence_scope=TEST_ONLY`, retained separate leg requests, and created no plan or Guardian side effects.
- The expiry and revoke-during-outbound tests return `STALE`; the latter uses a second SQLAlchemy session to revoke the handoff after the outbound operation commits and verifies that no return operation is submitted.

### Fresh signed Chromium

Authoritative command:

```text
npm run test:e2e -- --config=playwright.config.ts e2e/r79-buddy-rescue-handoff.spec.ts e2e/r80-private-buddy-route.spec.ts --project=chromium
```

Result: **3 passed** (one real-seed setup and two Chromium scenarios) using a new isolated SQLite database, frontend port `47151`, backend port `47152`, external AI disabled, and no reuse of port `8000`. Provenance is recorded in `reports/e2e-provenance/authoritative.json`.

The signed three-context flow kept the bystander out of the private handoff, captured separate caller-only locations for both participants, and verified each separately consented route request. The directions scenario intercepted both destination-only Google Maps URLs, verified the exact WGS84 destination and walking mode with no origin parameter, and confirmed that a changed cursor sends no map request. Interception aborted the external map requests; no external map visit or real navigation is claimed.

Final isolated R80 database counts: 2 private location observations; 4 private route operations (2 `TO_HANDOFF`, 2 `RETURN_TO_SHARED_STOP`); all 4 `UNAVAILABLE / ROUTE_PROVIDER_NOT_CONFIGURED`; 0 `ProviderCall`, 0 `MobilityFact`, 0 `AgentRun`, 0 `GuardianRun`, and 0 `GuardianPulse`. The shared plan remained at one `PlanVersion`; route-specific backend assertions confirm no plan, event, outcome, or Guardian side effects. No observation IDs or tested precise-coordinate markers appeared in group audit `after_json`.

The selected destination remains `DEMO_FIXTURE_NOT_LIVE_VERIFIED`; opening hours and accessibility are `UNKNOWN`. With no configured route provider, server route times and overall feasibility remain `UNKNOWN`. This run does not establish production identity-provider behavior, real Valhalla routes, external-map completion, physical arrival, or rejoining the group.

### Static checks

- `tsc -p tsconfig.typecheck.json --noEmit` — passed.
- `vite build` — passed; Vite reported the existing large-chunk warning.
- `python -m compileall -q app` — passed.
- `git diff --check` — passed.

## Out-of-scope test failure observed

`pytest tests/test_provider_runtime_gate.py -k prt09 -q --tb=short` remains red in a fresh SQLite run: `test_prt09_twin_reports_selected_plan_frozen_mobility_without_c4_commitment` expects one `used_edge_ids` entry but the twin projection includes four additional seeded-plan edges. This check is outside the R81 route/session changes and was left unchanged; it is not counted as an R81 pass.

## Result checkpoint

The R81 implementation is committed as `6ce1273296b3201ad42f6ee78b047359dd736716`. The exact result checkpoint SHA will be filled in by the follow-up commit that records this report commit.
