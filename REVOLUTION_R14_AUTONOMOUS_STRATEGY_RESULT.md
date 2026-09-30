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
18 passed, 1 warning

uv run pytest backend/tests/test_agent_mission_runtime.py \
  backend/tests/test_agent_runtime_gate.py \
  backend/tests/test_revolution_r77_recovery.py \
  backend/tests/test_v18_2_agent_productization.py \
  backend/tests/test_sol_execution_cursor.py \
  backend/tests/test_postgate_provider_foundation.py \
  backend/tests/test_provider_runtime_gate.py \
  backend/tests/test_qoder_mobility_truth_contract.py \
  backend/tests/test_v10_generic_compose.py -q
132 passed, 1 warning
```

## Candidate/base delta and remaining frontier

The candidate adds named current-disruption targeting and a regression gate;
the pre-existing focused suite remains green. The real run moved from
wrong-cursor removal to correct named-activity removal, then to a completed
Journey with an auditable old/new PlanVersion lineage.

The next autonomous experiment is to use the existing VOI decisions to acquire
one decision-sensitive second-source opening/cost fact for a new real Lijiang
Place, regenerate the same intent-driven strategy, and measure whether the
candidate set changes. The estimate envelope must remain separate from
canonical truth, and any source that cannot corroborate must remain UNKNOWN.
