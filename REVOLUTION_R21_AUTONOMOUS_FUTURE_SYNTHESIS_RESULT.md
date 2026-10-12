# Revolution R21 — Autonomous Future Synthesis

## Result

R21 reached the primary C/D path on the isolated Revolution Lab tree:

```text
truth-grounded ACTIVE Journey
→ two materially different standby futures
→ user-observed closure outside their trigger contracts
→ real Hermes-compatible Agent inspected Journey/Twin/event/portfolio
→ Agent chose request_replan without a prescribed plan ID or action sequence
→ deterministic solver created a new future with live mobility evidence
→ Agent inspected the proposal and chose accept_replan
→ Gateway activated the new PlanVersion
→ revised Journey execution completed
→ Journey COMPLETED
```

Final machine state:

- Journey: `ef58097f-e4d7-4b20-8ce6-402e6f77f3ec`
- final status: `COMPLETED`
- active PlanVersion: `77edffc2-d1f4-49f4-9aea-41f76dfb3f95`
- current activity: `null`
- Twin projection: `READY`
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- Agent provider/runtime: `HERMES_COMPAT_ENDPOINT`, model `cn:glm-5.3-flash`
- mobility provider: `valhalla-http`
- final actual edges: 3; all 3 have `LIVE_PROVIDER_CAPTURE` and `HARD_ELIGIBLE`

## Source binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- starting base SHA: `8a6ac5470a1fe4ff5596517b0b4b4e03a07855db`
- R21 product code commit: `6b6c412f1f46657685cd4448b756c7f86c791a8c`
- final experimental code commit: `b414a0e045c1f447210b11b0da74256b426862b6`
- no authority/mainline merge
- all provider calls used a disposable SQLite database; no real-user DB or persistent secret was used

## Neutral mission contract

The compiled mission contains `evaluate_recovery_options` with `tool_name=null`. It contains capabilities and authority boundaries, but does not order `activate_standby` before `request_replan`, and does not put either mutation tool in the mission steps.

The actual successful mission text was neutral:

> 请检查当前 Journey、Twin、现有未来分支和最新用户报告。旅行者观察到后续地点的现实情况发生变化；请依据当前事实判断现有未来是否足够，在权限边界内自主选择最稳妥的恢复方式或不做修改，并推进到可执行结果。

The mission payload did not contain the event ID, standby ID, proposal ID, correct plan ID, or expected tool sequence. The Agent discovered the current event through `inspect_twin`.

## Materially different prepared futures

The post-refresh portfolio had two distinct executable fingerprints:

| branch | scenario | material difference | fingerprint |
|---|---|---|---|
| `30c7b7c5-b34e-42db-9fbe-a2016205f7f4` | `route_plus_20` | DROP Daigokuden museum activity; 4 activities | `2320b5bec2d1a8dcb6482fd4` |
| `6341e8cc-0afa-4d05-b4a0-c90087d9e35d` | `route_plus_10` | RETIME Daigokuden and preserve it; 5 activities | `f75830234679555327ee19b9` |

Equivalent DROP scenarios were deduplicated by the executable fingerprint. Scenario labels alone were not used as evidence of distinct futures.

## R21 disruption and autonomous synthesis

Controlled user-observed event:

- event: `0629f0f9-8288-4b03-875b-1d2a8c9625a0`
- type: `CLOSURE`
- provenance: `USER_REPORTED`
- severity: `MAJOR`
- affected activity: `021e15b2-8ed8-5f54-9681-f6f4a2fd7b8e`
- affected Place: `real-place-b47a20314c81d5a81381d4a4`

The prepared mobility branches allowed only `TRAFFIC_DELAY` / `SCHEDULE_DELAY`. Server trigger matching returned `TYPE_MISMATCH` for both, so neither standby could solve this closure.

The successful AgentRun was `03c9ab4b-4284-4776-ac9b-86e17eeffdfd`:

1. `inspect_journey`
2. `inspect_twin`
3. `inspect_twin` with the current user event
4. one malformed `request_replan` argument was rejected as `MALFORMED_TOOL_ARGUMENTS`
5. the model corrected its arguments and called `request_replan` successfully
6. `list_replans`
7. `accept_replan`

The resulting proposal was `69966387-95a8-4c55-a6a8-53801bba42f7`, family `F1_OPTIONAL_REMOVAL`. It removed the closed craft museum, preserved the remaining active execution position, and produced PlanVersion `77edffc2-d1f4-49f4-9aea-41f76dfb3f95`.

The deterministic proposal receipt records:

- `hard_constraints_passed=true`
- `locked_commitments_preserved=true`
- cost delta `0`
- schedule end drift `-116` minutes
- journey-end slack increased from `81` to `197` minutes
- incident mobility snapshot provider `valhalla-http`
- incident route provenance `RUNTIME_CAPTURE`
- all actual edges `LIVE_PROVIDER_CAPTURE`

No model prose was used as authority. The Gateway and deterministic feasibility gate performed the mutation.

## Execution completion

The revised plan was executed through the real HTTP activity state machine:

```text
73dddbdf...  depart → arrive → begin → complete
5637cb61...  depart → arrive → begin → complete
```

Both sequences returned HTTP 200. The final completion response set:

```json
{
  "journey_status": "COMPLETED",
  "active_plan_version_id": "77edffc2-d1f4-49f4-9aea-41f76dfb3f95",
  "current_activity_id": null
}
```

The final Twin retained the same active PlanVersion, showed `projection_status=READY`, and reported 3/3 actual edges as hard-eligible.

## NO_ACTION control

Run `7429b574-8d62-4f06-aee5-101e8b70b415` used the same configured Agent runtime and a neutral mission. The model inspected the Journey/Twin, saw a user-reported closure, attempted a deterministic replan, acquired provider-backed official facts, and chose no mutation because the official source contradicted the user report and the current plan remained feasible. The active PlanVersion was unchanged in that run.

This is a real control trace, not a wrapper assertion. The final successful run then demonstrated the opposite decision when the later user-observed closure targeted a different future activity and the model found a deterministic recovery path.

## Hygiene fix

`accept_replan` now retires all `STANDBY` siblings whose parent is the superseded active PlanVersion at the same authority handover. A completed Journey was also reconciled through the existing standby maintenance path; the old R19/R20 siblings are now `RETIRED/REJECTED` and no longer appear as READY futures.

The runtime reports `CONFIGURED_UNVERIFIED` for the active Hermes-compatible process rather than the false `DISABLED_BY_OPS`. Startup reconciliation closes stale old `RUNNING` AgentRun/JourneyMission rows with reason `PROCESS_RESTARTED_DURING_AGENT_RUN`.

## Focused tests

```text
49 passed, 1 warning
python -m compileall -q backend/app backend/tests   PASS
```

Focused set:

- `test_v18_2_agent_productization.py`
- `test_r20_standby_trigger.py`
- `test_agent_mission_runtime.py`
- `test_qoder_ord0359_ai_state_three_ways.py`
- `test_r21_autonomous_future_synthesis.py`

## Evidence artifacts

- `backend/r21-refresh-clean.json`
- `backend/r21-closure-event.json`
- `backend/r21-craft-closure-event.json`
- `backend/r21-agent-main.json` — NO_ACTION control
- `backend/r21-agent-fresh-replan.json` — successful AgentRun response
- `backend/r21-replan-live-diagnostic.json` — direct deterministic diagnostic, explicitly not counted as Agent autonomy
- `backend/r21-execution-completion.json`
- `backend/r21-final-machine-receipt.json`
- `backend/r21-runtime-final.json`

## Remaining blocker

R21 primary C/D is closed on this disposable run. Native Hermes MCP was not proven; the successful path is the configured Hermes-compatible gateway. R22 should not repeat this proof or add homogeneous standby branches; the next product frontier is only warranted if it creates a materially new autonomous capability.
