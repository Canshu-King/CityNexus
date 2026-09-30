# Revolution R14 — Autonomous Strategy Engine

## Machine checkpoint

- Base SHA: `f21d82c1910502de094117edeac9f1c83c5c0b21`
- Final SHA: `c236fbfec2d311971d827352495d44ce28c07761`
- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Product database: `C:\Users\仓鼠王\AppData\Local\Temp\citynexus-r13-metadata-fix-20260930-b.sqlite3`
- Runtime: `HERMES_COMPAT_ENDPOINT`
- Model used for the successful recovery run: `cn:glm-5.3-flash`
- Fallback configured: `cn:deepseek-v4.1-flash`
- Endpoint: local WB2api `http://127.0.0.1:7863/v1/chat/completions`
- Credentials: process environment only; no raw credential is persisted in this tree.

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
frontier is to carry the same strategy/VOI/pivot mechanism to another
unseeded city and to tighten search-budget continuity so a bounded multi-step
Agent run can pivot across turns without misreading per-turn search limits.
