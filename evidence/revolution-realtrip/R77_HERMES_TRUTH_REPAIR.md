# R77 Hermes truth-projection repair

## Source binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:/moodle/CityNexus-Revolution-RealTrip-Recovery`
- starting commit: `4ee14229f80691cf8e5ea913375c0caf83ac02ee`
- prior clean product code: `8c05fb4373efc866fbcc30e49e6177be4e07721a`
- mobility projection repair commit: `001882a34e479b6c111937aeee0608ca92745559`
- used-edge projection repair commit: `f7cc3d45888035a9abbb9b88397c70b149251333`
- selected-plan experience projection repair commit: `86d2f27a`
- truthful live-navigation repair commit: `91cbf629`
- live routing mode binding commit: `b24975b0`
- cross-projection mode binding commit: `570c7eff`
- actual-mode count UI commit: `bb8ca6f5`
- final product/evidence commit before this receipt update: `e25f47d0` (`revolution lab: capture live mobility mode receipt`)
- clean before product calls: yes (`git status --porcelain` empty)
- authority/mainline merge: none

## Scenario

The same disposable R77 Journey was used throughout:

- destination: `苏州市`
- city: `CN-SUZHOU`
- journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- selected plan: `e311ab50-5e61-5520-92fa-15ad977a565d`
- real provider-backed places: `real-place-8bc850f117297987997c87cf` and `real-place-ba7377353c422c39dfd752b7`
- disposable database: `backend/r77_selectable_probe.db`

The selected PlanVersion held a Valhalla snapshot with 72 facts. The plan's actual consecutive activity edge is:

```json
{
  "used_edge_ids": [[
    "real-place-8bc850f117297987997c87cf",
    "real-place-ba7377353c422c39dfd752b7"
  ]],
  "minutes": 42,
  "provider": "valhalla-http",
  "route_provenance": "LIVE_PROVIDER_CAPTURE",
  "fact_quality": "LIVE_PROVIDER_CAPTURE",
  "degraded": false
}
```

## Defect and repair

Before `001882a3`, `_twin_snapshot()` initialized `context.mobility` as `mock-mobility / deterministic-offline` whenever there was no active C4 commitment, even when the selected PlanVersion carried frozen provider evidence. The Plans API and the agent inspection therefore disagreed.

The repair exposes a compact summary of the selected plan's persisted evidence:

- `provider` / `source_provider`
- `snapshot_id`
- `fact_count`
- `fact_quality`
- `route_provenance`
- evidence-backed `used_edge_ids` and `used_edges`

Precedence is preserved: an active C4 commitment's persisted replan snapshot/fact still overrides the context used for that commitment window. The selected-plan summary is used when that override is absent. Missing or incomplete evidence continues to use the existing honest mock fallback; no fact is synthesized.

## DeepSeek Builder execution

The WorkBuddy OpenAI-compatible endpoint was called in process memory with no credential persisted or printed:

- model calls: `cn:deepseek-v4-pro`, then `cn:deepseek-v4.1-flash`
- role: Builder proposal for the bounded `_twin_snapshot()` repair
- result: runtime calls executed; provider returned reasoning/truncated final content, not an authoritative patch or PASS
- contribution: independently pointed to selected-plan frozen evidence as the fallback precedence before mock, while the actual patch was made from the source trace and deterministic tests

This was a WorkBuddy-compatible DeepSeek model call, not native CityNexus DeepSeek Responses runtime.

## Hermes Operator execution

Runtime status on the clean experimental service:

```json
{
  "runtime_identity": "HERMES_COMPAT_ENDPOINT",
  "native_mcp_proven": false,
  "deepseek_configured": false,
  "hermes_compat_configured": true,
  "ai_state": "CONFIGURED_UNVERIFIED"
}
```

The final bounded operator run:

