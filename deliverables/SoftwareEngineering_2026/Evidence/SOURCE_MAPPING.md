# Source mapping

Every shape and every plan row traces to something that exists. This is the
table to open when a marker asks "where did you get that from?".

## Measured from the tree, at generation time (2026-10-23)

| Fact used in the drawings | How it was measured | Value |
|---|---|---|
| HTTP endpoints on the backend | count of `^@app.(get\|post\|patch\|put\|delete)` in `backend/app/main.py` | 175 |
| Size of the backend entry module | line count of `backend/app/main.py` | 14,569 |
| Database tables | count of `__tablename__ = ` in `backend/app/db/models.py` | 60 |
| Python modules under the backend app | recursive `*.py` count | 146 |
| Backend test modules | `backend/tests/test_*.py` | 234 |
| Frontend e2e specs | `frontend/e2e/*.ts` | 184 |
| Requirements | `requirements/requirements.yaml` lists: {'business_goals': 8, 'functional_requirements': 61, 'business_rules': 24, 'non_functional_requirements': 16, 'security_requirements': 14, 'integration_requirements': 15} | 138 |
| Use cases | `use-cases/use-cases.yaml` | 13 top level, 14 detail |
| Actors | same file | 9 |
| include / extend relationships | same file | 14 include, 3 extend |
| Agent tools | `backend/app/agent/tool_catalog.py:26-59` | 11 (6 V1 + 5 typed) |
| Commits on this branch | `git rev-list --count HEAD` | 1109 |
| First commit anywhere in the repo | `git log --all --date=short` | 2026-09-05 |
| Top authors | `git log --format=%an` | 浠撻紶鐜� (1016), qoder-ai-lane (23), cff87c64 (13), lane-82f55d8a (9), lane-5a53846b (8) |

## The four Visio drawings

| Drawing | Shapes | Connectors | What each shape carries |
|---|---|---|---|
| `01_CityNexus_System_Architecture.vsdx` | 23 | 24 | a code anchor in its caption and in the custom property `SourceRef` |
| `02_CityNexus_User_Journey.vsdx` | 28 | 34 | a code anchor in its caption and in the custom property `SourceRef` |
| `03_CityNexus_Agent_Workflow.vsdx` | 38 | 43 | a code anchor in its caption and in the custom property `SourceRef` |
| `04_CityNexus_Use_Case.vsdx` | 39 | 47 | a code anchor in its caption and in the custom property `SourceRef` |

Anchors cited inside the drawings, by layer:

**Users and frontend** - `frontend/src/main.tsx:38`, `frontend/src/app/V8Experience.tsx:1`,
`frontend/src/routes/v8Routes.ts:1-33`, `frontend/src/components/JourneyMap.tsx:1`,
`frontend/src/features/agent/CopilotDock.tsx:1`, `frontend/src/features/agent/AgentRunRail.tsx:1`,
`frontend/src/features/planning/PlanComparison.tsx:1`,
`frontend/src/features/checkin/checkins.ts:14`, `frontend/src/features/collections/collections.ts:16`

**Backend transport** - `backend/app/main.py`: journeys `:3136`, `:7139`, `:9294`, `:10019`;
plans `:7369`, `:7728`, `:7790`; replanning `:10923`, `:13097`, `:13569`; places `:7328`,
`:7355`, `:5558`, `:5572`; commerce `:14404`, `:14471`, `:14508`; twin and capability
`:9846`, `:2761`, `:2568`; guardian and autopilot `:1599`, `:1608`, `:1772`; SSE `:1982`;
copilot `:14169`, agent commands `:1367`, tool call `:1246`, approvals `:2081`, feed `:10125`

**Agent plane** - `backend/app/agent/mission.py:231,384`; `mission_plan.py:74`;
`runtime.py:62,238,289,336,660`; `gateway.py:59,71,338-347,357-398`;
`tool_catalog.py:20-22,26-59`; `ai_availability.py`; `delegation_policy.py`;
`backend/app/integrations/ai/semantic_compiler.py:123,229`;
`backend/app/integrations/hermes/native_client.py:34,71,132,158,169`;
`agent-mcp/citynexus_mcp/server.py:128,157-207,378,404-549`

