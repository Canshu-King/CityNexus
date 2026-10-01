# Revolution R17 — Predictive Self-Healing Journey

## Why R17 exists

R15 taught CityNexus to seek truth.
R16 taught it to wake after reality already broke the plan.

R17 must teach it to act before the break.

The target product behavior is:

```text
truth-grounded ACTIVE Journey
  -> live provider forecast/observation arrives
  -> future activity becomes predictively weak, not yet failed
  -> resilience snapshot records PREDICTIVE_WEAKNESS
  -> bounded counterfactuals quantify the risk/alternatives
  -> Guardian wakes a real configured Agent
  -> Agent inspects Journey/Twin/predictive evidence
  -> Agent chooses preventive request_replan
  -> deterministic solver + Gateway validate
  -> bounded replacement plan activates
  -> recomputed exposure/risk is materially lower
  -> revised Journey continues to COMPLETED
```

This is a product species change:
reactive recovery -> anticipatory self-healing.

## Hard truth boundaries

For the R17 success run:
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`;
- initial and replacement used Places must satisfy canonical authority facts;
- used mobility must remain real/provider-backed;
- forecast/event must come from a provider path, not model prose;
- model may choose strategy, but cannot invent weather, mobility, opening, cost, or approval.

## Phase 0 — small contract cleanup only

Fix the stale Guardian cost regression before or during R17 if it blocks the focused suite.

The failing fixture currently writes legacy `metadata_json.cost_minor`.

Required:
- mutate canonical cost evidence instead;
- prove recovery cost delta reads the current canonical contract;
- prove legacy metadata cannot override canonical cost truth.

Timebox this. Do not let one historical fixture consume the Revolution round.

## Phase A — fresh mixed indoor/outdoor real trip

Use a fresh disposable Journey in a city not used as the R16 final proof.

Requirements:
- at least one future outdoor/scenic activity;
- at least one viable indoor/low-exposure alternative;
- canonical opening/cost truth;
- live/provider mobility;
- selected and ACTIVE plan;
- standing Guardian mission with explicit bounds.

Do not hand-author the exact preventive answer.

## Phase B — provider-native predictive trigger

Prefer the existing live OpenMeteo path.

The provider observation must create or update a real weather Event attributable to a future activity.

R17 final proof must NOT use an operator-posted WEATHER/CLOSURE event.

If the first city has no qualifying live forecast:
- timebox it;
- pivot to another fresh city whose live provider forecast exceeds the configured predictive threshold;
- do not fake rain.

A captured provider replay may be used only for debugging, not final R17 success.

## Phase C — deterministic predictive evidence first

Before any mutation, persist:
- provider observation;
- weather Event ID;
- event provenance;
- affected activity;
- resilience snapshot;
- `status=PREDICTIVE_WEAKNESS`;
- forecast risk score and threshold;
- dominant failure mode;
- counterfactual simulations.

Counterfactuals remain bounded/heuristic when probabilities are unavailable. Do not claim statistical certainty the provider did not supply.

## Phase D — real model chooses preventive action

The success GuardianRun must use:
- `controller=configured_agent_runtime`;
- actual configured GLM/DeepSeek/Hermes-compatible runtime;
- persisted AgentRun/AgentRunStep.

Required model behavior:
1. inspect Journey;
2. inspect Twin;
3. inspect/list the predictive trigger or enough live state to understand it;
4. decide that prevention is warranted;
5. call `request_replan` with the predictive event.

Do not hardcode the wrapper to always request a replan merely because `PREDICTIVE_WEAKNESS` exists.
The model must retain the option to choose NO_ACTION when the forecast does not materially threaten the mission.

## Phase E — prevention must be objectively better

Do not accept "mutation executed" as proof.

After the proposed/accepted preventive replan, recompute deterministic evidence.

R17 success requires at least one of:
- targeted weather-exposed activity removed;
- activity moved outside the provider risk window;
- replacement activity is indoor/less exposed;
- protected commitment slack materially improves;
- route/mobility buffer materially improves.

And require a before/after comparison:
- pre-action resilience/exposure;
- post-action resilience/exposure;
- exact activity/plan change;
- cost delta;
- schedule drift;
- protected commitments preserved.

If the post-action plan does not reduce the actual provider-linked risk, the Agent chose badly. Reject or pivot.

## Phase F — Gateway authority stays in charge

Valid outcomes:
- `ALLOW_AUTO` inside the standing mission + traveler policy envelope;
- or explicit approval if policy requires it.

Do not lower policy limits simply to claim autonomy.

If the model proposes an over-budget or high-drift preventive plan:
- deterministic policy rejects/holds it;
- Agent may choose a safer alternative.

That is healthy Revolution behavior.

## Phase G — complete the revised trip

After prevention:
- continue through real execution states;
- Journey must reach `COMPLETED`;
- final Twin agrees with the active replacement plan;
- original plan, predictive Event, resilience snapshot, counterfactuals, AgentRun, GuardianRun and lineage remain persisted.

## Phase H — do not confuse fallback with autonomy

Deterministic Guardian fallback remains valuable resilience.

But it does not count as R17 native autonomy.

Final success must prove:
- configured model provider/model;
- model-selected `request_replan`;
- no `deterministic-recovery-controller-v1` success substitution.

## Aggressive stretch — dual-signal prevention

If time remains after one real predictive closure:
- add mobility-buffer pressure from live Valhalla/provider observations into the preventive decision;
- show the Agent choosing between weather exposure and route-delay risk.

Do not build a new prediction framework. Reuse current resilience components and counterfactual machinery.

## Anti-ORD rules

- one capability branch;
- one result report;
- inline blocker fixes;
- no micro-ORDs;
- no report-only recut;
- no "one more reactive closure" as progress;
- no manually injected final predictive event;
- no spending the round tuning evidence formatting.

## Success levels

### REVOLUTION_A — provider-native prediction
Live provider observation creates predictive evidence and `PREDICTIVE_WEAKNESS` on an ACTIVE real Journey.

### REVOLUTION_B — model-selected prevention
REVOLUTION_A + real configured model chooses `request_replan` before hard failure.

### REVOLUTION_C — measurable self-healing
REVOLUTION_B + governed plan mutation + deterministic before/after risk reduction + revised Journey COMPLETED.

### REVOLUTION_D — multi-signal anticipation
REVOLUTION_C + the same engine demonstrates prevention using a second independent live signal class (for example mobility-buffer deterioration) without city-specific logic.

Target C. Push for D only after C is real.

## Final report

One file:

`REVOLUTION_R17_PREDICTIVE_SELF_HEALING_RESULT.md`

Include:
- base/final SHA;
- fresh city/Journey;
- initial canonical fact and live mobility provenance;
- standing mission/policy bounds;
- provider observation ID;
- predictive Event ID/provenance;
- pre-action resilience snapshot;
- counterfactuals;
- GuardianRun;
- actual Agent provider/model;
- ordered model-selected tools;
- request_replan receipt;
- proposal/policy/approval;
- old/new PlanVersion;
- before/after exposure/risk;
- final Journey/Twin;
- focused tests and candidate-vs-base delta;
- any deterministic fallback, clearly separated from success evidence.

## Success sentence

R17 closes when this becomes a machine fact:

> Before a real trip actually failed, a live provider forecast exposed a material weakness, CityNexus predicted the risk, a real model chose a preventive recovery, deterministic authority approved a demonstrably safer plan, and the revised Journey completed.
