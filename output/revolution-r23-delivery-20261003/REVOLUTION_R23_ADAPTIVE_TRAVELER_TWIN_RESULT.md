# Revolution R23 — Adaptive Traveler Twin

## Result

R23 reached the intended product path on the isolated LAB database:

```text
real Traveler evidence
  -> LEARNED_SOFT TravelerTwin
  -> causal opportunity ranking change
  -> configured DeepSeek Agent sees the learned context
  -> canonical fact + live Valhalla opportunity candidate
  -> deterministic F4 proposal
  -> Gateway approval/consumption
  -> additive active PlanVersion
  -> HTTP execution of the added Place and protected trip
  -> Journey COMPLETED
```

The learned signal never became hard feasibility, budget, opening, mobility,
commitment, or authority truth. `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` was
used for the positive run. No raw credential is stored in this package.

## Source binding

- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Starting code SHA: `8a7856a98ca32bcfdcc53959fc3db1405a0cebd1`
- Final experimental code SHA: `5f0c69b9bd0ac108eb36dac68a07e50045a29050`
- Estimate authority: `false`
- Signal provider: `open-meteo` (the positive R23 path used a server-derived opportunity window)
- Agent provider/model: `hermes / cn:deepseek-v4.1-flash`
- Runtime endpoint: local WB2API-compatible Hermes endpoint; the key is not included

The GPT taskbook carrier branch was not checked out over this LAB worktree.

## R23 fixes

- Plain `ACTIVITY_COMPLETED` and `ACTIVITY_SKIPPED` no longer imply liking or disliking.
- Explicit feedback is `EXPLICIT_USER_FEEDBACK`; a genuine voluntary choice is
  `VOLUNTARY_CHOICE`; execution telemetry is normally no signal.
- Locked, disruption-forced, no-choice, and replan-removed activities are excluded
  from soft preference learning.
- Learning uses canonical Place category and bounded provider tags, not names.
- Receipts separate hard feasibility, explicit preference contribution,
  learned-soft contribution, and effective fit. `learned_soft_is_authority=false`.
- F4 opportunity insertion validates each candidate independently, including
  canonical opening/cost and two new live mobility legs.
- Opportunity windows below 30 minutes are not actionable.
- English opportunity bounds (`at most` / `up to`, JPY, `minutes`) now reach the
  deterministic mission envelope instead of silently compiling to `0/0`.
- A failed replan attempt does not prevent a typed, server-owned `NO_ACTION`.

## Machine run: learned context and no-action control

The same Traveler was used throughout the learning experiment:

`11111111-1111-4111-8111-111111111111`

Evidence created from a real voluntary choice:

- OutcomeEvent: `a9d4d6df-09d1-4306-8351-57948598f1c2`
- TravelerPreferenceEvidence: `3e7c4d11-2967-4b09-8d59-74ad79ccb403`
- learned dimension/direction: `interest / garden`
- class: `VOLUNTARY_CHOICE`
- strength/confidence: `0.55 / 0.70`
- source: `LEARNED_SOFT`
- expiry: `2027-04-01T04:54:57.993013+08:00`

The earlier ordinary completion path produced no learned preference. Learned
evidence was also cleared once through the product endpoint; explicit
preferences remained, then the voluntary evidence was recreated for the
positive run.

Before learned evidence, Journey B generated museum-first plan
`c7304bd3-0f1c-565e-a84f-30ea873c2e26`. With the same hard facts, the learned
garden signal generated garden-first plan
`c83cf9b6-be00-52a8-848e-bd4f96c92fbc`. Cost remained 2,000 JPY and both
plans used live Valhalla evidence. A temporary explicit museum override
restored museum-first ordering, proving `EXPLICIT > LEARNED_SOFT`; the original
explicit preferences were then restored.

The real-model no-action control was:

