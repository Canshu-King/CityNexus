# Revolution R20 — Autonomous Branch Arbitration Result

## Result

R20 reached REVOLUTION_C on the isolated lab database:

~~~text
real user-observed mobility disruption
-> real configured Agent inspected Journey/Twin
-> Agent selected a compatible standby from the server portfolio
-> deterministic Gateway required and received user confirmation
-> dedicated activate_standby Gateway activated the branch
-> old parent and siblings retired
-> revised active plan executed through the HTTP activity state machine
-> Journey COMPLETED
~~~

P7=false. No authority/mainline merge was made. No plan ID was supplied in the
Agent prompt or mission command.

## Source binding

- Worktree: D:/moodle/CityNexus-Revolution-RealTrip-Recovery
- Branch: codex/revolution-realtrip-recovery
- R19 local code SHA: 9e261475b1274fe2b92e20866337cf374fefd538
- R19 published remote head: 486270efdad215d7d9913f2e5f7f7faadd77c7ef
- R20 carrier taskbook commit: dea9876f30431638da526a515999b6bb9ce11377
- R20 taskbook blob: 1c3cd3bb6a4ce1349c7dbc6d32619ae66d298cd0
- Final experimental code SHA before this report: 8cb2a10ceb09bcb458649897765f06c72502cdc9
- Estimate authority: CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false
- Agent runtime: HERMES_COMPAT_ENDPOINT / cn:glm-5.3-flash
- Guardian signal provider: open-meteo
- Mobility provider: valhalla-http

The R20 carrier was read from the fetched reference; it was not checked out
over the R19 worktree.

## Primary arbitration trace

Journey: 4ce744f4-46e0-4d3d-af5d-3801f32f2bda (JP-NARA).

Disruption event:

- Event: a042435f-04ae-4193-b063-8f44d514cc63
- Type: SCHEDULE_DELAY
- Provenance: USER_REPORTED
- Severity: MAJOR
- Affected current activity: d3c73060-8a2a-5950-b0a0-79f6d1d588c6
- Place: real-place-22cf72809897ff4c7f312fcf

The fresh primary portfolio contained two server-owned mobility futures:

- route_plus_20: 13a8a420-3f73-4fc3-b9aa-c74855ae9a47
- route_plus_30: a75a2986-b1bd-406e-8767-98cc6f400cd9

Both had live Valhalla snapshots, non-expired evidence, current-parent
equality, and trigger_match=MATCH for the observed event. The Agent selected
route_plus_30 after inspecting the returned portfolio. The correct standby ID
was not in user_text, system prompt, or mission instructions.

The same-city portfolio transfer run also produced a grounded WEATHER_SHIFT
branch 988fb998-5957-40a0-8627-188fc98c40f3 alongside mobility branches. A
traffic event against that weather branch was rejected by the shared matcher
and Gateway:

~~~text
HTTP 409 STANDBY_TRIGGER_MISMATCH:TYPE_MISMATCH
~~~

This is the required negative proof that an actionable event is not a wildcard
activation token.

## Authority and activation

The real Agent run:

- AgentRun: a3c801ad-064e-4b0f-852d-45bebc7dba23
- Mission: 43b66d26-3a40-4596-a58d-3d26b8ed13ba
- Provider/model: hermes / cn:glm-5.3-flash
- Runtime identity: HERMES_COMPAT_ENDPOINT
- Status: COMPLETED
- Ordered tool calls: inspect_journey, inspect_twin, activate_standby

The activation tool first returned REQUIRE_CONFIRMATION. Approval
5a0c886c-8ca5-42e1-814e-b002f4b9eb31 was approved through the approval
endpoint. The dedicated Gateway then returned executed=true for
a75a2986-b1bd-406e-8767-98cc6f400cd9.

## Before / after product state

Before activation:

- Active PlanVersion: fc7705e0-2f5f-5a71-8ffb-4c71a0a4722a
- Current activity: d3c73060-8a2a-5950-b0a0-79f6d1d588c6
- route_plus_20 and route_plus_30 were STANDBY/CANDIDATE
- weather branch was rejected by the traffic-event matcher

After activation and execution:

- Active PlanVersion: a75a2986-b1bd-406e-8767-98cc6f400cd9
- Journey status: COMPLETED
- Current activity: null
- Final Twin projection: READY, journey_status=COMPLETED
- Old parent: SUPERSEDED/RETIRED
- All sibling standby branches: REJECTED/RETIRED
- The revised active activities completed through depart, arrive, begin, complete

Final active-plan mobility evidence:

- Provider: valhalla-http
- Route provenance: LIVE_PROVIDER_CAPTURE
- Actual used edges:
  - real-place-0783c88172a57c0b7f4ce101 -> real-place-21ab302a8e71729b15395d94
  - real-place-21ab302a8e71729b15395d94 -> real-place-22cf72809897ff4c7f312fcf
  - real-place-22cf72809897ff4c7f312fcf -> real-place-b47a20314c81d5a81381d4a4
- Every actual edge had hard_eligible=true and decision=HARD_ELIGIBLE.

## Inline repairs

1. Omitted request_replan candidate count now uses the bounded server default.
2. Executed/current activities are anchored once, not duplicated as solver slots.
3. Same-location anchors no longer fail because of a movement buffer at minute zero.
4. Stale standby branches are retired and rematerialized from the current cursor.
5. Bounded weather and P80/P95 mobility scenarios can sacrifice the first
   mutable future visit to form distinct grounded branches.
6. Autonomous mission envelopes expose activate_standby while Gateway approval
   remains mandatory.

## Focused gates

~~~text
python -m compileall -q backend/app                 PASS
39 focused tests                                     PASS
1 Starlette/httpx deprecation warning               WARN only
~~~

The focused command covered R20 trigger authority, Guardian evidence, Guardian
runtime, mission runtime, and R15 source authority.

## Evidence artifacts

- backend/r20-agent-arbitration.json
- backend/r20-final-agent-run.json
- backend/r20-final-journey.json
- backend/r20-final-twin.json
- backend/r20-final-events.json
- backend/r20-portfolio-final-two-modes.json
- backend/r20-runtime-status.json

These are raw machine responses from the isolated lab run. Raw WB2API
credentials were never persisted in the repository or evidence files.

## Remaining product note

Two earlier compatibility runs were interrupted by server restarts and left an
orphaned RUNNING mission/run row in the disposable lab database. They were not
used as the success trace. The accepted trace is the completed
a3c801ad-064e-4b0f-852d-45bebc7dba23 run above.

## Replay

1. Use the isolated lab DB:
   C:/Users/仓鼠王/AppData/Local/Temp/citynexus-r13-metadata-fix-20260930-b.sqlite3
2. Set CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false and use the configured WB2API
   endpoint without printing its key.
3. Start the backend from this worktree.
4. POST the same disruption command to
   /api/v1/journeys/4ce744f4-46e0-4d3d-af5d-3801f32f2bda/agent/commands.
5. Inspect the AgentRun and Twin. The model must inspect the server portfolio
   before choosing a branch.
6. Approve the Gateway approval, activate the returned branch, and run the
   HTTP activity state machine until Journey.status=COMPLETED.

