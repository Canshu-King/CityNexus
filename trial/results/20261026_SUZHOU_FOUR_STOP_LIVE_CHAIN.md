# Suzhou: same-run four-stop native HTTP chain with one external Guardian execution

Product SHA: `724f44a084da738657603be402260c0f999412b9`; runtime checkout HEAD: `d79ee27c91a028695afcf420e4bbb635cf658bbf`. This receipt adds live acceptance evidence, without changing product code. Scope is the owned isolated database on backend 60622 / frontend 14522. No browser or physical-device acceptance is claimed.

## Outcome and exact binding

The same simulation run completed four distinct canonical Places, two on each local date, after a current-event external Guardian execution, authenticated native proposal acceptance, and resume. Normal stop/resume of the owned service against the same database/auth preserved the terminal state and acceptance result.

| Object | ID / result |
| --- | --- |
| Journey | `e7f868e4-2d03-4d3c-b563-962e47b185f4` |
| GoalTask | `ad695293-72e5-4482-9659-0784b98e829f` |
| SimulationRun | `7188e2e7-b216-47e0-b446-ebf747abdb83` |
| Current event | `605f34ef-d199-4ec1-9abf-bf0d471ee4f5`, SCHEDULE_DELAY 15 minutes, subsequently RESOLVED |
| External AgentRun | `616a13de-4789-40c8-8ab1-2d7e727ccbf5`, PARTIAL, 9 persisted steps including 2 TOOL_ERROR |
| Accepted proposal | `7626e38a-1b70-4754-bd6e-deb2f197f93c` |
| Accepted plan | `06a7766a-96b5-493d-b6e4-6cfd20216269` |
| Acceptance audit | `6ff47d34-3b67-4f49-b464-b691539b5599`, AUTHENTICATED_TRAVELER |
| Final native progress | SIMULATED_COMPLETED, sequence 12, PROPOSAL_ACCEPTED |

The proposal's Journey, trigger event and source AgentRun were checked against persisted server objects. The run started with no completed activities. Its history contains exactly four SIM_ACTIVITY_COMPLETED entries. The completion records use the original Day1 IDs and the accepted plan's Day2 IDs; there is no historical completion borrowed from another run.

| Local date | Stops completed in this run |
| --- | --- |
| 2026-12-05 | 拙政园; 苏州博物馆本馆 |
| 2026-12-06 | 苏州园林博物馆; 平江路 |

All movement, virtual time, GPS and activity transitions are explicitly simulated. The model call and provider calls described below were actual external requests.

## Legal native preparation and bounded source changes

The previous candidate's 狮子林 opening-hours gap was not fabricated away. The operator explicitly replaced that stop with 苏州园林博物馆, canonical `real-place-7169e1bb4fcfafa220d5d6b4`, already present in this task's captured source. Its existing source specifies Tuesday–Sunday 09:00–16:30; the selected 2026-12-06 Sunday morning satisfies the current date parser. No new POI search was made. Both previous candidates remain preserved.

Native signed draft PUT 200 -> prepare 201 created candidate `44326a11-7ca7-454a-88c1-19426a40b102`. Freeze returned 200, verified 3/3: one reused route and two genuinely new WALK pairs, each called once:

| ProviderCall | Pair | Native duration / distance |
| --- | --- | --- |
| `c0e8548e-b6de-43f9-9ae0-785b195ee2bb` | 苏州博物馆本馆 -> 苏州园林博物馆 | 423 s / 529 m |
| `e6e3e648-872c-4728-a505-99cf25399df2` | 苏州园林博物馆 -> 平江路 | 1080 s / 1350 m |

Both geometries are AVAILABLE under the unchanged geometry rule. ProviderCall count moved 115 -> 117; AgentRun stayed 39 during preparation. The first QA helper assertion incorrectly rejected a pre-freeze TRANSFER_ROUTE gap after a successful prepare 201; that helper assertion was corrected and the existing candidate was used. Prepare and source acquisition were not repeated to hide that first helper failure.

The isolated demo operator explicitly acknowledged four unknown prices through the native endpoint; they remain unknown and outside the known subtotal. This is operator-authorized demo setup, not a claim of verified prices, bookings, purchases or physical-device user acceptance. Native unknown-price acceptance, departure commit and Journey start returned 200 and made the Journey ACTIVE through its normal writers.

## One Guardian execution and authenticated continuation

The standing mission was configured PLAN_ONLY. Day1 completed through native simulation advances. One current SCHEDULE_DELAY scene paused this run; exactly one Guardian POST then used the configured `hermes` / `auto:cheapest` route through the existing local chat-completions adapter. The physical upstream model was not returned and is not guessed.

Agent execution lasted approximately 100.6 seconds, 2026-10-26T12:34:13.175591Z to 12:35:53.792820Z. Its persisted steps were inspect_journey, inspect_twin, request_replan, list_replans, request_replan, list_replans and three conclude_recovery attempts. Two conclude_recovery steps have TOOL_ERROR; the AgentRun remains PARTIAL. No retry or second-model fallback was invoked by the operator.

The resulting native proposal reached PAUSED_FOR_ACCEPTANCE / sequence 10. Signed accept returned 200, recorded the authenticated traveler actor, and resolved this event. Resume returned 200 / sequence 11; the final advance reached SIMULATED_COMPLETED / sequence 12 at virtual 2026-12-06T17:00:00+08:00. Agent count moved 39 -> 40; ProviderCall stayed 117 through Guardian, acceptance and completion.

The accepted proposal family is F2_SUFFIX_DELAY. Its diff preserves all four canonical stops and their activity times, with zero cost/end-time delta and SCHEDULE_DELAY_ABSORBED. This proves the current proposal/accept/resume path; it does not prove a 15-minute activity shift or model-generated half-day rewrite.

## Restart persistence and an unresolved projection defect

Before and after normal owned-service restart, signed progress returned 200 with `Cache-Control: private, no-store`, SIMULATED_COMPLETED / sequence 12 / PROPOSAL_ACCEPTED. Agent 40 and ProviderCall 117 did not increase. Safe persisted steps and the PARTIAL/two-error result remain visible. The JSON receipt includes both readbacks and the four raw completion records.

**Confirmed, not fixed in this receipt:** `summarize_activity_coverage` counts only the run's original completed activity IDs. After acceptance, Day1's terminal prefix has been copied to new activity IDs. Those clones retain `execution_truth.evidence.simulation_run_id` equal to this run, but progress labels both Day1 stops as inherited completion (run count 0, inherited count 2). Day2 reports run count 2. Raw run history and original completed activities prove 2+2; the display projection does not yet represent that correctly.

The narrow next product change should preserve the inherited-history guard while recognizing server-persisted same-run terminal copies. Regression must distinguish this run from other-run evidence, bare COMPLETED status, missing/invalid truth and copied activities with no authoritative completion. Do not relaunch the model or map providers to validate that read projection.

Remaining delivery gates: this coverage projection, Qoder classroom integration and actual browser acceptance/map refresh, and user-operated physical-device USER_VERIFIED. This receipt does not establish those gates. Three-city source READY receipts and the existing Nanjing geometry failure are unchanged.

Receipt: `20261026_SUZHOU_FOUR_STOP_LIVE_CHAIN.json`. Full local pre-condense export, guarded operation journals and consistent pre-write database backups remain in the owned QA folder `C:/Users/仓鼠王/cn51/classroom-20261026-qa/supply-native-20261026`.
