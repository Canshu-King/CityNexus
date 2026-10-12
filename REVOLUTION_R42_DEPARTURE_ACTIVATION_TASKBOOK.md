# REVOLUTION R42 — Departure Activation & Confirmed Journey Launch

## Starting truth

R41 is complete and immutable.

Accepted facts:
- commit: `4c5530283fc80ec5b49e5653744616c12610a5be`
- one fresh Route Session closure: `ROUTE_SESSION_READY`
- real Valhalla route: 22 minutes, WALK
- exact MobilityFact frozen with `LIVE_PROVIDER_CAPTURE`
- R39 consumed the same exact fact
- R38 computed `must_leave_by=2026-10-07T08:08:00+08:00`
- no second Route Session / no provider retry
- no PlanVersion mutation
- Event=0, AgentRun=0, proposal=0, mutation=0
- focused backend 49 passed; Python compile and TypeScript passed
- R33-R41 live closures must not be rerun

R41 answered:

> “When should I leave?”

R42 must answer the next product question:

> “When that moment arrives, how does the trip actually begin?”

## Code-level opportunity

The repository already contains the authoritative execution state machine:

- `ACTIVE/NOT_STARTED -> EN_ROUTE`
- `EN_ROUTE -> ARRIVED`
- `ARRIVED -> IN_PROGRESS`

and the existing execution-truth boundary already supports:

`OPERATOR_CONFIRMED_EXECUTION`

for an authenticated Journey member.

This is exactly the right boundary.

What is missing is the product layer connecting:
- grounded `must_leave_by`;
- a just-in-time departure cue;
- one explicit traveller action;
- the existing strong execution transition;
- immediate Guardian phase change from pre-trip/approaching to in-transit.

R42 must use that existing execution truth gate, not create a parallel “started trip” flag.

## Revolution objective

Build **Departure Activation & Confirmed Journey Launch**.

The product loop becomes:

`READINESS + MUST_LEAVE_BY -> DEPARTURE CUE -> USER CONFIRMS "I'M LEAVING" -> OPERATOR_CONFIRMED_EXECUTION -> EN_ROUTE -> GUARDIAN IN_TRANSIT`

This is the first R33+ capability where the product intentionally crosses from read-only operational guidance into a real execution-state write — but only on explicit user authority.

## A. Departure Activation projection

Create a deterministic read-only projection for the current/next move.

Suggested states:

- `NO_ROUTE`
- `NOT_DUE`
- `LEAVE_SOON`
- `DUE_NOW`
- `OVERDUE`
- `BLOCKED`
- `ALREADY_EN_ROUTE`
- `ARRIVED_OR_LATER`
- `COMPLETE`

Suggested payload:

```json
{
  "state": "LEAVE_SOON",
  "activity_id": "...",
  "target_title": "...",
  "must_leave_by": "...",
  "minutes_to_leave": 8,
  "readiness_state": "READY_WITH_UNCERTAINTY",
  "can_confirm_departure": true,
  "recommended_action": "CONFIRM_WHEN_LEAVING",
  "authority_required": "OPERATOR_CONFIRMED_EXECUTION"
}
```

The projection must not write execution state.

## B. Timing bands

Use `must_leave_by` as a derived operational cue, not as truth about movement.

Recommended bands:
- >30 min: NOT_DUE
- 30..10 min: LEAVE_SOON
- 10..-5 min: DUE_NOW
- < -5 min: OVERDUE

Exact thresholds may be adjusted if existing product conventions are stronger, but must be deterministic and testable with `execution_clock`.

No sleeping in tests.

## C. Blocked readiness

If Departure Readiness is `BLOCKED`:
- activation state = BLOCKED;
- normal CTA should not say “Leave now”;
- UI should show the blocker.

However, the server execution endpoint remains the authoritative state machine. Do not make the projection a hidden mutation authority.

If product requirements allow the traveller to depart despite advisory warnings, that must be an explicit user override path, not an automatic transition.

## D. Just-in-time departure cue

Reuse the existing `NotificationEvent` + `notify()` path.