- Journey: `57080c98-8844-445b-822a-28ebb96f573f`
- AgentRun: `6f7a8a3c-d778-47b5-941c-1e4ec3e9a5a3`
- Mission: `b659023c-fc84-4ce2-9a27-e43bc95234b8`
- model: `cn:deepseek-v4.1-flash`
- tool path: `inspect_journey -> inspect_twin -> list_replans -> conclude_recovery`
- result: typed `NO_ACTION`, active plan unchanged (`5509823c-dfb7-5023-95f8-ccd770253061`)
- learned context was present in the `inspect_twin` receipt

## Positive product run

### Journey and base reality

- Journey: `f7f23556-29f0-4214-a69c-edb126d78d32`
- initial active PlanVersion: `69ee3bd6-a5ba-5547-9e15-d61c0228056a`
- C4 commitment: `70014a3d-6b12-443b-ad91-815702aeec46`
- current event: `ba0f737c-3277-4399-b711-816e640b6c77`
- event type/provenance: `OPPORTUNITY_WINDOW / SYSTEM_DERIVED`
- window: 383 minutes, next protected commitment at 15:00 local
- standing mission: `ff28b1aa-8346-485e-9df0-8f3fc3a9d235`
- scan: `077cf416-f895-45dc-9913-87617375b2d7`

The mission contained no Place ID, action recipe, target approval ID, or tool
sequence. It required canonical facts and live mobility, forbade estimates and
UNKNOWN facts, and bounded the change to 1,000 JPY and 120 minutes. The
compiled server envelope recorded:

```json
{"max_cost_delta_minor":1000,"max_schedule_drift_min":120}
```

### Real Agent decisions

- AgentRun: `5faf3952-a8f2-4e7a-bda8-82969b9b1a74`
- controller: `configured_agent_runtime`
- provider/model: `hermes / cn:deepseek-v4.1-flash`
- ordered tools:
  `inspect_journey -> inspect_twin -> list_replans -> search_city_services -> generate_plans -> generate_plans -> request_replan -> accept_replan -> conclude_recovery`
- the first `generate_plans` attempt was a machine-visible tool error; the Agent
  adapted and retried through the same product tool surface
- estimated facts were not used in the successful candidate evaluation

The Agent selected the only grounded new culture candidate it could prove:

- Place: `奈良市杉岡華邨書道美術館`
- Place ID: `real-place-d8820981440574ee50a0c1d5`
- opening: `OFFICIAL_WEB_VERIFIED`, 09:00–17:00
- cost: `VERIFIED_PROVIDER`, 300 JPY
- candidate search did not treat a Place ID as authority

The Agent requested proposal `60df1c63-1f98-4f1d-b023-5f4555bdd75e`:

- family: `F4_OPPORTUNITY_INSERTION`
- parent: `69ee3bd6-a5ba-5547-9e15-d61c0228056a`
- proposed child: `46192c7d-01b7-4b49-94b8-4a3ffe4060f0`
- `hard_constraints_passed=true`
- `locked_commitments_preserved=true`
- cost delta: 300 JPY
- schedule drift: 0 minutes at journey end
- new Place added: 1
- old active PlanVersion remained active until approval

Gateway first returned `REQUIRE_CONFIRMATION`, then the product approval
endpoint approved receipt `f52511ad-1a39-44d8-b5a5-042b7b4e6830`. The subsequent
Agent Gateway `accept_replan` call consumed that exact server-issued receipt:

- reason codes: `IMPACT_TARGET_NOT_SERVER_VALIDATED`,
  `USER_APPROVAL_RECEIPT_CONSUMED`
- `executed=true`
- proposal status: `ACCEPTED`
- old plan superseded; new plan active

This is an approval-boundary success, not a direct database pointer write.

### Mobility and eligibility

Final frozen mobility snapshot: `67572a8a-058d-4307-9031-9ddfaa799f32`.

Provider: `valhalla-http`; provenance: `LIVE_PROVIDER_CAPTURE`; degraded: false.
The final active route used exactly these edges:

