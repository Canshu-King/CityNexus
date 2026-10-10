# Revolution R19 — Living Plan Portfolio Result

## Closure

R19 reached the living-portfolio path on the existing lab database with
`CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`:

```text
one ACTIVE Journey reality
  -> bounded STANDBY branch with live mobility and a real TTL
  -> generic select rejected
  -> dedicated activate_standby Gateway path
  -> approval required and consumed
  -> new ACTIVE PlanVersion and cursor remap
```

This is a real product execution, not a report-only or provider-only result.
The model runtime was configured as `HERMES_COMPAT_ENDPOINT / cn:glm-5.3-flash`.
This round's mutation was exercised through the machine Gateway tool directly;
no model prose is counted as authority and no raw credential was persisted.

## Source binding

- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Branch: `codex/revolution-realtrip-recovery`
- Starting commit: `0b90bdc7f5de0e6571d6189607d80ec229642546`
- Code commit: `9e261475b1274fe2b92e20866337cf374fefd538`
- Report commit: added after the code commit; it is documentation only.
- Database: disposable lab SQLite `citynexus-r13-metadata-fix-20260930-b.sqlite3`

Every product call in the run used the checked-out source after the R19 code
change; the server was restarted from that worktree before the live calls.

## Machine execution

Journey:

```text
id = 0a6f6b2d-c78a-48f0-8732-40e8a8253608
city = JP-NARA
estimate authority = false
old active = da5a39b5-a273-588d-8266-af5610bf7c70
```

1. Autopilot pulse ran with `open-meteo` signal provider. The migrated R18
   branch `e7d5201b-e3d2-49a7-b383-4a71bd7d3546` had no real expiry and was
   retired as `MOBILITY_EVIDENCE_EXPIRED`; active reality was untouched.
2. `/resilience/refresh` ran the existing bounded counterfactual pipeline.
   `rain_earlier` produced the R19 branch
   `c538539c-c8e7-4e00-9c29-955ec7a5f8b7`.
3. The branch was persisted as `status=CANDIDATE, lifecycle=STANDBY`, with
   parent `da5a39b5-a273-588d-8266-af5610bf7c70`. It was not current and its
   projection was `selectable=false`.
4. Generic `POST /journeys/{id}/plans/{standby}/select` returned HTTP 409:
   `STANDBY branches require the activate_standby Gateway action`.
5. A traveler-reported closure event was persisted by the normal event API:
   `34156563-8f07-4cb6-934f-9f1ddde037d6`, affected activity
   `4fe0fc7f-fd0a-527b-b5a1-08267986dfa8`.
6. `POST /api/v1/agent/tools/v2/activate_standby` first returned
   `REQUIRE_CONFIRMATION` with approval
   `27426afe-57dd-4d07-8997-4bc402dd5a6a`. After normal user approval, the
   same dedicated tool consumed the approval and returned `executed=true`.
7. Final Journey pointer became
   `active_plan_version_id=c538539c-c8e7-4e00-9c29-955ec7a5f8b7`, while the
   previous plan became `SUPERSEDED/RETIRED`. Only one active reality exists.

## Evidence and recomputation

The activated branch was originally captured as a standby with:

```text
mobility snapshot = 346e66b3-2b15-477f-baa8-a89ab1e16943
captured_at = 2026-10-01T13:42:40.972169+00:00
expires_at = 2026-10-01T13:57:40.972169+00:00
provider = valhalla-http
```

The exact branch edges were recomputed from the standalone snapshot:

| from | to | minutes | quality | cost |
|---|---|---:|---|---|
| `real-place-0783c88172a57c0b7f4ce101` | `real-place-470b4d1080037ab7f7e9b562` | 73 | `LIVE_PROVIDER_CAPTURE` | `KNOWN_FREE` |
| `real-place-470b4d1080037ab7f4ce101` | `real-place-b47a20314c81d5a81381d4a4` | — | — | — |
| `real-place-470b4d1080037ab7f7e9b562` | `real-place-b47a20314c81d5a81381d4a4` | 56 | `LIVE_PROVIDER_CAPTURE` | `KNOWN_FREE` |

The middle row is intentionally not a route edge; it shows the omitted
activity, not synthesized evidence. The persisted `JourneyLeg` rows contain
only actual edges with their own expiry and provider provenance.
`KNOWN_FREE` is used only for the provider-confirmed
deterministic walking/no-fare mode; unknown paid costs are not changed to zero.

The branch had three activities: the protected/current prefix plus the two
indoor future activities. Activity times retained available schedule slack and
were moved only when the newly captured edge required it. Total activity cost
was recomputed to 50,000 JPY from the retained canonical activities.

## Lifecycle behavior

- `PlanVersion.lifecycle` is explicit: `ACTIVE`, `STANDBY`, or `RETIRED`.
- Existing R18 explanation-only standby rows are migrated on schema startup.
- `captured_at` is never used as `expires_at`; mobility expiry is capture time
  plus the configured cache TTL.
- Autopilot maintenance retires branches whose parent is no longer current,
  whose mobility evidence is expired/missing, or which exceed the bounded
  portfolio size of three.
- `inspect_twin` includes a compact server-owned `standby_portfolio` view.
- A standby cannot become authoritative through generic plan selection.
  Activation requires current parent, fresh evidence, deterministic feasibility,
  an actionable non-synthetic trigger, and Gateway policy/approval.

## Focused tests

```text
uv run pytest \\
  tests/test_guardian_model_evidence.py \\
  tests/test_guardian_v4.py \\
  tests/test_agent_mission_runtime.py \\
  tests/test_r15_source_authority.py -q

35 passed, 1 warning
```

`git diff --check` passed. The warning was the pre-existing Starlette/httpx
deprecation warning. No production/mainline merge was performed.

## Remaining boundary

This R19 run proves a grounded standby branch can live, expire, be exposed to
the Agent surface, and be activated only through the dedicated Gateway path.
It does not claim a configured model independently chose this activation: the
machine tool call and Gateway approval are the authority evidence. The next
bounded experiment is to have the configured Agent inspect the compact
portfolio after a real provider/user trigger and choose between two already
grounded STANDBY branches; it must still use `activate_standby` and cannot
write the Journey pointer itself.
