# Revolution R14 — Autonomous Strategy Engine

## Machine checkpoint

- Base SHA: `f21d82c1910502de094117edeac9f1c83c5c0b21`
- Final experimental code SHA: `86b893bb`
- Report closure commit: follows this runtime receipt update
- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Product database: `C:\Users\仓鼠王\AppData\Local\Temp\citynexus-r13-metadata-fix-20260930-b.sqlite3`
- Runtime: `HERMES_COMPAT_ENDPOINT`
- Model order for the current recovery run: `cn:deepseek-v4.1-flash` → `cn:glm-5.3-flash`
- Endpoint: local WB2api `http://127.0.0.1:7863/v1/chat/completions`
- Credentials: process environment only; no raw credential is persisted in this tree.

## Current domestic-WB2api checkpoint: Chongqing

This is the fresh second-city transfer executed after the Kunming runs. It
entered an unseeded `CN-CHONGQING` Journey with a natural-language preference,
used the domestic DeepSeek runtime, hit a real calendar/opening gate, changed
strategy, and completed the revised product Journey. The result is selectable
only inside the isolated coursework estimate envelope; it is not a claim that
UNKNOWN opening/cost facts became provider truth.

### Source and runtime binding

- experiment starting commit: `e593162de587f4523ab8632f77e3d2e50667888b`
- experimental product-code commit used by this run: `46457355b054771f6c97b9fd903510c1e14515cd`
- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\\moodle\\CityNexus-Revolution-RealTrip-Recovery`
- database: `C:\\Users\\仓鼠王\\AppData\\Local\\Temp\\citynexus-r13-metadata-fix-20260930-b.sqlite3`
- endpoint: `http://127.0.0.1:7863/v1/chat/completions`
- model order: `cn:deepseek-v4.1-flash` primary, `cn:glm-5.3-flash` fallback
- this Chongqing AgentRun persisted `model_key=cn:deepseek-v4.1-flash`; no raw
  credential was persisted in source, report, database, or commit

### Real Agent entry and first machine blocker

Journey `0b1c4ae1-e1e4-4e5f-8449-61779bf89dd0` entered `CN-CHONGQING` in
`DRAFT` with no pre-authored itinerary. The user intent was:

```text
室内展览、地方工艺、安静文化空间、少走路、路线紧凑；事实不足或路线过重时主动放弃并换地点/类别；不要编造 provider、开放时间、价格或交通。
```

The real domestic AgentRun was
`f69820f9-ecea-4cbf-8943-446f45b77525`, mission
`25f507e4-5b02-4e88-a6eb-20703ba668f4`, trace
`5d880f9d-9069-4e12-a64e-03f4873ce714`. Its machine trace began with
`inspect_journey → inspect_twin → search_city_services`. Live OSM discovery
returned eight provider-backed museum Places, including:

- `real-place-cb18acfd1f4e7bf639baabfd` — 三峡博物馆;
- `real-place-503e1999cbfa048b2cebefd8` — 桂园;
- `real-place-582b0eeaff5b29e4bac0af89` — 同盟国驻渝外交机构旧址群;
- `real-place-706b602f4af48527d2ec4e23` — 飞虎队博物馆.

The first candidate was plan
`e4c17219-b16e-558e-bfd6-585c42cdde8c`, using 三峡博物馆 and 桂园. It had
real Valhalla mobility and was `COURSEWORK_ESTIMATED_FACTS`, but the actual
product selection boundary rejected it:

```text
POST /api/v1/journeys/0b1c4ae1-e1e4-4e5f-8449-61779bf89dd0/plans/e4c17219-b16e-558e-bfd6-585c42cdde8c/select
HTTP 422
PLACE_CLOSED:real-place-cb18acfd1f4e7bf639baabfd
```

That was a real deterministic blocker: the captured 三峡博物馆 window was
`Tu-Sa 10:00-17:00`, while the Journey date was Sunday 2026-10-18. No model
prose overruled the gate and the Journey remained `DRAFT`.

### Strategy pivot and successful product path

The Agent then changed the candidate set rather than retrying the same plan.
The bounded follow-up used the actual Gateway and selected two other provider
entities from the same live catalog: 同盟国驻渝外交机构旧址群 and 飞虎队博物馆.
Both received explicit `ESTIMATED_AGENT` hypotheses of 10:00–17:00 and zero
minor cost for this coursework run. The canonical rows stayed unchanged:
`opening_hours.status=UNKNOWN`, `cost_evidence.status=UNKNOWN`,
`authority_eligible=false` for each estimate.

The second composition created plan
`45c11359-b798-5a7a-a788-cf2970ad5ff2`, version 2. It carried:

```text
authority_state: COURSEWORK_ESTIMATED_FACTS
authority_envelope: COURSEWORK_ESTIMATE
mobility_snapshot_id: d10c6239-ae8f-438e-a85a-08bb8fbb1257
mobility_provider: valhalla-http
```

The product-generated mobility evidence was:

```json
{
  "used_edge_ids": [[
    "real-place-582b0eeaff5b29e4bac0af89",
    "real-place-706b602f4af48527d2ec4e23"
  ]],
  "provider": "valhalla-http",
  "route_provenance": "LIVE_PROVIDER_CAPTURE",
  "fact_quality": "LIVE_PROVIDER_CAPTURE",
  "hard_minutes": 42,
  "hard_eligible": true,
  "decision": "HARD_ELIGIBLE",
  "degraded": false
}
```

The real product calls then returned `select=200` (`PLANNED`) and `start=200`
(`ACTIVE`). Both activities traversed the product lifecycle
`depart → arrive → begin → complete`; no activity or mobility edge was
fabricated. Final API/Twin truth agrees:

```text
Journey.status                 = COMPLETED
Journey.active_plan_version_id = 45c11359-b798-5a7a-a788-cf2970ad5ff2
Journey.current_activity_id    = null
Twin.projection_status         = READY
Twin.now_state                 = COMPLETE
activity statuses              = COMPLETED, COMPLETED
```

The final plan still exposes two unresolved facts and `cost_summary.status=PARTIAL`.
That is intentional: the estimate envelope made a coursework candidate
possible, but did not turn UNKNOWN into FREE or LIVE. The machine receipt is a
completed product Journey with live mobility and estimated activity facts, not
a production-ready factual itinerary.

### Chongqing result

This run demonstrates transfer of the same Strategy Engine to a second fresh
city: the first strategy was rejected by a real date/opening gate, the Agent
changed place selection, a new plan crossed deterministic selection, and the
Journey completed. The remaining frontier is to repeat the same transfer with
the lab estimate envelope disabled and acquire corroborated opening/cost facts
before selection; this run does not claim that stronger production state.

### Estimate-authority-off boundary replay

The promised boundary replay used the same current LAB source and disposable
database, but a separate server process with
`CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`. Journey
`ebdd40f0-5769-4c6a-9dd3-de8349150948` received the same two real provider
Places and the same explicit `ESTIMATED_AGENT` hypotheses. The deterministic
composition result was:

```text
plan: 5462acc1-07c8-576d-854c-e98898d010ab
authority_state: PROVISIONAL_UNRESOLVED_FACTS
selectable: false
mobility_provider: valhalla-http
mobility_snapshot_id: 96ad3817-0d82-4e0f-b850-764ae64cefeb
```

The real selection endpoint then rejected it:

```text
POST /api/v1/journeys/ebdd40f0-5769-4c6a-9dd3-de8349150948/plans/5462acc1-07c8-576d-854c-e98898d010ab/select
HTTP 409
reason_code: UNRESOLVED_ACTIVITY_FACTS
error_receipt_id: CNX-57NWWZP5
```

The follow-up `start` call also returned `409` because the Journey remained
unselected. This replay proves the estimate is strategy evidence only: turning
the isolated lab envelope off does not turn UNKNOWN into FREE, LIVE, or
authoritative selection.

## Current domestic-WB2api checkpoint: Chengdu outdoor contrast

The next live run used a materially different natural-language intent in a
third unseeded city. It is the outdoor polarity contrast to the Chongqing
indoor/cultural run above, not a score-only variation.

### Agent trace and live discovery

Journey `aca99ce4-3ffd-463b-9e8d-770c6fd6e07b` entered `CN-CHENGDU` as `DRAFT`.
The user intent compiled to exactly:

```text
objective_codes: [PREFER_OUTDOOR]
preferences: {outdoor: true}
```

