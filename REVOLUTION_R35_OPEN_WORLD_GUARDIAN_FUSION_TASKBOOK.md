# REVOLUTION R35 — Open-World Guardian Fusion

## Starting truth

R34 is complete for its actual live result and must not be rewritten.

Accepted live fact:
- source closure commit: `120ce1af17e292755d57c9becf8c91795f5d519a`;
- Journey: `d264cb72-154d-4704-91cf-3d7709797a5d`;
- the one authorized R34 live closure returned `NO_MATERIAL_CHANGE`;
- two active-plan venues acquired fresh exact-provider evidence;
- both planned activity intervals were genuinely compatible with the fresh opening-hours evidence;
- R34 AgentRun count = 0;
- R34 recovery Event count = 0;
- R34 mutation count = 0;
- R33-1 remains honestly BLOCKED;
- R32/R33-1 were not rerun and R33-2 does not exist.

That is a valid product result. Do not rerun R34 to hunt for a closure or bad weather.

## GPT post-review corrections already seeded after R34

Treat these commits as a proposed implementation that must be verified locally, not as pre-proven code:

- `545cb2f9d55968c5b0a5def0915dbe6ad666cacc`
  - opening-hours compatibility now requires the full planned activity interval to fit inside verified opening hours; partial overlap is no longer called compatible.
- `a92885a0534c4949947615d5b5d0e2f4904e7c7b`
  - focused tests for partial overlap and cross-midnight containment.
- `e7e05b2de7edba882d3a688b2d0897aea1f43f55`
  - context-watch evidence is rebound at runtime to both exact Place id and exact provider entity.
- `02920a7dff2e13cd9f9ee66b20b76b751feac161`
  - mismatched provider-entity receipts are rejected by test.
- `af5e1f64b6b85057d64ba4d93e3148ae0953fee2`
  - the existing Guardian pulse now runs the R34 live venue context watch in the same live sensing cycle as weather/mobility.
- `0caadac43d40d09674f963a4e80c4779609a56b6`
  - a qualified R34+ live-world conflict may not fall back to the deterministic Guardian controller when the configured external Agent is unavailable.
- `1b138eee1493ebcf584cfd7dc97e08eb7b20b61e`
  - regression test pins the no-deterministic-fallback rule for live-world conflicts.
- `0f01789f86b3a37b3a7220480abd5ca6df6018c2`
  - adds the bounded product endpoint `POST /api/v1/journeys/{journey_id}/guardian/pulse` for exactly one sensing/evaluation cycle and exposes the latest pulse through Guardian status / latest-pulse read.
- `4b3e7939cddcab0a47f211b19af6f89d3e4b2ada`
  - live venue conflicts now have durable semantic incident identity; repeated fresh polls refresh the same incident rather than spawning Event storms; a later qualified `OPEN_COMPATIBLE` observation resolves the old conflict and invalidates its pending replan, while UNKNOWN/DEGRADED evidence cannot clear it.

These changes do not alter the historical R34 live artifact. In particular, the R34 two live intervals were already fully contained in their verified opening windows, so the stricter interval semantics do not turn the original `NO_MATERIAL_CHANGE` into a failure.

## Revolution objective

R35 must turn CityNexus from a collection of real-provider checks into an actual **open-world Journey Guardian**.

The product behavior is:

> A traveller gives CityNexus a standing mission and authority envelope once.  
> CityNexus can then perform one coherent live pulse that checks relevant external reality.  
> If reality is compatible, it stays quiet but can show that the trip was checked.  
> If reality materially conflicts with the active Journey, the existing Guardian hands the exact server-owned incident to the configured external Agent, which autonomously investigates and proposes or executes only within legal authority.  
> If evidence or the external Agent is unavailable, CityNexus stops honestly instead of fabricating recovery.