| from | to | minutes | decision |
|---|---|---:|---|
| `real-place-22cf72809897ff4c7f312fcf` | `real-place-d8820981440574ee50a0c1d5` | 21 | `HARD_ELIGIBLE` |
| `real-place-d8820981440574ee50a0c1d5` | `real-place-1ffd66e7224682f5558f1579` | 27 | `HARD_ELIGIBLE` |
| `real-place-1ffd66e7224682f5558f1579` | `real-place-b47a20314c81d5a81381d4a4` | 26 | `HARD_ELIGIBLE` |

All actual used edges were hard-eligible. No mock mobility, synthetic fixture,
or fabricated `used_edge_ids` was used.

### Execution and convergence

The additive plan executed through the real HTTP state machine:

```text
依水園 -> 杉岡華邨书道美术馆 -> 东大寺博物馆 -> なら工藝館
depart -> arrive -> begin -> complete for each activity
```

Final machine state:

- `Journey.status=COMPLETED`
- `Journey.active_plan_version_id=46192c7d-01b7-4b49-94b8-4a3ffe4060f0`
- `Journey.current_activity_id=null`
- `JourneyTwin.status=COMPLETED`
- `JourneyTwin.active_plan_version_id=46192c7d-01b7-4b49-94b8-4a3ffe4060f0`
- `JourneyTwin.projection_status=READY`
- all four final activities `COMPLETED`
- C4 destination remained in the final plan and was executed

## Focused verification

```text
py -3.13 -m pytest -q \
  tests/test_foundation_opportunity_window.py \
  tests/test_r20_standby_trigger.py \
  tests/test_r21_autonomous_future_synthesis.py \
  tests/test_r22_opportunity_capture.py \
  tests/test_r23_adaptive_traveler_twin.py \
  tests/test_v7_traveler_twin.py \
  tests/test_v19_traveler_capability.py \
  tests/test_agent_mission_runtime.py -s
```

Result: **70 passed, 1 existing Starlette/httpx deprecation warning**.

Additional checks:

- `py -3.13 -m py_compile` on all changed Python modules: passed
- `git diff --check`: passed

## Replay

1. Use the isolated worktree and final code SHA above.
2. Point `CITYNEXUS_DATABASE_URL` at a disposable SQLite database.
3. Configure WB2API through the existing local config path as
   `CITYNEXUS_HERMES_API_URL` + `CITYNEXUS_HERMES_API_KEY`; do not copy the key
   into the repository or package.
4. Set `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` and
   `CITYNEXUS_LIVE_VALHALLA_URL=https://valhalla1.openstreetmap.de`.
5. Create the fresh Nara Journey, import the structured C4 anchor, generate and
   select the grounded base plan, then start and begin the first activity.
6. Install the strategy-neutral standing mission used above and run Guardian
   scan. Inspect the persisted AgentRun, proposal, approval, live mobility
   snapshot, and final Twin.
7. Approve only the server-issued approval receipt through the product approval
   endpoint, then consume it with the Agent Gateway `accept_replan` tool.
8. Run the ordinary HTTP execution transitions for every final activity and
   verify Journey/Twin convergence and the three `used_edge_ids` above.

## Honest limitations

- This is a disposable LAB database with future-dated Nara activities; it did
  not mutate real-user data or perform real payment.
- Valhalla route capture is live provider capture but reports no live traffic
  signal in this run; that does not turn the routes into mock evidence.
- The deterministic impact resolver remained a fallback for this opportunity;
  the autonomous part was the configured model's inspection, search, candidate
  rejection/selection, and request/accept decision. Deterministic truth gates
  remained final authority.
- The earlier approval-pending run is preserved as machine history; the final
  positive run is the post-parser-reload run identified above.

## Closure

R23 is closed at the intended product level: CityNexus learned cautiously from
real voluntary evidence, changed a later hard-feasible opportunity ranking,
let a configured Agent decide whether to use a real opportunity, required and
consumed normal authority approval, and completed the revised Journey without
turning learned soft evidence or estimated facts into truth.