The domestic DeepSeek run was
`b79b392a-6c17-431b-a5e0-8829d09c87ec`, mission
`e1b4b144-a6de-4756-a433-fe39d92293bf`, trace
`48684bb7-f6ae-42c2-a3be-9e8bb1650219`, model
`cn:deepseek-v4.1-flash`. Its useful tool path was:

```text
inspect_journey
→ inspect_twin
→ search_city_services (LIVE_PROVIDER, 8 park/garden Places)
→ acquire_place_facts (人民公园, Nominatim exact-entity match)
→ acquire_place_facts (三洞古桥公园, Nominatim exact-entity match)
→ acquire_place_facts (成华公园, Nominatim exact-entity match)
→ estimate_place_facts (five real outdoor candidates)
→ generate_plans
```

The model did not invent a museum or indoor venue. Live Overpass returned
eight provider-backed outdoor candidates, including People’s Park, 盆景园,
成华公园, 后子门游园, and 三洞古桥公园. The three secondary-source
acquisition receipts all reported `matched_provider_entity=true`; Nominatim
extratags were either a real Wikidata/Wikipedia pair or empty. No opening or
cost fact was promoted from those lookups: each receipt retained
`known_opening_count=0`, `known_cost_count=0`, and canonical UNKNOWN values.

### Intent-driven plan and execution

The Agent selected real provider Places
`real-place-18f19b3c8314398de9276a65` (人民公园) and
`real-place-589f196c84b73844c0e9d552` (盆景园), with explicit
`ESTIMATED_AGENT` hypotheses only inside the lab envelope. Plan
`aefa60a3-2f33-5319-92ce-1697bb03de52` was generated as
`COURSEWORK_ESTIMATED_FACTS`; canonical opening/cost stayed UNKNOWN and the
plan explanation retained `cost_summary.status=PARTIAL`.

The real product start receipt contained:

```json
{
  "used_edge_ids": [[
    "real-place-18f19b3c8314398de9276a65",
    "real-place-589f196c84b73844c0e9d552"
  ]],
  "provider": "valhalla-http",
  "route_provenance": "LIVE_PROVIDER_CAPTURE",
  "hard_minutes": 4,
  "hard_eligible": true,
  "decision": "HARD_ELIGIBLE",
  "degraded": false
}
```

`select` returned `200`, `start` returned `200`, and both activities completed
through `depart → arrive → begin → complete`. Final product truth:

```text
Journey.status                 = COMPLETED
Journey.active_plan_version_id = aefa60a3-2f33-5319-92ce-1697bb03de52
Journey.current_activity_id    = null
Twin.projection_status         = READY
Twin.now_state                 = COMPLETE
```

This is a genuine outdoor candidate-set transfer from the same Strategy
Engine, with real provider identity and live mobility. It remains a
coursework-estimated result, not a claim that unknown opening/cost facts are
production verified.

The post-run R14 regression gate was rerun on the current source:

```text
uv run pytest tests/test_r14_terminal_disruption_recovery.py \
  tests/test_agent_mission_runtime.py \
  tests/test_v14_grounded_adaptive_recovery.py \
  tests/test_v1923_final_code_gate.py \
  tests/test_replan_completion_truth.py \
  tests/test_sol_concurrency_and_remap.py -q
58 passed, 1 warning
```

## Current domestic-WB2api checkpoint: Kunming

This is the latest R14 execution after the Guilin checkpoint. The same
strategy/agent path entered a new unseeded city, used domestic WB2api, selected
a coursework-envelope plan, started the trip, handled a controlled closure,
and completed the revised Journey.

### Source and runtime binding

- starting source commit: `052d4a604202f9f95a6b91ddac90b16ef7275be4`
- final experimental code commit: `46457355b054771f6c97b9fd903510c1e14515cd`
- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\\moodle\\CityNexus-Revolution-RealTrip-Recovery`
- database: `C:\\Users\\仓鼠王\\AppData\\Local\\Temp\\citynexus-r13-metadata-fix-20260930-b.sqlite3`
- endpoint: `http://127.0.0.1:7863/v1/chat/completions`
- domestic model order: `cn:deepseek-v4.1-flash` primary, `cn:glm-5.3-flash` fallback
- raw credentials: process-only; none persisted in source, report, database, or commit

The first Kunming AgentRun was `5f5e8ae0-c858-4931-bb23-aae014dab237` and
completed real inspect/search/estimate/generate tool work. The later recovery
AgentRun was `9e312262-bf3c-4a2c-966d-4319cfaab0f1`; DeepSeek was attempted as
the primary domestic model and the persisted run fell back to GLM after the
primary response failed. The run's tool trace is still authoritative evidence;
model narration is not counted as a product decision.

### Same-city product path

Journey `4d50d0b8-51b1-498f-a0e9-33b775b80df5` entered `CN-KUNMING` with no
golden itinerary. Live OSM discovery materialized eight provider-backed Places.
The strategy loop retained canonical UNKNOWN opening/cost fields and used only
explicitly labelled `ESTIMATED_AGENT` strategy hypotheses where the course
experiment needed a bounded candidate. In particular:

- `real-place-6ecfee02978665da62454688` — 盘龙区图书馆 / Kunming Children’s Library;
  canonical opening and cost stayed UNKNOWN, with a non-authoritative agent estimate.
- `real-place-018894348601730c92ddab91` — Prague Bistro; a bounded agent estimate
  supplied the coursework candidate without changing provider truth.
- `real-place-f4af94a7bb144e4d08300ef8` — Salvador’s Cafe; the provider/Nominatim
  tags supplied `http://www.salvadors.cn/` and `Mo-Su 09:00-23:00`, but no
  structured cost authority was invented.

The selected provisional plan was `8fdc316b-6c0c-5438-9e91-2816cda637d6`,
with `authority_state=COURSEWORK_ESTIMATED_FACTS`, `selectable=true` only
inside the isolated lab estimate envelope, and mobility provider
`valhalla-http`. The real baseline leg was:

```text
real-place-018894348601730c92ddab91
  -> real-place-6ecfee02978665da62454688
minutes: 34
provider: valhalla-http
route_provenance: LIVE_PROVIDER_CAPTURE
decision: HARD_ELIGIBLE
baseline_snapshot: d490eb21-0702-4cff-9fee-52fcdce6e7ac
```

The plan was selected and started through the product API. Prague Bistro was
advanced through `depart → arrive → begin → complete`; the Journey cursor then
pointed to the library. No synthetic `used_edge_ids` or eligibility receipt
was added.

### Real disruption, agent critique, bounded repair, rerun

Controlled event `0df8a600-51c5-4fcc-9dd5-caf3ebe2a574` was a deliberately
labelled `SIMULATED` `CLOSURE` of the current library activity
`8328b630-59ad-5d4d-9a50-5355807ec83a`. Its payload carries
`COURSEWORK_CONTROLLED_CLOSURE` and `simulation_only=true`; it is not LIVE.

Hermes first inspected Journey/Twin, listed replans, and requested a real
replan. The deterministic recovery engine produced proposal
`9944425c-72bc-4ffe-bf71-efa5e0bbec78`:

- family: `F1_OPTIONAL_REMOVAL`;
- kept: Prague Bistro;
- removed: the closed library;
- proposed PlanVersion: `33ca54c9-a67e-4c11-abb2-c8fe60ef6382`;
- incident mobility snapshot: `5ec14999-1ca8-48f1-bfa1-42a1f95d6a8b`;
- incident evidence: Valhalla runtime capture, 34 minutes, not mock;
- hard constraints: passed;
- utility: `0.76`.

Before the repair, acceptance stopped at the shared truth boundary with:

```text
HTTP 409
replan does not preserve the current execution position
Journey.status = ACTIVE
proposal.status = PRESENTED
```

Hermes did not claim success. The bounded product repair in
`backend/app/main.py` now distinguishes a genuine terminal disruption from a
stale child plan. It requires the raw event to identify the actual current
activity, limits the event to `CLOSURE`/`WEATHER`, rejects terminal rows as a
new cursor, requires every child activity to be terminal, marks the disrupted
base activity `SKIPPED` with reason
`ACTIVE_ACTIVITY_DISRUPTED_AND_REMOVED`, records an outcome event, and moves
the Journey to `COMPLETED`. An ordinary missing-cursor replan still returns the
original 409.

The focused regression is
`backend/tests/test_r14_terminal_disruption_recovery.py`; it exercises the
same authority path and also proves a same-sequence terminal child row is not
mistaken for a live cursor.

The same Agent Gateway was rerun after the repair and returned:

