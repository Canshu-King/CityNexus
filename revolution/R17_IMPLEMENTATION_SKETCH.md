# R17 implementation sketch — shortest path

## 1. Use the code that already exists

The shortest path is already present:

```text
OpenMeteo provider
 -> weather_runtime provider-verified Event
 -> autorun._live_weather_refresh
 -> build_resilience_snapshot
 -> PREDICTIVE_WEAKNESS
 -> simulate_counterfactuals
 -> run_preemptive_guardian
 -> _model_recovery
 -> configured Agent runtime
 -> request_replan
 -> Gateway
```

Do not replace it.

## 2. First inspect why the preemptive path has not been used in a real run

High-value checkpoints:
- `settings.guardian_signal_provider` points to live/open-meteo;
- forecast attribution reaches a future activity;
- Event payload carries `predictive_only=true`;
- provider provenance is `PROVIDER_VERIFIED` / live capture;
- forecast risk exceeds `settings.predictive_risk_threshold`;
- resilience snapshot becomes `PREDICTIVE_WEAKNESS`;
- signal result is not degraded;
- standing mission exists before the pulse;
- configured model runtime is available.

Patch only the smallest missing link.

## 3. Avoid chasing weather forever

Use a bounded city-selection loop:
- inspect live OpenMeteo forecast for candidate fresh cities;
- choose a city with a qualifying future precipitation risk and real mixed indoor/outdoor catalogue;
- cap attempts.

Do not fabricate provider conditions.

## 4. Strengthen prevention proof

Current code can mark `predictive_prevented` after execution.

Add/record stronger proof:
- pre-snapshot ID/score/activity risk;
- active plan before;
- accepted replacement;
- recomputed post-snapshot;
- target exposure before/after;
- protected commitment result.

A simple deterministic comparison is enough. Do not create a new ML risk model.

## 5. Repair the stale cost test with the current contract

Update `test_guardian_over_mission_budget_requires_confirmation` to populate the same canonical cost evidence consumed by current planning/recovery.

Add one test proving legacy `metadata_json.cost_minor` alone cannot overwrite canonical price truth.

Then stop touching cost code unless R17 reveals a real product bug.

## 6. Model trace contract

For final success:
- real AgentRun provider/model;
- inspect Journey/Twin;
- model-selected `request_replan`;
- model-selected `accept_replan` only if policy allows;
- deterministic fallback excluded.

If model repeatedly returns final prose instead of a tool call, tighten the recovery mission prompt/context. Do not hardcode the tool call in the wrapper.

## 7. Finish with product behavior, not test counts

Once one predictive preventive plan is accepted:
- recompute risk;
- finish the revised Journey;
- produce one compact report.

Do not spend the remaining time building another evidence layer.
