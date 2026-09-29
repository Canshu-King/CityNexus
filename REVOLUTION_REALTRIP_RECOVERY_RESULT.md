# Revolution real-trip recovery result

## Milestones

- `REAL_DRAFT_CLOSED`: closed on the unseeded disposable Suzhou journey.
- `REAL_SELECTABLE_CLOSED`: closed; the selected plan survived API reload and its
  Journey pointer remained authoritative.
- `REAL_AGENT_CLOSED`: closed for the supported Hermes compatibility runtime in
  `PLAN_ONLY`; native MCP is not claimed.

## Source and scope

- Starting commit: `4ee14229f80691cf8e5ea913375c0caf83ac02ee`
- Latest product code commit: `c352bacd`
- Final experimental/evidence commit for this recovery continuation: `f8cb2417`
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

Replay evidence and screenshots are under `evidence/revolution-realtrip/` and
`frontend/output/playwright/`, including `r77-suzhou-live-executing-clean.png`.