```text
decision: ALLOW_AUTO
executed: true
reason_codes: DELEGATION_POLICY_MATCHED, DETERMINISTIC_GATE_VERIFIED
proposal.status: ACCEPTED
Journey.status: COMPLETED
Journey.active_plan_version_id: 33ca54c9-a67e-4c11-abb2-c8fe60ef6382
Journey.current_activity_id: null
Twin.projection_status: READY
Twin.current_activity_id: null
```

The final child has no remaining leg, so its actual `used_edge_ids=[]` is the
truthful zero-leg result. The real baseline edge and hard eligibility receipt
remain in the accepted proposal evidence; no route edge was synthesized for
the terminal child. The raw simulated closure remains `ACKNOWLEDGED`, which
means the trigger was recorded and acted on; it is not relabelled LIVE or
silently erased.

### Kunming focused gate

```text
uv run pytest tests/test_r14_terminal_disruption_recovery.py \\
  tests/test_agent_mission_runtime.py \\
  tests/test_v14_grounded_adaptive_recovery.py \\
  tests/test_v1923_final_code_gate.py \\
  tests/test_replan_completion_truth.py \\
  tests/test_sol_concurrency_and_remap.py -q
58 passed, 1 warning
```

### Kunming non-terminal strategy pivot continuation

The next run was executed on Journey `3b9836a8-5cee-49b5-a4f4-8f8bfe627b6c`
with the intent “室内工艺和美术馆，少走路、路线紧凑”. The domestic model
run `47cd0bd8-42f8-4296-9909-436a7895dbf0` first discovered only the real
library, exhausted its bounded search budget, and stopped with a machine-visible
`SEARCH_SATURATION`; its one-place `generate_plans` call was rejected with
HTTP 422. It did not invent a second Place or claim a plan.

The bounded follow-up changed the acquisition strategy to a new OSM `cafe`
category through the Agent Gateway. It discovered the real provider Place
`real-place-e1e58e1b2dd07a773f3eec8a` (蓝白红咖啡馆), recorded an
`ESTIMATED_AGENT` hypothesis without changing canonical UNKNOWN facts, and
generated plan `3bd2fd1a-ce7b-58db-8599-2c574d0e7aa3`. The live Valhalla
snapshot `9efcf94d-c61f-4d65-b77f-d4e4a14998b5` measured the actual library →
cafe edge at 38 minutes. Selection returned `PLANNED`, start returned `ACTIVE`,
and the product receipt contained the actual edge plus
`HARD_ELIGIBLE=true`.

A new controlled closure `a72e84da-0f12-414a-ac75-e144a25e326c` targeted the
current library. Agent Gateway proposal `a5b28138-d46b-4975-99ec-86fe44459950`
removed only the closed library and kept the cafe. Its incident snapshot was
`e667925b-db1f-47ae-b188-103eb50d7065`; the proposal was accepted with
`ALLOW_AUTO`, `DELEGATION_POLICY_MATCHED`, and
`DETERMINISTIC_GATE_VERIFIED`. Unlike the terminal-removal case, the result
remained `ACTIVE` and carried the cursor to the cafe activity
`2ea03513-bc9b-4d7d-8da4-1534a7e94033`. The competing same-slot proposal was
deterministically invalidated, not silently selected.

The cafe then completed through the real lifecycle
`depart → arrive → begin → complete`. Final product state:

```text
Journey.status                 = COMPLETED
Journey.active_plan_version_id = f071f823-bf4e-4712-9acc-f0c89f7fc736
Journey.current_activity_id    = null
accepted replan                = a5b28138-d46b-4975-99ec-86fe44459950
closure status                 = ACKNOWLEDGED / SIMULATED
```

This proves the non-terminal branch carries execution forward to a real
remaining activity; it is not merely a report-only pivot. The active child has
one completed provider-backed cafe activity, while the removed library remains
in the superseded plan lineage.

The current checkpoint is pushed to the isolated branch; no authority/mainline
merge was performed. The next autonomous experiment is a second unseeded city
transfer using the same domestic model order, with a preference that forces a
different category mix rather than another Kunming-only recovery.

## Current domestic-WB2api checkpoint: Guilin

This is the latest executed checkpoint on top of the prior R14/Dali report.
The experimental code commit for this checkpoint is `c53df8e6` (the report
closure commit follows it). The clean source branch remains
`codex/revolution-realtrip-recovery`; no authority/mainline branch was merged.

### Real discovery and strategy loop

Journey `7a6f9360-5834-4a93-a849-24b7c72895f6` entered previously unseeded
Guilin (`CN-GUILIN`) through the live product path. Nominatim was unreachable,
so the new Photon OSM-backed geocoder supplied a captured city anchor; Overpass
then returned HTTP 200 with 52 elements and materialized eight provider-backed
Places. The fallback is recorded as `photon_city_anchor`; it did not promote
opening hours or prices.

The domestic WB2api path was used as:

```text
primary:  cn:glm-5.3-flash
fallback: cn:deepseek-v4.1-flash
endpoint: http://127.0.0.1:7863/v1/chat/completions
```

The key was process-only. It is not in the repository, report, database, or
commit. Successful Hermes-compatible AgentRuns included GLM runs
`9e928578-e8d0-48f0-8a9b-d78797e4796e`,
`288f94c1-d321-42bd-9a58-117c8b0b47e7`, and
`07ef88bd-f45c-4a97-b951-e6ba4858399e`; domestic DeepSeek also completed
`61551482-ef83-4e01-ae20-33c68fa01de8` after a search-saturation stop.

The first Agent estimate for 叠彩山公园 was persisted as strategy-only
`ESTIMATED_AGENT` facts: opening 08:00–18:00 and cost 3,200 CNY minor. A
planner bridge repair then made the estimate influence provisional selection,
and allowed a coursework candidate to mix provider-complete facts with
agent-estimated facts. It did not change the canonical UNKNOWN opening/cost
fields. The deterministic parser also accepted the official 七星景区 ticket
context and persisted 5,500 CNY as provider-backed evidence; it did not treat
the unrelated 100 CNY team figure as the admission price.

### Select, execute, disrupt, replan, complete

AgentRun `07ef88bd-f45c-4a97-b951-e6ba4858399e` eventually generated plan
`5ba08863-52dd-592d-bc18-2310356fd3e4` (version 6):

- authority state: `COURSEWORK_ESTIMATED_FACTS`;
- selectable: `true` inside the explicit isolated coursework envelope;
- Places: `real-place-5e87d712b0faf693f25aac0f` (虞山公园) and
  `real-place-7cfb04805ea00e43e24d9ea3` (叠彩山公园);
- estimated total: 6,400 CNY minor, still explicitly estimated;
- mobility: Valhalla snapshot `3a876dcf-4a74-49eb-a5d4-b6b9023c4075`.

The product select endpoint returned HTTP 200 and bound that plan. Start then
returned `ACTIVE`; the first activity was advanced through `depart`, `arrive`,
and `begin`. The baseline runtime evidence contained the actual edge

```text
real-place-5e87d712b0faf693f25aac0f
  -> real-place-7cfb04805ea00e43e24d9ea3
provider: valhalla-http
minutes: 22
route_provenance: LIVE_PROVIDER_CAPTURE
decision: HARD_ELIGIBLE
```

The controlled disruption was deliberately labelled `SIMULATED`, not LIVE:
event `a3b2dac4-0674-46d8-b1aa-d36c763228f1`, type `CLOSURE`,
`COURSEWORK_CONTROLLED_CLOSURE`, bound to the current Yushan activity.
Deterministic `request_replan` created proposal
`d2b99b79-2fc2-408a-a43f-0e3d3b38d37c` with family
`F1_OPTIONAL_REMOVAL`: remove the closed Yushan stop, keep Diecai, reduce
travel by 22 minutes, zero cost delta, and preserve hard constraints. Its
incident mobility snapshot `38f9d6c6-36e5-4062-a5d2-5e7a08789d12` was again
captured from `valhalla-http`.

The Gateway accepted the proposal with `executed=true` and reason codes
`DELEGATION_POLICY_MATCHED` and `DETERMINISTIC_GATE_VERIFIED`. The active
PlanVersion became `c6302d09-3919-4d9b-8c05-e53d521407d9` (version 7), retaining
lineage to version 6. The revised single-stop plan was then advanced through
`depart`, `arrive`, `begin`, and `complete`. The final machine state is:

```text
Journey.status                 = COMPLETED
Journey.active_plan_version_id = c6302d09-3919-4d9b-8c05-e53d521407d9
Journey.current_activity_id    = null
event.status                   = ACKNOWLEDGED
Twin cursor                    = null
execution state                = COMPLETE
```

