# REVOLUTION R37 — Grounded Presence & Next Move

## Starting truth

R36 is complete and immutable as a historical live closure.

Accepted facts:
- R36 source/result commit: `5a6d3cbfa6f8b33aac8f98c9f0b2c1b8999c9b7f`.
- Fresh Journey: `1f772a88-2e34-4a0e-8683-e9d7125ba3b1`.
- Exactly one scheduled live pulse: `74182f46-5e03-479c-b8cc-4093a7e157bf`.
- Result: `WATCH_ALL_CLEAR`.
- Watch: `DAY_AHEAD`, configured 3600 s, effective 1800 s.
- Phase: `PRE_TRIP`, `CONTROL_PLANE_ONLY`.
- Two exact provider-bound venues were `OPEN_COMPATIBLE`.
- Material Event=0, AgentRun=0, proposal=0, mutation=0.
- Active plan did not change.
- The receipt-writing harness error was repaired from the same persisted DB; no second pulse occurred.
- R33/R34/R35/R36 live closures must not be rerun.

R36 gave CityNexus temporal judgment. R37 must give it **grounded presence**.

## The code-level gap

The repository already contains three pieces that do not yet form a product:

1. `LocationObservation` and `POST /api/v1/journeys/{journey_id}/location`.
2. `DEVICE_LOCATION_VERIFIED_EXECUTION` as a strong execution-truth kind.
3. A strict execution gate that already validates:
   - authenticated traveller principal,
   - fresh location,
   - location accuracy,
   - exact Journey binding,
   - distance to the activity Place,
   - a trusted location source,
   - matching principal audit.

But the ordinary location ingestion path always persists:

`source = FOREGROUND_WEB`

and the strong execution gate explicitly refuses that source. It accepts only trusted sources such as:

`DEVICE_ATTESTED` / `LOCATION_ATTESTED`.

That means CityNexus currently knows how to *consume* trustworthy presence but has no product bridge from ordinary foreground presence to useful Guardian behavior.

Do not weaken the strong gate. Do not relabel browser JSON coordinates as device-attested.

## Revolution objective

Build **Grounded Presence & Next Move**.

When the traveller voluntarily shares a fresh foreground location, CityNexus should be able to answer:

> “Where am I relative to the current/next plan stop, and what does that mean for the next move?”

without falsely claiming that the traveller has arrived.

This capability should connect:
- fresh foreground location;
- exact provider-bound Place coordinates;
- R36 Journey phase/watch scope;
- live/frozen mobility evidence where available;
- JourneyTwin Now/Next;
- the existing strong execution truth boundary.

The first R37 product should expose a traveller-facing readiness state such as:

- LOCATION_UNAVAILABLE
- LOCATION_STALE
- LOCATION_IMPRECISE
- TARGET_UNBOUND
- AWAY_FROM_TARGET
- NEAR_TARGET
- VERIFIED_AT_TARGET

The exact enum names may vary, but authority must remain explicit.

## Authority ladder

### Foreground web location

`FOREGROUND_WEB` is **advisory presence evidence**.

It may:
- compute distance to an exact Place;
- explain that the traveller appears near/far from the next stop;
- influence watch urgency;
- choose which route/venue evidence is worth refreshing;
- power a “Next Move” card;
- suggest “Confirm arrival” when near enough.

It must not:
- set Activity.status to ARRIVED/IN_PROGRESS/COMPLETED;
- write `DEVICE_LOCATION_VERIFIED_EXECUTION`;
- claim cryptographic/device-attested location;
- authorize plan mutation.

### Trusted device/location attestation

Only an actual trusted ingestion path may persist a source accepted by the existing strong execution gate.

If such a path is implemented in R37, it must:
- bind to an authenticated traveller/device principal;
- be fresh and auditable;
- use anti-replay/idempotency;
- preserve accuracy and capture timestamp;
- make it impossible for a caller to promote arbitrary JSON coordinates merely by naming `DEVICE_ATTESTED`.

Do not invent attestation if the local environment cannot genuinely provide it.

## Required product slice

### A. Presence projection

Add one server-owned deterministic projection that combines:

- latest LocationObservation for the Journey;
- Journey current activity / R36 monitored scope;
- exact Place coordinates;
- freshness;
- accuracy;
- distance.

Return at least:

```json
{
  "state": "AWAY_FROM_TARGET",
  "authority": "ADVISORY_FOREGROUND",
  "location_observation_id": "...",
  "source": "FOREGROUND_WEB",
  "captured_at": "...",
  "age_seconds": 42,
  "accuracy_m": 25,
  "target_activity_id": "...",
  "target_place_id": "...",
  "distance_to_target_m": 1830,
  "arrival_transition_allowed": false,
  "reason_code": "FOREGROUND_LOCATION_NOT_EXECUTION_TRUTH"
}
```