Do not build another Guardian subsystem. Use the existing:
- `backend/app/agent/autorun.py`
- `backend/app/agent/guardian.py`
- standing Guardian mission;
- GuardianRun / GuardianPulse;
- RecoveryEpoch;
- WB2api/Hermes configured Agent runtime;
- Agent Gateway / delegation policy / collective authority;
- R33 public proposal provenance;
- Live Recovery surface.

R35 is primarily a **fusion and productization** round.

## What R35 must add or finish

### A. One coherent live pulse

The bounded `guardian/pulse` route is the canonical R35 proving door.

One pulse should compose the existing live provider capabilities without inventing facts:

1. Open-Meteo weather runtime;
2. live mobility runtime / current configured mobility provider;
3. R34 exact-provider venue/opening-hours context watch;
4. JourneyTwin / current execution truth;
5. existing resilience / standby maintenance where already part of Guardian pulse;
6. Guardian evaluation.

The result must persist as one GuardianPulse and name the provider observations it actually acquired.

Do not treat provider success as equivalent to a disruption.

### B. Quiet success is a first-class user experience

If all qualified evidence says the active Journey remains feasible, the pulse should end without:
- new recovery Event;
- new recovery AgentRun;
- proposal;
- authority receipt;
- mutation.

But the traveller-facing Live surface must be able to say, in ordinary language, that CityNexus recently checked the trip and currently sees no change requiring action.

Example meaning, not required literal copy:

> "刚刚检查了天气、路线和地点开放信息，目前的安排仍然可行。"

This must not be rendered as a warning card.

Useful supporting detail may include:
- last checked time;
- which provider classes were checked;
- how many planned venues were checked;
- whether some source was unavailable.

Do not expose raw internal enum names by default.

### C. Unknown/degraded is visible but not alarming

If a provider fails or venue evidence is UNKNOWN:
- do not invent a conflict;
- do not clear an existing qualified conflict merely because the fresh provider is unavailable;
- do not mutate;
- surface a calm truthful status such as "部分实时信息暂时无法确认；没有自动修改你的行程."

The product should distinguish:
- "we checked and it is okay";
- "we could not verify part of it";
- "we found a real material problem."

### D. Material conflict hands off to the existing Guardian

If the live venue context watch creates or refreshes a qualified:
- `CLOSED_CONFLICT`, or
- `OUTSIDE_VERIFIED_HOURS`

then the same Guardian pulse may treat its `truth-mesh / SYSTEM_DERIVED / CLOSURE` Event as actionable.

The Guardian must:
- bind to the exact Event;
- compile recovery from the active standing mission;
- use the configured external WB2api/Hermes path;
- bind the resulting AgentRun to the current RecoveryEpoch;
- let the Agent inspect/search/reason without a prescribed replacement;
- bind proposals to the exact AgentRun + RecoveryEpoch;
- obey current delegation/collective authority;
- execute at most one legal Journey mutation.

The context-watch itself must not prescribe:
- a replacement place;
- proposal id;
- tool order;
- final mutation.

### E. No fake autonomy

For R34+ live-world triggers, an unavailable configured external Agent is a truthful stop condition.

Do not use:
- `citynexus-guardian / deterministic-recovery-controller-v1`;
- copied Agent output;
- deterministic request_replan/accept_replan fallback;
- a hand-built proposal;
- a fixture AgentRun

to claim the R35 autonomous handoff.

Expected honest state when a qualified live conflict exists but the external Agent cannot run:
- GuardianRun `PARTIAL`;
- action status `RETRYABLE_FAILURE` or an equally explicit non-success state;
- no proposal invented by fallback;
- no mutation;
- active plan unchanged;
- evidence says external Agent required.

Historical deterministic Guardian behavior may remain for older fixture/internal paths. Do not widen this R35 rule into unrelated regressions unless necessary.

### F. Incident lifecycle must survive continuous operation

A continuous Guardian cannot create a new "incident" every time it sees the same world fact.

