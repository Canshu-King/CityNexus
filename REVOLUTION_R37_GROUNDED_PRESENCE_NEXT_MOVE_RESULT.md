# Revolution R37 — grounded presence / Next Move closure

## Result

- **Outcome:** `LIVE_LOCATION_UNAVAILABLE`
- **Fresh Journey:** `86478b77-7085-4eb9-8d0d-bef56db6f614`
- **Target:** `依水園` (`real-place-22cf72809897ff4c7f312fcf`, provider `overpass`)
- **Source head before live:** `06879db6b70c69a1bcf40dd094343685433d1eac`
- **Machine receipt:** [backend/output/r37-grounded-presence-next-move-v1.json](backend/output/r37-grounded-presence-next-move-v1.json)

The Journey was newly created, planned, selected, started, and enrolled in Guardian Watch. The target activity kept an exact provider-backed Place binding. The read-only presence projection returned `LOCATION_UNAVAILABLE` because this local run had no browser foreground location observation. The Next Move projection exposed the scheduled target, route evidence, venue readiness state, phase authority, and ordinary traveler-facing copy:

> Location sharing is off; Guardian is using the plan schedule only.

No coordinate was invented and no second observation was attempted. The trusted device/location bridge remains unavailable, so physical arrival was not claimed and strong execution transition stayed blocked.

## Invariants

- `FOREGROUND_WEB` remains advisory and cannot become `DEVICE_ATTESTED` through the location endpoint.
- The live closure persisted **0** location observations, **0** Guardian pulses, **0** Events, **0** AgentRuns, **0** ReplanProposals, and **0** accepted-mutation audit rows.
- The active plan ID remained unchanged before and after the closure.
- Presence projection and Next Move are read-only; watch policy only tightens cadence for fresh near-term presence and never creates an incident or grants execution authority.
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` was set for the live run.

## Verification

- Focused backend suite: **37 passed**
- Frontend TypeScript check: **passed**
- The receipt records before/after autopilot and Guardian status, presence, Next Move, target binding, action-row counts, and execution-truth limits.

## Scope limit

This closure proves the local control-plane behavior and the honest unavailable branch. It does not claim physical arrival or device-attested location because no trusted bridge was configured.