For trusted sources, the projection may say that strong execution attestation is eligible, but the transition still goes through the existing execution endpoint/gate.

### B. Next Move

Add a read-only “Next Move” projection that fuses:

- Journey phase;
- Now/Next execution projection;
- presence;
- next activity;
- route/mobility evidence if already live/frozen;
- exact venue readiness from latest Guardian pulse where available.

The traveller should get a useful answer even when there is no disruption.

Examples of ordinary copy:
- “You’re still far from your next stop. Guardian is watching the route and venue.”
- “You appear close to the next stop. Confirm arrival when you’re there.”
- “Your location is too old to judge where you are.”
- “Location sharing is off; Guardian is using the plan schedule only.”

Do not display raw internal enum names by default.

### C. Presence-aware Watch

R36 cadence remains the base scheduler.

Presence may tighten urgency when:
- a fresh foreground position is far from a near-term activity and the route budget is becoming tight;
- the traveller is near the next stop and venue reality is worth refreshing.

Presence must not create a material disruption Event by itself.

A location mismatch is not automatically a closure, traffic incident, or failed Journey.

### D. Strong truth bridge stays fail-closed

Keep the existing `DEVICE_LOCATION_VERIFIED_EXECUTION` gate strict.

Add focused regression proof that:
- a fresh accurate `FOREGROUND_WEB` observation can yield `NEAR_TARGET` advisory presence;
- the exact same observation is still refused as `DEVICE_LOCATION_VERIFIED_EXECUTION`;
- caller-supplied source text cannot relabel it trusted;
- stale / inaccurate / wrong-Journey / too-far observations remain refused by strong execution truth.

This is one of the most important R37 acceptance conditions.

## Tests before any live closure

At minimum:

1. no location -> LOCATION_UNAVAILABLE;
2. stale location -> LOCATION_STALE;
3. inaccurate location -> LOCATION_IMPRECISE;
4. exact Place missing -> TARGET_UNBOUND;
5. fresh foreground location near target -> advisory NEAR_TARGET;
6. fresh foreground location far from target -> AWAY_FROM_TARGET;
7. foreground NEAR_TARGET still cannot pass DEVICE_LOCATION_VERIFIED_EXECUTION;
8. presence projection creates no Event/AgentRun/proposal/mutation;
9. R36 phase/watch tests remain green;
10. R35 opportunity isolation remains green;
11. Next Move UI has ordinary traveller copy and does not claim “arrived” from foreground location;
12. TypeScript and focused Playwright pass.

Do not spend this run on a broad verifier.

## One bounded R37 live closure

Do not rerun R33-R36.

Use a new fresh Journey and at most one explicitly user/device-supplied foreground location observation.

The live closure is allowed to prove a truthful state such as:
- LIVE_LOCATION_AWAY_FROM_TARGET
- LIVE_LOCATION_NEAR_TARGET_ADVISORY
- LIVE_LOCATION_UNAVAILABLE
- LIVE_LOCATION_BLOCKED

It does not need to prove physical arrival.

If the environment can genuinely obtain a trusted device/location attestation, a strong transition may be tested exactly once. If it cannot, do not fake it; record that strong execution remains unavailable and preserve the gate.

For a foreground live closure record:
- how the location was obtained;
- source persisted;
- capture time / age / accuracy;
- target Place/provider binding;
- distance;
- presence state;
- Next Move copy;
- whether Guardian cadence/scope changed;
- AgentRun/proposal/mutation counts;
- active plan before/after;
- confirmation that no physical arrival was inferred.

Do not retry location to manufacture NEAR_TARGET.

## Required artifacts

- `REVOLUTION_R37_GROUNDED_PRESENCE_NEXT_MOVE_RESULT.md`
- `backend/output/r37-grounded-presence-next-move-v1.json`

## Stop conditions

After one bounded live presence closure:
- write the receipt;
- commit;
- push;
- stop.

Do not:
- rerun previous live closures;
- spoof coordinates;
- relabel FOREGROUND_WEB as attested;
- weaken location freshness/accuracy/principal checks;
- auto-arrive merely because the user is nearby;
- turn a distance estimate into a material Event;
- chase a mutation.

R37 succeeds when CityNexus can use real foreground presence to become more useful **without confusing “I can see where you are” with “I am authorized to declare what happened.”**