Required:
- repeated fresh evidence for the same plan/activity/provider conflict refreshes one semantic incident;
- repeated pulse cannot create unbounded duplicate CLOSURE Events for the same incident;
- a newly qualified compatible observation may resolve that incident;
- resolving the incident invalidates pending replans triggered by the now-cleared event;
- UNKNOWN/DEGRADED evidence cannot resolve it;
- a genuinely different active plan/activity/material conflict may create a new incident.

The seeded implementation is only proposed until local tests confirm these rules.

### G. Live Recovery becomes the traveller's Guardian surface

Extend the existing Live Recovery product instead of adding a lab-only screen.

The Live surface should have three understandable states based on latest persisted GuardianPulse/context evidence:

1. **Checked / all clear**
   - recent live check exists;
   - no material conflict;
   - no action required;
   - no fake recovery card.

2. **Verification incomplete**
   - some real source is unknown/degraded;
   - the trip was not auto-modified on weak evidence.

3. **Material change / recovery**
   - use the existing disruption and proposal experience;
   - show the affected activity in traveller language;
   - if an autonomous proposal exists, retain R33 `live-agent-origin`;
   - if authority executed it, do not ask the traveller to accept a change that already happened;
   - if confirmation is legally required, keep that gate.

Do not expose internal GuardianRun ids, RecoveryEpoch jargon, provenance enums, or policy codes in the normal UI. Those may remain in advanced/debug surfaces.

## Local verification before the live pulse

Codex must first fetch the branch and run narrow verification against the GPT-seeded changes.

At minimum cover:

- R34 full-containment opening-hours semantics;
- cross-midnight verified opening interval;
- exact Place + provider-entity evidence binding;
- stable incident identity across repeated fresh conflict polls;
- repeated conflict poll reuses/refreshes one Event rather than creating an Event storm;
- qualified `OPEN_COMPATIBLE` resolves the prior live-context conflict and invalidates pending replan;
- UNKNOWN/DEGRADED does not clear prior conflict;
- `NO_MATERIAL_CHANGE` pulse starts no recovery Agent and mutates nothing;
- a context-watch conflict exists before Guardian decides recovery;
- live-world conflict + external runtime unavailable refuses deterministic fallback;
- bounded `guardian/pulse` persists exactly one GuardianPulse;
- latest-pulse/status read returns the persisted result;
- R33 proposal `source_agent_run_id` / `recovery_epoch_id` remains intact;
- existing current authority tests touched by the fusion remain green;
- frontend typecheck and one narrow Live Recovery test for the new all-clear/degraded presentation.

Do not run the whole historical evidence suite by default.

If any GPT-seeded implementation is wrong, repair it. Do not preserve a GPT change merely because GPT authored it.

## One bounded R35 live closure

Run exactly **one** R35 live closure on a new/clean live Journey after local verification.

This is not:
- R34 retry;
- R33 retry;
- an attempt to force a mutation.

### Preconditions

The Journey should:
- be ACTIVE;
- have a meaningful active plan with at least one real provider-bound venue;
- have a standing Guardian mission that expresses traveller goals and bounded autonomy;
- retain current `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`;
- retain the configured WB2api/Hermes selection;
- use live Guardian provider configuration, not provider fixtures.

A standing mission is allowed setup. It represents the traveller asking CityNexus to watch the trip.

### Closure door

Use exactly one call to the bounded product path:

`POST /api/v1/journeys/{journey_id}/guardian/pulse`

Do not start a fast recurring background worker for the proving closure.

The single pulse may make the normal provider calls that belong to one pulse, but do not call `guardian/pulse` again because reality was inconvenient.

### Valid live outcomes

#### 1. ALL_CLEAR / NO_MATERIAL_CHANGE

This is a full R35 product success if:
- fresh live provider observations were acquired honestly;
- venue context classifications are qualified and compatible;
- no material disruption was invented;
- no recovery AgentRun was started;
- mutation count is zero;
- the latest GuardianPulse persists the result;
- Live Recovery visibly communicates that the trip was checked and currently needs no change.

