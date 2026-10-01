# Revolution R18 — Anticipatory Resilience OS

## Result

R18 reached REVOLUTION_B on a healthy ACTIVE Journey without waiting for bad
weather:

```text
LIVE OpenMeteo + LIVE Valhalla
  -> healthy ACTIVE Journey
  -> bounded counterfactual
  -> on-demand/independent mobility evidence
  -> deterministic feasibility
  -> NON_ACTIVE CANDIDATE Shadow Plan
```

No active PlanVersion was changed and no synthetic weather event was posted.
The live forecast remained below the predictive threshold, so no Agent/Gateway
activation was claimed.

## Source binding

- Branch: `codex/revolution-realtrip-recovery`
- R18 base SHA: `d637e0546b98ae377dc16a9363894b72eedda2d7`
- R18 final SHA: `7a5f4eced3fb85b5fa98d1a8953078a97c310c37`
- Taskbook blob SHA: `2f94a1600a14ab15b3eb552bdc83271030f93fbb`
- Estimate authority: `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- Agent runtime: `HERMES_COMPAT_ENDPOINT / cn:glm-5.3-flash`
- Guardian signal provider: `open-meteo`
- Mobility provider: `valhalla-http`

## Healthy Journey proof

Journey:

```text
0a6f6b2d-c78a-48f0-8732-40e8a8253608
```

Active PlanVersion before and after standby preparation:

```text
da5a39b5-a273-588d-8266-af5610bf7c70
status=SELECTED
```

The live resilience snapshot reported:

```text
status=STABLE
risk_score=28
forecast_risk=0
threshold=65
provider=open-meteo
mobility_provider=valhalla-http
```

The persisted weather and mobility observations were both `LIVE_PROVIDER`.
The Journey stayed healthy while the standby was prepared.

## Shadow Plan proof

The existing bounded `rain_earlier` counterfactual produced:

```text
CounterfactualSimulation = 881dd640-5e3c-4f4c-8fdd-108596b4ab9e
scenario_type = WEATHER_SHIFT
feasible = true
c4_preserved = true
```

Materialized standby:

```text
PlanVersion = e7d5201b-e3d2-49a7-b383-4a71bd7d3546
status = CANDIDATE
is_current = false
parent_plan_version_id = da5a39b5-a273-588d-8266-af5610bf7c70
lifecycle = NON_ACTIVE_STANDBY
mobility_snapshot_id = bb702085-815e-4b81-b499-dd6dcc9a2946
```

The standby retained canonical Place facts, preserved the protected
commitment policy, and passed deterministic feasibility against its own
mobility evidence. The active Journey pointer remained unchanged.

## Evidence-on-demand Trip Studio

For Journey `4ce744f4-46e0-4d3d-af5d-3801f32f2bda`, the reordered hypothetical
plan requested new/unknown directed edges. The preview path captured a separate
mobility snapshot:

```text
preview_id = 525e6423-484f-52be-8aa7-07a6a198f097
preview_snapshot_id = 69710e17-4c7c-41bd-8041-25b79b7a9b86
provider = valhalla-http
route_provenance = LIVE_PROVIDER_CAPTURE
fact_quality = LIVE_PROVIDER_CAPTURE
```

The base PlanVersion snapshot was not extended or rewritten. The preview used
explicit `KNOWN_FREE` only for provider-confirmed `WALK` facts; no paid/unknown
cost was converted to zero.

The deterministic gate then failed honestly on:

```text
INSUFFICIENT_TRAVEL_GAP:
real-place-22cf72809897ff4c7f312fcf -> real-place-470b4d1080037ab7f7e9b562
real-place-470b4d1080037ab7f7e9b562 -> real-place-21ab302a8e71729b15395d94
```

This is evidence-on-demand working as intended: missing mobility truth was
acquired, then the real gate—not the old frozen matrix—made the decision.

## Forecast-aware behavior

The live provider reading was preserved as a source-backed signal:

```text
provider = open-meteo
observation = LIVE_PROVIDER WEATHER/CITY_SIGNAL
forecast_risk = 0
scheduled outdoor exposure = present in the active plan
threshold relation = 0 < 65
decision = CONTINUE_MONITORING + maintain standby
```

Because the provider did not cross threshold, R18 intentionally did not wake a
real Agent or activate a standby plan. This is a safe-state proof, not a
weather-trigger closure.

## Implementation changes

- Trip Studio now detects missing/stale/UNKNOWN-cost edges for a hypothetical
  order.
- It calls the existing runtime mobility capture path only for those edges.
- It persists the result as a `CounterfactualSimulation` mobility preview bound
  to base PlanVersion, draft order, and independent snapshot ID.
- Preview acceptance reuses that exact persisted snapshot and never recaptures
  or rewrites the active frozen evidence.
- `WALK` is `KNOWN_FREE` only when live provider fact quality is explicit;
  unknown paid modes remain blocking.
- Healthy counterfactuals can materialize one bounded `CANDIDATE` PlanVersion
  with explicit `NON_ACTIVE_STANDBY` lifecycle and a new evidence snapshot.

## Focused verification

```text
35 passed, 1 warning
```

Command:

```text
uv run pytest tests/test_guardian_model_evidence.py tests/test_guardian_v4.py tests/test_agent_mission_runtime.py tests/test_r15_source_authority.py -q
```

Additional runtime checks:

- live Trip Studio preview created an independent snapshot;
- preview gate rejected insufficient travel gaps;
- active plan pointer remained unchanged;
- Shadow Plan was persisted as `CANDIDATE` and `is_current=false`;
- no manual WEATHER/CLOSURE event was used.

## Remaining frontier

R18 C/D remains open. The current safe-state run proves live forecast-aware
standby preparation, but not a threshold-crossing Agent activation. A future
live provider signal may exercise the existing Guardian/Agent/Gateway path; the
absence of such a signal is not repaired by manufacturing one.
