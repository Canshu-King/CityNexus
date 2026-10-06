# REVOLUTION R36 — Adaptive Journey Watch

## Starting truth

R35 is complete for its actual live result and must not be rewritten.

Accepted historical facts:
- R33-1 remains honestly `BLOCKED`.
- R34 remains `NO_MATERIAL_CHANGE`.
- R35 source/result head is `268198a02b58b7ebf59677f2d0954559fa92063b`.
- R35 used exactly one bounded live Guardian pulse on Journey `70b48ebc-991d-4708-bfbb-264e94e09103`.
- GuardianPulse `03e09fbb-6bd5-4cb3-be9d-f3b49c032f2e` captured live weather, mobility and venue context.
- both real provider-bound venues were `OPEN_COMPATIBLE`;
- live context produced no material conflict and no Journey mutation;
- final active plan stayed unchanged;
- the historical pulse also saw an older R28 `OPPORTUNITY_WINDOW`, causing one unrelated external AgentRun with `MODEL_NO_ACTION`; the receipt preserves this honestly.
- commit `268198a02...` corrected the product boundary so bounded live pulses exclude opportunity signals from disruption recovery.
- do not rerun R33, R34 or R35 and do not reinterpret their outcomes.

R35 proved that CityNexus can perform one coherent reality check. R36 must stop treating that capability as a button or a blind fixed timer.

## Revolution objective

Turn Guardian Autopilot into an **Adaptive Journey Watch**.

A living travel companion should not poll the world at one fixed cadence forever. It should know when the next meaningful part of the Journey is approaching, when a real unresolved incident exists, when evidence is degraded, and when the trip is quiet enough to stay quiet.

R36 should make the standing Guardian mission behave like a durable watch subscription:

> “Keep an eye on this trip for me.”

The system then decides **when the next live check is justified** from server-owned Journey state. It must be more alert near an upcoming activity or unresolved material incident, quieter when nothing important is near, and transparent about why the next check is scheduled.

This is a product capability, not a scheduler benchmark.

## Existing product surface to extend

Use the current implementation:
- `backend/app/agent/autorun.py`
- `AutopilotEnrollment`
- `GuardianPulse`
- standing `JourneyMission`
- current live provider mesh from R35
- `POST /api/v1/journeys/{journey_id}/guardian/autopilot/start`
- `POST /api/v1/journeys/{journey_id}/guardian/autopilot/stop`
- `GET /api/v1/journeys/{journey_id}/guardian/autopilot/status`
- Live Recovery / Guardian status surface

Do not create a second worker or another Guardian subsystem.

## A. Server-owned adaptive cadence

Add one deterministic policy that computes the effective watch cadence from current Journey truth.

The first R36 policy should remain deliberately small and explainable.

Suggested policy bands:

1. **INCIDENT_ACTIVE**
   - there is an unresolved non-predictive material disruption Event relevant to the active Journey;
   - exclude `OPPORTUNITY_WINDOW`;
   - target cadence: no slower than 60 seconds.

2. **APPROACHING**
   - next non-terminal planned activity begins within 2 hours;
   - target cadence: no slower than 5 minutes.

3. **TODAY**
   - next non-terminal planned activity begins within 8 hours;
   - target cadence: no slower than 15 minutes.

4. **DAY_AHEAD**
   - next non-terminal planned activity begins within 24 hours;
   - target cadence: no slower than 30 minutes.

5. **QUIET**
   - no unresolved material incident and next meaningful activity is farther away;
   - use the enrollment's configured interval.

Backward compatibility rule:

`AutopilotEnrollment.interval_seconds` remains the traveller/operator's maximum requested interval. The adaptive policy may shorten that interval when Journey state demands more attention, but must never silently make checks less frequent than the configured interval.

This avoids a schema migration in R36 and preserves existing explicit interval behavior.

For the normal user-facing Watch toggle, it is acceptable for the UI/API to choose a calmer default enrollment interval (for example one hour) while tests and explicit callers can still provide a shorter interval.

Do not use model reasoning to choose cadence. This is deterministic server policy.

## B. Event-aware wake-up

A fixed “time since last pulse” check is insufficient.

If a new qualified material Event is persisted after the previous pulse, the Journey should become due immediately on the next worker wake, even if its normal interval has not elapsed.

Requirements:
- only persisted server-visible Events count;
- `OPPORTUNITY_WINDOW` must not wake disruption recovery;
- predictive-only Events must not masquerade as present disruption;
- resolved Events must not keep the Journey urgent;
- a stale historical Event older than the last pulse must not continuously force immediate due state.

This is scheduling urgency only. It does not grant mutation authority.

## C. First-class watch status

Expose a compact server projection in Guardian Autopilot status:

- `watch_state`: one of `QUIET`, `DAY_AHEAD`, `TODAY`, `APPROACHING`, `INCIDENT_ACTIVE`;
- `effective_interval_seconds`;
- `next_due_at` when calculable;
- `next_activity_id` and start time when that activity drives cadence;
- `reason_code` as a stable server/debug value;
- latest pulse time/status;
- latest provider degradation flag if available.

Do not expose raw Event payloads or internal authority details merely to explain scheduling.

The status must be derived from current persisted Journey state, not copied from a previous response.

## D. Traveller-facing “Guardian is watching”

Extend the existing Live Recovery/Guardian surface.

When Autopilot is enrolled, the traveller should be able to understand:

- Guardian Watch is on;
- last checked time;
- what broad reason determines the current watch intensity;
- roughly when the next check is expected;
- whether the latest check was all clear, incomplete, or in recovery.

