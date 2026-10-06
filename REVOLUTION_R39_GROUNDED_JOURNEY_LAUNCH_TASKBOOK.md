# REVOLUTION R39 — Grounded Journey Launch & Door-to-Door Mobility

## Starting truth

R38 is complete and immutable as a historical closure.

Accepted facts:
- R38 commit: `c96d6347e8eea9ecf17f42e77f91c1505cc02497`.
- Fresh Journey: `1f20ebaa-b95d-4956-85eb-6306e2027642`.
- Result: `READINESS_READY_WITH_UNCERTAINTY`.
- The selected plan contained two real provider mobility facts.
- No mobility fact matched the pre-trip launch -> first target edge.
- `must_leave_by=null` with reason `NO_TRAVEL_EDGE`.
- R38 correctly refused to infer ETA from aggregate route evidence.
- No location, Event, AgentRun, proposal, mutation, or plan change occurred.
- R33-R38 live closures must not be rerun.

The R38 limitation is now the R39 product opportunity.

## Product gap

CityNexus can route between activities, but before the first meaningful activity it often has no explicit answer to:

> Where is the traveller actually launching from?

The repository already contains possible grounded origins:
- fresh foreground LocationObservation;
- selected AccommodationOfferSnapshot;
- JourneyTripContext arrival anchor;
- structural arrival/departure anchors;
- existing JourneyLeg / MobilityFact infrastructure.

But there is no single launch-origin contract connecting those facts to Next Move / Departure Readiness.

That is why a plan can contain valid provider mobility while the first stop still has `NO_TRAVEL_EDGE`.

R39 must not “fix” this by selecting an arbitrary mobility fact. It must create a grounded origin and then acquire/match one exact edge.

## Revolution objective

Build **Grounded Journey Launch & Door-to-Door Mobility**.

For the first/next move, CityNexus should be able to answer:

> “Where are you leaving from, what route connects that origin to the next stop, and when should you leave?”

without confusing inferred launch context with physical execution truth.

## A. Launch Origin projection

Create one deterministic server-owned projection with a strict precedence ladder.

Recommended states/sources:

1. `FOREGROUND_LOCATION`
   - latest fresh, sufficiently precise LocationObservation;
   - authority remains advisory unless separately trusted;
   - may be used as a route origin;
   - must not mark execution ARRIVED/EN_ROUTE.

2. `SELECTED_STAY`
   - only a selected/materialized accommodation;
   - target time must fall in a temporally plausible stay window;
   - coordinates come from AccommodationOfferSnapshot;
   - provenance/provider must be exposed.

3. `ARRIVAL_ANCHOR`
   - JourneyTripContext arrival anchor with explicit coordinates;
   - only if anchor time is before the target and no stronger later origin supersedes it.

4. `PREVIOUS_ACTIVITY`
   - for an already executing Journey, existing current/previous activity identity remains authoritative for the next edge.

5. `UNKNOWN_ORIGIN`
   - no routable origin can be grounded.

A projection should resemble:

```json
{
  "state": "READY",
  "source": "SELECTED_STAY",
  "authority": "PLANNED_GROUNDED_ORIGIN",
  "origin_key": "stay-offer:...",
  "name": "...",
  "latitude": 34.68,
  "longitude": 135.82,
  "captured_at": "...",
  "provider_key": "...",
  "target_activity_id": "...",
  "reason_code": "SELECTED_STAY_COVERS_TARGET_START"
}
```

## B. Precedence and temporal correctness

Do not blindly prefer a hotel over an arrival anchor.

Example:
- train arrives 08:00;
- hotel check-in 15:00;
- first activity 10:00.

The hotel is not a valid 10:00 launch origin merely because it is selected.

Likewise:
- hotel stay covers the overnight period;
- next activity is 09:00 next morning.

The hotel should supersede yesterday's arrival anchor.

Fresh foreground location may supersede both for routing, but remains advisory execution evidence.

Every source choice must have an inspectable reason.

## C. Door-to-door launch edge

For a grounded launch origin and exact target Place:

- look for an existing exact provider-backed MobilityFact/JourneyLeg first;
- if absent and the normal runtime provider path supports bounded route capture, acquire exactly the launch-origin -> target edge;
- bind origin identity + target Place identity;
- persist/freeze the provider fact using existing mobility conventions;
- expose provider, provenance, captured_at, expires_at, duration, distance, mode when provider actually supplied them.

No aggregate fallback.
No nearest-looking edge.
No city-centre placeholder.
No synthetic duration.

If provider route acquisition is unavailable:
- return `LAUNCH_EDGE_UNAVAILABLE` honestly;
- do not fabricate `must_leave_by`.

