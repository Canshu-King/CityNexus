# CityNexus Revolution Lab — R6 result

## Scope

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- starting commit: `05e66f151ca689284915d3c7357896120c62217a`
- final experimental commit: `0dfe2621c254d16c9e65dc8189433fd7e3ae6c78`
- mainline/P7: untouched; `P7=false`
- database: disposable SQLite only, `citynexus-r77-authority-gate-r4-20260930.sqlite3`
- clean-source gate: `git status --porcelain` was empty before every product HTTP call in this round

This round continued the same R77 Suzhou scenario. No canonical demo seed, real-user database,
payment, booking, or authority/mainline merge was used.

## Scenario and destination identity

- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- Journey title: `R77 Suzhou verified garden candidate 2`
- city: `CN-SUZHOU`
- window: `2026-10-04T09:00:00+08:00` to `2026-10-04T19:00:00+08:00` (`Asia/Shanghai`)
- final selected plan: `09715a08-4e06-57b7-bebc-b9a5adf872a2`, version 11
- final Journey state: `PLANNED`, `active_plan_version_id=09715a08-...`

The two R6 target entities were not inserted into canonical seed data:

| Place ID | Name | Provider entity | Identity evidence |
|---|---|---|---|
| `real-place-8bc850f117297987997c87cf` | 网师园 | `overpass:way/44679452` | exact Overpass entity + Nominatim way/44679452 + operator-verified municipal page id=45 |
| `real-place-ba7377353c422c39dfd752b7` | 拙政园 | `overpass:way/468359738` | exact Overpass entity + Nominatim way/468359738 + operator-verified municipal page id=58 |

## Before/after behavior

Before the bounded repair, the real facts endpoint fetched the official pages but retained lower-
priority map values whenever Overpass already had a value. The first post-acquisition candidate
(version 10) therefore still carried 网师园 3000 minor units / 07:30–17:00 and 拙政园 9000
minor units / 07:30–17:30.

The repair in commit `d149c8b7c7e45d6620b2b1f7de3a3c038cc12481` makes only an exact,
operator-bound `MUNICIPAL_AUTHORITY` source able to supersede the map tag. Unbound arbitrary
websites are not promoted.

After the repair, the same product endpoint persisted:

- 网师园: `OFFICIAL_WEB_VERIFIED`, 07:30–17:30, `VERIFIED_PROVIDER`, 4000 CNY minor units
- 拙政园: `OFFICIAL_WEB_VERIFIED`, 07:30–17:30, `VERIFIED_PROVIDER`, 8000 CNY minor units

The next real generate call returned HTTP 201, `selectable=true`, and plan version 11. The real
select call returned HTTP 200 and made that exact plan authoritative (`Journey.active_plan_version_id`
points to it; persisted plan status is `SELECTED`).

## Provider and preparation evidence

The fact-acquisition receipt records, for both targets:

- Overpass HTTP 200 with the exact provider entity;
- Nominatim `/lookup` `status=ACQUIRED`, `matched_provider_entity=true`, with `extratags`;
- official municipal source `https://visitsz.wglj.suzhou.com.cn/scenic-spot-detail.aspx?id=45`
  for 网师园 and id=58 for 拙政园;
- official parser status `ACQUIRED` and source binding `approval=OPERATOR_VERIFIED`;
- no SearXNG promotion (`UNCONFIGURED`, no observations).

The official pages were captured in the package. The exact Nominatim response and the product
receipt are also included; no raw credential is included.

## Actual selected path and hard eligibility

The selected plan's persisted mobility snapshot is:

- snapshot: `2b121388-16b3-4fcd-8fcd-fcda27eb619b`
- provider: `valhalla-http`
- route provenance: `LIVE_PROVIDER_CAPTURE`
- fact quality: `LIVE_PROVIDER_CAPTURE`
- degraded: `false`
- facts in frozen snapshot: 110

Actual used edges, taken from the selected plan's consecutive activities and persisted evidence:

1. `real-place-06361e97cfc5a371f68f7875` → `real-place-054fa857eff7a99169399bdf`, WALK, 13 min
2. `real-place-054fa857eff7a99169399bdf` → `real-place-8bc850f117297987997c87cf`, WALK, 38 min
3. `real-place-8bc850f117297987997c87cf` → `real-place-ba7377353c422c39dfd752b7`, WALK, 42 min

