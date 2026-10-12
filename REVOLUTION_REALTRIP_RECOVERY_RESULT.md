# Revolution real-trip recovery result

## R77-R4 latest authority-gate checkpoint

The latest clean-source experiment supersedes the earlier recovery candidate's
selection claim where its live Place facts were still `UNKNOWN`.  The earlier
known-fact baseline remains historical evidence; it is not evidence that this
new candidate may be selected.

- Round start commit: `e0ef44c5615055fefb2107fe37fb75a288e03cff`.
- Final experimental commit: `a71d0c249170d8e232ba93e8f23ef896e49ddfe7`.
- Branch: `codex/revolution-realtrip-recovery`.
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`.
- Clean disposable clone: `C:\Users\仓鼠王\AppData\Local\Temp\citynexus-r77-authority-gate-r4-20260930.sqlite3`.
- Destination: `苏州市 / CN-SUZHOU`, Journey
  `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`.

DeepSeek ran through the supported native tool loop:
`inspect_journey → inspect_twin → list_replans → search_city_services →
request_replan`.  It produced proposal
`d2b9d02f-fcc0-459e-a72c-7023691ee6e7`, candidate PlanVersion
`fd914ff8-3699-4d6c-90d7-6c4feeaaf60b`, and live Valhalla evidence with
87 captured facts, `LIVE_PROVIDER_CAPTURE`, `degraded=false`, and zero
synthetic facts.

The exact candidate Places were then refreshed through Overpass plus exact
Nominatim lookup.  Both provider entities matched, but the machine receipt
reported `known_opening_count=0` and `known_cost_count=0`; both Places remain
`opening=UNKNOWN` and `cost_evidence.status=UNKNOWN`.  This is honest fact
absence, not free/always-open inference.

Selection was tested against the real product endpoint.  The pre-repair clone
accepted an equivalent unresolved candidate with HTTP 200, exposing the
authority defect.  On the clean `a71d0c24` source, the same boundary returns
HTTP 409 with `reason_code=UNRESOLVED_ACTIVITY_FACTS` and the actual used Place
IDs, while Journey `active_plan_version_id` remains
`3c176241-de74-47af-9c3c-7018e52ef56b` and the new candidate remains
`CANDIDATE`.  Therefore the current R77 recovery result is:

`REAL_DRAFT_CLOSED` + `REAL_AGENT_CLOSED`;
`REAL_SELECTABLE_CLOSED` is not claimed for this unresolved-facts candidate.

The complete machine receipt is
`evidence/revolution-realtrip/r77_authority_gate_r4_receipt.json`.
The focused gates passed `108 passed, 1 warning`; the warning is the existing
Starlette/httpx deprecation.  Native Hermes is not claimed: its current probe
still stops at `RESET/SEED HTTP 403: DEMO_MODE_REQUIRED`.

## Milestones

- `REAL_DRAFT_CLOSED`: closed on the unseeded disposable Suzhou journey.
- `REAL_SELECTABLE_CLOSED`: closed only for the earlier known-fact baseline;
  the latest R77 recovery candidate is correctly blocked until its own live
  opening/cost facts are resolved.  The earlier HTTP 200 on an equivalent
  unresolved recovery candidate is recorded as a product defect, not success.
- `REAL_AGENT_CLOSED`: closed for the supported Hermes compatibility runtime in
  `PLAN_ONLY`; native MCP is not claimed.

## Source and scope

- Starting commit: `4ee14229f80691cf8e5ea913375c0caf83ac02ee`
- Latest product code commit: `c352bacd`
- R77 recovery repair commit: `f03f3f053c7566200ac75c6e7441a228ffe89eee`
- Final material experimental/evidence snapshot commit: `c0cd28baef04300b4cabe1e19a3c9332923c1532`
- Live DeepSeek receipt commit: `aa430280` (`r77_live_agent_loop_receipt.json`)
- Live DeepSeek UI evidence commit: `49fad3c2` (`r77-suzhou-replan-live-deepseek.png`)
- The final handoff metadata commit may contain only this explicit commit annotation; the material R77 source/evidence snapshot is the commit above.
- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Database: `backend/r77_selectable_probe.db` (disposable lab DB)
- Authority/mainline merge: none; `P7=false`

## Real destination path

`苏州市 / CN-SUZHOU` was not seeded as a golden demo answer. The live product
persisted these provider entities:

- `real-place-8bc850f117297987997c87cf` → `overpass:way/44679452` → 网师园
  (`Mo-Su 07:30-17:00`, cost evidence `KNOWN`, 3000 CNY minor units).
- `real-place-ba7377353c422c39dfd752b7` → `overpass:way/468359738` → 拙政园
  (`Mo-Su 07:30-17:30`, cost evidence `KNOWN`, 9000 CNY minor units).

Nominatim exact secondary identity matched both OSM entities. Missing facts were
not converted to free/open. Official web was attempted without additional
structured facts; search was unconfigured.

## Product evidence

- `POST /plans/generate`: HTTP 201; candidate used the two persisted real Places.
- Actual used edge: `real-place-8bc850f117297987997c87cf` →
  `real-place-ba7377353c422c39dfd752b7`.
- Valhalla: 42 minutes, `WALK`, `LIVE_PROVIDER_CAPTURE`, `degraded=false`.
- `POST /plans/e311ab50-5e61-5520-92fa-15ad977a565d/select`: HTTP 200.
- Reload: Journey `PLANNED`, `active_plan_version_id=e311ab50-5e61-5520-92fa-15ad977a565d`,
  plan `SELECTED`, `selectable=true`, `is_current=true`, `stale=false`.
- Real `/api/v1/journeys/{journey_id}/start`: HTTP 200; Journey became `ACTIVE`,
  the first activity became `ACTIVE`, and the active PlanVersion became `ACTIVE`.
- `/experience`, `/twin`, `/v8/live`, and `/v8/map` agree on `WALK`, 42 minutes,
  `valhalla-http`, and `LIVE_PROVIDER_CAPTURE`.

## Agent evidence

The real same-Journey `PLAN_ONLY` run is recorded in
`evidence/revolution-realtrip/r77_agent_plan_only_rerun.json`:

`inspect_journey → inspect_twin → list_replans`, all `COMPLETED / ALLOW_AUTO`,
with no mutation. After the Twin repair, the agent saw
`next_leg_id=plan-evidence:e311ab50-5e61-5520-92fa-15ad977a565d:0`,
`next_mode=WALK`, and `next_eta_min=42`.

After `/start`, the execution-state run is recorded in
`evidence/revolution-realtrip/r77_agent_execution_plan_only.json`; it saw
`cursor_status=VALID`, current `网师园=ACTIVE`, and the same real next edge.

DeepSeek Builder activity remains the earlier WorkBuddy-compatible proposal
recorded in `R77_HERMES_TRUTH_REPAIR.md`; current product authority came from
deterministic CityNexus evidence and tests. No native MCP execution is claimed.

## Focused gates

The focused recovery/provider/agent suite remains `71 passed, 1 warning` on
Python 3.13; the new Twin execution regression passed separately. Frontend
`npm run typecheck` and `npm run build` passed; only the existing Vite chunk-size
advisory remains.

## Remaining truth gaps

- The pre-start Journey correctly used `ABSENT_FALLBACK`; after `/start`, the
  persisted cursor is `VALID` and points to the first activity.
- This one-day plan has one used mobility edge; the 72 captured Valhalla facts
  are not all used edges.
- No replan was requested because there is no server-owned disruption event.
- `JourneyTwin.latest_event_id=null` is the separate disruption-Event lane, not
  an assertion that execution history is absent. `/outcomes` contains the real
  `ACTIVITY_STARTED` event for the current activity. TravelerTwin preference/
  capability evidence is still empty; route evidence was not used to fill it.

## R77 follow-on: execution disruption and authoritative recovery

The same disposable Suzhou Journey was continued after `/start`. A server-owned
diagnostic `SIMULATED` closure event targeted the still-planned 拙政园 activity;
the event is explicitly not live provider evidence. The real recovery path then
ran through the deterministic impact resolver, live Valhalla capture, proposal
presentation, and `/replans/{id}/accept`:

- event `b649a9c0-b2d4-4e2f-9e9f-7dc461702a30` → `CLOSURE`, target
  `real-place-ba7377353c422c39dfd752b7`;
- accepted proposal `90a0b3aa-b2e0-4544-a416-77bf921308cc` replaced that place
  with real persisted OSM place `real-place-054fa857eff7a99169399bdf`;
- authoritative Journey pointer became
  `3c176241-de74-47af-9c3c-7018e52ef56b`, with current 网师园 retained and
  next 狮子林 planned;
- incident snapshot `3dd5ab27-5445-4977-b609-8770e022fe0e` contains 45
  Valhalla facts; the actual used edge is WALK/38 minutes with
  `LIVE_PROVIDER_CAPTURE`, `degraded=false`, and
  `used_edge_ids=[[real-place-8bc850f117297987997c87cf,
  real-place-054fa857eff7a99169399bdf]]`;
- after reload, `/v8/live` showed 网师园 → 狮子林 · 步行 · 38 min, supplier
  route/WGS84, low risk, and “刚才的行程变化已经处理好”. Screenshot:
  `frontend/output/playwright/r77-suzhou-replan-live.png`;
- a fresh Hermes compatibility run `d66bc824-888d-41cc-816d-c0995f7f5403`
  completed PLAN_ONLY inspection with `inspect_journey → inspect_twin →
  list_replans`; no mutation tool was called. Native MCP remains unclaimed.

Full machine evidence is in
`evidence/revolution-realtrip/r77_replan_recovery_receipt.json`.

The focused follow-on suite passed `53 passed, 1 warning in 8.07s`.

## R77 follow-on: false-positive disruption capture and bounded repair

The first real Hermes compatibility inspection exposed a product defect. The
read-only command

`检查当前已经启动的苏州行程，确认闭馆后的恢复提案是否已成为权威计划，并报告当前站、下一站、路线来源和是否还有待处理调整；只读，不要修改。`

was incorrectly compiled as a new current `CLOSURE` and the legacy agent
command endpoint persisted event `476b258b-6c02-46a7-b3cb-e07db1be3e91`.
The same old server process produced a second probe artifact
`48dc9f2d-5078-4a87-b447-9279ad8ab298`. Both were `USER_REPORTED`/`user-command`
events, not live provider evidence. The cause was the combination of broad
closure words (`闭馆`) and an unconditional `DISRUPTION_REPORT` → Event path;
the command's inspection/recovery-reference meaning was not treated as
read-only.

Commit `f03f3f053c7566200ac75c6e7441a228ffe89eee` adds the narrow
`is_status_inspection_reference()` boundary, makes the deterministic event
classifier return no disruption for this shape, prevents model compilation
for this shape, and guards the agent command Event creation path. It does not
weaken genuine reports such as `现在博物馆关门了`. The focused regression
tests cover both a model that falsely returns an asserted `CLOSURE` and the
actual command endpoint.

After the commit, with `git status --porcelain` empty, the same endpoint was
run against the same disposable Journey. Event IDs were unchanged
(`3 → 3`) and the response contained `event_id=null`. The runtime status was
`NOT_CONFIGURED`; the attempted agent run was `SKIPPED_EXTERNAL_DEPENDENCY`
with zero tool steps, so this replay claims deterministic product evidence,
not a new Hermes/DeepSeek execution. The earlier real compatibility run
`d66bc824-888d-41cc-816d-c0995f7f5403` remains the Hermes evidence for the
accepted recovery.

The two precisely identified false-positive rows were then removed only from
the disposable `backend/r77_selectable_probe.db` probe database, preserving
the intended simulated trigger `b649a9c0-b2d4-4e2f-9e9f-7dc461702a30`. This
cleanup is recorded as probe-artifact cleanup, not as a product authority
operation. Final readback has one acknowledged diagnostic event, Twin
`latest_event_id` points to the intended trigger, the accepted plan remains
`3c176241-de74-47af-9c3c-7018e52ef56b`, and the real Valhalla edge remains
`real-place-8bc850f117297987997c87cf → real-place-054fa857eff7a99169399bdf`
with `WALK`, 38 minutes, `LIVE_PROVIDER_CAPTURE`, and `degraded=false`.

The complete repair/replay/cleanup receipt is
`evidence/revolution-realtrip/r77_status_inspection_repair_receipt.json`.
The refreshed user-visible proof is
`frontend/output/playwright/r77-suzhou-replan-live-fixed.png`.

The combined focused backend gates passed `73 passed, 1 warning`; the warning
is the existing Starlette/httpx deprecation. `P7=false`, `MOCK != LIVE`, and
no authority/mainline merge were introduced.

## Live DeepSeek tool-loop continuation

After the system-supported `HKCU` `DEEPSEEK_API_KEY` presence was confirmed
without exposing its value, the isolated backend was restarted with that key
only in the child-process environment and `CITYNEXUS_AI_ENABLED=true`. No
credential was written to the worktree, database, logs, receipt, or archive.
The runtime endpoint reported `NATIVE_DEEPSEEK_TOOL_LOOP`,
`deepseek_configured=true`, and `native_mcp_proven=false`.

Two real same-Journey native DeepSeek runs then completed in `PLAN_ONLY`:

- `ecd49946-d11f-461b-aa9e-0264e319da52` / mission
  `bd32c6a6-e82a-4e54-9864-31c33ea322fb`: `inspect_journey → inspect_twin →
  list_replans`, all `COMPLETED`/`ALLOW_AUTO`, no Event created.
- `78d4d483-b944-40a8-a148-ef02202d9b26` / mission
  `924199e4-573c-44ed-8b8f-2069d6f0e7bb`: the stricter authority/route
  cross-check used the same three read tools, all completed, and found the
  Journey/Twin plan pointers equal, one `ACCEPTED` proposal plus two
  `INVALIDATED` proposals, no pending proposal, and no synthetic mobility
  marker. The actual edge remained Valhalla WALK/38 minutes with
  `LIVE_PROVIDER_CAPTURE`.

Both runs observed the single preserved diagnostic event only; the repaired
status-inspection guard continued to return `event_id=null`. This is actual
DeepSeek execution evidence, not model prose substituted for product state.

The repository Hermes H11 probe was also attempted with the same supported
registry credential path in a separate temporary runtime. Its exact blocker
was `RESET/SEED HTTP 403: DEMO_MODE_REQUIRED`; the probe's own backend sets
`CITYNEXUS_DEMO_MODE=false`, and the product gate correctly refused the demo
reset. The probe reported `nothing was deleted`; no source or R77 database was
changed. Native Hermes execution is therefore not claimed for this continuation;
the earlier real compatibility run `d66bc824-888d-41cc-816d-c0995f7f5403`
remains separately recorded.

The live agent receipt is
`evidence/revolution-realtrip/r77_live_agent_loop_receipt.json`.

Replay evidence and screenshots are under `evidence/revolution-realtrip/` and
`frontend/output/playwright/`, including `r77-suzhou-live-executing-clean.png`.
