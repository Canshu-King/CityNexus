# Revolution R22 — Autonomous Opportunity Capture

## Result

R22 achieved the primary product path on the isolated LAB database:

ACTIVE Journey -> SYSTEM_DERIVED OPPORTUNITY_WINDOW -> real Agent inspect/search/acquire/generate/request_replan -> F4 additive proposal with a new provider-backed Place -> deterministic feasibility gate -> Gateway REQUIRE_CONFIRMATION -> consumed user approval -> new active PlanVersion -> inserted activity executed -> protected commitment executed -> Journey COMPLETED.

CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false throughout the successful path. No mock mobility or synthetic plan authority was used.

## Source binding

- Branch: codex/revolution-realtrip-recovery
- Worktree: D:\moodle\CityNexus-Revolution-RealTrip-Recovery
- Starting code SHA: cd1e5dd214f3ea7e52198674487ffa7d1cbf66e7
- R22 implementation commit: 01b1a5f7c17115308fa2ced16cc3a99916b6cf41
- Final experimental code commit: c9fb37f9d1c20b7341cf2a3bc2f004408ba494f3
- Remote: origin/codex/revolution-realtrip-recovery
- Taskbook blob: 27d6898fc7ad39a157797e11fa091a2a320ad8d8

The GPT taskbook branch was read but was not checked out over the LAB worktree.

## Runtime

- Agent runtime: Hermes-compatible persisted AgentRun
- Provider/model: hermes / cn:deepseek-v4.1-flash
- WB2API endpoint: local 127.0.0.1:7863 configuration path; raw credentials are not included
- Fallback configured: cn:glm-5.3-flash
- Mobility: valhalla-http, deployment 3.9.0-685e3d8
- Signal provider: open-meteo
- Estimate authority: false

Successful AgentRun: 41426e1b-bb9a-4cda-a0af-b968047bd7b3.

Ordered machine-visible tool steps:

1. inspect_journey
2. inspect_twin
3. list_replans
4. search_city_services
5. acquire_place_facts
6. acquire_place_facts
7. generate_plans
8. request_replan
9. accept_replan
10. conclude_recovery

The Agent was not given a Place ID, action recipe, or tool sequence. It discovered the opportunity from inspect_twin, searched the live city catalogue, acquired facts, selected a candidate, and requested the replan.

## Scenario and destination

- Journey: fd29878e-8c6b-4bba-8a29-72193a710b59
- City: JP-NARA
- Active before opportunity: bf686752-bf9e-55e8-9de0-ebf739f83b85
- Active after opportunity: bb321722-3534-4938-8841-7533879db171
- Trigger: 79eacfd8-a3d9-4149-bf40-8d386ee5ecff
- Trigger provenance: SYSTEM_DERIVED
- Trigger type: OPPORTUNITY_WINDOW
- Trigger provider: citynexus-twin-opportunity

The lab fixture was aligned before the final run so the existing C4 Daigokuden commitment landed at 15:00, inside the provider-confirmed 09:00–16:30 opening window. Earlier attempts correctly failed when the commitment was after closing or when the candidate lacked canonical facts; those failures remain machine history and were not bypassed.

## New real Place

- Place: Nara Craft Museum (なら工藝館)
- Place ID: real-place-b47a20314c81d5a81381d4a4
- Provider: overpass
- External identity: overpass:node/2465643503
- Official source: https://www.city.nara.lg.jp/site/shisetsu/60140.html
- Opening: OFFICIAL_WEB_VERIFIED, 10:00–18:00
- Cost: VERIFIED_PROVIDER, JPY 0; explicitly known free from official evidence, not UNKNOWN-as-free
- Journey estimate authority: off; the persisted canonical fact was used

The new Place was not present in the active PlanVersion before R22. Activity count increased from 2 to 3.

## Opportunity and F4 evidence

Server-derived opportunity evidence:

- current execution location: Isuien (real-place-22cf72809897ff4c7f312fcf)
- candidate: Nara Craft Museum
- next protected commitment: Daigokuden (real-place-470b4d1080037ab7f7e9b562)
- window opens: 10:00 local
- candidate inbound live mobility: 22 minutes
- candidate outbound live mobility: 55 minutes
- bounded visit finish: 11:47 local
- remaining buffer to the 15:00 commitment: 178 minutes
- safety buffer: 15 minutes
- fits=true
- failed_primary_pairs=[]
- fallback_pairs=[]

F4 proposal: c108032b-e225-4984-a4e3-a0bf3954baaa.