After the replan there is no remaining leg, so the final plan's
`used_edge_ids=[]` is the real zero-leg result. No edge, receipt, or mobility
fact was synthesized. The baseline edge and its hard-eligibility receipt are
preserved above and in the database.

### Agent runtime limitation observed

Machine evidence also records the limitation honestly. AgentRun
`2f67a4fa-df14-42e3-9407-5e3e39bf6f63` completed inspection/listing steps but
the domestic GLM and DeepSeek responses both ended empty, so it is marked
`FAILED_EXTERNAL / PROVIDER_REFUSED`; it is not counted as a successful critic
run. Another GLM run made a malformed one-place `generate_plans` call; the
Gateway rejected it with HTTP 422 and no side effect, after which the run
recovered and generated the valid candidate. Because the native model did not
reliably issue `request_replan` in every prompt, the final replan request and
acceptance are explicitly attributed to the deterministic Agent Gateway, not
to invented model prose.

### Checkpoint repairs and focused tests

The checkpoint commit includes Photon live-anchor fallback, official ticket
context parsing, strategy ordering across the explicit-catalogue seam,
provider-truth plus coursework-estimate coverage, and the strategy tools in
the execute-within-bounds mission surface. The focused post-change gate was:

```text
uv run pytest backend/tests/test_v10_generic_compose.py \
  backend/tests/test_revolution_r77_recovery.py \
  backend/tests/test_agent_mission_runtime.py \
  backend/tests/test_v18_2_agent_productization.py \
  backend/tests/test_qoder_city_failure_reasons.py -q
69 passed, 1 warning
```

The remaining product frontier is domestic-model tool-call reliability and a
second autonomous city transfer using the same strategy engine. The current
Guilin result is a completed coursework-envelope Journey, not a claim that
estimated facts are production provider truth.

This round made the same product Journey inspect live state, identify a named
disruption, request a deterministic recovery, cross the authority boundary,
and complete the revised Journey. The recovery used live Valhalla evidence;
opening and cost remained explicitly coursework estimates and were never
renamed to provider truth.

## Cities and intent-driven catalogue

### Lijiang, second city

Journey `66f8a7ca-02da-4e3f-a684-8cccc3ebad31` is the completed second-city
transfer run. The agent was instructed to prefer indoor museums/cultural
spaces, low walking, and a compact route. Its actual tool path included
`inspect_journey`, `inspect_twin`, `search_city_services`,
`estimate_place_facts`, and `generate_plans`.

The final selected PlanVersion was `c7812857-a770-566e-8e64-d51a3acdb511`
(version 20), with real provider-backed Places:

- `real-place-ff3ab0cd21df8cd8508292e3` — 玉龙纳西族自治县文化馆
- `real-place-714c34dc753247bdb5c5d1fe` — 万德宫

The selected plan carried live Valhalla mobility snapshot
`43d97418-778f-4a47-9e34-aa197d839bc1`; the actual used edge was the pair
`[real-place-ff3ab0cd21df8cd8508292e3, real-place-714c34dc753247bdb5c5d1fe]`,
75 minutes, `LIVE_PROVIDER_CAPTURE`, and `HARD_ELIGIBLE`.

The strategy engine recorded Value-of-Information decisions during plan
generation. Missing opening/cost facts were prioritized for places whose
facts could change feasibility or ranking. It also records source-path pivots;
the Wande Palace official source was retained as unavailable and its
canonical facts stayed `UNKNOWN`.

### Real source state

- Cultural Center cost: `0 CNY`, `VERIFIED_PROVIDER`, municipal source
  `https://www.lijiang.cn/article/166182.html`; opening remains `UNKNOWN`.
- Wande Palace source binding: `http://www.ljrbw.com/content/2023-09/18/content_13460.html`;
  fetch was unavailable, so opening and cost remain `UNKNOWN`.
- Agent estimates are stored under `strategy_estimate` as
  `ESTIMATED_AGENT` / `AGENT_PROVIDED_HYPOTHESIS`; canonical Place facts are
  not overwritten.

## Disruption and replan evidence

### Before repair: reproduced product defect

Journey `4de4dd63-a6a2-4ed2-992c-25faac577885` was used to reproduce the
failure. The command was:

> 丽江金塔景区临时关闭了，保留当前重要文化体验，少走路，你自己重新安排并实际请求 replan。

Before the repair, Event `14c1d50a-4a96-4aac-8a94-bf36288b36ea` was scoped as
`CURRENT_POSITION` and incorrectly targeted `d42a8d44-e15a-5941-b9f8-120671ba0d1f`
(丽江恋歌), while the text named 丽江金塔景区. Proposal
`379f9ad9-ab70-459f-bc93-c1dad1d4a28e` consequently removed the wrong Place.
This is preserved in the database as the before trace; it was not rewritten.

### Repair

The smallest bounded repair is in:

- `backend/app/integrations/ai/copilot_contract.py`
- `backend/app/integrations/ai/event_targeting.py`
- `backend/app/main.py`
- `backend/tests/test_agent_mission_runtime.py`

The boundary now:

1. extracts a named venue only when it is attached to a known disruption verb;
2. carries that subject through the semantic envelope when the model omits it;
3. resolves a current named disruption against exactly one persisted active-plan
   Activity before falling back to the execution cursor;
4. fails closed on ambiguity or an explicit name with no unique plan match;
5. preserves generic unscoped reports such as “下一站临时闭馆” as
   `CURRENT_POSITION` behavior.

### After repair: same scenario, correct target

New Journey `8bd3d0ca-abe3-446d-bd34-1866920c89c0` used the same real Lijiang
pair and the same user command. It was started, and the first activity was
advanced to `IN_PROGRESS` through the real product endpoints before the
disruption was sent.

- Event: `7beb0447-61a8-4123-bed2-7054346e2863`
- Event type: `CLOSURE`
- `affected_activity_id`: `e5a5ff17-b33a-55a1-9da4-ca6659aab7d9`
  (丽江金塔景区)
- persisted `subject_text`: `丽江金塔景区`
- `target_resolution`: `AUTHORITATIVE_NAMED_ACTIVITY`
- AgentRun: `c369bd36-ec90-4877-baea-b5a83d823e0a`
- model key: `cn:glm-5.3-flash`
- mission status: `COMPLETED`
- tool steps, in order:
  `inspect_journey → inspect_twin → request_replan → list_replans → accept_replan`

Proposal `fdca9b84-c7c1-44ee-a8d8-9d6679460012` was accepted by the
deterministic authority gate:

- base PlanVersion: `72738a09-12a1-5078-ba9f-b9dddeaf2130`
- resulting PlanVersion: `d2cfff96-4f7e-4ba3-976e-14eb0c02f90a`
- status: `ACCEPTED` / active
- kept: 丽江恋歌 (`real-place-353711c2b3f8f91ce1b58d13`)
- removed: 丽江金塔景区 (`real-place-ed72672fa31d32ccbadde4a2`)
- travel delta: `-93` minutes
- end-time delta: `-153` minutes
- cost delta: `0`
- hard constraints: passed
- authority reason codes: `DELEGATION_POLICY_MATCHED`,
  `DETERMINISTIC_GATE_VERIFIED`

The replan captured a fresh live Valhalla incident snapshot
`301db4b6-998c-4408-835c-fae823ca58d0`. The baseline route evidence was
`LIVE_PROVIDER_CAPTURE`; the incident route evidence was
`RUNTIME_CAPTURE`, provider `valhalla-http`, not mock mobility.

The revised Journey then completed through the real completion endpoint:

- final Journey status: `COMPLETED`
- final active PlanVersion: `d2cfff96-4f7e-4ba3-976e-14eb0c02f90a`
- final `current_activity_id`: `null`
- final Twin cursor: `null`
- final execution state: `COMPLETE`

Because the accepted revised plan contained only the surviving activity, its
post-replan `used_edge_ids` is empty. No edge was synthesized. The selected
baseline plan before the disruption had the real edge
`[real-place-353711c2b3f8f91ce1b58d13, real-place-ed72672fa31d32ccbadde4a2]`
with 93 minutes, `LIVE_PROVIDER_CAPTURE`, and a hard-eligible receipt.

## Authority and truth boundaries

- `COURSEWORK_ESTIMATE` is explicit in the selected baseline plan; it is not
  reported as a LIVE provider-ready plan.
- `UNKNOWN` opening/cost was never converted to provider-verified truth.
- Agent prose did not activate the new plan. `accept_replan` did so only after
  deterministic authority verification.
- No payment, booking, canonical demo seed, user database, or mainline merge
  was used.
