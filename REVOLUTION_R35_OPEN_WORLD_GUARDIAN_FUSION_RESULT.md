# R35 Open World Guardian Fusion — Result

## Closure identity

- Taskbook commit: `835478598318f9733d373bd5ed602278c72d0f8e`
- Source before the one-time live pulse: `73a76317a2c871b9cc5ea8a62f204b434f1a02c6`
- Journey: `70b48ebc-991d-4708-bfbb-264e94e09103`
- Active plan before/after: `ac5549e2-ae83-5018-b529-ad74744f4b38`
- Standing Guardian mission: `3bb2c692-2ac1-407e-9998-6a30117f8772`
- GuardianPulse: `03e09fbb-6bd5-4cb3-be9d-f3b49c032f2e`
- One bounded pulse was executed; no recurring worker was started.
- Database receipt: `backend/r28-live-7e97c58ce161ea56.sqlite3`

## Live provider and context result

The pulse captured weather and mobility through live providers (`open-meteo` and the live mobility mesh). Provider observations were persisted with `LIVE_PROVIDER` provenance and `degraded=false`.

The context watch returned `NO_MATERIAL_CHANGE`:

- Two active activities were checked with exact Place + provider entity binding.
- Both verified intervals were `OPEN_COMPATIBLE`.
- No material conflict, unknown/degraded item, recovery Event, or plan mutation was produced.
- `agent_started=false` and context-watch mutation count was `0`.
- Final active plan remained `ac5549e2-ae83-5018-b529-ad74744f4b38`.

The persisted latest-pulse projection was read back from `/api/v1/journeys/{journey_id}/guardian/pulse/latest`. The Live Recovery surface rendered `CHECKED_ALL_CLEAR` with ordinary traveller copy and no internal status enum.

## Strict acceptance finding

The live receipt also contains one pre-existing `OPPORTUNITY_WINDOW` event created by the R28 setup path. The aggregate Guardian scan treated that event as actionable and started one external Hermes AgentRun:

- GuardianRun: `75f1950a-49ae-4ebd-be81-c382a9e4685e`
- decision: `RECOVERY_REQUIRED`
- action: `MODEL_NO_ACTION`
- AgentRun: `720bbf9f-87f6-425e-abc4-8987d21ac28d`
- proposal: none
- mutation: none

This AgentRun was not caused by the live weather, mobility, or Place context result, but it means the literal “no material change starts no recovery Agent” acceptance condition was not met by this historical receipt. The live context result itself stayed all-clear and mutation-free.

The product path is now corrected: bounded live pulses call Guardian scanning with opportunity signals excluded, while the separate Guardian scan endpoint keeps opportunity-window behavior. A regression test confirms an existing opportunity event produces `NO_ACTION` with no AgentRun on the live-pulse path. This fix was not re-run against the immutable one-time live receipt.

## Verification

- R35 backend focus: `13 passed` (context watch, Guardian evidence, pulse persistence/lifecycle).
- Pulse opportunity isolation regression: `4 passed` with the focused Guardian model tests.
- Frontend `npm run typecheck`: passed.
- Narrow Playwright R35 suite with the project Python: `3 passed`.
- Broader authority/runtime set: `75 passed, 1 failed`; the remaining failure is the pre-existing solver runtime expectation (`ORTOOLS_CP_SAT_V2` expected, `CITYNEXUS_SOLVER_V2_ENUMERATION` observed) in `test_guardian_v4.py`, unrelated to R35 changes.
- R32, R33-1, and R34 live closures were not rerun.
- No physical travel was claimed.