Do not create a second notification subsystem.

Create at most one deduped departure cue per semantic time band/readiness fingerprint.

Examples:
- LEAVE_SOON: “You’ll need to leave soon for 依水園.”
- DUE_NOW: “It’s time to leave for 依水園.”
- OVERDUE: “You’re past the planned leave time. Confirm when you’re on the way.”
- BLOCKED: “Hold before leaving — the next move has a blocker.”

The cue itself must never set EN_ROUTE.

Repeated worker/readiness refreshes in the same band must reuse the same notification identity.

## E. Confirm Departure

The traveller-facing action should be:

**I’m leaving**

or equivalent ordinary copy.

Do not create a new execution-truth mechanism.

The action must ultimately call the existing activity `/depart` state transition using:

`OPERATOR_CONFIRMED_EXECUTION`

Requirements:
- authenticated Journey member;
- current activity must match active Journey cursor;
- predecessor state must be ACTIVE or NOT_STARTED;
- explicit confirmation must be true;
- existing execution truth record must be appended;
- Activity becomes EN_ROUTE;
- JourneyTwin/offline snapshot update through existing path;
- an ACTIVITY_DEPARTED outcome event is allowed because this is execution history, not a disruption Event.

Important distinction:
- JourneyOutcomeEvent/ACTIVITY_DEPARTED is expected execution history.
- material `Event` rows remain zero unless the world actually reports a disruption.

## F. No clock-authority leakage

Absolutely forbidden:

- `must_leave_by` reached -> auto EN_ROUTE;
- OVERDUE -> auto EN_ROUTE;
- Guardian phase inference -> auto EN_ROUTE;
- route provider success -> auto EN_ROUTE;
- notification delivery -> auto EN_ROUTE.

Only an accepted strong execution transition changes the persisted state.

## G. Simulated transition boundary

The existing execution endpoint defaults to `SIMULATED_STATE_TRANSITION` when no strong attestation is provided.

R42 user-facing production launch must not use that default.

The UI/product API for “I’m leaving” must explicitly request:
- `truth_kind=OPERATOR_CONFIRMED_EXECUTION`
- `operator_confirmed=true`

Tests must prove the product path cannot silently fall back to SIMULATED when authentication/attestation is missing.

Do not delete simulation support globally; other test/demo surfaces may depend on it. Keep the production action explicit.

## H. Immediate post-departure convergence

After confirmed departure:

- Activity status = EN_ROUTE
- execution truth kind = OPERATOR_CONFIRMED_EXECUTION
- R36 phase projection = IN_TRANSIT
- R39 planned launch origin must no longer override executing activity context
- R38 readiness should stop presenting pre-departure `must_leave_by` as the primary action
- Next Move copy becomes in-transit oriented
- Guardian Watch may tighten according to existing phase policy
- offline snapshot reflects EN_ROUTE truth

Do not trigger Hermes merely because departure happened.

## I. Route evidence during launch

The R41 exact route remains evidence for the launched leg.

Do not mutate the route fact when the traveller confirms departure.

If the fact is stale at departure time:
- display “last checked” / uncertainty;
- do not silently reacquire a provider route as part of the depart POST.

A separate explicit Route Session may refresh in a future product slice, but R42 closure gets one previously acquired route and one confirmed execution action.

## J. UI

Near “Ready for next?” / Next Move:

Before due:
> “Leave around 08:08.”

Near due:
> “Time to leave for 依水園.”
> [I’m leaving]

After confirmation:
> “On the way to 依水園.”

If blocked:
> “Hold before leaving — check the issue first.”

Normal UI must not show:
- OPERATOR_CONFIRMED_EXECUTION
- execution truth enum
- internal state-machine codes

## K. Offline / Edge continuity

Offline snapshot should include:
- departure activation state;
- must_leave_by;
- cue captured-at;
- whether departure is already confirmed;
- execution truth summary after confirmation.

If Edge action infrastructure naturally supports authenticated `NEXT`/execution commands, it may surface the same confirmation action later, but R42 must not broaden scope into a new device-auth project.

