# R16 shortest implementation path

## 1. Start from existing Guardian, not a new event system

The shortest path already exists:

```text
Event(DETECTED)
 -> scan_guardian / Guardian pulse
 -> _recovery_mission
 -> configured_journey_agent().run(...)
 -> persisted AgentRun
 -> model tool trace
 -> request_replan
 -> optional accept_replan
```

First prove why R15's native Agent did not choose `request_replan` after closure. Likely areas:
- recovery mission prompt/tool context did not make the trigger sufficiently salient;
- model context included too much unrelated planning data;
- runtime stopped after a final-text turn before using request_replan;
- standing mission autonomy did not permit the intended action.

Patch the smallest cause.

## 2. Do not let deterministic fallback satisfy acceptance

`guardian.py` intentionally falls back to `_deterministic_recovery` on `AgentRuntimeUnavailable`.

Keep that behavior for resilience.

But mark/verify final proof using:
- Guardian evidence controller;
- AgentRun provider_key/model_key;
- tool steps.

The successful R16 run must be the configured model path.

## 3. Use the standing mission correctly

The standing mission is already copied into a recovery child mission with:
- trigger_event_id;
- protected activity IDs;
- mutable activity IDs;
- autonomy bounds;
- resolved intent.

Make sure the runtime prompt exposes the trigger event and asks the model to inspect live state before choosing a recovery tool.

Do not hardcode "always request_replan". The model should be able to decide NO_ACTION if the event is irrelevant.

## 4. Event provenance remains external truth

Do not add a model tool that simply invents CLOSURE/WEATHER facts.

If using a user/operator posted event:
- preserve provenance as user/operator observation;
- the Agent's role begins after event persistence.

If live Guardian provider signals can generate the event naturally, prefer that for REVOLUTION_D.

## 5. Real model trace contract

High-value regression:
- actionable closure + standing mission + configured fake model script
  -> inspect_journey
  -> inspect_twin
  -> request_replan
  -> proposal;
- policy allow path can accept;
- confirmation path stops at explicit approval;
- runtime unavailable path is labeled fallback and cannot be mistaken for native success.

Then immediately run a real GLM/DeepSeek scenario.

## 6. Keep R15 truth boundary intact

Replacement candidates must never regress to:
- estimate-authority selection;
- Agent-supplied URL self-approval;
- synthetic mobility;
- unknown-as-free/open.

If the best replacement lacks facts, Agent can acquire/corroborate or choose another candidate.

## 7. Autopilot proof

For final run:
1. create fresh truth-grounded active Journey;
2. activate standing Guardian mission;
3. enroll/start Autopilot;
4. persist or capture actionable event;
5. wait only within a bounded deadline for a Guardian pulse/run;
6. inspect GuardianRun/AgentRun;
7. continue execution after accepted replan.

If Autopilot scheduling is flaky, fix that boundedly. Do not replace it with another worker architecture.