- `MOCK != LIVE`; all mobility evidence cited above is Valhalla-backed.

## Focused tests

```text
uv run pytest backend/tests/test_agent_mission_runtime.py -q
20 passed, 1 warning

uv run pytest backend/tests/test_agent_mission_runtime.py \
  backend/tests/test_agent_runtime_gate.py \
  backend/tests/test_revolution_r77_recovery.py \
  backend/tests/test_v18_2_agent_productization.py \
  backend/tests/test_sol_execution_cursor.py \
  backend/tests/test_postgate_provider_foundation.py \
  backend/tests/test_provider_runtime_gate.py \
  backend/tests/test_qoder_mobility_truth_contract.py \
  backend/tests/test_v10_generic_compose.py -q
134 passed, 1 warning
```

## Candidate/base delta and remaining frontier

The candidate adds named current-disruption targeting and a regression gate;
the pre-existing focused suite remains green. The real run moved from
wrong-cursor removal to correct named-activity removal, then to a completed
Journey with an auditable old/new PlanVersion lineage.

The VOI acquisition and strategy pivot experiment below continued this
checkpoint. The estimate envelope remains separate from canonical truth, and
sources that cannot corroborate remain UNKNOWN.

## VOI experiment executed after the checkpoint

The next experiment was executed, not merely proposed, on Journey
`fa5db347-4f93-42bc-959d-4600f49f02ae` (`R14 Lijiang VOI second-source
experiment`). It remained isolated as `DRAFT` and was never selected or
activated.

- AgentRun: `6a487ff0-4e30-4852-812f-ed5ba7d4a823`
- model: `cn:glm-5.3-flash`
- mission: `c7da8742-d7d9-401f-94ea-1929550e3372`
- status: `COMPLETED`
- ordered tools:
  `inspect_journey → inspect_twin → search_city_services →
  search_city_services(category=attraction) → acquire_place_facts(OFFICIAL_TICKETING) →
  acquire_place_facts(MUNICIPAL_AUTHORITY) → generate_plans`

The Agent selected `real-place-5677eb6e9a22401a4f8c7c5d` (千古情大剧院) as
the VOI target because its theatre/ticket cost could change the ranking more
than the surrounding free/unknown attractions. The acquisition receipts show:

- Overpass answered with HTTP 200 and the exact provider entity
  `overpass:node/13016989428`.
- Nominatim lookup completed with `matched_provider_entity=true`, but
  `nominatim_extratags={}`.
- No exact official URL was bound (`official_web=NO_SOURCE_URL`).
- SearxNG was unconfigured and therefore not treated as evidence.
- `known_opening_count=0`, `known_cost_count=0`.
- Canonical opening and cost remained `UNKNOWN`; no estimate was written.

The Agent first sent one malformed `generate_plans` argument payload; the
Gateway rejected it as `MALFORMED_TOOL_ARGUMENTS` with no side effect. The
next valid call used four real Place IDs and produced candidate
`fa79ea3b-bef6-548f-bbdd-76105731a167` with:

- `status=CANDIDATE`
- `selectable=false`
- `authority_state=PROVISIONAL_UNRESOLVED_FACTS`
- `mobility_provider=valhalla-http`
- mobility snapshot `d24e0313-0641-484b-bbb7-6f445f8fedf1`
- unresolved opening/cost facts preserved for the selected real Places

This is the intended R14 behavior: the strategy engine chose a decision-
sensitive fact, attempted bounded source acquisition, retained UNKNOWN when
corroboration was absent, and continued to a non-authoritative candidate
without silently promoting evidence.

## Strategy pivot, selection, and completed execution

The same Journey continued with a second domestic-model AgentRun instead of
restarting the scenario:

- Journey: `fa5db347-4f93-42bc-959d-4600f49f02ae`
- AgentRun: `abd9de3c-0bfc-4ea4-9e28-794c70fc544f`
- mission: `90d788e8-3dad-44cc-94e4-3e0d4e2bc8df`
- model: `cn:glm-5.3-flash`
- run status: `COMPLETED`
- persisted tool steps: 7 (one rejected malformed call had no side effect)
- ordered useful path:
  `inspect_journey → inspect_twin → list_replans → search_city_services →
  acquire_place_facts(OFFICIAL_OPERATOR) → generate_plans`

The persisted before/after candidate activities show an actual Place-set
change:

| Candidate | Provider-backed Place IDs | Inter-place walk | State |
| --- | --- | ---: | --- |
| Before, `fa79ea3b-bef6-548f-bbdd-76105731a167` | 千古情大剧院 `real-place-5677eb6e9a22401a4f8c7c5d` + 邱塘关 `real-place-2390ded5c079f8ac2aa626d3` | 148 min | provisional candidate, not selected |
| After, `200e74ef-cc42-5d4f-b2b3-54a48135f014` | 丽江恋歌 `real-place-353711c2b3f8f91ce1b58d13` + 万德宫 `real-place-714c34dc753247bdb5c5d1fe` | 92 min | selected and completed |

The Agent explicitly abandoned the 千古情 source path after its second-source
lookup confirmed the same OSM entity but found no structured opening or cost
facts. It chose a theatre-plus-museum alternative to preserve cultural intent
and reduce walking burden. The 丽江恋歌 acquisition was exact-entity-bound to
`overpass:way/1492458576`; official structured facts remained absent, so its
canonical opening and cost stayed UNKNOWN. The municipal/search path was
unconfigured/unavailable; no claim was promoted from Nominatim tags.

The alternative candidate became `selectable=true` only inside the explicitly
enabled lab `COURSEWORK_ESTIMATE` envelope. Its Place records carried earlier
persisted `ESTIMATED_AGENT` hypotheses (10:00–18:00, estimated cost 0); those
hypotheses were not acquired in this pivot run and are not provider facts. The
plan itself preserves four unresolved canonical facts (two opening, two cost),
with cost summary `PARTIAL`, `unknown_item_count=2`; its explanation says
coursework-only and not LIVE provider-ready. Estimated zero is not described
as verified free.

### Product execution receipts

- `POST /api/v1/journeys/fa5db347-4f93-42bc-959d-4600f49f02ae/plans/200e74ef-cc42-5d4f-b2b3-54a48135f014/select` returned Journey `PLANNED` with that active PlanVersion.
- `POST /api/v1/journeys/fa5db347-4f93-42bc-959d-4600f49f02ae/start` returned Journey `ACTIVE`, current activity 丽江恋歌.
- The actual used edge was `[real-place-353711c2b3f8f91ce1b58d13, real-place-714c34dc753247bdb5c5d1fe]`, 92 minutes, `valhalla-http`, `LIVE_PROVIDER_CAPTURE`, `degraded=false`, `hard_minutes=92`, decision `HARD_ELIGIBLE`.
- The active plan's eligible mobility snapshot was `e914b4ce-1358-4975-85b0-98e46da8ba25`.
- Both activities were executed through their persisted `depart → arrive → begin → complete` endpoints.
- Final API state: Journey `COMPLETED`; `active_plan_version_id=200e74ef-cc42-5d4f-b2b3-54a48135f014`; `current_activity_id=null`; Twin `projection_status=READY`, `now_state=COMPLETE`, cursor absent, and the same Valhalla snapshot/edge eligibility receipt.

This is a real coursework-usable result, not a claim that unknown canonical
opening/cost facts became verified. The Agent strategy pivot, product
selection, execution cursor, persisted activities, and final Twin all agree.
Next strategy frontier: compare a second explicit natural-language preference
against this cultural/low-walk run and make the resulting Place set or order
diverge for a reason traceable to intent and actual catalogue evidence.

## Outdoor-intent contrast, polarity repair, and completed product journey

### Preference contrast and semantic repair

The second Lijiang intent was explicitly different from the completed
cultural/low-walk journey: outdoor nature and old buildings, relaxed pace, and
dislike of theatres/indoor venues. The first live compile correctly emitted
only `PREFER_OUTDOOR` for the phrase “不喜欢剧场和室内馆”. A later Agent-authored
phrase, “明确放弃剧场和室内馆路径”, exposed a narrower deterministic
polarity gap: the compiler did not yet treat `放弃`/`跳过`/`不选` as negative
preference markers, so a mission briefly persisted both `PREFER_INDOOR` and
`PREFER_OUTDOOR`.

