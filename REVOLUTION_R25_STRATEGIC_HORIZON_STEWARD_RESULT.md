# Revolution R25 — Strategic Horizon Steward

## Result

R25 reached live runtime closure on a fresh provider-backed Nara Journey. The configured Hermes-compatible model made the strategic decision; no deterministic prose fallback, mock mobility, synthetic Event, fake booking, or future reservation was counted.

Machine result:

```text
grounded W1 feasible
  -> real cn:glm-5.3-flash inspects Journey/Twin
  -> NO_ACTION + DEFER
  -> W1 skipped without optional spend
  -> independent live recompose/revalidation of the later opportunity
  -> second real AgentRun confirms continue-current-plan
  -> W2 executes
  -> departure executes
  -> Journey COMPLETED
```

The W1 signal was the server-owned `remaining_opportunity_horizon`, not an
external-world event. It was resolved by the typed AgentRun conclusion
`NO_ACTION` with `horizon_decision=DEFER` and reason
`DEFERRED_FOR_HIGHER_VALUE_HORIZON`. No fake `OPPORTUNITY_WINDOW` Event was
created merely to strengthen the receipt.

## Source binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\\moodle\\CityNexus-Revolution-RealTrip-Recovery`
- starting source SHA: `0290fbd88d3958a321bc2610c103f9b811dfb984`
- final experimental SHA: `9a9ef63cf52be2bddff7578998a8192f0716c7d6`
- remote: `origin/codex/revolution-realtrip-recovery`
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- Agent runtime: `HERMES_COMPAT_ENDPOINT`, provider `hermes`, model `cn:glm-5.3-flash`
- model key loaded from local WB2api configuration; credentials were not persisted or printed
- mobility: live Valhalla; no mock mobility counted

The mission compiler receipt remains deterministic
(`mission-compiler-v2-fallback`). That is only the server's bounded mission
envelope. The actual AgentRuns below are persisted as
`provider_key=hermes`, `model_key=cn:glm-5.3-flash`, with real external
model tool calls.

## Fresh Journey and canonical facts

- traveler: `ff3366fa-e5a4-49d2-b683-37132da71126`
- Journey: `46ba31da-e78b-4e34-b449-2bc23f754ad6`
- city: `JP-NARA`
- budget: `10000 JPY`
- declared stay allocation: `8500 JPY`
- optional budget at the horizon decision: `1500 JPY`
- active PlanVersion: `5e1c78f8-f407-4377-9696-dc50adfbfa73`
- final Journey: `COMPLETED`
- final Twin: `READY`, current activity `null`

Real catalog rows:

| Role | Place | Canonical evidence |
| --- | --- | --- |
| completed activity | Nara Park, `real-place-21ab302a8e71729b15395d94` | live Overpass/Nominatim entity; `fee=no`; normalized 24/7 |
| W1 | Isuien, `real-place-22cf72809897ff4c7f312fcf` | live entity; `09:00–16:30`; known `1200 JPY`; Nominatim website tag |
| W2 | Todaiji Museum, `real-place-1ffd66e7224682f5558f1579` | exact provider entity; official source `https://www.todaiji.or.jp/en/information/museum/`; verified opening; known `800 JPY` |

Todaiji's official URL was deterministically bound from its exact provider entity;
it is not claimed as Agent-discovered source evidence.

## Machine preflight

Before the first model call the live Twin exposed:

| Window | Candidate | Cost | Preference fit | Status | Mobility |
| --- | --- | ---: | ---: | --- | --- |
| W1 | Isuien | `1200 JPY` | `0.0` | `GROUNDED` | Valhalla, `FROZEN_PLAN_EVIDENCE` |
| W2 | Todaiji Museum | `800 JPY` | `1.0` | `GROUNDED` | Valhalla, `FROZEN_PLAN_EVIDENCE` |

Each cost was individually within `1500 JPY`, but
`1200 + 800 = 2000 > 1500`; `future_live_traffic=false` was explicit.
The active pointer was unchanged before the model call.

## First real AgentRun: strategic DEFER

- AgentRun: `b87808e2-26c2-4b98-916a-6de81a3eebaf`
- mission: `d03c4860-c09e-4136-a925-5f0a5bc57a0c`
- provider/model: `hermes` / `cn:glm-5.3-flash`
- status: `COMPLETED`
- completion: `kind=NO_ACTION`, `source=server_trace`
- mission text contained no Place ID, correct choice, W1/W2 instruction, DEFER instruction, or tool sequence

Persisted trace: `inspect_journey` -> `inspect_twin` -> typed
`conclude_recovery`. The model reasoned that taking W1 would leave
`300 JPY), preventing the higher-fit `800 JPY) W2. W1 was feasible and was
deliberately left unused.

## W1 and W2

