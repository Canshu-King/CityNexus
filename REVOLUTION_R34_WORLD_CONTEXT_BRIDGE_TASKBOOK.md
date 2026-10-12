# REVOLUTION R34 — World Context Bridge

## Why R34 exists

R33-1 is accepted as an honest BLOCKED result. Do not rerun it.

The live Open-Meteo call succeeded and persisted a real `LIVE_PROVIDER`
ProviderObservation, but the current product reduced every below-policy weather
reading to:

- a list of provider target timestamps; and
- an empty risk snapshot.

No concrete Journey-overlapping precipitation probability or weather code
survived. No `PROVIDER_VERIFIED` Event existed, so Hermes was correctly not
started.

That is not an Agent failure. It is a product boundary: CityNexus remembered
the world only after the world became a disruption.

R34 fixes that boundary without weakening provenance or authority.

## Product objective

Make open-world sensing continuously useful even when no disruption exists:

```
provider observation
  -> durable Journey-relevant world context
  -> deterministic server materiality
     -> benign: Agent/user can inspect + NO_ACTION
     -> material: PROVIDER_VERIFIED Event
          -> existing RecoveryEpoch / Agent / authority / replan path
```

An Observation is evidence. It is not an Event.
An Event is a server-owned materiality claim. It is not mutation authority.
Agent autonomy remains downstream of both server truth and current authority.

## Implementation already placed on this branch

Branch:

`gpt/revolution-r34-world-context-bridge`

Base:

R33 honest BLOCKED head
`804aaf3a8594a05c39bb5965fa174e9f67f67fb9`

### 1. Preserve provider readings

`backend/app/integrations/context/weather_runtime.py`

Weather ProviderObservations now retain only the bounded forecast readings that
actually overlap a weather-sensitive Journey Activity:

- activity id;
- Place id;
- forecast hour;
- precipitation probability;
- WMO weather code;
- overlap/scope/sensitivity reason codes.

This context is persisted even if it does not become a risk Event.

Do not broaden this into dumping the provider's entire response.

### 2. Broaden deterministic weather materiality without lowering the old gate

`backend/app/integrations/context/open_meteo.py`

The existing heavy-rain probability threshold remains 70%.

R34 additionally consumes the WMO weather code already returned by Open-Meteo:

- 45/48 -> `LOW_VISIBILITY_RISK`
- 51/53/55, 61/63/65, 80/81/82 -> `RAIN_CONDITION_RISK`
  when the 70% heavy-rain rule has not already fired;
- 56/57, 66/67 -> `FREEZING_PRECIPITATION_RISK`
- 71/73/75/77, 85/86 -> `SNOW_RISK`
- 95/96/97/99 -> `THUNDERSTORM_RISK`

Clear/mainly-clear/cloudy/overcast readings remain context only.

A risk only becomes Journey-material when its forecast validity overlaps a
weather-sensitive Activity at the exact scoped Place.

Do not tune thresholds based on the live forecast you hope to see.

### 3. Server-owned world context projection

`backend/app/world_context.py`

`GET /api/v1/journeys/{journey_id}/world-context`

returns bounded recent ProviderObservations. For weather it distinguishes:

- `activity_observations`: relevant provider context;
- `risk_facts`: frozen provider-classified weather risks;
- `activity_risk_facts`: risks actually attributed to a Journey Activity;
- `material_risk`: true only when an activity-attributed risk exists.

No endpoint may let the client promote an Observation into an Event.

### 4. Agent can inspect world context

`inspect_twin` now returns `provider_context`.

The runtime tool contract explicitly tells Hermes:

- provider context may support explanation or a typed `NO_ACTION`;
- provider context by itself is not a disruption;
- `request_replan` still requires a current actionable Event.

Do not add a generic `replan_from_observation` escape hatch.

### 5. User can see benign open-world behavior

`frontend/src/features/execution/LiveRecovery.tsx`

When a recent live weather observation overlaps a planned Activity and no
activity-material weather risk exists, the surface says that current weather
was checked and no plan-impacting risk was found. It may show the persisted
precipitation probability.

It must not say the Journey is safe if no overlapping provider reading exists.

Existing Event/replan UI continues to own material recovery.

## Required local verification before any live call

Codex owns local execution. Start from the branch above and inspect the existing
R34 code as proposed implementation, not pre-proven code.

At minimum run and repair:

```text
backend/tests/test_r34_world_context_bridge.py
backend/tests/test_weather_refresh_endpoint.py
backend/tests/test_weather_runtime_gate_gpt.py
backend/tests/test_weather_runtime_hardening.py
backend/tests/test_gpt_weather_adversarial_next.py
backend/tests/test_agent_runtime_gate.py
backend/tests/test_agent_mission_runtime.py
```

Also run the frontend typecheck and the narrowest useful LiveRecovery test/e2e.
Add a narrow UI assertion for `live-world-context` if no existing test can
cover it.

Required assertions:

1. 69% + clear/cloudy code does not become HEAVY_RAIN_RISK.
2. 70% keeps the existing HEAVY_RAIN_RISK behavior.
3. a material WMO rain/snow/fog/thunderstorm code can create a named risk
   without changing the 70% threshold;
4. a benign live reading persists its Journey-overlapping values;
5. that benign observation does not create a PROVIDER_VERIFIED weather Event;
6. `inspect_twin.provider_context` exposes the same durable observation;
7. `request_replan` still cannot use the observation as an Event;
8. LiveRecovery only says "checked/no material risk" when an overlapping
   reading exists;
9. R30/R32 authority behavior remains untouched.

Do not expand into full historical regression unless one of these focused tests
reveals a real shared regression.

## Exactly one R34 live pulse

After focused verification is green, perform exactly one new live Open-Meteo
refresh on a fresh/clean active Journey with at least one weather-sensitive
discretionary Activity.

Do not reuse R33's observation.
Do not query repeatedly until weather becomes interesting.
Do not choose a city/time by looking for a forecast that will make the test pass.

Persist the complete causal receipt for that one pulse.

Then follow whichever reality the provider actually returned.

### Path A — benign live world context

If there is no activity-material risk:

1. prove the new ProviderObservation contains concrete overlapping readings,
   not only timestamps;
2. prove `world-context` exposes them with `material_risk=false`;
3. start one real configured WB2api/Hermes Agent mission;
4. give no weather values in the mission prompt. Tell it only to inspect the
   current Journey and current server-owned world state, and act only if current
   truth/authority allows;
5. Hermes must discover `provider_context` through `inspect_twin`;
6. with no actionable weather Event, it must not manufacture one or request a
   weather replan as though one existed;
7. a typed `NO_ACTION` based on current server facts is a valid R34 product
   outcome;
8. prove the user surface renders `live-world-context`.

Report this as:

`PROVEN_CONTEXT_BRIDGE / ADAPTATION_NOT_EXERCISED`

It is not evidence that R33's strategy-changing goal is complete.

### Path B — material live world fact

If deterministic server materiality produces an activity-attributed
`PROVIDER_VERIFIED` Event:

1. prove Event -> ProviderObservation lineage;
2. start one real configured WB2api/Hermes mission;
3. do not prescribe the replacement, tool sequence, proposal id, or final plan;
4. let the Agent inspect current Journey, Event, provider context, grounded
   alternatives, member values and commitments;
5. if it autonomously finds a legal materially different strategy, existing
   authority may permit at most one Journey mutation;
6. proposal must bind the exact AgentRun/current RecoveryEpoch;
7. user surface must show what changed plus Agent origin;
8. if authority or feasibility refuses, keep that refusal as the result.

Only if the Journey actually changes may the result claim:

`PROVEN_OPEN_WORLD_ADAPTATION`

A material Event plus a completed AgentRun is not enough.

## Live prompt constraint

Use a strategy-neutral mission such as:

"Inspect the current Journey and the current server-owned world state. Protect
confirmed commitments and traveler goals. If a truthful current Event makes
the existing strategy unsuitable, choose your own grounded response and act
only within current authority. If the current provider context is benign or
does not justify a domain change, finish with the truthful typed no-action
outcome. Do not invent facts, events, places, approvals, or authority."

Do not include:
- precipitation probability;
- weather code;
- desired replacement category/place;
- expected tool sequence;
- expected verdict.

The Agent must discover those from CityNexus.

## Result file

Write:

`REVOLUTION_R34_WORLD_CONTEXT_BRIDGE_RESULT.md`

Include:

- exact git head before live pulse;
- focused test/typecheck results;
- Journey id and initial active plan;
- ProviderObservation id/provenance/capture time/provider;
- relevant `activity_observations`;
- deterministic materiality result;
- Event id/provenance if and only if one exists;
- AgentRun id and RecoveryEpoch id;
- Agent tool sequence at summary level;
- typed terminal outcome;
- proposal/authority/mutation ids if they exist;
- final active plan;
- whether `live-world-context` or `live-agent-origin` is the applicable
  user-visible state;
- exact limitations.

If the live provider fails, report BLOCKED.
If context is benign, report the benign R34 success class above.
If an Agent/tool/authority link is missing, report PARTIAL/BLOCKED honestly.

## Hard prohibitions

- no R33 rerun;
- no R34 second weather pulse to hunt for risk;
- no lowered rain threshold;
- no SIMULATED fact promoted as open-world proof;
- no hand-authored Event;
- no DB edits;
- no fixture/replay presented as live Open-Meteo;
- no model-supplied authority;
- no verifier-only loop;
- no `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=true`;
- no change to configured WB2api/Hermes path merely to pass;
- no claim of physical travel.

## Stop condition

After the single R34 live pulse and result push, stop.

Do not automatically create R34-2.

The next Revolution step, if R34 proves context visibility but weather happens
to be benign, should be chosen on product value rather than by retrying nature.
A strong later candidate is an official place/service availability or closure
signal, because that is a discrete real-world fact whose change can directly
alter a Journey without requiring a probabilistic weather threshold.
