# CityNexus Mission OS V2 | Agent-native product and UI execution spec
2026-10-18 · Product overhaul, not another ORD/review round.

## 0. One audacious decision
CityNexus is **not** a travel-form wizard with an AI chat tab. It is a persistent, real-world Mission Operating System. The traveler describes an outcome; the Agent coordinates research, plans, maps, real-world changes, collaboration and execution. The interface is a continuously updated canvas containing **goal + Agent activity + map + schedule + decisions + real-world state**.

**No new fourth product.** Ship to the current \`/revolution\` entry. DSH/EAC/V8/Guardian/Revolution are sources of capabilities and interaction patterns, not separate compulsory navigation journeys. Use strong identity, explicit authority for irreversible actions, and honest source provenance **at their actual side-effect boundary**, never as blanket permission to refuse useful DRAFT research or partially useful output.

### Existing confirmed baselines (read before coding, refresh HEAD)
- Codex PR #23 \`design/revolution-mobile-first-v1\` @ \`eba965649befbcd955edfb69f0a033ecc0028ef6\`: signed DRAFT GoalTask, AgentRun/Step, server audit events, Photon/Nominatim query, MapLibre, editable 14-day draft, real run 13 model turns/12 tools/59 events, map-places, Workbench and ACTIVE UI. Positive POI after fixed public-region scope still unverified.
- Qoder PR #35 \`reform/qoder-capability-adapters-1018\` @ \`3044e31dbba459b49d904695ba49404ce76bdc6c\`: eight exported agent research/route tools; PLAN_ONLY allowlist, gateway approval, recovery credentials; still open on V8 base, not automatically available on Revolution.
- Native DSH-like reuse: \`frontend/src/features/agent/CopilotDock.tsx::NativeMissionTimeline\`, \`nativeHermesTimeline.ts\`, \`AgentRunRail\`, mobile \`AgentWorkStatus\`, \`MobileHermesRun\`, \`LiveRecovery\`. These are implementation assets, **not evidence** that all capabilities are live under the same signed Journey.
- Other source capability domains: \`recovery_epoch\`, \`shared_stop_coplanning\`, \`live_context_watch\`, \`route_session_operations\`, \`launch_origin\`, \`JourneyMission\`, \`PlanVersion\`, Guardian/Predictive/Opportunity/MomentScout, alternative plan portfolio, consent epoch, Traveler Twin, Side Quest, group recovery, stay, booking and notifications.

## 1. Radical user journey: zero preparatory maze
### 1A. Cold start
Fullscreen intelligent command field: "我想周末在福建玩两天，吃当地小吃，看古村落，尽量少走路。" Optional voice/photo/current public map area; extras progressive disclosure, **not six required fields**. User can also choose a sample prompt or resume a saved Mission. Ask for missing information only when it changes the next concrete decision. User can tell the Agent "自己想办法" and the Agent has an actual tool loop, not a fixed four-category classifier.

### 1B. One bounded research authorization, then autonomous loop
Confirm an understandable cost/scope once; allow Agent to investigate within that scope without asking after each zero result. Real Agent:
1) parse goal + constraints → persist Mission;
2) split into geographic discovery / source verification / feasible movement / timing / cost / group fit subgoals;
3) select available tool based on observed results; change source, query, geospatial partition or strategy after failure;
4) persist every tool event and partial research artifact; render immediately;
5) update map pins, editable day schedule and options without waiting for all facts;
6) surface **one meaningful decision** if the next material action needs the human.

Zero results are observations, not a global stop. Model unavailable? Keep cached facts, schedule editor, map and explicit continuation affordance. No blind unbounded retries and no pretend POI.

### 1C. The user never goes back to step one
"第二天下午别看博物馆，换成自然风景" = modify affected Mission constraints only; retain unaffected verified places and selected decisions; research alternative, project schedule/route/budget changes. Do not regenerate whole Journey or silently replace an in-force PlanVersion. When in ACTIVE, propose a versioned change, not casual direct mutation.

### 1D. On-trip agent
The same canvas pivots to NOW: what am I doing, where next, route, departure window, delays and decisions. Guardian checks context under enabled watch scope; changes become opportunity/risk cards. Examples: rain at 15:00 → research indoor alternative; venue closure → route + opening evidence + proposal; tired traveler → easier branch; group disagreement → Council presents trade-offs & consent states. If no actual watcher or route provider has run, do not simulate activity.

### 1E. Mission may continue between visits
Add server-owned durable Mission scheduling: task states, lease and checkpoint, event-triggered reevaluation, accepted source budget, revocation, idle status and recovery after process restart. The current synchronous request and client polling are only the first vertical slice. No reliance on keeping a web tab open, no fake background operations. Tasks with a scheduled/event trigger execute only if the server job infrastructure actually supports them.

## 2. New interaction primitives (these replace pages, not existing domain models)
1. **Mission Composer:** omnipresent one-line command box, text/voice-ready. Suggest next useful action contextual to the Journey; can accept "keep researching", "compare alternatives", "make it less tiring", "share with group".
2. **Living Spatial Canvas:** map is the visual center, with persisted SOURCE_LEAD / GEOLOCATED_PLACE / VERIFIED_FACT / PLAN_ITEM distinctions; Day 1/Day 2 layers, route snapshots with timestamp, cluster/focus and drag-to-propose. Never invent coords/ETA.
3. **Agent DSH Trace:** inline compact lane plus expandable Control Tower. Real backend \`AgentRun\`, \`AgentRunStep\`, \`AuditLog\` and native tool events unify by mission/run_id/sequence; show planning **summary** (not private model reasoning), actual tool, elapsed time, result, failed/alternate action, budget, provider, consent, last persisted timestamp. Streaming if available; cursor-based signed polling fallback.
4. **Artifact Deck:** editable itinerary, place dossiers, source receipts, route alternatives, spending projection, room/group proposals, guardian incidents. Artifacts update progressively; no separate submit wizard.
5. **Decision Inbox:** one prioritized approval queue in plain Chinese, with why, before/after impacts, affected members, one-tap approve/reject/edit, ability to defer; irreversible payments/booking/group decisions remain separately authorized.
6. **Agent Team surface:** real orchestration roles **Scout** (place/source), **Architect** (schedule/alternatives), **Navigator** (routes/execution), **Guardian** (world adaptation), **Mediator** (group). They are role *capabilities*, not five decorative fake agents. Only mark a role RUNNING if a bound real run/step exists.
7. **Timeline of Reality:** Now/Next/Later fused with map. Past fact events, active execution, pending proposals and contingency options live on one timeline.
8. **Mission Memory:** user-controlled preference/Twin and group consent, bound to signed account/Journey; action explains memory sources and can be corrected or forgotten. Reuse existing traveler preference APIs.

### Mobile layout (390–430px target)
- Hero: one-line current Mission + live status; not settings/AI connected status first.
- Primary surface: spatial map with itinerary cards overlaid / swipable, or honest "awaiting grounded place" state.
- Bottom: **always accessible Agent composer**; a small running trace strip above it, tap to expand Control Tower.
- One thumb zone for NOW, MAP, MISSIONS and ME. Explore, places, plans and group decisions are **Mission views/layers**, not mandatory sequential tab clicks.
- Fast affordances: pause, undo tentative edits, approve pending decision, change objective; no 40-field form wall.
- Special states: cold start, research working, partial with zero sources, draft ready, plan proposed, ACTIVE guardian, recovery, auth renewal, model offline.

### Desktop layout (1280–1600px)
Three spatial panes with shared selection: left Agent chat and Missions; middle large MapLibre + layered route and activity markers; right editable timeline + source/approval/Agent trace. No modal covering the whole map when user asks a question. Pinned context shared by click, no duplicate state.

### Visual language
Editorial consumer app quality. Cool midnight-indigo for Agent intelligence, warm off-white surfaces, restrained teal for verified reality, amber only when a decision is required, red only for a real consequential failure. Semantic colors indicate **evidence/status**, not decoration. Large type for today's question, compact metadata, soft-radius cards, 44px target sizes, keyboard/voice/accessibility, reduced-motion and low-end Android safe. Do not scatter developer codes into primary copy.

## 3. Ability map: historical work must reach the Agent
| Role / UX result | Reuse domain surfaces | Required callable output |
| --- | --- | --- |
| Scout / real discoveries | Photon/Nominatim/OSM/Overpass, \`research_place_sources\`, \`acquire_place_facts\`, \`estimate_place_facts\` | Place lead with source, geo/identity status, known/unknown fields, source call receipt |
| Architect / coherent days | \`JourneyIntent\`, \`TravelBrief\`, draft artifacts, \`generate_plans\`, PlanVersion/portfolio | Editable multi-day schedule; competing better-cheaper-less-tiring branches |
| Navigator / route and NOW | MobilityFact, Valhalla, \`compare_routes\`, \`acquire_route\`, LaunchOrigin, Pocket Walk, execution | Sourceful route, departure/arrival estimates only if acquired, execution step state |
| Guardian / proactive adaptation | \`live_context_watch\`, \`recovery_epoch\`, weather/opening/event/incident, opportunity scouting | Real changed-world event → consequence → repair options → changed plan proposal |
| Mediator / shared trip | \`shared_stop_coplanning\`, consent epoch, member invitations, shared recovery | Who agreed, open conflicts, negotiated alternatives, member-bound decisions |
| Steward / trip economy and continuity | Traveler Twin, stay, budget, booking/refund, notifications, history | Preferences, options, spend estimate vs verified price, confirmations, after-trip recap |

No "blocked because tool is not on same branch" at UX layer. Product integration must expose implementation status; Codex/Qoder create contract adapters that reuse service/domain entities, not bypassing the requirement by prompting fabricated results. \`generate_plans\` creates a candidate PlanVersion; design Mission continuation to **survive** candidate creation, not to forbid the tool globally. A scoped authorization model lets the Agent freely read/research/create reversible drafts while purchases/commitments/effective group changes are explicit.

## 4. Event and action architecture: concrete contracts to converge on
Do not create redundant shadow databases. Use \`JourneyMission\`, \`AgentRun\`, \`AgentRunStep\`, \`AuditLog\`, \`JourneyIntent\`, \`PlanVersion\`, \`ProviderCall\`, \`WebObservation\`, \`RecoveryEpoch\` plus narrowly necessary mapping tables.

- \`GET /api/v1/journeys/{id}/mission-workspace\`: new signed projection with mission summary, capabilities, last Agent events, artifacts, live plan, map markers (source types), pending decisions, Guardian state, resume action; one server-owned current mission ref. This is a *proposed new API*, not a claim that the route already exists.
- \`GET /api/v1/journeys/{id}/missions/{missionId}/events?after=cursor\`: signed cursor, resumable event feed. Existing \`getDraftGoalTaskEvents\`/native timeline are temporary compatibility adapters; no stale client-only pointer as authority.
- \`POST /api/v1/journeys/{id}/missions\`: goal and optional bounded standing mandate, persistence/semantic fingerprint/idempotency. Model decides tool selection.
- \`POST /api/v1/journeys/{id}/missions/{missionId}/intent\`: user change command; compute impacted artifacts/slots, preserve unaffected authority.
- \`POST /api/v1/journeys/{id}/missions/{missionId}/pause|resume|cancel\`: real durable task control, actual running job state. Don't mark cancelled while a dispatched provider write can still silently commit.
- \`GET /api/v1/journeys/{id}/decisions\`, \`POST .../decisionId/resolve\`: unified approval UI, underlying approval/consent receipts and scope unchanged.
- \`MissionArtifact\`: stable id, owner scope, semantic type, revision, evidence_level, source_ref, time, geospatial refs, provenance, tentative/selected/active status, undoable, affected_plan_items, task_id. This may be a projection assembled from current rows rather than a new table unless persistence requires it.

**Streaming UX:** use SSE or WebSocket only after real signed server production; polling snapshot is allowed for first slice. No client fake thinking animation. Screens cannot discard task state when changing tabs or reloading.

## 5. First implementation in this feature branch
Branch \`design/revolution-mission-os-v2-20261018\` is anchored at Revolution \`eba965649b\`. It adds:
- \`frontend/src/trial/mobile/MissionCockpit.tsx\`: signed existing Journey map read, current GoalTask pointer + authenticated task/event reads, live work stats, editable command to existing goal-task launcher, prior drafted day cards, core action entrypoints.
- \`MissionCockpit.css\`: distinct responsive premium UI, desktop two-pane / mobile single-pane; real MapLibre via existing \`WorkspaceMap\` instead of imitation coordinates.
- Integrates this above legacy manual exploration in existing \`/revolution\` without deleting functionality. Adds map expansion event to existing signed map dialog and removes the hard-coded default county.
- This is a **first working UI slice**, not the complete Mission OS implementation, not verified locally, not USER_VERIFIED. No runtime/network/provider call made by writing code via GitHub.

## 6. Next implementation slices, **parallel but integrated**
**Codex / primary \`/revolution\`**
1. Full Mission OS state-based shell: user goal first, jump to Mission canvas immediately after Journey creation; replace the old 5-tab/modal behavior with persistent non-modal Agent + map + schedule and meaningful progressive disclosure. Preserve one-tap manual fallback, old data and the real LIVE GO path. Real Chrome use screenshots on 390/430/1366 and sourceful event/POI evidence.
2. Connect signed \`mission-workspace\` projection. Unify DRAFT and ACTIVE agent trace into one rail with accurate states, real event cursor, user task control, partial results and explicit resume. Remove localStorage pointer as sole recovery mechanism; server owns latest task lookup.
3. Bring real research-place pins, multi-day draft, source links and selected PlanVersion into shared canvas. Extract public city from structural signed trip context, not user-custom Journey title. No longer let an existing unselected candidate PlanVersion shut down useful Goal research.
4. Introduce three real compareable variant canvases (less-walking/cheaper/more-interesting) with route/price unknown clearly shown. User edits a slot, impacted options recompute without wiping the Journey.

**Qoder / capability plane**
1. Expose \`source/geo/route\` and discovery/research even with zero canonical Places. Fix public city scope leakage in source research, and signed task-to-tool adapter. Provide handoff to Codex as schema + code, not another list.
2. Port Guardian watcher/recovery, group mediator/consent, Traveler Twin, stay/budget, notifications, booking and route collectors as callable typed adapters. For each: registered → reachable with Journey owner → actual dispatch → persisted artifact/event → UI action. Existing proven domain truth never downgraded.
3. Design real background lease/heartbeat/checkpoint/event subscription for bounded autonomous Missions, including durable stop/resume and provider budget reservation. The Agent should survive closing the tab where server infrastructure is available.
4. Shared adapter PRs merge in small verified slices into the main product, not a second V8 face.

## 7. Human acceptance: reject green-test theater
A normal traveler on one real SHA does, without a written manual:
1. types a two-day multi-interest goal and starts research;
2. sees real run and tool trace, including first provider zero result and chosen follow-up;
3. gets geographically grounded pins and an editable provisional day schedule, without classifying four categories;
4. says "换成轻松路线" and sees only affected time/routes/research update;
5. selects an itinerary, starts and sees NOW/Next with real sourceful route/arrival state;
6. introduces a genuine change event (provider-backed when possible), and sees Guardian investigate, propose and obtain any needed consent;
7. group member B sees their own state and proposal before any shared-plan change;
8. close/reopen/re-authenticate keeps the same task and artifacts, without exposing another person's trace.

Report \`PRODUCT_SHA\`, \`ENTRY_URL\`, \`USER_FLOW\`, \`REAL_AGENT_RUN\`, \`REAL_TOOL_EVENTS\`, \`REAL_MAP_PINS\`, \`DRAFT_EDIT_RESTORED\`, \`ACTIVE_NAVIGATION\`, \`GUARDIAN_EVENT\`, \`GROUP_DECISION\`, \`USER_VERIFIED\` **as independent evidence fields**. Failures must produce a next user-usable action, not a pile of fixtures. Update the screen and workflow before writing extensive test policy.