- Nara Park completed through `depart -> arrive -> begin -> complete`.
- W1 Isuien used the public `/skip` endpoint.
- W1 optional spend: `0 JPY); no booking or future reservation.
- Active pointer remained `5e1c78f8-f407-4377-9696-dc50adfbfa73`.

After W1 was skipped, normal `authoritative-compose` created a separate
post-W1 candidate for the remaining real route `Nara Park -> Todaiji Museum)
plus anchors:

- candidate: `eb5831c3-2491-4621-8f4a-b03003790ef2`
- status: `CANDIDATE`, `selectable=true), not active
- snapshot: `v12-authoritative-da0be5081bbc828ade272b0aa4ff90c3`
- capture: `2026-10-04T01:37:56.60465+08:00`
- provider: Valhalla, `LIVE_CAPTURE`
- mode matrix: `24`
- provider-grounded: `true`; synthetic count: `0`
- deterministic gate: `PASSED`
- direct Park -> Museum edge: `6 min AUTO`
- candidate cost: `3200 JPY`

The active PlanVersion frozen snapshot was not overwritten.

## Second real AgentRun

- AgentRun: `af9e0de0-fc02-474a-b0fe-ce762a0522e3`
- mission: `40759a80-0e20-4889-bb67-9c76483e8e76`
- provider/model: `hermes` / `cn:glm-5.3-flash`
- status: `COMPLETED`
- completion: `kind=NO_ACTION`, `source=server_trace`

The model inspected current Todaiji and Twin, saw no truthful actionable event,
a valid cursor, robust feasibility, and live Valhalla hard-eligible mobility.
It chose no plan mutation so the already-authorized current activity could
continue. Its intermediate `list_replans` returned and persisted
`NO_ACTIONABLE_EVENT`/ `TOOL_ERROR`; this was not counted as a replan.

## Final execution and authority state

```text
Nara Park: depart -> arrive -> begin -> complete
Isuien: skip
Todaiji Museum: depart -> arrive -> begin -> complete
departure anchor: depart -> arrive -> begin -> complete
```

Final machine facts:

- Journey `COMPLETED`
- Twin `READY`
- `active_plan_version_id=5e1c78f8-f407-4377-9696-dc50adfbfa73`
- `current_activity_id=null`
- active mobility provider `valhalla`
- active snapshot `v12-authoritative-95fc97a86824e9833554f2205b590261`
- `all_actual_edges_hard_eligible=true`
- W2 exists in execution history as completed

No Gateway activation or PlanVersion pointer mutation was needed after execution
began because W2 was already part of the selected authorized plan. This is an
honest strategic-deferral closure, not a fabricated re-selection.

## Code changes

- Exposed `require_fully_grounded` on authoritative compose.
- Resolved canonical Place IDs carried by Journey anchors before live capture.
- Corrected optional-budget semantics: future activities are candidates, not
  pre-reserved spend; declared stay allocation and consumed activity cost alone
  reduce optional budget.

## Focused tests

Executed with the project Python 3.13 pytest environment:

```text
37 passed, 1 warning
```

Covered:
`test_r21_autonomous_future_synthesis.py`,
`test_r22_opportunity_capture.py`,
`test_r23_adaptive_traveler_twin.py`,
`test_r24_adaptive_memory.py`,
`test_r25_strategic_horizon.py`.

Also passed `python -m compileall -q backend/app` and `git diff --check`.
The initial system-Python 3.10 attempt failed at collection because it lacks
`enum.StrEnum); the supported environment passed.

## Honest limits

- The deterministic mission compiler is not presented as AI.
- W1 was a server-derived horizon signal, not a weather/closure/provider Event.
- Future planning mobility is not future live traffic.
- The independent W2 candidate stayed `CANDIDATE`; active plan was not rewritten.
- No R25 D control was run after C closure.
- P7 remains false; no authority/mainline merge occurred.

## Replay procedure

1. Start a clean disposable DB with WB2api/Hermes-compatible runtime,
   `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`, live real-city discovery, and live Valhalla.
2. Create a fresh traveler/Journey with 10000 JPY budget and 8500 JPY declared stay allocation.
3. Live-discover Nara, bind canonical facts, compose with
   `require_fully_grounded=true), select, start, and complete arrival.
4. Persist explicit museum preference and assert two grounded windows, each
   individually feasible, combined cost over 1500, and
   `future_live_traffic=false`.
5. Run the strategy-neutral Agent command; require persisted
   `NO_ACTION + DEFER`.
6. Complete the current activity, skip W1 through public API, recompose the
   remaining Park -> Museum route with live Valhalla without selecting the
   disposable candidate.
7. Run the second real Agent inspection, then execute W2 and departure through
   `depart/arrive/begin/complete`.
8. Assert Journey `COMPLETED`, Twin `READY`, unchanged active pointer, and
   hard-eligible provider receipts.