The bounded repair adds those Chinese negation forms and the equivalent
English `exclude`/`skip`/`reject`/`dislike` markers to the existing clause-level
polarity logic. It also keeps an explicit final polarity guard at the
`create_mission` authority boundary. Regression tests cover both “不喜欢室内”
and “放弃室内路径”. A fresh live `/agent/commands` replay after service restart
persisted mission `7cacabeb-0bcc-4554-ae2e-2180cf882448` with exactly
`objective_codes=["PREFER_OUTDOOR"]` and `preferences={"outdoor":true}`; no
`PREFER_INDOOR` leaked into the mission. The replay used domestic GLM through
`HERMES_COMPAT_ENDPOINT`, AgentRun
`ca16df27-077d-441f-acea-6ac73ba0abc3`, model `cn:glm-5.3-flash`.

### Real catalog strategy and bounded estimate

Journey `cc2d7b07-6567-430c-9544-5deb842d8adb` was used for the independent
outdoor-intent contrast. AgentRun
`de743fd1-26b7-4fdc-93e0-f1133f62de63` (`cn:glm-5.3-flash`) inspected Journey
and Twin, searched live Lijiang OSM-backed catalog, and generated the
candidate. An earlier search trace on the same Journey proved that natural /
historic terms could return zero; the Agent changed to the `park` category and
obtained two real Place IDs:

- `real-place-b1d338c31a9b5b4cb26d99e2` — 世界记忆遗产公园
- `real-place-cfa76a6b4c7dd1fe68a4dfdf` — 文笔公园

The Agent used `estimate_place_facts` on both returned IDs. Each hypothesis is
stored as `ESTIMATED_AGENT` / `AGENT_PROVIDED_HYPOTHESIS`: 09:00–18:00 and
¥50 per place. The canonical opening records still say
`REQUIRES_CONFIRMATION`, canonical cost evidence remains `UNKNOWN`, verified
cost subtotal remains zero with two unknown items, and the estimated ¥100
total is not described as verified or free.

The resulting PlanVersion is `7133780a-03f7-5ba4-8f95-b89334113864`
(version 4), containing only those two searched Places. It is
`selectable=true` solely within the explicit `COURSEWORK_ESTIMATE` envelope;
the explanation states it is not a LIVE provider-ready result. Its frozen
mobility snapshot is `87dcf106-d96a-49d8-977d-b67a50949c45`, provider
`valhalla-http`. The actual used edge is
`[real-place-b1d338c31a9b5b4cb26d99e2,
real-place-cfa76a6b4c7dd1fe68a4dfdf]`, 45 minutes, `WALK`,
`LIVE_PROVIDER_CAPTURE`, not degraded, with a persisted 45-minute
`HARD_ELIGIBLE` receipt.

### Product selection and completion

The deterministic selection endpoint accepted that candidate and set it as
the active PlanVersion. The product start endpoint moved the Journey to
`ACTIVE`; both real catalog activities then traversed the persisted lifecycle
through `depart → arrive → begin → complete`. The resulting API and Twin state
agree:

- Journey `cc2d7b07-6567-430c-9544-5deb842d8adb`: `COMPLETED`
- active PlanVersion: `7133780a-03f7-5ba4-8f95-b89334113864`
- `current_activity_id=null`; Twin projection `READY`; execution state `COMPLETE`
- mobility source remains `valhalla-http`, frozen snapshot remains
  `87dcf106-d96a-49d8-977d-b67a50949c45`, actual edge remains hard eligible
- opening and price remain visibly unresolved canonical facts; this is a
  coursework-estimated product Journey, not a claim about a physically
  completed real-world visit

This contrast materially changed the activity set from the earlier cultural
pair (玉龙纳西族自治县文化馆 + 万德宫) to two outdoor parks, based on the explicit
outdoor preference and real provider categories. The only remaining R14
frontier at that checkpoint was to carry the same strategy/VOI/pivot mechanism
to another unseeded city; the Dali run below is that transfer. Search-budget
continuity remains a follow-up engineering opportunity.

## Dali unseeded-catalog recovery and completed autonomous replan

The next run used the same product path on an unseeded Dali Journey rather than
adding Dali to demo data. Journey `898830a3-3aad-4970-9522-f18240798c0e`
(`CN-DALI`) started with two real provider Places: People Park
(`real-place-332c2d0e9568186ef6010329`) and Erhai Park
(`real-place-68a115779f0198818a55065f`). Both canonical opening and cost
evidence were still `UNKNOWN`.

### Defect observed and bounded repair

The first Dali Agent attempt exposed a real integration gap: the Agent's
`search_city_services` tool only read local catalog rows, so an unseeded live
Journey could not enter the provider discovery path. AgentRun
`fa634019-a259-4467-8b44-6315f111a80e` ended with `SEARCH_SATURATION` despite the product's live
Overpass discovery being available. The bounded repair in
`backend/app/agent/gateway.py` bridges an empty live Journey catalog to the
existing `capture_real_city_candidates(..., mode="live")` path. It returns a
discovery receipt and only materialized provider-backed rows; it does not let
the Agent invent Place IDs.

The second defect was strict replacement ranking: the real Dali catalog had
provider-backed Places but canonical cost was `UNKNOWN`, so the recovery engine
could not choose an otherwise viable replacement. The bounded lab-only repair
adds an explicit `allow_strategy_estimate` path. It accepts a persisted
`ESTIMATED_AGENT` strategy hypothesis only when the isolated
`COURSEWORK_ESTIMATE` envelope is enabled. The default remains strict, and
compatibility `cost_minor=0` is never treated as known free. Canonical
provider opening/cost fields remain unchanged.

### Actual domestic-model Agent loop

Controlled disruption Event `4238a285-720a-4203-901e-ab526d3a63be` reported a
major user-reported closure of Erhai Park while People Park was already
completed. The first recovery attempt preserved the failure evidence:
`accept_replan` rejected proposal `35e77e4b-b333-4518-9c9e-573995ffa0af` because it did not preserve
the current execution position, and replacement attempts failed with real
`MOBILITY_DATA_UNAVAILABLE` / `SERVICE_UNAVAILABLE` results. Those were not
counted as success.

After the bounded repairs, AgentRun
`a4e2b17b-0e5a-4e79-aa77-53bae776510a` completed through the domestic
`HERMES_COMPAT_ENDPOINT` runtime with model `cn:glm-5.3-flash` and mission
`f484e7db-3169-4862-ab6e-337b734e0009`. Its persisted useful tool order was:

```text
inspect_journey
→ inspect_twin
→ search_city_services (live discovery receipt, 8 provider-backed Places)
→ estimate_place_facts (Erhai ecological corridor, ESTIMATED_AGENT)
→ request_replan
→ list_replans
→ accept_replan
```

The Agent chose the unused outdoor provider Place Erhai Ecological Corridor
(`real-place-8fba1ea421a36176c31fa564`). The persisted estimate was explicitly
09:00–18:00 and 5,000 CNY with status `ESTIMATED_AGENT`, basis
`AGENT_PROVIDED_HYPOTHESIS`, and `authority_eligible=false`. The canonical
Place still reports opening `UNKNOWN` and cost evidence status `UNKNOWN`.

Deterministic recovery accepted proposal
`cc97afb0-131b-4d2e-aa35-960a0053ba7d` under policy v2:

- family: `F0_SAME_SLOT_REPLACEMENT`
- base PlanVersion: `ca79d124-a358-5b7d-b074-63340232bd5e`
- accepted PlanVersion: `be6159dd-785b-405d-8b9c-9d0d4c5e37a4`
- kept People Park; removed closed Erhai Park; added the ecological corridor
- cost delta: +5,000 CNY minor
- travel delta: +4 minutes
- `hard_constraints_passed=true`
- `locked_commitments_preserved=true`
- `DETERMINISTIC_GATE_VERIFIED`

The accepted plan froze mobility snapshot
`9827a08c-8a13-4704-aeab-79864af21918`. Its actual used edge was collected
from product/Twin state, not synthesized:

```json
{
  "used_edge_ids": [[
    "real-place-332c2d0e9568186ef6010329",
    "real-place-8fba1ea421a36176c31fa564"
  ]],
  "provider": "valhalla-http",
  "route_provenance": "LIVE_PROVIDER_CAPTURE",
  "fact_quality": "LIVE_PROVIDER_CAPTURE",
  "hard_minutes": 63,
  "decision": "HARD_ELIGIBLE",
  "degraded": false
}
```

The new activity `80e98c88-0d7c-45f4-a338-425b93f51997` then traversed the
real product lifecycle: `depart` 200, `arrive` 200, `begin` 200, and
`complete` 200. Final machine state agrees across Journey, PlanVersion,
activities, and Twin:

