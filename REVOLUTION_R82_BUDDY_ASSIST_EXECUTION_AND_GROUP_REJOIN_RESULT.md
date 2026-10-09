# Revolution R82 — Buddy Assist Execution and Group Rejoin Result

## Scope and source state

- Work branch: `codex/revolution-r63-planned-parallel-journey` (pushed to `gpt/revolution-r33-open-world-journey-adaptation`).
- Starting local and fetched remote HEAD: `d615050826c86fd1483d6b5dcf832abe2bf11204`.
- Implemented the requirements in `REVOLUTION_R82_BUDDY_ASSIST_EXECUTION_AND_GROUP_REJOIN_TASKBOOK.md`; did not run archival R58–R80 campaign suites.

## Product behavior delivered

- R79 location proposals keep their original strict 20-minute deadline. A helper may offer a bounded 30-, 60-, or 90-minute execution window. The requester must separately accept that exact window; only then is the execution lease started. An already accepted legacy handoff uses a new helper offer and requester acceptance rather than gaining time retroactively.
- The durable pair execution binds both in-force members and signed travelers, the original handoff/help/acknowledgement, both public Place snapshots, the member audience, original active plan and cursor, both consent timestamps, finite expiry, status, and idempotency data. The R78 help signal and R79 proposal may expire while a still-valid execution lease remains active. Explicit revocation closes the pair execution and does not resurrect it.
- Each participant can submit one signed, idempotent `BUDDY_MET_ACK`, `CANNOT_MEET`, or `CANCEL_PARTICIPATION` receipt for their own participation. Only two independent `BUDDY_MET_ACK` receipts create `MUTUALLY_ACKNOWLEDGED_ASSIST_NOT_PHYSICALLY_VERIFIED`. The UI states that this is self-reported and does not prove physical arrival. A single `CANNOT_MEET` receipt instead produces `REPLAN_REQUIRED` and offers fresh help coordination.
- A later member D does not receive the A/C handoff or execution projection. Pair reads and reports do not mutate the shared plan, create a Journey outcome, invoke a provider, or start Agent/Guardian work.
- After an eligible pair outcome, each participant can separately consent to send only the current public shared-stop WGS84 destination to Google Maps for walking directions. The UI rechecks the pair outcome, active shared plan/cursor, membership projection, and destination just before release. A stale cursor closes the consent and sends no URL; the stale execution view offers fresh help coordination.

## Focused verification

| Check | Result |
| --- | --- |
| `backend\\.venv\\Scripts\\python.exe -m pytest tests\\test_r80_private_buddy_route.py tests\\test_r81_private_location_binding.py tests\\test_r82_buddy_execution.py -q --tb=short` | **21 passed** |
| `npm run typecheck:all` | Passed |
| `npm run build` | Passed; Vite reported the existing large-chunk size warning |
| `backend\\.venv\\Scripts\\python.exe -m compileall -q app` | Passed |
| `git diff --check` | Passed |
| Fresh authoritative isolated SQLite Chromium run `r82-20261009-123052`: `npm run test:e2e -- --config=playwright.config.ts e2e/r82-buddy-assist-execution.spec.ts --project=chromium` | **2 passed** (real-product seed + signed A/B/C/D browser closure) |

The browser closure used `CITYNEXUS_E2E_PORT=43251`, `CITYNEXUS_BACKEND_PORT=43252`, AI disabled, and a new database at `backend/_r82-r82-20261009-123052.db`. It creates a signed helper A, existing bystander B, requester C, and later member D. It independently accepts a 60-minute window, expires the R79 proposal and R78 help signal in the isolated database, confirms that A/C still have the pair execution while B/D have no pair card or handoff identifiers, then records the two separate self-reports.

Recorded execution: `935ad7d4-4c53-4e5c-84b7-a2f496e17af3`; status `MUTUALLY_ACKNOWLEDGED`; outcome `MUTUALLY_ACKNOWLEDGED_ASSIST_NOT_PHYSICALLY_VERIFIED`; agreed window 60 minutes. Two distinct member-owned `BUDDY_MET_ACK` receipts were persisted. The execution began at `2026-10-09T04:31:06.248497+00:00` and was set to expire at `2026-10-09T05:31:06.248497+00:00`, while the R79 handoff and R78 signal were already expired. The test verified that PlanVersion and cursor were unchanged by the pair reports. It then opened a separate destination-only directions consent and changed the cursor while that consent was open; the expected Google Maps request was blocked. The original cursor was `3a58c470-524c-5854-aa39-6c37a350eb80`; the deliberate stale-consent test cursor became `abe4e842-249e-516f-ac43-b41695083792`; active PlanVersion remained `55523d40-cafe-5bd2-b30a-de057ec7a839`.

Before and after the browser actions, the test asserted equal counts for `plan_versions`, `route_acquisition_operations`, `provider_calls`, `agent_runs`, `guardian_runs`, `guardian_pulses`, and `journey_outcome_events`. Final isolated DB counts were respectively **1, 0, 0, 0, 0, 0, 1**. The pre-existing single Journey outcome remained unchanged. The Google Maps request was intercepted locally, contained the public destination and `travelmode=walking`, and contained no `origin`; no real Google Maps navigation is claimed. Backend R81 location capture after the R79 proposal expiry also remained `CALLER_PRIVATE` and reported `external_provider_contacted=false`.

## GPT review follow-up

The subsequent web GPT review identified a real lifecycle gap: after the R79 offer's 20-minute expiry, the active pair execution still remained valid but the static handoff pin and external handoff directions were checked against the old offer expiry. The inverse risk was that a cancelled, expired, or stale execution could leave those old actions visible. The UI now treats an active, current finite execution lease as the navigation authority; it hides the handoff map, external directions, and private route start after the execution closes, and rechecks the active execution, current PlanVersion/cursor, member audience, and public Place before release. The copy distinguishes the original offer expiry from the active execution-window expiry. The R82 browser closure now explicitly opens and intercepts both the OpenStreetMap handoff pin and Google Maps handoff walking URL after the original offer has been expired, then confirms both old handoff actions disappear after the two member acknowledgements.

Fresh authoritative run after that fix: `r82-review-20261009-124526`, frontend `43271`, backend `43272`, database `backend/_r82-r82-review-20261009-124526.db`; the real-seed setup and the signed A/B/C/D closure both passed (**2 passed**). The same focused backend suite remains **21 passed**, with typecheck, build, compileall, and diff-check passing again. The build retains only the existing large-chunk warning.

## Push and GPT review

The initial R82 implementation and this result were committed and pushed to the same Revolution branch. The lifecycle correction from the GPT review is now included in the follow-up commit and will be pushed to the same ref after the final checks above. All web GPT inspection, authorization, and response reading in this cycle was performed with `chrome-use` in the existing `moodle` project conversation.
