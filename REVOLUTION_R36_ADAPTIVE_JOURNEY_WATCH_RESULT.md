# R36 Adaptive Journey Watch — Result

## Closure identity

- Taskbook/source before the live closure: `153767bd1f3ffb6e93876f77b56e13bc568c7aec`
- Fresh Journey: `1f772a88-2e34-4a0e-8683-e9d7125ba3b1`
- Active plan before/after: `20ecccff-0d0e-5b26-bd95-8b20fac7232e`
- Standing Guardian mission: `c590a570-8ae4-431d-9924-72f773f5df44`
- Autopilot enrollment: enabled, configured interval `3600` seconds
- One scheduled live pulse: `74182f46-5e03-479c-b8cc-4093a7e157bf`
- No recurring worker was started and no second pulse was run.
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.

## Adaptive watch projection

Before the pulse, the server projection was:

- `watch_state=DAY_AHEAD`
- `effective_interval_seconds=1800`
- `initial_watch_due=true`
- reason: next planned activity within 24 hours
- Journey phase: `PRE_TRIP`
- phase authority: `CONTROL_PLANE_ONLY`
- monitored scope: two activity ids, current destination and one following activity

After the pulse, the projection remained `DAY_AHEAD` with the same 1800-second effective cadence. The latest-pulse endpoint returned the persisted `result.phase`, and both `/guardian/autopilot/status` and `/guardian/status` returned the watch projection.

The traveller-facing surface now shows that Guardian Watch is on, explains the broad cadence reason and next-check time, and exposes a Stop Guardian Watch control. Internal phase and policy enum names are not shown in the ordinary copy.

## Unique live pulse result

- Weather, city signal and mobility observations were persisted with live provider provenance; all provider states were `CAPTURED` and `degraded=false`.
- `run_live_context_watch` checked only the bounded phase scope.
- Both exact provider-bound venues were `OPEN_COMPATIBLE` with `PLANNED_INTERVAL_WITHIN_VERIFIED_HOURS`.
- Context status: `NO_MATERIAL_CHANGE`.
- Material Events: `0`.
- `GuardianRun`: one persisted `NO_ACTION` run for the quiet scan.
- `AgentRun`: `0`.
- Proposal: `0`.
- Mutation count: `0`.
- Active plan remained unchanged.
- The receipt contains one RecoveryEpoch opened by the Journey start path before the pulse; it was not created by a phase transition and no AgentRun or recovery mutation used it.

This is a valid `WATCH_ALL_CLEAR` closure. No physical travel is claimed.

## Implementation and verification

- Added deterministic cadence and phase projection in `backend/app/agent/watch_policy.py`.
- Added bounded phase-scoped context refresh and persisted pulse phase in `backend/app/agent/autorun.py`.
- Kept `run_live_context_watch(activity_ids=...)` backward compatible.
- Kept `OPPORTUNITY_WINDOW` outside disruption urgency and recovery pulse evaluation.
- Added watch data to both Guardian status projections and ordinary traveller UI with a stop control.
- Fixed older lightweight policy callers to degrade phase metadata to `UNKNOWN/CONTROL_PLANE_ONLY` without changing cadence.
- Backend R36/R35 focused suite: `22 passed`; final post-UI backend rerun: `20 passed`.
- Frontend `npm run typecheck`: passed.
- Related Live Recovery Playwright suite: `3 passed`.
- The first receipt-writing attempt hit a harness-only field-name error after the pulse had completed. The receipt was finalized from the persisted fresh database without rerunning the pulse.

R33-1, R34 and R35 live closures were not rerun or reinterpreted.