The final product Twin and Scene expose edge-scoped receipts computed by the product's own
`MobilitySnapshot.hard_minutes` gate:

- all three persisted minutes equal hard minutes: 13, 38, 42;
- all three `hard_eligible=true`;
- all three `decision=HARD_ELIGIBLE`;
- `all_actual_edges_hard_eligible=true`;
- Scene coverage: `mobility_legs_hard_eligible=3` of `mobility_legs_total=3`.

No `used_edge_ids`, eligibility receipt, route, or selectable result was synthesized by the
reporting layer.

## Agent execution

### DeepSeek Builder / critic runtime

DeepSeek was executed through the native product runtime, not represented by narration:

- runtime identity: `NATIVE_DEEPSEEK_TOOL_LOOP`
- model: `deepseek-v4-flash`
- final run: `93c3029d-07f5-4b02-94fa-51a54653ad33`
- final status: `COMPLETED`
- final run used read-only PLAN_ONLY tools only

The agent first exposed two real observation gaps:

1. `search_city_services` could not find an exact place when the model added fact terms after
   the exact name; commit `8d07b409a2a7b522a45ea55a1c60511fb6198f67` fixed only this exact-name
   query direction and added a regression test.
2. Twin exposed only aggregate hard-eligible counts; commit `0dfe2621...` added per-edge receipts
   derived from the same deterministic hard gate.

The final DeepSeek run consumed the official facts and all three edge receipts and concluded all
requested checks pass. Its complete response and tool trace are included in the package.

### Hermes Operator / Critic

Hermes was not fabricated. The runtime readback says:

- `configured=false`
- `reachable=false`
- `ready=false`
- no provider/model

Therefore this round has no Hermes trace. The deterministic product gates and the native DeepSeek
read-only trace remain the evidence sources.

## Focused tests

The focused gate run on the final source:

```text
50 passed, 2 warnings
```

Suites:

- `tests/test_revolution_r77_recovery.py`
- `tests/test_agent_runtime_gate.py`
- `tests/test_qoder_mobility_evidence_sources.py`
- `tests/test_qoder_catalog_reason_code.py`

The two warnings are existing Starlette/httpx deprecation warnings. A broader unrelated matrix
probe suite still has two environment-sensitive failures (`CAPTURED` vs its expected oversized
matrix fixture and a missing `error_type` in that fixture); those failures were not caused by the
R6 source diff and are retained as separate evidence rather than relabeled.

## Exact result

**SELECTED / usable product plan path.** The same real Suzhou destination now travels through:

```text
exact provider entities
→ Nominatim second source
→ operator-bound municipal official facts
→ persisted catalog facts
→ real planner
→ Valhalla live mobility evidence
→ 3/3 edge hard eligibility
→ HTTP 200 plan selection
→ user-visible Experience/Twin/Scene readbacks
```

This is not a booking or payment success, and the Journey was deliberately not started. `MOCK !=
LIVE`, `UNKNOWN != ACCESSIBLE`, and P7 remains false.

## Replay

1. Use the final commit listed above in the isolated worktree.
2. Point `CITYNEXUS_DATABASE_URL` at a disposable copy of the packaged SQLite snapshot.
3. Start `uvicorn app.main:app` from `backend` on an isolated port with live city mode and the
   Valhalla URL; inject DeepSeek credentials only into the child process environment if the agent
   read-only run is being replayed.
4. POST the two target Place IDs to `/api/v1/journeys/{journey_id}/facts/acquire`.
5. POST `/api/v1/journeys/{journey_id}/plans/generate` with `{"candidate_count":1}`.
6. Read the returned plan, then POST `/api/v1/journeys/{journey_id}/plans/{plan_id}/select`.
7. Read `/journeys/{journey_id}/experience`, `/journeys/{journey_id}/twin`, and `/demo/scene`;
   compare `used_edge_ids`, `eligibility_receipts`, and `all_actual_edges_hard_eligible`.
8. Optionally POST the final read-only PLAN_ONLY DeepSeek command; do not call booking/payment or
   replan mutation endpoints.

