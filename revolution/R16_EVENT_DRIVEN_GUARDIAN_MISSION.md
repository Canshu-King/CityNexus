# Revolution R16 — Event-Driven Guardian Operator

## Revolution target

R15 taught CityNexus to seek truth before selecting a trip.

R16 must teach CityNexus to wake up when the world changes.

The target product behavior is:

```text
real trip is ACTIVE
  -> external/provider/user-reported disruption becomes a persisted Event
  -> Guardian sees an actionable event
  -> standing mission defines autonomy envelope
  -> real configured AgentRun starts automatically
  -> Agent inspects Journey/Twin
  -> Agent chooses recovery action
  -> Agent calls request_replan itself
  -> deterministic solver/authority returns grounded proposal
  -> Gateway either allows bounded acceptance or requires explicit approval
  -> replacement plan becomes active
  -> revised Journey continues to COMPLETED
```

This is not another planner round.
This is the transition from "tool-using assistant" to "event-driven travel operator".

## Do not build a new architecture first

The repository already has:
- `app.agent.guardian.scan_guardian`
- `app.agent.guardian._model_recovery`
- `app.agent.autorun.pulse_journey`
- standing Journey missions
- Autopilot enrollment
- persisted GuardianRun / AgentRun / AgentRunStep
- `request_replan` / `accept_replan` Gateway tools
- provider weather/mobility pulse infrastructure

Use them.

Fix only what prevents the real R16 flow.

## Success run prerequisites