- Journey: `COMPLETED`
- active PlanVersion: `be6159dd-785b-405d-8b9c-9d0d4c5e37a4`
- current activity: `null`
- Twin: `projection_status=READY`, `now_state=COMPLETE`
- both activities: `COMPLETED`
- plan explanation: `COURSEWORK_ESTIMATED_FACTS`, envelope
  `COURSEWORK_ESTIMATE`
- no canonical/provider fact was relabeled as LIVE or FREE

This is the first R14 run in which a domestic Agent discovered an unseeded
provider catalog, chose a new strategy target after a closure, crossed the
deterministic authority boundary, and completed the revised Journey. It is a
coursework-estimated selectable result, not a claim that unknown opening/cost
facts are production verified.

### Focused verification and next frontier

The focused regression run after the bounded repairs was:

```text
uv run pytest backend/tests/test_hotfix_v2_closure_truth.py backend/tests/test_agent_mission_runtime.py -q
37 passed, 1 warning
```

The new tests cover the live unseeded discovery bridge and the rule that an
Agent estimate can affect replacement ranking only inside the explicit lab
envelope. The next autonomous experiment is to transfer the same strategy
engine to another freshly unseeded city with the lab estimate envelope off,
so the system must either acquire corroborated facts or retain a truthful
provisional/non-selectable result instead of widening authority.

## R14 fact-driven score boundary (current experimental delta)

Starting from `cad32950bba88e9cc9358526938b1493a5540187`, the authoritative
multiday compose path was changed in product code at
`backend/app/planning/authoritative_v12.py` and committed as
`4d7f0a2e18d51b9be54ba3e034685cc22dadc042`.

The old real-city path wrote fixed values for `preference_fit`,
`mobility_fit`, `time_reliability`, `robustness`, `opportunity_value`, and the
candidate total. The current path computes the persisted score from the
candidate that was actually composed:

- preference fit comes from persisted mission/preference keys matched against
  the selected provider Place category/tags;
- mobility fit comes from the selected `MobilityFact` duration and walking
  minutes, with provider-route coverage and reliability recorded;
- budget fit comes from the persisted plan total against the Journey budget;
- time reliability comes from captured opening-window close times and the
  scheduled activity end;
- robustness and opportunity value include actual opening/cost coverage and
  route evidence rather than venue-quality constants.

The same computed `metrics["total"]` is persisted as both
`PlanVersion.utility_score` and `score_breakdown_json.total`. A machine-readable
`explanation_json.score_provenance` records the counts and source basis used by
each dimension. Unknown opening/cost facts remain unknown; this change does
not convert them into free or provider-verified facts.

The focused product regression after this delta passed:

```text
uv run pytest tests/test_r14_terminal_disruption_recovery.py \
  tests/test_agent_mission_runtime.py \
  tests/test_v14_grounded_adaptive_recovery.py \
  tests/test_v1923_final_code_gate.py \
  tests/test_replan_completion_truth.py \
  tests/test_sol_concurrency_and_remap.py \
  tests/test_v13_1_1_semantic_integrity.py \
  tests/test_v10_generic_compose.py -q
65 passed, 1 warning
```

That exact-code live check completed below; the score receipt is followed by a
second domestic-model run on a fresh unseeded Chengdu Journey.

### HTTP runtime receipt on the exact code checkpoint

The live code was restarted from `4d7f0a2e18d51b9be54ba3e034685cc22dadc042`
with the domestic WB2api endpoint and model order
`cn:glm-5.3-flash` → `cn:deepseek-v4.1-flash`. A disposable runtime database
was used so the shared R14 evidence database was not reset. The product HTTP
path was:

```text
POST /api/v1/journeys/803b04aa-cf6d-4fd8-a33b-156809292d05/
     plans/authoritative-compose
place_ids = r14-score-place-park, r14-score-place-museum
HTTP 201
complete_plan_count = 2
```

The persisted PlanVersions proved that the score was no longer the former
constant sequence. For plan
`9203bb0a-231c-4c74-afeb-c2d35eeba854`, the product returned
`utility_score=0.772231`, `mobility_fit=0.661111`, `budget_fit=0.914`,
`robustness=0.9`, and `total=0.772231`; its provenance recorded 61 actual
travel minutes, 3 route facts, 3 provider-captured routes, and 2 verified
opening/cost rows. The alternate plan
`41800ece-fd79-4161-a8e8-b5ef53ae17d1` returned a different actual score
(`0.766539`) because its route facts included one synthetic fallback and its
travel burden was 55 minutes. The response and subsequent GET of
`/journeys/{journey_id}/plans` agreed on these persisted values.

The runtime mobility envelope was explicitly mixed
(`LIVE_CAPTURE` plus `SYNTHETIC_FIXTURE`); this receipt validates score-source
binding, not a claim that synthetic mobility is live. The domestic model was
not allowed to write score or authority truth.

## Domestic GLM Chengdu strategy, authority crossing, and completed recovery

To verify the domestic model path on the current service, a fresh unseeded
Journey `ee12f5a7-3b40-4b10-a3d5-3e4cec9ea451` was created in `CN-CHENGDU`
with the natural-language intent: outdoor parks, quiet walking, local
culture, little walking, and a compact route. The service was configured with
`cn:glm-5.3-flash` as the primary WB2api model and
`cn:deepseek-v4.1-flash` as the domestic fallback. The raw WB2api credential
was process-only and is not in the repository or this report.

The first AgentRun was a real HTTP model/tool loop, not a scripted narrative:

```text
AgentRun: 124e5323-6dc6-4f2d-9014-dc356f5893b1
mission: bb04a0f7-eba5-414a-b0b9-eecc05d806c6
trace: 535e396f-7000-4f7a-bf50-7c72aff49a54
model: cn:glm-5.3-flash
runtime: HERMES_COMPAT_ENDPOINT
tools: inspect_journey → inspect_twin → search_city_services
        → acquire_place_facts → estimate_place_facts
        → generate_plans → list_replans
```

The model discovered real Chengdu provider Places rather than seeded golden
rows, preserved canonical opening/cost `UNKNOWN`, and used the explicit
coursework envelope for the strategy estimate. The generated plan was
selectable under `COURSEWORK_ESTIMATED_FACTS`; its mobility was still
`valhalla-http` / `LIVE_PROVIDER_CAPTURE`. The plan was selected through the
normal HTTP select endpoint and the Journey was started normally.

A controlled closure then affected the active `人民公园` activity. The
domestic Agent performed a real inspection and deterministic replan request:

```text
AgentRun: deeae984-b302-4790-a609-385c5c7b2543
mission: 41b16393-54f9-470b-b54c-00740e5295b4
trace: 0f9f76cf-ff10-4cfc-a103-fd064fd4df31
model: cn:glm-5.3-flash
tools: inspect_journey → inspect_twin → search_city_services
        → request_replan
```

The deterministic engine produced three genuinely different live proposals.
The selected rank-0 proposal
`2f7a5ee0-4821-4e3b-a4f8-dc8c16920850` kept `成华公园`, removed the closed
People's Park, and added the real provider Place
`real-place-73024784c2781fef0000bf23` (`后子门游园`). Its live route evidence
was 16 minutes for the replacement comparison and 52 minutes for the
accepted plan's actual edge.

The follow-up model run inspected the proposals but ended in prose before
emitting an `accept_replan` tool call. Machine evidence is treated as final;
that run is therefore not counted as an Agent acceptance. The proposal was
then executed through the same CityNexus authority gateway (no direct DB
mutation and no direct assignment to `active_plan_version_id`):

```text
request_id: r14-accept-domestic-20261001120441
decision: ALLOW_AUTO
executed: true
reason_codes: DELEGATION_POLICY_MATCHED, DETERMINISTIC_GATE_VERIFIED
base_plan: 33bfa2cc-819a-56d1-b763-5a3d22cca81e
accepted_plan: 31c66187-138c-4dfa-b6d5-01f3875754c2
```

The final product evidence agrees across Journey, PlanVersion, activities,
and Twin:

```json
{
  "journey_status": "COMPLETED",
  "active_plan_version_id": "31c66187-138c-4dfa-b6d5-01f3875754c2",
  "current_activity_id": null,
  "activities": [
    {"place_id": "real-place-73024784c2781fef0000bf23", "status": "COMPLETED"},
    {"place_id": "real-place-61d0c62a55c60485a4035b98", "status": "COMPLETED"}
  ],
  "mobility_provider": "valhalla-http",
  "route_provenance": "LIVE_PROVIDER_CAPTURE",
  "used_edge_ids": [[
    "real-place-73024784c2781fef0000bf23",
    "real-place-61d0c62a55c60485a4035b98"
  ]],
  "eligibility_receipts": [{
    "persisted_minutes": 52,
    "hard_minutes": 52,
    "hard_eligible": true,
    "decision": "HARD_ELIGIBLE"
  }],
  "all_actual_edges_hard_eligible": true,
  "twin_projection_status": "READY"
}
```

