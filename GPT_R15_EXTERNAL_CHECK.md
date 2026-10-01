# GPT external check — R15 -> R16

Inspected result: `REVOLUTION_R15_TRUTH_SEEKING_OPERATOR_RESULT.md`
Verified code checkpoint: `fc6a6d61224084c3a6e4489ca03f99948ea462b3`

## What R15 genuinely moved

R15 crossed an important boundary:
- estimate authority was off;
- exact Nominatim/Photon OSM identities can now re-enter exact Overpass/Nominatim enrichment;
- canonical opening/cost can be promoted from exact provider-backed facts;
- real PlanVersion became selectable;
- live Valhalla used-edge evidence remained hard eligible;
- the Journey selected, started, recovered, and completed.

This is materially beyond R14's estimate-envelope success.

## What R15 did NOT yet prove

The report itself is explicit:
- the disruption was operator-reported;
- deterministic recovery generated the proposal;
- the native AgentRun that preceded fact acquisition did not autonomously call `request_replan` after the closure.

Therefore R15 is truth-seeking autonomy before execution, plus deterministic recovery during execution. It is not yet an event-driven autonomous operator.

## Existing product architecture already contains the next capability

Do not invent a new event bus.

Current `app.agent.guardian` and `app.agent.autorun` already provide:
- standing Journey missions;
- actionable event filtering for WEATHER/CLOSURE/TRAFFIC_DELAY/SCHEDULE_DELAY;
- Guardian pulses and persisted cooldown/idempotency;
- recovery child-mission compilation from live events;
- configured model runtime execution;
- model tool-trace extraction for `request_replan` and `accept_replan`;
- deterministic fallback only when the configured runtime is unavailable;
- periodic Autopilot enrollment/provider mesh.

R16 should wire/prove these existing pieces on top of the R15 truth path, not build another subsystem.

## Critical proof rule

Guardian has a deterministic fallback that can leave a trace resembling an autonomous run:
- provider/model: `citynexus-guardian / deterministic-recovery-controller-v1`;
- tools may include `inspect_twin -> request_replan -> accept_replan`.

That is useful resilience, but it is NOT evidence for R16 native autonomy.

R16 success must prove:
- Guardian evidence `controller=configured_agent_runtime`;
- AgentRun provider/model is the actual configured domestic model (GLM/DeepSeek or another explicitly configured real runtime);
- the model-selected tool trace itself contains `request_replan`;
- if acceptance is automatic, the model trace contains `accept_replan` and Gateway policy permits it;
- if Gateway requires confirmation, the model must stop at proposal/policy boundary and the human approval receipt remains explicit.

Do not relabel deterministic fallback as Agent success.

## Event truth boundary

The Agent should not invent the disruption fact.

Acceptable trigger sources:
- real provider observation/event;
- Guardian live weather/mobility signal;
- explicit user/operator-reported real-world observation with provenance recorded as such.

The event may wake the Agent. The Agent may decide recovery strategy. The Agent may not fabricate the closure/weather/traffic event.

## Evidence note

The uploaded R15 result is a report, not a complete raw-receipt package. GitHub confirms the fc6 code repair and the relevant Guardian/runtime code exists. R16 should produce compact raw receipts for its single success run, but do not turn this into another evidence-only round.
