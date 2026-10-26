# Same-run completion coverage survives accepted-plan terminal copies

Product: `e2c893a0115d381abe83e781c448766a1c148b78`, based on `1794e3b2242e82c117e49126835b562eaa82ccc1`. Addresses Issue49 external review [6417721314](https://github.com/Canshu-King/CityNexus/issues/49#issuecomment-6417721314); scoped hot-file notice [6418024829](https://github.com/Canshu-King/CityNexus/issues/49#issuecomment-6418024829).

Accepting a replan copies the completed terminal prefix into the new active plan with new activity IDs. The run correctly retains its original four completion IDs and history, but progress previously intersected those IDs with only the new plan. Suzhou Day1 therefore displayed zero current-run completions and two inherited completions. The projection now authenticates unchanged terminal copies against their original server-persisted completion records.

## Product behavior and boundary

`progress.py` resolves original completion IDs from the intersection of this run's persisted state and SIM_ACTIVITY_COMPLETED history. Original rows must belong to a PlanVersion in the same Journey and join an existing canonical Place. The pure `resolve_run_completed_activity_ids` helper retains those original IDs and adds active-plan copies only when:

- The source and copy are COMPLETED, with the same nonempty Place ID, activity type and start/end timestamps; FREE_TIME does not qualify.
- Complete execution-truth records are equal. Their kind is SIMULATED_STATE_TRANSITION, transition COMPLETED, actor TRAVELER matching the current run actor, and location source SIMULATED_GPS.
- The truth's simulation_run_id is the current run. Its integer sequence matches an original completion-history entry and is not beyond the run sequence. Captured virtual time matches the history entry. Wall-clock timestamps must be valid but need not be identical between the two native writes.

Standalone metadata claiming a run ID cannot add a completion. Other-run truth, altered Place/time/type, missing or malformed truth, invalid evidence and foreign-Journey sources fail to certify copies. Existing daily Place deduplication remains intact. No HTTP fields, execution writers, status/history records, source facts or Guardian behavior were changed; GET remains read-only.

## Isolated acceptance

Root alone ran these non-overlapping test sets, serially, against explicit isolated SQLite `C:/Users/仓鼠王/cn51/classroom-20261026-qa/coverage-terminal-copy-20261026/isolated-regression.db`:

| Scope | Result |
| --- | --- |
| Existing coverage, coverage API, Issue47 simulation, Presenter integration, accepted Guardian outcome (five files) | 45 passed, 6 warnings, exit 0 |
| New terminal-copy regression file | 28 passed, 4 warnings, exit 0 |

The new suite covers proof and copy negative cases, duplicate Place counting, original/active plan switching, a forged-but-well-shaped foreign-Journey source, and signed GET snapshots proving SimulationRun, Activity, AgentRun/steps and provider rows are unchanged. This API plan-copy setup is an isolated fixture, not a new live acceptance action. Initial new-suite result was 27 pass / 1 failure: its assertion accessed an expired ORM ID after session close. Root backed up the test and captured clone IDs before commit; the final 28 passed without changing product logic. Initial failure stdout and final JUnit/stdout are retained in the QA folder.

## Same owned run, signed GET after normal restart

After normal stop/resume of only the owned launcher, backend reports exact product SHA `e2c893a0115d381abe83e781c448766a1c148b78`, same database/auth, backend 60622 / frontend 14522. Automatic browser pairing was disabled. Frontend remains Qoder `2176c811…` plus its existing dirty files; this is not a browser/UI acceptance claim.

Journey `e7f868e4-2d03-4d3c-b563-962e47b185f4`, run `7188e2e7-b216-47e0-b446-ebf747abdb83`, accepted plan `06a7766a-96b5-493d-b6e4-6cfd20216269`:

| Local date | Before: run / inherited | After: run / inherited |
| --- | --- | --- |
| 2026-12-05 | 0 / 2 | 2 / 0 |
| 2026-12-06 | 2 / 0 | 2 / 0 |

Both reads returned signed HTTP 200 with `Cache-Control: private, no-store`; status remains SIMULATED_COMPLETED, sequence 12, outcome PROPOSAL_ACCEPTED. The exact named run and relevant source/active Activity rows have identical canonical serialized SHA-256 before and after: `e289e912ad3b355415fea7d156c428e47ac2d092bf4790bc4e83a8cc28d10391`. AgentRun count remains 40 and ProviderCall 117. The existing external Agent remains PARTIAL, nine steps including two TOOL_ERROR; acceptance audit and four original completion-history entries are retained.

This increment made zero new model/provider/POI/route requests, injected no event, and did not repeat proposal acceptance or simulation advancement. A consistent private pre-restart database backup is retained as `supply-native-20261026/before-coverage-projection.db`; public-safe before/after readbacks are in `20261026_COVERAGE_TERMINAL_COPY_HTTP.json`.

The previously recorded three-city READY evidence is unchanged. Qoder must integrate PR56 into current rescue and verify classroom Chrome/map behavior; physical-device USER_VERIFIED remains pending. The earlier four-stop receipt is preserved as historical evidence of the then-unfixed projection. Exact pushed-head CI results are linked in the Issue49 handoff after verification.