Use ordinary language, for example:
- “守护中 · 下一项安排还早，会低频检查。”
- “两小时内有行程，已提高检查频率。”
- “发现未解决的实时问题，正在密切关注。”

Do not show seconds-level countdowns by default.
Do not show enum names, Event ids, GuardianRun ids, or policy codes in normal UI.

Provide a clear off control using the existing stop endpoint. Do not trap the traveller in monitoring.

## E. No Agent for scheduling

Adaptive scheduling itself must never:
- create an AgentRun;
- create a proposal;
- create a RecoveryEpoch;
- mutate a plan.

Only a later due Guardian pulse may discover or act on real disruption through the existing R35 path.

A change from QUIET to APPROACHING is not a disruption.

## F. Product invariants inherited from R35

Keep all R35 truth boundaries:
- exact provider-bound venue evidence;
- full activity-interval containment for opening hours;
- UNKNOWN/DEGRADED is not closure;
- `OPPORTUNITY_WINDOW` stays outside bounded disruption pulse recovery;
- live-world material conflict requires configured external Agent;
- no deterministic recovery fallback for R34+ live-world conflicts;
- at most one legal Journey mutation per incident closure;
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` for any live proving closure.

## Narrow verification

Before any R36 live closure, add focused tests for at least:

1. no enrollment => no watch scheduling;
2. explicit configured interval remains the maximum interval;
3. >24h / quiet Journey uses configured interval;
4. next activity within 24h => DAY_AHEAD;
5. next activity within 8h => TODAY;
6. next activity within 2h => APPROACHING;
7. unresolved material CLOSURE/WEATHER/TRAFFIC/SCHEDULE event => INCIDENT_ACTIVE;
8. `OPPORTUNITY_WINDOW` does not create INCIDENT_ACTIVE and does not force immediate disruption watch;
9. predictive-only Event does not create INCIDENT_ACTIVE;
10. resolved Event does not create INCIDENT_ACTIVE;
11. material Event newer than `last_pulse_at` makes the enrollment due immediately on the next worker cycle;
12. old Event before `last_pulse_at` does not force repeated immediate cycles;
13. schedule-state calculation creates no AgentRun/proposal/mutation;
14. autopilot status exposes `watch_state`, effective interval and next due projection;
15. existing R35 pulse opportunity-isolation regression remains green;
16. frontend Watch state + stop control narrow test;
17. frontend typecheck.

Do not run the full historical evidence suite by default.

## One bounded R36 live closure

Use a new/clean Journey. Do not reuse R35's Journey.

Setup may:
- create/start a real Journey with at least one real provider-bound venue;
- create one standing Guardian mission;
- enroll Guardian Autopilot once.

Do not rerun R33/R34/R35.

The R36 closure is about the **watch lifecycle**, not forcing a disruption.

Record:
- initial Journey / plan / next activity;
- enrollment and configured interval;
- computed watch state;
- effective interval and next due time;
- one scheduled live Guardian pulse when the policy says it is due;
- resulting GuardianPulse and provider observations;
- whether schedule urgency changed after the pulse;
- AgentRun/proposal/mutation only if a real material conflict independently requires them.

Only one live provider pulse is allowed for the R36 causal receipt.

After that pulse, stop the live closure. Do not wait and poll until a more interesting event appears.

Valid outcomes include:
- WATCH_ALL_CLEAR;
- WATCH_DEGRADED;
- WATCH_MATERIAL_CONFLICT_HANDOFF;
- WATCH_EXTERNAL_AGENT_REQUIRED.

A quiet/all-clear scheduled pulse is a valid R36 success.

## Required artifacts

Create:
- `REVOLUTION_R36_ADAPTIVE_JOURNEY_WATCH_RESULT.md`
- `backend/output/r36-adaptive-journey-watch-v1.json`

The causal receipt should include:
- source HEAD before the live closure;
- Journey and initial plan ids;
- standing mission id;
- AutopilotEnrollment state;
- configured interval;
- initial `watch_state` and reason;
- effective interval / next due;
- next relevant activity;
- the one GuardianPulse id;
- actual live provider observations;
- context-watch classifications;
- any material Event ids;
- external AgentRun / RecoveryEpoch / proposal / authority only if they truly exist;
- final active plan id;
- mutation count;
- final watch-state projection;
- traveller-visible Watch state;
- limitations.

Do not create a verifier framework.

## Stop conditions

After the one R36 scheduled live pulse:
- write the receipt;
- commit;
- push;
- stop.

Do not:
- rerun R35;
- pulse repeatedly to prove cadence;
- fabricate a near activity merely after seeing an inconvenient live outcome;
- manufacture a disruption;
- use `OPPORTUNITY_WINDOW` as a fake urgency incident;
- call Hermes merely because watch intensity changed;
- lower provider provenance;
- hand-edit Events;
- claim physical travel.

## Codex handoff

Continue in the same local Codex thread on:

`gpt/revolution-r33-open-world-journey-adaptation`

First:
1. fetch latest;
2. verify HEAD includes `268198a02b58b7ebf59677f2d0954559fa92063b` and this taskbook;
3. read R35 result and immutable one-pulse receipt;
4. inspect `autorun.py`, Autopilot endpoints/model, current Live Recovery Guardian status;
5. implement the smallest coherent Adaptive Journey Watch slice;
6. run focused tests;
7. repair real defects rather than weakening policy;
8. execute exactly one R36 scheduled live pulse;
9. write the R36 result + causal JSON;
10. commit and push.

The target is not “more polling.”

The target is that CityNexus begins to have **temporal judgment**: it knows when a Journey deserves attention, when to stay quiet, and when a real unresolved problem justifies heightened vigilance—without confusing vigilance with permission to change the trip.