- family: F4_OPPORTUNITY_INSERTION
- parent: bf686752-bf9e-55e8-9de0-ebf739f83b85
- added: Nara Craft Museum
- removed: none
- protected commitment preserved: 1
- cost delta: 0 JPY
- travel delta: 13 minutes
- hard constraints: passed
- Gateway decision: REQUIRE_CONFIRMATION
- approval: 313c7257-7bed-47e4-8147-8c7656a73d70
- approval method: USER_CONFIRMATION
- approval receipt: consumed by the Agent Gateway

Mobility snapshot: 711b116d-a847-4032-ad0e-e61559c97246.

Actual used edges after activation:

| from | to | minutes | provider | provenance | hard eligibility |
|---|---|---:|---|---|---|
| Isuien | Nara Craft Museum | 22 | valhalla-http | LIVE_PROVIDER_CAPTURE | HARD_ELIGIBLE |
| Nara Craft Museum | Daigokuden | 55 | valhalla-http | LIVE_PROVIDER_CAPTURE | HARD_ELIGIBLE |

all_actual_edges_hard_eligible=true.

## Execution result

The real HTTP execution state machine completed all three activities:

Isuien: depart -> arrive -> begin -> complete
Nara Craft: depart -> arrive -> begin -> complete
Daigokuden: depart -> arrive -> begin -> complete

Final machine state:

- Journey.status=COMPLETED
- Journey.active_plan_version_id=bb321722-3534-4938-8841-7533879db171
- Journey.current_activity_id=null
- JourneyTwin.active_plan_version_id=bb321722-3534-4938-8841-7533879db171
- JourneyTwin.current_activity_id=null
- JourneyTwin.projection_status=READY
- proposal status: ACCEPTED
- old plan status: SUPERSEDED
- new plan selectable projection: true
- new plan authority projection: LIVE_PROVIDER_FACTS

The consumed opportunity event was resolved with reason OPPORTUNITY_CONSUMED.

## Product fixes

- server-derived opportunity event creation from JourneyTwin plus live mobility;
- English Agent search terms (culture, cultural, experience) mapping to provider-backed catalogue categories;
- F4 validation for provider identity, canonical opening, canonical cost, currency, active-plan exclusion, and two new mobility legs;
- additive replan materialization preserving the executed prefix and C4 commitment;
- Gateway approval consumption through the existing Agent boundary;
- Agent retry/completion contracts, stale-run reconciliation, and bounded conclusion reasons;
- projection consistency: canonical used Place truth is shown as LIVE_PROVIDER_FACTS; unresolved opening/cost truth still blocks selection.

## Focused tests

60 passed, 1 warning.

Command:
py -3.13 -m pytest -q tests/test_r22_opportunity_capture.py tests/test_r15_source_authority.py tests/test_agent_mission_runtime.py tests/test_guardian_v4.py tests/test_vertical_slice_hardening_next.py tests/test_r21_autonomous_future_synthesis.py

The warning is the existing Starlette/httpx deprecation warning.

## Honest limitations

- The experiment uses a disposable LAB SQLite database and future-dated lab activities; it does not mutate a real-user database.
- Valhalla supplies route truth but reports no live traffic in this capture (has_live_traffic=false); route provenance is still live provider capture.
- R22 NO_ACTION control was not used as the primary closure claim. The primary positive path is the completed additive opportunity path above.
- Nara Craft activity metadata retains an older agent-hypothesis trace for historical provenance, but authority-crossing fields are canonical official-web/provider facts. The plan projection derives visible authority from actual used Place truth.

## Replay

1. Checkout the published branch at the final commit in the isolated LAB worktree.
2. Set the LAB SQLite URL and CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false.
3. Configure WB2API through the existing local configuration path without copying its key into artifacts.
4. Set CITYNEXUS_LIVE_VALHALLA_URL=https://valhalla1.openstreetmap.de.
5. Start the backend and run Guardian scan on Journey fd29878e-8c6b-4bba-8a29-72193a710b59.
6. Inspect the SYSTEM_DERIVED OPPORTUNITY_WINDOW, then run the standing mission with the Agent surface that omits candidate/action hints.
7. Verify the AgentRun tool order, F4 evidence, live snapshot, Gateway approval, active PlanVersion lineage, and HTTP execution transitions.
8. Verify final Journey/Twin convergence and used_edge_ids from selected-plan frozen evidence.

## Closure

R22 is closed at the primary REVOLUTION_C target: CityNexus found a real new experience during an active trip, proved it fit with canonical facts and live provider mobility, passed authority approval, executed it, preserved the protected commitment, and completed the revised Journey.