## D. Readiness integration

R38 Departure Readiness should consume the launch edge when the target has no previous activity edge.

Only then may it calculate:

`must_leave_by = target_start - grounded_travel_minutes - explicit_safety_buffer`

The result must record:
- launch origin source;
- exact edge identity;
- provider provenance;
- duration;
- safety buffer;
- computed must_leave_by.

For stale/degraded route evidence:
- do not present it as live;
- either use explicitly labelled frozen evidence under the existing policy or keep uncertainty.

## E. Next Move / UI

Upgrade Next Move / Ready for next? with ordinary traveller copy such as:

- “Leave your hotel around 08:20 for 依水園.”
- “Your first route is not ready yet; Guardian cannot safely estimate when to leave.”
- “Using your shared location, the next stop is about 18 minutes away.”
- “Using your arrival point as the trip start.”

Do not expose raw origin enum names to normal users.

The UI should distinguish:
- where the route starts;
- whether that origin is current/advisory/planned;
- route freshness;
- leave time when grounded.

## F. Launch origin is not execution truth

Critical boundary:

A launch origin projection may power routing and readiness, but must never by itself:
- mark an Activity EN_ROUTE/ARRIVED/IN_PROGRESS;
- write DEVICE_LOCATION_VERIFIED_EXECUTION;
- claim the traveller is physically at the hotel/arrival anchor;
- create a material Event;
- start Hermes;
- mutate the plan.

A selected hotel is a planning fact, not proof of physical presence.

A foreground location is useful routing evidence, not strong execution truth.

## G. Offline continuity

Store the latest launch origin + launch edge summary in OfflineJourneySnapshot:
- source/name;
- target;
- route minutes;
- provider/provenance;
- captured_at/expires_at;
- must_leave_by;
- freshness semantics.

Offline copy must say “last known / last synced”, not imply live traffic.

## Tests before live closure

At minimum:

1. fresh foreground location wins as advisory route origin;
2. foreground location does not become strong execution truth;
3. selected stay covering target start beats older arrival anchor;
4. selected stay whose check-in is after target start does not win;
5. valid arrival anchor becomes origin when no stronger source exists;
6. no grounded source => UNKNOWN_ORIGIN and no fabricated edge;
7. exact pre-trip launch edge yields route minutes and must_leave_by;
8. unrelated plan mobility fact cannot satisfy launch edge;
9. degraded/stale launch edge is labelled, not promoted to live;
10. launch projection creates zero Event/AgentRun/proposal/mutation;
11. R38 readiness tests remain green;
12. R37 execution/location boundary remains green;
13. R36 watch tests remain green;
14. frontend typecheck and focused Playwright pass.

Do not run a broad verifier.

## One bounded R39 live closure

Do not rerun R33-R38.

Use a new fresh Journey.

Preferred proving path:
- real provider-bound first target;
- one genuinely grounded non-location origin if available (selected stay or arrival anchor);
- one bounded provider launch-edge acquisition if needed;
- one readiness projection consuming that edge.

Do not require browser location.

Do not manufacture a hotel or reservation solely to make the result pretty. If a selected stay/arrival anchor naturally exists in the fresh Journey setup, use it. Otherwise record `UNKNOWN_ORIGIN` honestly.

Valid truthful outcomes:
- `LAUNCH_ROUTE_READY`
- `LAUNCH_ROUTE_READY_FROZEN`
- `LAUNCH_ORIGIN_UNKNOWN`
- `LAUNCH_EDGE_UNAVAILABLE`
- `LAUNCH_PROVIDER_DEGRADED`

The live result does not need a mutation.

Receipt must record:
- source HEAD;
- fresh Journey / plan;
- first/next target;
- launch origin source and evidence;
- origin coordinates/identity where applicable;
- exact target Place/provider binding;
- launch edge provider/provenance;
- route duration/distance/mode;
- captured_at/expires_at;
- must_leave_by and safety buffer, or exact absence reason;
- readiness before/after;
- offline snapshot launch summary;
- Event/AgentRun/proposal/mutation counts;
- active plan before/after.

One bounded provider attempt only. No retry to force a route.

## Required artifacts

- `REVOLUTION_R39_GROUNDED_JOURNEY_LAUNCH_RESULT.md`
- `backend/output/r39-grounded-journey-launch-v1.json`

## Stop condition

After the one R39 live closure:
- write receipt;
- commit;
- push;
- stop.

R39 succeeds when CityNexus stops treating the trip as if it begins at Activity #1 and instead understands the missing real-world transition:

**“You start somewhere. I know which grounded origin I am using, I know which exact route leads from there to your first stop, and only then will I tell you when to leave.”**