## Authority invariants

R42 is the first slice here that intentionally changes execution state.

Allowed write after explicit authenticated user confirmation:
- Activity.status -> EN_ROUTE
- execution truth append
- JourneyOutcomeEvent ACTIVITY_DEPARTED
- audit
- JourneyTwin/offline snapshot

Forbidden:
- PlanVersion mutation
- replan proposal
- RecoveryEpoch
- AgentRun
- material Event generated merely because departure is late
- booking/commitment changes
- automatic departure from time/provider inference

Keep `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.

## Tests before live closure

At minimum:

1. no route/must_leave_by -> NO_ROUTE;
2. >30 min -> NOT_DUE;
3. 30..10 min -> LEAVE_SOON;
4. around leave time -> DUE_NOW;
5. overdue clock alone leaves Activity ACTIVE;
6. BLOCKED readiness produces no normal leave CTA;
7. repeated cue in same band dedupes;
8. band/readiness material change can create a new cue identity;
9. user-facing depart action explicitly uses OPERATOR_CONFIRMED_EXECUTION;
10. unauthenticated confirmation fails closed;
11. missing operator_confirmed fails closed;
12. confirmed depart writes EN_ROUTE + strong execution truth;
13. confirmed depart writes expected JourneyOutcomeEvent but zero material Event;
14. departure creates zero AgentRun/proposal/PlanVersion mutation;
15. post-depart phase becomes IN_TRANSIT;
16. old planned launch origin no longer overrides executing context;
17. pre-depart `must_leave_by` is no longer primary action after EN_ROUTE;
18. R41 route fact remains unchanged;
19. R41/R40/R39/R38 authority regressions stay green;
20. TypeScript + focused Playwright pass.

Do not run broad verifier loops.

## One bounded R42 live closure

Do not rerun R33-R41.

Use one new fresh Journey.

Preparation is allowed through normal real product APIs:
- real provider-backed plan;
- R40 planned launch origin;
- one R41 Route Session if necessary to ground `must_leave_by`.

Those are setup for the fresh R42 Journey, not reruns of historical closures.

But once the R42 closure begins:
- do not repeat route provider calls;
- do not manufacture a better leave time.

Required proving sequence:
1. reach grounded readiness with a real `must_leave_by`;
2. use frozen clock/test-safe setup to prove activation timing deterministically;
3. for the actual live execution closure, issue exactly one authenticated product “I’m leaving” action;
4. verify EN_ROUTE / OPERATOR_CONFIRMED_EXECUTION / IN_TRANSIT convergence;
5. stop.

If local environment cannot establish authenticated traveller principal:
- do not fall back to SIMULATED;
- closure result may be `DEPARTURE_CONFIRMATION_BLOCKED_AUTH`.

Valid truthful outcomes:
- `DEPARTURE_CONFIRMED_EN_ROUTE`
- `DEPARTURE_CONFIRMATION_BLOCKED_AUTH`
- `DEPARTURE_CONFIRMATION_REFUSED`

Do not retry authentication by weakening the gate.

Receipt must record:
- source HEAD
- fresh Journey/active plan/current activity
- exact R41 route fact + provider provenance
- readiness + must_leave_by
- activation state
- departure cue notification/dedupe
- authenticated principal/member if available
- exactly one departure action
- execution truth kind
- Activity status before/after
- phase before/after
- JourneyOutcomeEvent ids/types
- material Event count
- AgentRun count
- proposal count
- PlanVersion mutation count
- route fact before/after identity

## Required artifacts

- `REVOLUTION_R42_DEPARTURE_ACTIVATION_RESULT.md`
- `backend/output/r42-departure-activation-v1.json`

## Stop condition

After the one R42 departure closure:
- write receipt;
- commit;
- push;
- stop.

R42 succeeds when CityNexus crosses a fundamental product boundary correctly:

**It no longer only tells the traveller when to leave. At the right moment it asks for one explicit human confirmation, records that real execution decision, and immediately becomes an in-transit guardian — without pretending that a clock, route estimate, or notification proves the traveller has moved.**
