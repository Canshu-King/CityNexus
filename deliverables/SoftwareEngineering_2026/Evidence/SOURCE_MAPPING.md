# Source mapping

Every shape and every plan row traces to something that exists. This is the
table to open when a marker asks "where did you get that from?".

## Measured from the tree, at generation time (2026-10-22)

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
| Commits on this branch | `git rev-list --count HEAD` | 1095 |
| First commit anywhere in the repo | `git log --all --date=short` | 2026-09-05 |
| Top authors | `git log --format=%an` | 浠撻紶鐜� (1006), qoder-ai-lane (23), cff87c64 (13), lane-82f55d8a (9), lane-5a53846b (8) |

## The four Visio drawings

| Drawing | Shapes | Connectors | What each shape carries |
|---|---|---|---|
| `01_CityNexus_System_Architecture.vsdx` | 23 | 24 | a code anchor in its caption and in the custom property `SourceRef` |
| `02_CityNexus_User_Journey.vsdx` | 28 | 34 | a code anchor in its caption and in the custom property `SourceRef` |
| `03_CityNexus_Agent_Workflow.vsdx` | 29 | 35 | a code anchor in its caption and in the custom property `SourceRef` |
| `04_CityNexus_Use_Case.vsdx` | 36 | 47 | a code anchor in its caption and in the custom property `SourceRef` |

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
* `M1  Topic and scope agreed` -> 2026-09-05
* `M2  Requirements baseline drafted` -> 2026-09-12
* `M3  Architecture design complete` -> 2026-09-15
* `M4  Core backend running end to end` -> 2026-09-14
* `M5  Provider mesh integrated behind one interface` -> 2026-09-21
* `M6  Agent surface proven against a live model` -> 2026-09-23
* `M7  Frontend running against the real backend` -> 2026-10-13
* `M8  Integration line stable` -> 2026-10-08
* `M9  System test complete` -> 2026-11-02
* `M10  Part 1 deadline (missed)` -> 2026-10-02
* `M11  Mid-term review` -> 2026-10-22
* `M12  Part 2 submission deadline` -> 2026-11-06
* `M13  Final coursework delivery` -> 2026-11-06

The one deliberate exception is M9 (system test complete), which is a plan
choice rather than a fact and is marked provisional in its own Notes field.

## Files produced, with fingerprints

**Visio**

| file | bytes | sha256/16 |
|---|---|---|
| `Visio/01_CityNexus_System_Architecture.vsdx` | 57854 | `e5c59fcbd8777c00` |
| `Visio/02_CityNexus_User_Journey.vsdx` | 58343 | `7262e57ae18c6ec9` |
| `Visio/03_CityNexus_Agent_Workflow.vsdx` | 47953 | `12bc16742a7d8f8a` |
| `Visio/04_CityNexus_Use_Case.vsdx` | 84063 | `8206e8ac86e40dba` |
| `Visio/previews/01_CityNexus_System_Architecture.gate.json` | 9907 | `4c514f8a540127a6` |
| `Visio/previews/01_CityNexus_System_Architecture.pdf` | 50297 | `6a5af7a061b40edc` |
| `Visio/previews/01_CityNexus_System_Architecture.png` | 147009 | `5f106c41234413ee` |
| `Visio/previews/02_CityNexus_User_Journey.gate.json` | 12664 | `bc5195bb111edb5d` |
| `Visio/previews/02_CityNexus_User_Journey.pdf` | 46380 | `e73363bb8930712d` |
| `Visio/previews/02_CityNexus_User_Journey.png` | 159783 | `a4d8ed593e543beb` |
| `Visio/previews/03_CityNexus_Agent_Workflow.gate.json` | 12547 | `6f2f4cb1903e64c2` |
| `Visio/previews/03_CityNexus_Agent_Workflow.pdf` | 46235 | `9b69fa2675905a14` |
| `Visio/previews/03_CityNexus_Agent_Workflow.png` | 154636 | `e27b49ced9eee7e0` |
| `Visio/previews/04_CityNexus_Use_Case.gate.json` | 18586 | `751ef58b20043172` |
| `Visio/previews/04_CityNexus_Use_Case.pdf` | 52267 | `d69cb560a6e99e54` |
| `Visio/previews/04_CityNexus_Use_Case.png` | 325141 | `24e89c0178f8dfee` |

**Microsoft Project**

| file | bytes | sha256/16 |
|---|---|---|
| `Microsoft_Project/Detailed_Gantt.pdf` | 468403 | `a9a19ff6c5d924ea` |
| `Microsoft_Project/Gantt_Chart.pdf` | 775484 | `a09996fa0a0dffcf` |
| `Microsoft_Project/Milestone_Timeline.pdf` | 385816 | `d68438d3c06509d2` |
| `Microsoft_Project/Network_Diagram.pdf` | 150871 | `502bddf072097645` |
| `Microsoft_Project/Resource_Sheet.pdf` | 126924 | `f1fa63ee58758f91` |
| `Microsoft_Project/Tracking_Gantt.pdf` | 543591 | `49405b51c5e0fd57` |
| `Microsoft_Project/WBS_View.pdf` | 194261 | `516636ab8fb0f35b` |
| `Microsoft_Project/CityNexus_Milestone_View.mpp` | 253952 | `e936d77beabcebf0` |
| `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` | 485888 | `04c5478c9bcb2a3a` |
| `Microsoft_Project/previews/Calendar.png` | 200761 | `44d5e6a4bcaef4b3` |
| `Microsoft_Project/previews/Gantt_Chart.png` | 159451 | `c1524868dc31f521` |
| `Microsoft_Project/previews/Network_Diagram.png` | 178837 | `e4de5486dbb6753b` |
| `Microsoft_Project/previews/Resource_Sheet.png` | 127135 | `324ca42dacfaff2f` |
| `Microsoft_Project/previews/Tracking_Gantt.png` | 247812 | `2944194351ecd717` |
| `Microsoft_Project/previews/WBS_Task_Sheet.png` | 237177 | `8e94fa4e28ca80c7` |