- mission: `6a894604-c171-441c-9cc4-e72e394ca14b`
- AgentRun: `ed5938a0-c8d1-4e7b-af5e-6778e72f5271`
- provider: `hermes`
- model: `cn:deepseek-v4.1-flash`
- runtime: `HERMES_COMPAT_ENDPOINT`
- status: `COMPLETED`
- tools, in order: `inspect_journey`, `inspect_twin`, `list_replans`
- all three: `COMPLETED / ALLOW_AUTO`
- mutation: none

Machine-returned operator lines:

```text
AUTHORITY=PLAN_ONLY; read-only, all three calls ALLOW_AUTO
MOBILITY=provider=valhalla-http, snapshot=52541f63-1d56-49c7-b371-73984268e0c5, fact_quality=LIVE_PROVIDER_CAPTURE, degraded=false
USED_EDGE_IDS=[["real-place-8bc850f117297987997c87cf","real-place-ba7377353c422c39dfd752b7"]] -> 42 min (provider valhalla-http, LIVE_PROVIDER_CAPTURE)
GAPS=No replan proposals exist and journey has no confirmed capabilities or commitments.
```

## Product readback after the run

- `GET /api/v1/journeys/{journey_id}`: HTTP 200; status `PLANNED`; active pointer is the selected plan
- `GET /api/v1/journeys/{journey_id}/plans`: HTTP 200; plan `SELECTED`, `selectable=true`, `is_current=true`, `stale=false`, total cost `12000 CNY`
- `GET /api/v1/journeys/{journey_id}/twin`: HTTP 200; projection `READY`; mobility and used-edge fields agree with the selected plan evidence
- Journey remained `PLANNED`; no agent mutation occurred

## Focused gates

```text
py -3.13 -m pytest -q \
  tests/test_revolution_r77_recovery.py \
  tests/test_qoder_beijing_catalogue.py \
  tests/test_qoder_catalog_reason_code.py \
  tests/test_qoder_generic_compose_reason_codes.py \
  tests/test_qoder_mobility_evidence_sources.py \
  tests/test_provider_runtime_gate.py \
  tests/test_agent_runtime_gate.py \
  tests/test_agent_authority_v2_actions.py \
  tests/test_gpt_adversarial_provider_hardening.py

71 passed, 1 warning
```

The warning is the existing Starlette/httpx deprecation warning.

## Frontend gates

The isolated frontend had no installed dependencies initially. `npm install --no-package-lock` populated only the ignored local `node_modules`; it did not change `package.json` or `package-lock.json`.

```text
npm run typecheck  -> passed
npm run build      -> passed
```

Vite emitted only its existing chunk-size advisory; the production bundle was generated successfully.

## Latest clean product readback

The later frontend repair was exercised only after the isolated worktree was clean. The
backend process was already running from the clean backend-compatible commit
`54960cc0`; the later commits changed only the frontend and evidence artifacts.

### API projection

The clean selected-plan readback remained:

```text
GET /api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/experience -> HTTP 200
options = 0
active_status = SELECTED
leg_count = 1
used_edge_ids = [["real-place-8bc850f117297987997c87cf","real-place-ba7377353c422c39dfd752b7"]]
leg_provider = valhalla-http
leg_provenance = LIVE_PROVIDER_CAPTURE
leg_minutes = 42
valhalla_status = CAPTURED
valhalla_source = selected-plan-frozen-evidence
```

### Same-Journey live mode rerun

After the mode repair, the same disposable Suzhou Journey was rerun on a clean
worktree. `POST /plans/generate` returned HTTP 201 and created candidate
`e311ab50-5e61-5520-92fa-15ad977a565d`. Its newly captured Valhalla evidence
contained `mode=WALK` for the real route facts. The real selection endpoint then
returned HTTP 200 and made that PlanVersion current; no mode was injected into
the database by the probe.