Do not retry.

#### 2. MATERIAL_CONFLICT_HANDOFF

If the one pulse honestly finds a qualified material conflict:
- a server-owned conflict Event exists;
- Guardian selects it through the normal actionable-event path;
- configured external Agent actually runs;
- its exact AgentRun / RecoveryEpoch are durable;
- any proposal is bound to that run/epoch;
- current authority decides whether mutation is legal;
- at most one mutation occurs;
- Live Recovery shows the real-world reason and Agent-origin proposal/outcome.

If legal authority requires user confirmation, that is a valid bounded result; do not bypass it.

#### 3. EXTERNAL_AGENT_REQUIRED

If a qualified live conflict exists but the external Agent is unavailable:
- record PARTIAL/BLOCKED honestly;
- no deterministic fallback;
- no fabricated proposal;
- no mutation;
- keep the live conflict visible.

Do not retry the live pulse merely to get the model online.

#### 4. LIVE_CONTEXT_DEGRADED

If one or more required live boundaries are unknown/degraded:
- persist what was actually captured;
- no hard conflict from weak evidence;
- no mutation caused by uncertainty;
- Live surface explains that some current information could not be confirmed.

Do not retry to make it greener.

## Required R35 causal receipt

Create:

- `REVOLUTION_R35_OPEN_WORLD_GUARDIAN_FUSION_RESULT.md`
- `backend/output/r35-open-world-guardian-pulse-v1.json`

Record only facts that actually exist.

At minimum include:
- git source head before live pulse;
- Journey id;
- initial active plan id and short traveller-language strategy;
- standing Guardian mission id and autonomy mode;
- GuardianPulse id;
- provider observations from weather, mobility, venue context that actually exist;
- venue observation ids, provider entities, source classes and classifications;
- degraded/unknown provider facts, if any;
- recovery Event ids created/refreshed/resolved by this pulse;
- GuardianRun id and decision, if one exists;
- exact external AgentRun id and RecoveryEpoch id only if the Agent actually ran;
- proposal id / proposed plan id only if they exist;
- authority mode / receipt only if it exists;
- final active plan id;
- mutation count;
- whether public replan provenance matches the exact external AgentRun, if applicable;
- the traveller-visible Live state that was rendered;
- limitations: software/provider execution only, no claim of physical travel.

Do not introduce a new verifier framework just for this round.

## Stop conditions

After the one live R35 pulse and its receipt:
- stop;
- push;
- report the real outcome.

Do not:
- rerun R34;
- rerun R33-1 or R32;
- create R33-2;
- repeat R35 pulse until weather/venue conditions become interesting;
- switch to a fixture to obtain a conflict;
- hand-edit a provider fact or Event;
- lower evidence thresholds;
- weaken exact provider identity;
- turn UNKNOWN into CLOSED;
- use deterministic Guardian fallback for R35 live-world conflict;
- prescribe Hermes' tool sequence or replacement;
- create a fake proposal/authority receipt;
- claim a physical trip happened.

## Codex handoff

Continue in the same local Codex thread on:

`gpt/revolution-r33-open-world-journey-adaptation`

First:
1. fetch latest branch;
2. verify the post-R34 GPT commits listed above are present;
3. read immutable R34 result and live receipt;
4. read this R35 taskbook;
5. inspect the seeded diffs as proposed implementation;
6. run the narrow local verification;
7. repair real defects;
8. finish the Live Recovery latest-pulse UI;
9. execute exactly one bounded live `guardian/pulse`;
10. write the R35 result + JSON receipt;
11. commit and push.

The target is not a mutation.

The target is that CityNexus now behaves like a living travel companion: it checks reality through real providers, stays quiet when the trip is fine, admits uncertainty when reality cannot be verified, and hands a real material problem to a real external Agent only when the world actually demands intervention.