This is a completed coursework-estimated Journey, not a claim that unknown
canonical opening/cost facts became verified or free. `MOCK != LIVE` remains
true. That earlier run exposed a runtime reliability gap: the model stopped
after reading proposals and a deterministic continuation performed the
Gateway mutation. The bounded runtime repair and the exact-code rerun below
close that gap without weakening the authority boundary.

## Exact-code domestic GLM acceptance continuation and completed Journey

The service was restarted from the current experimental source with the
process-only WB2api credential and this domestic model chain:

```text
primary:  cn:glm-5.3-flash
fallback: cn:deepseek-v4.1-flash
runtime:  HERMES_COMPAT_ENDPOINT
```

The bounded repair has two parts. First, complete proposal evidence remains
persisted in `AgentRunStep`, but the next model turn receives the proposal
identity, scores, hard-constraint facts, schedule deltas, and provider
summaries without captured route geometry. Second, when the mission text
explicitly requires `accept_replan`, the runtime does not accept a prose-only
finish after proposal evidence: it adds one continuation turn requiring the
exact feasible proposal ID and waits for the Gateway receipt. It does not
write Journey or PlanVersion state directly.

The exact-code run used the same Chengdu Journey after the closure event:

```text
journey: 0a0685bb-44a1-4689-afe9-bec81cde4182
AgentRun: 6ade8eaa-626c-4ca1-a29d-16e06b79ecef
mission: b2b31d45-3927-42a6-9eaa-677d5ddcdd75
model_key: cn:glm-5.3-flash
provider_key: hermes
tool order: inspect_journey → inspect_twin → list_replans → accept_replan
proposal: 901977ee-8bb3-4cbf-9552-7d3f982132f6
Gateway decision: ALLOW_AUTO
Gateway executed: true
Gateway reason_codes: DELEGATION_POLICY_MATCHED, DETERMINISTIC_GATE_VERIFIED
accepted PlanVersion: b21c3900-87f1-49d2-8a72-7241074af3ba
```

After the AgentRun, the product lifecycle was executed through the real
activity endpoints for both the replacement and the preserved next activity:

```text
bd7b0f0b-00ad-45f5-9456-570a917320b3  depart → arrive → begin → complete
a29f472d-6b0c-4677-af71-b77d730c5ee7  depart → arrive → begin → complete
```

The final HTTP/Twin receipt agrees across persisted state:

```json
{
  "journey_status": "COMPLETED",
  "active_plan_version_id": "b21c3900-87f1-49d2-8a72-7241074af3ba",
  "current_activity_id": null,
  "twin_projection_status": "READY",
  "used_edge_ids": [[
    "real-place-73024784c2781fef0000bf23",
    "real-place-61d0c62a55c60485a4035b98"
  ]],
  "eligibility_receipts": [{
    "provider": "valhalla-http",
    "route_provenance": "LIVE_PROVIDER_CAPTURE",
    "fact_quality": "LIVE_PROVIDER_CAPTURE",
    "persisted_minutes": 52,
    "hard_minutes": 52,
    "hard_eligible": true,
    "decision": "HARD_ELIGIBLE"
  }],
  "all_actual_edges_hard_eligible": true
}
```

Canonical opening and cost remain `UNKNOWN`; the replacement plan is
explicitly `COURSEWORK_ESTIMATED_FACTS` / `COURSEWORK_ESTIMATE`. The Agent
estimate was not relabeled as provider truth or free. Live mobility remains
`valhalla-http` / `LIVE_PROVIDER_CAPTURE`, and the real selected Journey was
completed only after the Gateway created the new active PlanVersion.

The regression tests cover both mechanisms:

```text
uv run pytest tests/test_agent_mission_runtime.py \
  tests/test_dsh_list_replans_bound.py \
  tests/test_agent_runtime_gate.py -q
```

The next R14 experiment is to transfer this same domestic-agent acceptance
loop to another freshly discovered city and force a strategy change driven by
the user intent, while keeping the estimate envelope explicit and preserving
`P7=false`.

## R14 Wuhan transfer: domestic Agent estimate, live route, completed Journey

The same isolated runtime then entered a fresh, unseeded `CN-WUHAN` Journey
`0a4418c1-17ee-494d-90a5-2401481fab08` from the natural-language intent
“室内工艺、美术馆、安静文化空间、少走路、路线紧凑”. No itinerary or golden
Place IDs were inserted before the Agent run.

The first Agent run discovered eight live Overpass entities but the product
candidate correctly remained `selectable=false` because the chosen pair did
not both have estimate envelopes. Search then hit the real
`SEARCH_SATURATION` gate. The Agent did not keep repeating the same search:
it moved to source acquisition and facts. For the final pair, the product
also performed Nominatim entity matching:

```text
real-place-3168db3852e335393b1f54af  overpass:node/1194992420
  Nominatim: ACQUIRED / matched_provider_entity=true / extratags cuisine=chinese

real-place-393bc6a425cc41be5f9a9304  overpass:node/1252118660
  Nominatim: ACQUIRED / matched_provider_entity=true / extratags fast_food=cafeteria
```

Neither second source supplied opening hours or price. The persisted canonical
rows stayed `opening_hours.status=UNKNOWN` and
`cost_evidence.status=UNKNOWN`; `known_opening_count=0` and
`known_cost_count=0`.

The completed domestic DeepSeek Agent run was:

```text
AgentRun: 5d1bbdbb-1b01-494d-91de-0fd38001ff08
mission: bd5c535f-3e17-44e4-a68d-f86965b66acf
trace: 92124278-8048-43f7-9bcd-b90739b5ad7e
runtime: HERMES_COMPAT_ENDPOINT
persisted model_key: cn:deepseek-v4.1-flash
tools: inspect_journey → inspect_twin → estimate_place_facts → generate_plans
```

It estimated only the missing second candidate using the explicit lab
envelope:

```json
{
  "place_id": "real-place-393bc6a425cc41be5f9a9304",
  "opening_hours": {"status": "ESTIMATED_AGENT", "open_minutes": 420, "close_minutes": 1320},
  "cost_evidence": {"status": "ESTIMATED_AGENT", "amount_minor": 3000, "currency": "CNY"},
  "authority_eligible": false,
  "basis": "agent_bounded_hypothesis"
}
```

The real `generate_plans` tool then returned a candidate, not an invented
success:

```text
plan: 29733bc9-e6bd-5858-b87b-81a1633f1a01
status: CANDIDATE
selectable: true
authority_state: COURSEWORK_ESTIMATED_FACTS
authority_envelope: COURSEWORK_ESTIMATE
mobility_provider: valhalla-http
mobility_snapshot: 1cebaa64-a947-422f-b383-e7f89464b7d6
```

The response still listed the unresolved provider facts for both Places,
including `opening=REQUIRES_CONFIRMATION` and `cost=UNKNOWN`. The product then
crossed its ordinary authority path: `select` returned `PLANNED`, `start`
returned `ACTIVE`, and the two real activities completed through the actual
execution endpoints.

Final product/Twin receipt:

```json
{
  "journey_status": "COMPLETED",
  "active_plan_version_id": "29733bc9-e6bd-5858-b87b-81a1633f1a01",
  "current_activity_id": null,
  "twin_projection_status": "READY",
  "used_edge_ids": [[
    "real-place-3168db3852e335393b1f54af",
    "real-place-393bc6a425cc41be5f9a9304"
  ]],
  "eligibility_receipts": [{
    "provider": "valhalla-http",
    "fact_quality": "LIVE_PROVIDER_CAPTURE",
    "route_provenance": "LIVE_PROVIDER_CAPTURE",
    "persisted_minutes": 40,
    "hard_minutes": 40,
    "hard_eligible": true,
    "decision": "HARD_ELIGIBLE"
  }],
  "all_actual_edges_hard_eligible": true
}
```

This transfer demonstrates a real strategy change in a second unseeded city:
search saturation caused the Agent to stop broad discovery, acquire exact
entity facts, then use an explicitly bounded estimate to make a coursework
candidate. It does not claim live opening/cost truth, free entry, or
production authority. `MOCK != LIVE`, `UNKNOWN != FREE`, and `P7=false` remain
unchanged.
