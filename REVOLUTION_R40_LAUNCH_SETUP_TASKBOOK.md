# REVOLUTION R40 — Launch Setup & Origin Clarification

## Starting truth

R39 is complete and immutable.

Accepted facts:
- commit: `cd83eaea4746ea866f446c2de835b1a9199f125b`
- outcome: `LAUNCH_ORIGIN_UNKNOWN`
- the fresh Journey had no fresh location, temporally valid selected stay, or coordinate-bearing arrival anchor
- CityNexus correctly generated no route and no `must_leave_by`
- plan/execution truth/Event/AgentRun/proposal/mutation all remained unchanged
- focused backend: 53 passed
- TypeScript: passed
- focused Guardian Playwright: 3 passed
- 5 legacy/live Playwright cases stopped at existing reset/auth preconditions before R39 assertions
- R33-R39 live closures must not be rerun

R39 proved the system can refuse a false start point.

R40 must make the product capable of **obtaining a usable start point intentionally**, rather than hoping one already exists.

## Product gap

Today launch origin is passive. The projection checks:
- previous activity;
- fresh foreground location;
- selected stay;
- arrival anchor;
- otherwise UNKNOWN.

If none exist, the user receives an honest dead end.

A real travel operating system must be able to say:

> “I cannot safely calculate when you should leave yet. Where will you start from?”

and turn the answer into a durable, auditable planning fact.

This is not execution truth.

The user may plan to start from a hotel tomorrow morning without CityNexus claiming that the user is physically at the hotel now.

## Revolution objective

Build **Launch Setup & Origin Clarification**.

When R39 reports `UNKNOWN_ORIGIN`, expose a traveller-facing setup flow that can resolve a planned launch origin from one of these sources:

1. current shared location (when available);
2. selected stay (when temporally valid);
3. arrival point / reservation anchor (when valid);
4. an exact existing Place explicitly chosen by the traveller;
5. a provider-resolved place search result explicitly confirmed by the traveller.

The confirmed result becomes a persisted **planned launch origin contract**.

Suggested semantic distinction:

- `ADVISORY_FOREGROUND` — current shared location, useful for routing, not strong execution truth;
- `PLANNED_CONTEXT` — selected stay/arrival anchor inferred from existing persisted journey facts;
- `USER_CONFIRMED_PLANNED_ORIGIN` — user explicitly selected a start point;
- never `DEVICE_LOCATION_VERIFIED_EXECUTION` unless the existing strong execution gate separately proves it.

## A. Persisted launch-origin contract

Do not overload:
- arrival_anchor_json;
- departure_anchor_json;
- Activity.status;
- LocationObservation.source;
- Commitment;
- Event.

Introduce one explicit persisted home for the launch contract.

Preferred model:

`JourneyLaunchContext`

with fields roughly:
- journey_id (PK/FK)
- source_kind
- authority_kind
- place_id nullable
- display_name
- latitude / longitude nullable
- coordinate_crs
- source_ref_type nullable
- source_ref_id nullable
- valid_from nullable
- valid_until nullable
- confirmed_by nullable
- confirmation_method nullable
- created_at
- updated_at

If repository schema conventions strongly favour extending JourneyOperationsContext, that is acceptable only if the launch contract remains a named structured field and not an anonymous blob mixed with luggage constraints.

The persisted contract must be auditable.

## B. Candidate projection

Add a read-only launch setup projection:

```json
{
  "status": "NEEDS_ORIGIN",
  "current_origin": null,
  "candidates": [
    {
      "kind": "SELECTED_STAY",
      "display_name": "...",
      "eligible": true,
      "reason": "STAY_COVERS_TARGET_START"
    }
  ],
  "actions": [
    "SHARE_LOCATION",
    "USE_SELECTED_STAY",
    "USE_ARRIVAL_POINT",
    "CHOOSE_PLACE"
  ]
}
```

Only show actions that are actually available.

No selected stay => do not offer “Use hotel”.
No coordinate-bearing arrival anchor => do not offer “Use arrival point”.
No location => “Share current location” may be offered as a user action, but must not pretend a location already exists.

## C. Explicit place choice

The traveller may choose an existing exact Place as a **planned launch origin**.

Requirements:
- exact Place row must exist;
- coordinates must exist;
- provider/source provenance must remain visible;
- Journey binding/audit must be recorded;
- user choice must not mutate the active PlanVersion;
- user choice must not claim physical presence.

If the UI searches for a place, provider discovery may create/select a real Place candidate using existing discovery/fact-acquisition rules. Do not accept free-text coordinates as trusted evidence.

## D. Clarification lifecycle

When readiness / Next Move sees:
- pre-trip or launch phase;
- first target exists;
- launch origin UNKNOWN;
- target is within a useful planning horizon;

the UI should surface one clear CTA:

**Set starting point**

Do not start Hermes just to ask this question.

This is a deterministic missing-input clarification owned by the product UI/server.

After confirmation:
1. persist launch contract;
2. recompute R39 launch origin;
3. if an exact route already exists, consume it;
4. otherwise allow one bounded route acquisition through the normal provider path;
5. recompute R38 readiness.