Use a fresh disposable Journey whose initial plan satisfies the R15 truth boundary:
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`;
- used Places have canonical authority facts;
- selected plan uses hard-eligible live/provider mobility;
- no golden fixture;
- no copied selected PlanVersion.

You may reuse R15 code, but not the completed Hangzhou Journey as the final proof.

## Phase A — standing mission and explicit autonomy envelope

Create/activate a standing Guardian mission before the disruption.

The mission must encode real bounds, for example:
- preserve protected/anchor activities;
- maximum cost increase;
- maximum schedule drift;
- walking/mobility preference;
- whether bounded replan acceptance may be automatic.

Do not give the model unlimited mutation authority.

Prefer `EXECUTE_WITHIN_BOUNDS` for the main experiment so the system can prove autonomous recovery when the policy allows it.

If current Gateway policy still requires user confirmation, respect it. Revolution means autonomous strategy inside authority boundaries, not bypassing them.

## Phase B — real event wake-up

Start Guardian Autopilot or invoke the actual Guardian scan path from the same persisted event state.

The trigger must be a truthful external observation:
- live weather/provider event;
- live mobility/provider incident;
- or explicit user/operator-reported closure/delay with provenance recorded.

Do not create the event from model prose.

The final success proof should prefer Autopilot/pulse wake-up over a hand-called recovery function.

A manual `guardian/scan` may be used for debugging. It is not the desired final product proof if the Autopilot path is operational.

## Phase C — native Agent must choose request_replan

The success AgentRun must use the configured real model runtime.

Required model tool behavior:
1. inspect Journey;
2. inspect Twin;
3. optionally inspect/list current replans or relevant live facts;
4. decide that the event materially affects the active plan;
5. call `request_replan` with the persisted trigger event ID.

The model may choose another safe tool first if justified, but `request_replan` must be model-selected in the final success trace.

Do not inject `request_replan` from a deterministic wrapper and then describe it as model autonomy.

## Phase D — preserve deterministic truth and solver authority

After `request_replan`:
- impact resolution remains deterministic/evidence-backed;
- mobility recapture remains provider-backed;
- proposal feasibility remains deterministic;
- protected commitments remain protected;
- replacement Places must satisfy the same canonical truth boundary as R15;
- estimate authority remains OFF.

If the model proposes an invalid strategy, the deterministic core must reject it and the Agent may try a different strategy.

That rejection-and-pivot is a positive Revolution behavior, not a failure.

## Phase E — bounded acceptance

Two valid success modes:

### Mode 1: autonomous bounded acceptance
If policy returns `ALLOW_AUTO`:
- model selects a proposal and calls `accept_replan`;
- Gateway verifies policy/feasibility;
- replacement plan activates.

### Mode 2: explicit human approval
If policy returns `REQUIRE_CONFIRMATION` or `REQUIRE_STEP_UP`:
- model presents the proposal;
- system persists the pending approval;
- user/operator supplies the approval receipt;
- same proposal is accepted through Gateway.

Do not weaken policy just to force Mode 1.

## Phase F — complete the revised trip

After replan:
- execute the new current activity/activities through real state transitions;
- Journey must reach `COMPLETED`;
- final Twin must agree with the revised active plan;
- old/new PlanVersion lineage and trigger Event remain persisted.

Do not stop at "proposal generated".

## Phase G — prove event-driven, not deterministic fallback

This is a hard acceptance condition.

The final GuardianRun must show:
- `controller=configured_agent_runtime`;
- persisted AgentRun provider/model is the actual configured model;
- tool steps are model runtime steps;
- `request_replan` appears in that tool sequence;
- deterministic fallback provider/model is NOT the success path.

If the real model is unavailable and Guardian falls back, that proves resilience, not R16 autonomy. Fix the runtime or rerun; do not relabel.

## Phase H — allow one real strategy pivot

If the first replan cannot pass truth/feasibility:
- Agent may acquire canonical facts for a replacement Place;
- choose another Place;
- choose another proposal;
- reduce schedule drift;
- or preserve the original plan if no safe recovery exists.

At least one bounded rejection/pivot is valuable, but do not manufacture one solely for the report.

## Runtime discipline

R15 already showed the domestic model may need a larger reasoning budget.

Keep:
- bounded same-model retry for genuine length/reasoning exhaustion;
- explicit total AgentRun wall-clock budget;
- compact tool results;
- preserved `finish_reason` if streaming is used.

Do not spend most of R16 on runtime plumbing. One real successful recovery matters more than another compatibility layer.

## Anti-ORD rules

- one capability branch;
- one main report;
- inline blocker fixes;
- no branch-per-bug;
- no R16.1/R16.2 recut carousel;
- no report-only round;
- no replaying R15 truth acquisition repeatedly after it is established;
- no new "Guardian evidence framework" unless the existing one genuinely cannot prove the flow.

## Success levels

### REVOLUTION_A — native recovery decision
Actionable persisted event wakes a real AgentRun and the model itself calls `request_replan`.

### REVOLUTION_B — governed autonomous mutation
REVOLUTION_A + the model selects/accepts a grounded proposal inside Gateway policy, or cleanly reaches the explicit human approval boundary.

### REVOLUTION_C — event-driven completed trip
REVOLUTION_B + replacement plan activates + revised trip executes to `Journey COMPLETED`.

### REVOLUTION_D — provider-driven wake-up
REVOLUTION_C with the disruption produced by a live provider/Guardian pulse rather than manually posted user/operator event.

Target C. Push for D if provider conditions make it possible without faking an incident.

## Final report

One file:

`REVOLUTION_R16_EVENT_DRIVEN_GUARDIAN_RESULT.md`

Include only:
- base/final SHA;
- fresh Journey/city;
- estimate-authority=false receipt;
- initial selected plan and canonical fact provenance;
- standing mission/autonomy envelope;
- event ID, type, source and provenance;
- GuardianRun ID;
- actual AgentRun provider/model;
- ordered model-selected tools;
- `request_replan` receipt;
- proposal/solver/provider evidence;
- policy decision;
- approval receipt if required;
- old/new PlanVersion lineage;
- final Journey/Twin state;
- focused tests + candidate-vs-base delta;
- fallback occurrences, clearly separated from success evidence.

## Success sentence

R16 closes when this is a machine fact:

> While a real trip was already running, a truthful disruption woke CityNexus automatically, a real model inspected live state and chose to request a grounded replan, the existing authority boundary governed the mutation, and the revised Journey completed without a human scripting the recovery sequence.
