# REVOLUTION R38 — Departure Readiness & Just-in-Time Briefing

## Starting truth

R37 is complete and its live closure is immutable.

Accepted historical facts:
- R37 commit: `800079489f4d2c2c984ab3ce102e00469522107c`.
- Fresh Journey: `86478b77-7085-4eb9-8d0d-bef56db6f614`.
- Exact provider-backed target: 依水園.
- Live closure result: `LIVE_LOCATION_UNAVAILABLE`.
- The local environment had no browser foreground location observation.
- No coordinates were fabricated and no second location attempt was made.
- LocationObservation=0, Event=0, AgentRun=0, proposal=0, mutation=0.
- Strong execution remained fail closed.
- R33-R37 live closures must not be rerun.

R37 proved that CityNexus can use presence when it exists and stay truthful when it does not.

R38 must move the product from **“Guardian knows what is next”** to **“Guardian can tell me whether I am ready for what is next.”**

## Product gap

The repository already has:
- Next Move projection;
- Adaptive Guardian Watch;
- provider-backed venue readiness;
- mobility evidence;
- weather/provider observations;
- TransportReservation;
- Commitments;
- NotificationEvent + web push/SSE/in-app recording;
- OfflineJourneySnapshot;
- execution truth and JourneyTwin.

But these facts are still exposed as separate subsystems.

A traveller about to leave should not need to inspect five panels and infer:

- Is the next venue actually open?
- Is route evidence present and fresh enough?
- Is there a protected reservation/commitment I cannot miss?
- Is the next leg at risk?
- Is location missing, and does that matter?
- Is Guardian merely watching, or is there something I should do now?

R38 creates a single, read-only **Departure Readiness** projection plus a bounded **Just-in-Time Briefing** notification lifecycle.

## Revolution objective

For the next meaningful activity, CityNexus should be able to answer:

> “Are you ready to go, what is still uncertain, and what should you do next?”

without inventing world truth and without mutating the Journey.

Suggested readiness states:

- READY
- READY_WITH_UNCERTAINTY
- ACTION_NEEDED
- BLOCKED
- NOT_DUE
- COMPLETE
- UNKNOWN

These names may change if code conventions demand it, but semantics must remain inspectable.

## A. Departure Readiness projection

Create one deterministic server-owned projection that fuses:

1. Next Move
2. R36 Journey phase
3. latest Guardian venue readiness
4. route/mobility evidence
5. open material Events
6. active C3/C4 commitments for the next activity or upcoming departure anchor
7. confirmed TransportReservation status/realtime status
8. latest location/presence only when relevant
9. time until the next meaningful activity

The projection should contain:

```json
{
  "state": "READY_WITH_UNCERTAINTY",
  "target_activity_id": "...",
  "target_title": "...",
  "starts_at": "...",
  "minutes_until_start": 42,
  "must_leave_by": "...",
  "blocking_reasons": [],
  "warning_reasons": ["LOCATION_UNAVAILABLE"],
  "checks": {
    "venue": "OPEN_COMPATIBLE",
    "route": "AVAILABLE",
    "reservation": "CONFIRMED",
    "commitment": "PROTECTED",
    "presence": "LOCATION_UNAVAILABLE"
  },
  "recommended_action": "LEAVE_ON_SCHEDULE",
  "authority": "READ_ONLY_PROJECTION"
}
```

The exact shape may evolve, but every negative/unknown fact must be distinguishable from a positive fact.

## B. Readiness semantics

### READY

Only when all required evidence for the next move is positively compatible.

Examples:
- exact venue is OPEN_COMPATIBLE when a venue check is relevant;
- route evidence is available and not degraded;
- required protected reservation/commitment is confirmed/intact;
- no unresolved material Event affects the next move.

Location is not universally required. A missing foreground location must not block a pre-trip traveller merely because R37 supports presence.

### READY_WITH_UNCERTAINTY

Use when the system can recommend proceeding but one or more non-critical facts are unknown/unavailable.

Examples:
- location sharing off while still PRE_TRIP;
- no fresh venue check yet but no contradictory evidence;
- realtime reservation status unknown while static confirmed reservation remains valid.

### ACTION_NEEDED

The Journey is still feasible, but the traveller should do something.

Examples:
- departure window is close and a required confirmation/check is missing;
- reservation needs review;
- location is stale when it is needed to judge an in-transit next move;
- next venue is UNKNOWN/PROVIDER_DEGRADED close to departure.

### BLOCKED

Use only for a real blocker:
- exact venue has CLOSED_CONFLICT / OUTSIDE_VERIFIED_HOURS;
- confirmed transport reservation is CANCELLED;
- unresolved CRITICAL material Event affects the move;
- required protected commitment cannot be satisfied.

Do not use BLOCKED for missing optional evidence.

## C. Must-leave-by / action timing

Use existing route evidence and schedule facts.

Do not claim a live ETA if the route evidence is frozen/static.