This is the first closed product loop:
`UNKNOWN_ORIGIN -> USER_CLARIFICATION -> GROUNDED_ORIGIN -> EXACT_ROUTE -> READINESS`.

## E. Contract precedence

Update R39 launch precedence carefully.

For a first/pre-trip move:

1. fresh foreground location if the product is explicitly using “route from where I am now”;
2. valid explicit user-confirmed planned origin;
3. temporally valid selected stay;
4. valid arrival anchor;
5. unknown.

For an executing Journey:
- previous/current activity execution context still wins over a stale planned launch contract.

A planned launch origin must not teleport a traveller back to the start after execution has begun.

## F. Staleness / validity

A persisted planned origin may have validity bounds.

Examples:
- “Start from Nara Hotel tomorrow morning” can have a validity window around the first departure;
- a launch origin confirmed for Day 1 must not silently become the launch origin for Day 3;
- after the first activity is completed, the launch contract should normally become historical context, not a current route origin.

Do not use wall-clock expiry alone to rewrite execution state.

## G. UI

When origin is unknown:

> “Where will you start from? CityNexus needs a starting point before it can estimate when to leave.”

Candidate buttons may include:
- Use my current location
- Use Hotel Nikko Nara
- Use Nara Station arrival
- Choose another place

After user confirmation:

> “Planning your first route from Hotel Nikko Nara.”

Do not say:
> “You are at Hotel Nikko Nara.”

unless strong execution truth separately supports that claim.

## H. Route/readiness integration

Once a launch contract is persisted, R39/R38 should consume it like any other grounded launch origin.

If exact edge exists:
- use it.

If not:
- one bounded provider capture may be attempted by explicit refresh/normal runtime path.

No route provider retry loops.

No route capture merely because a GET projection was read.

GET endpoints must remain read-only.

## I. Offline continuity

Offline snapshot should include:
- confirmed planned launch origin;
- whether it is user-confirmed vs inferred;
- validity window;
- last launch route if any;
- last must_leave_by if any;
- capture timestamps.

## J. Authority invariants

Launch setup may write the launch contract and its audit record.

It must not:
- alter Activity.status;
- set journey.current_activity_id;
- write execution truth;
- create a material Event;
- start Hermes;
- create AgentRun;
- create proposal;
- mutate PlanVersion;
- change booking/commitment authority.

Changing a planned launch point is a planning-context write, not a replan mutation.

Keep `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` for proving.

## Tests before live closure

At minimum:

1. UNKNOWN_ORIGIN exposes NEEDS_ORIGIN setup state;
2. candidate list only contains actually available sources;
3. exact Place can be persisted as USER_CONFIRMED_PLANNED_ORIGIN;
4. free-text/user payload cannot inject trusted device authority;
5. explicit planned origin is consumed by R39 launch projection;
6. explicit planned origin never writes execution truth;
7. executing previous activity beats old planned launch origin;
8. expired/out-of-window launch contract does not apply;
9. changing launch contract is audited and idempotent;
10. GET projection does not capture provider route or mutate anything;
11. confirmed origin + existing exact edge yields grounded readiness;
12. confirmed origin + no exact edge stays honest until explicit bounded route refresh;
13. R39 exact-edge tests remain green;
14. R38 readiness tests remain green;
15. R37 execution/location boundary remains green;
16. TypeScript + focused Playwright pass.

## One bounded R40 live closure

Do not rerun R33-R39.

Use a fresh Journey with no incidental launch origin.

This time the product should intentionally resolve the missing input.

Preferred path:
- create/select a real provider-backed target;
- verify launch setup returns `NEEDS_ORIGIN`;
- choose one real existing provider-backed Place as a user-confirmed planned launch origin;
- persist the launch contract through the real API;
- do at most one bounded route acquisition if the normal explicit refresh path requires it;
- recompute readiness once.

Do not use fake coordinates.
Do not relabel the planned origin as physical presence.
Do not repeat route capture to force success.

Valid outcomes:
- `LAUNCH_SETUP_GROUNDED_ROUTE_READY`
- `LAUNCH_SETUP_GROUNDED_EDGE_UNAVAILABLE`
- `LAUNCH_SETUP_GROUNDED_PROVIDER_DEGRADED`
- `LAUNCH_SETUP_BLOCKED`

Receipt must show:
- initial UNKNOWN origin;
- candidate/actions shown;
- exact user-confirmed origin Place + provider provenance;
- persisted launch contract + audit;
- resulting R39 origin;
- exact route result if attempted;
- readiness/must_leave_by result;
- execution truth unchanged;
- Event/AgentRun/proposal/mutation counts;
- active plan before/after.

## Required artifacts

- `REVOLUTION_R40_LAUNCH_SETUP_RESULT.md`
- `backend/output/r40-launch-setup-v1.json`

## Stop condition

After one R40 live closure:
- write receipt;
- commit;
- push;
- stop.

R40 succeeds when CityNexus no longer treats an unknown start point as a dead end or a reason to guess.

It should instead do the obvious, useful, product-grade thing:

**ask the traveller where the trip starts, remember that answer as planning context, and use it to build the first real route without pretending the traveller is physically there.**
