# Revolution R17 — Predictive Self-Healing Journey

## Result

R17 did not reach REVOLUTION_C. The clean runtime reproduced a truthful
LIVE-provider `STABLE` result, but no scheduled outdoor activity overlapped a
forecast at or above the configured predictive threshold. A bounded timing
pivot was attempted through the existing Trip Studio path and was rejected by
the deterministic mobility/travel-gap gate. No weather or closure event was
manually posted, no synthetic forecast was injected, and no preventive replan
was claimed.

This is an exact current blocker, not a `predictive_prevented=true` success.

## Source binding

- Branch: `codex/revolution-realtrip-recovery`
- Base SHA: `36b54545714b4f264a56a65a98e812b29b81ad111`
- R17 experimental commits:
  - `b2ce28211d0c9d4a17cf56795372388797078679` — canonical cost truth in guardian budget checks
  - `cfd21eb052711851cee91b217c6df65490a7c051` — align OpenMeteo risk filtering with configured threshold
- Executed source for the runtime: `cfd21eb052711851cee91b217c6df65490a7c051`
- Estimate authority: `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- Agent runtime configured: `HERMES_COMPAT_ENDPOINT / cn:glm-5.3-flash`
- Guardian signal provider: `open-meteo`
- Mobility provider: `valhalla-http`

## Real runtime attempts

### Active Journey `ef58097f-e4d7-4b20-8ce6-402e6f77f3ec`

- City: Nara, Japan (`JP-NARA`), fresh runtime journey.
- Plan was selected and started.
- Existing plan included the outdoor activities Nara Park and Isuien.
- Guardian Autopilot used the configured `open-meteo` signal provider.
- 12 live polls: `STABLE`, resilience score `28`, no events, no Guardian
  AgentRun, no replan.
- Persisted snapshot:
  - `forecast_risk=0`
  - `status=STABLE`
  - `preventive_recommendation.action=CONTINUE_MONITORING`
  - `risk_reduction_meaningful=false`
- Evidence provenance included live `open-meteo` WEATHER/CITY_SIGNAL and live
  `valhalla-http` MOBILITY observations.

### Active Journey `0a6f6b2d-c78a-48f0-8732-40e8a8253608`

- Same fresh Nara product path, selected and started.
- 10 live polls: `STABLE`, score `28`, no events, no Guardian AgentRun.
- The direct live OpenMeteo hourly probe for the scheduled Nara Park visit
  returned only `32%` precipitation probability at the activity time; the
  daily maximum for the selected date was `67%`, below neither the activity
  time nor the configured threshold in the relevant scheduled window.
- Persisted snapshot again recorded `forecast_risk=0` and
  `CONTINUE_MONITORING`.

## Bounded pivot attempt

Journey: `4ce744f4-46e0-4d3d-af5d-3801f32f2bda`

The existing Trip Studio was used to move Nara Park later in the day so that a
real provider forecast could be decision-relevant. The proposed order was:

1. 奈良学園セミナーハウス志賀直哉旧居
2. 依水園
3. 第一次大極殿復原事業情報館
4. 奈良公園
5. なら工藝館

The deterministic preview rejected the mutation:

- `risk_class=BLOCKED`
- `can_accept=false`
- `UNKNOWN_MOBILITY_COST` on newly required edges
- `INSUFFICIENT_TRAVEL_GAP` for the resulting schedule

Therefore the system did not accept an ungrounded timing change, did not
fabricate edge costs, and did not manufacture a predictive event merely to
exercise the Agent path.

## Exact blocker

The current R17 experiment cannot reach the predictive threshold on the
existing truth-grounded Nara plan because the live forecast is not risky at
the actual scheduled outdoor activity times. The only bounded strategy pivot
that could move the activity into a later forecast window is rejected before
activation by the deterministic mobility/travel-gap gate because the required
new route edges lack canonical mobility cost evidence.

This blocks the required chain at:

```text
live forecast
  -> scheduled activity predictive weakness
```

and independently blocks the attempted repair at:

```text
bounded timing pivot
  -> deterministic Trip Studio feasibility gate
```

No `PREDICTIVE_WEAKNESS`, real Agent `request_replan`, Gateway mutation,
before/after risk reduction, or Journey completion is claimed for R17.

## Narrow legacy-cost repair

The guardian budget regression now reads canonical `cost_evidence` instead of
legacy `metadata_json.cost_minor`. An explicit UNKNOWN canonical cost cannot be
overridden by a legacy zero or non-zero metadata value. Focused tests cover:

- mission-budget overflow requiring confirmation with canonical provider cost;
- legacy metadata cost cannot override canonical cost truth.

## Focused tests

Executed with external Agent credentials disabled so tests cannot accidentally
call a live model:

```text
35 passed, 1 warning in 12.67s
```

Command:

```text
uv run pytest tests/test_guardian_model_evidence.py tests/test_guardian_v4.py tests/test_agent_mission_runtime.py tests/test_r15_source_authority.py -q
```

## Guardrails preserved

- No hand-posted WEATHER/CLOSURE event.
- No synthetic forecast or synthetic mobility relabeled as LIVE.
- No estimate authority used for selection.
- No legacy cost field used as canonical truth.
- No authority/mainline merge.
- No new event bus, predictive framework, or Agent framework.

## Next bounded experiment

Use the same existing R17 runtime on a fresh city/date whose live OpenMeteo
forecast is above the configured threshold during a truth-grounded outdoor
activity window, or first acquire only the missing canonical mobility evidence
for the rejected Trip Studio edges. Then rerun the unchanged predictive
Guardian path and require machine before/after risk reduction before claiming
preventive recovery.