If there is enough grounded evidence, expose a conservative `must_leave_by`.

If not, return an explicit reason such as:
- ROUTE_EVIDENCE_UNKNOWN
- ROUTE_EVIDENCE_DEGRADED
- NO_TRAVEL_EDGE

Never fabricate a travel time.

## D. Just-in-Time Briefing

When readiness becomes useful to the traveller, create at most one deduped NotificationEvent for the same readiness fingerprint.

Examples:
- “Your next stop is ready. Leave by 08:25.”
- “Your train is confirmed, but live status is unavailable.”
- “The next venue is currently closed. Guardian is watching for recovery options.”
- “One check is still missing before departure.”

Use the existing `notify()` path so in-app/SSE/push behavior stays unified.

The notification layer must be idempotent:
- repeated identical projections increment/reuse a stable dedupe identity rather than spamming;
- a material readiness change may create a new briefing;
- a pure clock tick that does not cross a meaningful threshold should not create a new notification.

Recommended notification windows:
- 120 min: quiet readiness card only;
- 60 min: briefing eligible;
- 30 min: elevated priority if uncertainty/action is unresolved;
- <=15 min: high priority only for real action/blocker.

Do not send push merely because the worker ran.

## E. Offline continuity

Add Departure Readiness / Next Move summary into `OfflineJourneySnapshot`.

The traveller should still see:
- next activity;
- readiness state at last sync;
- last verified venue status;
- route evidence provenance/freshness;
- recommended next action;
- snapshot timestamp.

Offline data is stale-by-definition after capture. Do not imply it is still live.

## F. UI

Add one traveller-facing “Ready for next?” card near Next Move / Guardian.

Ordinary language only.

Examples:
- “Ready to go · next stop opens as planned.”
- “Mostly ready · live train status is unavailable.”
- “Check before leaving · Guardian could not verify the next venue.”
- “Do not leave yet · the next venue is closed.”

Show:
- next target;
- approximate start/departure timing;
- readiness summary;
- one recommended action.

Do not expose internal reason codes by default.

## Authority invariants

R38 is read-only unless an existing, separately authorized recovery path is triggered by a real Event.

Departure Readiness must never itself:
- create a material Event;
- start Hermes;
- create a proposal;
- create a RecoveryEpoch;
- mutate a plan;
- change a booking;
- mark an activity ARRIVED/COMPLETED.

A BLOCKED projection is a read model, not mutation authority.

Keep `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` for live proving.

## Tests before live closure

At minimum:

1. compatible venue + route + no material event => READY or READY_WITH_UNCERTAINTY;
2. location unavailable PRE_TRIP does not falsely BLOCK;
3. CLOSED_CONFLICT => BLOCKED;
4. provider degraded/venue unknown near departure => ACTION_NEEDED;
5. cancelled confirmed transport reservation => BLOCKED;
6. confirmed reservation with UNKNOWN_REALTIME => uncertainty, not cancellation;
7. protected commitment remains visible in readiness;
8. missing route evidence never fabricates must_leave_by;
9. identical briefing projection dedupes;
10. material readiness change produces a new dedupe fingerprint;
11. readiness computation creates zero AgentRun/proposal/mutation;
12. offline snapshot includes readiness but labels capture/freshness honestly;
13. R37 strong execution/location boundary remains green;
14. R36 watch tests remain green;
15. frontend typecheck + focused Guardian/Next Move Playwright pass.

Do not run a broad verifier.

## One bounded R38 live closure

Do not rerun R33-R37.

Use a fresh Journey with:
- a real provider-bound next venue;
- existing route evidence;
- at least one meaningful schedule/commitment fact if practical.

No location is required.

Perform one bounded readiness refresh. Provider access may be used only if the normal readiness path calls it; do not retry to manufacture a stronger state.

Valid truthful outcomes:
- READINESS_READY
- READINESS_READY_WITH_UNCERTAINTY
- READINESS_ACTION_NEEDED
- READINESS_BLOCKED
- READINESS_PROVIDER_DEGRADED

Record:
- fresh Journey / plan / next activity;
- readiness state;
- venue state/provenance;
- route state/provenance;
- commitment/reservation state;
- location/presence state;
- must_leave_by and its evidence, or explicit reason absent;
- notification created/reused;
- offline snapshot readiness;
- Event/AgentRun/proposal/mutation counts;
- active plan before/after.

Do not retry provider calls or alter the Journey just to obtain READY.

## Required artifacts

- `REVOLUTION_R38_DEPARTURE_READINESS_RESULT.md`
- `backend/output/r38-departure-readiness-v1.json`

## Stop condition

After one bounded R38 live readiness closure:
- write receipt;
- commit;
- push;
- stop.

The Revolution target is not another status panel.

The target is that CityNexus can finally turn scattered travel evidence into a single practical answer:

**“Here is whether you are actually ready for the next part of your trip, what I know, what I do not know, and what you should do now.”**