**Providers** - `integrations/discovery/photon.py:20-27`; `discovery/real_city.py:617,684-688`;
`integrations/context/open_meteo.py:29-36`; `integrations/mobility/valhalla_http.py:32`;
`integrations/china/amap.py:10,47`; `integrations/web/searxng.py:29`;
`integrations/ai/responses.py:244`; `integrations/mock/providers.py:13`

**Persistence** - `backend/app/db/models.py` at `:22,175,212,254,271,511,535,562,578,677,692,712,761,782,824,1324,1360,1382`;
`backend/app/db/session.py:70-88`; `backend/app/core/config.py:10,14,33,44,79-81,88,96-98`

**Status colours** - implemented-and-evidenced vs implemented-but-unproven vs planned is
decided from `BLOCKERS.md:9-16`, `BUG_REPORT_20260913.md`, `CURRENT_STATUS.md:4`,
`TEST_RESULTS.md`, `HERMES_INTEGRATION_STATUS.md`, `AGENT_TOOL_CATALOG.md:16-18` and
the deployment defaults in `core/config.py`.

## The Microsoft Project plan

| Row group | Evidence the work is real |
|---|---|
| 1  Initiation | the assignment brief PDF itself; first commit 2026-09-05 |
| 2  Requirements | requirements/requirements.yaml v0.3.0 (138 entries) and use-cases/use-cases.yaml v0.1.0 |
| 3  Design | AGENT_RUNTIME_ARCHITECTURE.md, contracts/openapi.yaml, visio/ baseline v1.0-RC5 |
| 4  Backend | 175 endpoints, 60 tables, backend/tests (234 modules) |
| 5  Map and place data | integrations/discovery/*, integrations/context/*, .env.example:18-31 |
| 6  Agent and Hermes | backend/app/agent/*, agent-mcp/*, BLOCKERS.md:9-12 for what is not proven |
| 7  Frontend | frontend/src/*, 184 e2e specs, CityNexus_进度汇报_2026-10-13.md walked the demo live |
| 8  Integration | the authoritative line and the four-leg landing loop of 2026-10-08 |
| 9  Verification | PROJECT_STATUS_SNAPSHOT_20260913.md (344/2), TEST_RESULTS.md (24 passed), the 2026-10-13 report (1887 passed / 45 failed) |
| 10 Coursework | the brief's own two deadlines: 2026-10-02 and 2026-11-06 |
| 11 Delivery | this Evidence folder |

Milestone dates are taken from dated artefacts in the tree, not chosen freely:
* `M1  Topic and scope agreed` -> 2026-09-08
* `M2  Requirements baseline drafted` -> 2026-09-15
* `M3  Architecture design complete` -> 2026-09-22
* `M4  Core backend running end to end` -> 2026-10-05
* `M5  Provider mesh integrated behind one interface` -> 2026-09-28
* `M6  Agent surface proven against a live model` -> 2026-10-05
* `M7  Frontend running against the real backend` -> 2026-10-01
* `M8  Integration line stable` -> 2026-09-23
* `M9  System test ready (plan target)` -> 2026-10-06
* `M10  Part 1 course deadline (contract 2026-10-02, missed)` -> 2026-09-29
* `M11  Mid-term teacher review (scheduled 2026-10-23 noon)` -> 2026-10-16
* `M12  Part 2 course deadline (contract 2026-11-06)` -> 2026-10-23
* `M13  Coursework delivery (plan)` -> 2026-10-23

The one deliberate exception is M9 (system test complete), which is a plan
choice rather than a fact and is marked provisional in its own Notes field.

## Files produced, with fingerprints

**Visio**

| file | bytes | sha256/16 |
|---|---|---|
| `Visio/01_CityNexus_System_Architecture.vsdx` | 62156 | `2869450c0f1d4e2d` |
| `Visio/02_CityNexus_User_Journey.vsdx` | 62749 | `d9c88139e7d82304` |
| `Visio/03_CityNexus_Agent_Workflow.vsdx` | 66526 | `3f7c57410bf6abfd` |
| `Visio/04_CityNexus_Use_Case.vsdx` | 84933 | `6d77427c4c085ca6` |
| `Visio/previews/01_CityNexus_System_Architecture.gate.json` | 7395 | `5402dc267d90c06f` |
| `Visio/previews/01_CityNexus_System_Architecture.pdf` | 48522 | `5e3749b68fc000e8` |
| `Visio/previews/01_CityNexus_System_Architecture.png` | 137597 | `44a46327dc95c208` |
| `Visio/previews/02_CityNexus_User_Journey.gate.json` | 8715 | `c283b9e226eefd23` |
| `Visio/previews/02_CityNexus_User_Journey.pdf` | 45109 | `7ebd1d5526198a94` |
| `Visio/previews/02_CityNexus_User_Journey.png` | 138386 | `4d200bc7bcb48302` |
| `Visio/previews/03_CityNexus_Agent_Workflow.gate.json` | 10997 | `7eb26c02ba8da043` |
| `Visio/previews/03_CityNexus_Agent_Workflow.pdf` | 51291 | `ade5be2e723b6582` |
| `Visio/previews/03_CityNexus_Agent_Workflow.png` | 211852 | `dc2f95b0b3c04232` |
| `Visio/previews/04_CityNexus_Use_Case.gate.json` | 17039 | `3673fa0aa322dbcd` |
| `Visio/previews/04_CityNexus_Use_Case.pdf` | 53112 | `f72929fadf44290a` |
| `Visio/previews/04_CityNexus_Use_Case.png` | 178603 | `6ed02dbdf39c345e` |
| `Visio/previews/04_CityNexus_Use_Case_p1.png` | 178603 | `6ed02dbdf39c345e` |
| `Visio/previews/04_CityNexus_Use_Case_p2.png` | 109974 | `a5b04adf63e2f0eb` |

**Microsoft Project**

| file | bytes | sha256/16 |
|---|---|---|
| `Microsoft_Project/Detailed_Gantt.pdf` | 454510 | `99449d41b60a65e0` |
| `Microsoft_Project/Gantt_Chart.pdf` | 842537 | `c8ecfc8663316dc1` |
| `Microsoft_Project/Milestone_Timeline.pdf` | 441384 | `7cc39d265043f0b9` |
| `Microsoft_Project/Network_Diagram.pdf` | 171583 | `b393c185c450df50` |
| `Microsoft_Project/Plan_Briefing_Print.pdf` | 450847 | `50d174e434c01739` |
| `Microsoft_Project/Resource_Sheet.pdf` | 147059 | `62f778f5d40380bc` |
| `Microsoft_Project/Tracking_Gantt.pdf` | 601735 | `9cb7e893f2f77e8a` |
| `Microsoft_Project/WBS_View.pdf` | 196387 | `54e10c5b0aa2291f` |
| `Microsoft_Project/CityNexus_Milestone_View.mpp` | 253952 | `d1def47164e694c0` |
| `Microsoft_Project/CityNexus_Plan_Briefing.mpp` | 272896 | `99adeb281957bb87` |
| `Microsoft_Project/CityNexus_Plan_Recovery.mpp` | 289792 | `7e4f561a46d32b22` |
| `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` | 386048 | `6398e58f9b4cd3b3` |
| `Microsoft_Project/previews/Calendar.png` | 491670 | `aad8217129b2d073` |
| `Microsoft_Project/previews/Gantt_Chart.png` | 339826 | `fa25166f0fb8f364` |
| `Microsoft_Project/previews/Milestone_Timeline.png` | 293526 | `ccbce7847ae160a4` |
| `Microsoft_Project/previews/Network_Diagram.png` | 290112 | `6021906c888c40fe` |
| `Microsoft_Project/previews/Resource_Sheet.png` | 255697 | `1c8dfe4b9582c4d0` |
| `Microsoft_Project/previews/Tracking_Gantt.png` | 511477 | `753ff0289f9adf03` |
| `Microsoft_Project/previews/WBS_Task_Sheet.png` | 484575 | `f692a09bcf838299` |