```text
GET /api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/experience -> HTTP 200
active_plan = e311ab50-5e61-5520-92fa-15ad977a565d
active_plan.legs[0].mode = WALK
active_plan.legs[0].provider_key = valhalla-http
active_plan.legs[0].provenance = LIVE_PROVIDER_CAPTURE
active_plan.mobility_evidence.used_edge_ids = [[
  real-place-8bc850f117297987997c87cf,
  real-place-ba7377353c422c39dfd752b7
]]
active_plan.mobility_evidence.used_edges[0].mode = WALK

GET /api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/twin -> HTTP 200
context.mobility.provider = valhalla-http
context.mobility.used_edges[0].mode = WALK
context.mobility.used_edges[0].route_provenance = LIVE_PROVIDER_CAPTURE
```

The frontend previously converted “some mode exists” into a fixed “5 modes”.
It now counts the actual distinct modes in the API facts. The clean Hub readback
is:

```text
1 个方案 · 1 种模式
已记录供应商支持的出行方式。
09:00 网师园 · 10:42 拙政园
```

This keeps the live provider mode, Twin projection, Experience projection, and
user-visible summary on one fact rather than claiming unsupported alternatives.

`options = 0` means this direct selected PlanVersion has no `StayJourneyOption`
lodging alternatives; it is not projected as “zero plans”. The selected plan remains
visible and authoritative in the experience projection.

### User-visible real-trip readback

The clean Playwright page at `/v8/live` showed:

```text
1 个方案 · 5 种模式
当前：网师园
下一步 · 拙政园 · 未提供出行方式 · 42 min
1 段路程 · 供应商支持的路线 · WGS84
预计到达 · 未提供出行方式
风险：低 · 路线证据有效
```

The navigation link now is the evidence-honest marker form:

```text
https://uri.amap.com/marker?position=120.6247266,31.3264725&name=拙政园&coordinate=wgs84&callnative=1
```

The previous UI emitted `mode=walk` even though the selected provider fact had no
mode. That behavior is removed. A provider mode is used only when it exists; otherwise
the UI opens the exact destination marker and says `打开目的地 →`.

### Unsupported mode control readback

The same clean page also proved that this direct selected PlanVersion has no
recomputation target (`experience.options = 0`). Before the bounded UI repair, clicking
`步行` focused the button but produced no request and no state change because the
frontend's `changeMode` correctly had no selected stay option to address. The control
was nevertheless presented as actionable.

At final commit `5a0cb7fe`, the page now renders:

```text
当前方案没有可重算的出行方式
步行 [disabled]
骑行 [disabled]
公交地铁 [disabled]
驾车 [disabled]
网约车 [disabled]
当前方案没有可比较的出行方式 [disabled]
```

The disabled state is derived from the actual absence of a recomputable selected
option; it does not infer or invent a route mode. `TRANSIT` is no longer presented as
an active mode for this plan.

The shell count was corrected in the same bounded follow-up. It now reads the actual
option `leg_modes` and selected plan `legs[*].mode` fields. The clean page consequently
shows:

```text
1 个方案 · 出行方式待补充
```

instead of `1 个方案 · 5 种模式`. The supported-mode count is retained only when a
real option or plan leg supplies a mode.

The execution status card had a separate wording defect: it labeled the saved offline
copy as `离线`, even on the same page that had just read the live API and displayed
captured Valhalla evidence. The clean readback now says:

```text
离线副本 · 只读就绪 · 未来 24 小时已保存
```

This describes offline availability without claiming that the current product session
is disconnected.

The V10 drawer's empty count was also narrowed from generic `来源` to `网页来源`.
That drawer reads only `/web-observations`; it is not the authority for the separate
Valhalla route evidence shown above. The clean page now says:

```text
0 个网页来源 · 暂无网页观察记录
```

This keeps an empty web-observation lane from contradicting the live provider route
lane or implying that all route evidence is absent.

The map entry point was then exercised on the same clean journey. Its diagnostic sheet
still opens so the missing mobility evidence is visible, but its mutation-looking bottom
action is now closed honestly:

```text
WALK/BICYCLE/TRANSIT/AUTO/RIDE HAIL -> disabled · 无供应商证据
当前没有可选择的供应商路线方式 -> disabled
```

No POST is possible from that empty sheet. This keeps the map's evidence diagnosis
available without presenting a no-op “let CityNexus choose” action.

The empty sheet title is now also `当前没有可选择的路线方式` rather than
`选择平稳路线`, so the diagnostic state cannot be mistaken for an available choice.

The final hardening commit `ab34e04c` binds every individual mode tile to the same
`canChoose` predicate as the bottom action. Even if facts are later present while the
selected plan target is absent, no tile can invoke the no-op selection callback.

The realtime evidence drawer was then exercised after the clean commit. It now projects
the actual next `active_plan.legs[*]` entry when the comparison collection is empty:

```text
未提供出行方式 · 约42分钟 · 费用未知
选中方案冻结路线证据 · valhalla-http · LIVE_PROVIDER_CAPTURE
```

The row is the persisted frozen leg; it does not infer a mode from duration, turn the
unknown cost into zero, or relabel the route as synthetic.

The map surface now uses the same fallback. Its clean readback is:

```text
未提供出行方式 · 约42分钟 · 费用未知
选中方案冻结路线证据 · valhalla-http · LIVE_PROVIDER_CAPTURE
```

This keeps the live and map evidence consumers aligned on the same selected-plan leg.

### Hub surface readback

After the final Hub wording repair, the clean page at `/v8/hub` was reloaded from
the same disposable journey and captured after commit `6f21c8ce`:

```text
1 个方案 · 出行方式待补充
已选行程
下面是已采用的真实行程；住宿方案仍未选择。
出行方式证据仍待补充。
09:00 网师园 · 10:42 拙政园
```

The Hub also renders the nine planner-dropped candidates without duplicating the
reason text:

```text
规划前被去掉的候选地点（9 个）
去掉「一个未读取到名称的地点」：这一站不满足一条未识别的硬性条件
```

This is the selected product state projected from the real PlanVersion; the pending
mode evidence remains visible and is not upgraded to a selectable mobility choice.

Hub screenshot receipt:

- `frontend/output/playwright/r77-suzhou-hub-truth-clean.png`
- `frontend/output/playwright/r77-suzhou-hub-live-mode-clean.png`

Captured artifacts:

- `frontend/output/playwright/r77-suzhou-user-visible-clean.png`
- `frontend/output/playwright/r77-suzhou-live-unknown-mode-clean.png`
- `frontend/output/playwright/r77-suzhou-live-mode-unavailable-clean.png`
- `frontend/output/playwright/r77-suzhou-live-pending-mode-count-clean.png`
- `frontend/output/playwright/r77-suzhou-live-offline-copy-clean.png`
- `frontend/output/playwright/r77-suzhou-live-web-source-label-clean.png`
- `frontend/output/playwright/r77-suzhou-map-mobility-unavailable-clean.png`
- `frontend/output/playwright/r77-suzhou-map-no-route-title-clean.png`
- `frontend/output/playwright/r77-suzhou-live-frozen-evidence-clean.png`
- `frontend/output/playwright/r77-suzhou-map-frozen-evidence-clean.png`
- `frontend/output/playwright/r77-suzhou-hub-truth-clean.png`

The final frontend gates after this repair were:

```text
npm run typecheck -> passed
npm run build     -> passed
```

The build retained only the existing Vite large-chunk advisory.

No new DeepSeek or Hermes execution is claimed for this presentation-only repair. The
agent evidence above remains the actual Builder/Operator execution record; the latest
UI behavior was verified by deterministic API and Playwright machine evidence.

## Truth boundaries

- `P7=false`
- `MOCK != LIVE`
- `UNKNOWN cost != known free`
- no synthetic mobility was relabeled as live
- no provider-only result was treated as product authority
- no authority/mainline merge
- no raw API credential in the tree or receipt
