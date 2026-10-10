# REVOLUTION R56 — In-Transit Reroute / Route Deviation Operator

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

## User capability — put this sentence at the top of the result

> **While the traveller is already EN_ROUTE, CityNexus can now compare the current shared/attested location with the grounded route, detect meaningful deviation, recalculate a route from where the traveller actually is, update arrival/commitment risk, and continue the same Journey instead of forcing the traveller to manually restart navigation. Advisory browser location stays advisory; only trusted device/location evidence may become authoritative off-route truth.**

If this becomes “draw a map”, “add a location badge”, or “build another route verifier”, stop and correct course.

## Starting truth

R55 is complete at `339248c63ef9d698ef7e40ac9139963adbc848bf`.

R55 proved:
- authenticated execution milestones create live schedule drift;
- exact route/commitment slack is propagated;
- harmless drift stays quiet;
- material drift creates one system-derived Event and wakes the existing Guardian;
- external planner unavailability remains an honest block.

Do not rerun R33-R55 historical closures.

## Existing capabilities to connect

Already present:
- `LocationObservation`;
- R37 `presence_projection()`;
- FOREGROUND_WEB advisory source;
- trusted sources `DEVICE_ATTESTED` / `LOCATION_ATTESTED`;
- R41 MobilityFact / JourneyLeg with geometry_json, duration, distance, provenance;
- R48 EN_ROUTE execution lifecycle;
- exact route acquisition operation;
- R55 progress / commitment risk;
- Guardian / Operator / Needs-you.

The gap:

**EN_ROUTE currently means “the user said they left.” CityNexus can tell proximity to the destination, but it does not yet continuously reason about whether the traveller is still following the route or needs a fresh route from the actual current position.**

## 1. First-class in-transit projection

Add an Operator section:

`transit`

Suggested states:
- `INACTIVE`
- `LOCATION_UNAVAILABLE`
- `LOCATION_STALE`
- `ROUTE_SHAPE_UNAVAILABLE`
- `ON_ROUTE`
- `ADVISORY_DEVIATION`
- `VERIFIED_DEVIATION`
- `REROUTE_NEEDED`
- `REROUTE_READY`
- `REROUTE_PROVIDER_DEGRADED`
- `COMMITMENT_AT_RISK`

Example:

```json
{
  "state": "ADVISORY_DEVIATION",
  "headline": "Your shared location is about 420 m away from the planned route.",
  "authority": "ADVISORY_FOREGROUND",
  "distance_to_route_m": 420,
  "accuracy_m": 35,
  "target": {...},
  "reroute": {
    "available": true,
    "action_label": "Recalculate from here"
  }
}
```

## 2. Only operate during EN_ROUTE

R56 is an in-transit capability.

If current activity is:
- ACTIVE
- ARRIVED
- IN_PROGRESS
- COMPLETED

do not classify route deviation.

Do not use a later stray location sample to reopen travel after arrival.

## 3. Route geometry boundary

Use the authoritative current JourneyLeg / MobilityFact geometry only if:
- it belongs to the current active plan and active travel edge;
- CRS is understood;
- geometry_json is nonempty and can be normalized;
- route provenance is explicit.

Support the actual geometry format already produced by CityNexus.

Do not invent a polyline when geometry_json is empty.

If no usable shape:
- `ROUTE_SHAPE_UNAVAILABLE`
- user may still explicitly request a fresh route from current location;
- no off-route claim.

## 4. Location authority tiers

### FOREGROUND_WEB
User/browser-shared coordinates.

May support:
- advisory distance to route;
- advisory current-to-target reroute;
- advisory ETA/commitment risk;
- user-facing “You may be off route.”

Must not:
- claim physical presence as independently verified;
- create authoritative ROUTE_DEVIATION Event;
- auto-mutate plan;
- auto-trigger Guardian solely from this observation.

### DEVICE_ATTESTED / LOCATION_ATTESTED
Existing trusted location tier.

May support:
- VERIFIED_DEVIATION after freshness/accuracy and persistence rules pass;
- material Event;
- Guardian handoff when route/commitment is actually at risk.

Do not weaken the existing attestation boundary.

## 5. GPS noise protection

A single noisy point should not become a verified incident.

For authoritative deviation require all:
- trusted source;
- fresh observation;
- acceptable accuracy;
- distance from route > dynamic threshold;
- preferably at least 2 consecutive qualifying observations or one very large deviation with high confidence.

Suggested threshold:
`max(150m, accuracy_m * 3)`

Tune against existing presence semantics, but keep deterministic/server-owned.

FOREGROUND_WEB can show advisory on one point because it does not mutate authority.

## 6. Distance-to-route calculation

Normalize route geometry into WGS84 points.

Calculate nearest distance from current observation to route polyline.

Do not use only:
- distance to destination;
- bounding box;
- route origin/destination chord.

If geometry is unavailable, stay unknown.

Keep math deterministic.

## 7. Wrong-way / no-progress signal

Optional v1 enhancement if enough observations exist:

Two or more fresh locations may show:
- distance to target increasing materially;
- along-route progress reversing;
- traveller stationary long enough to threaten ETA.

Treat these as supporting signals, not required for the first implementation.

Do not infer “wrong train” from one coordinate.

## 8. Reroute from current coordinates

This is the main user capability.

Add a bounded route operation using:
- current LocationObservation coordinates as origin;
- current activity exact Place as target;
- requested mode from the active leg / product context.

Unlike R41 launch route, this operation is explicitly an **in-transit reroute** and may use current coordinates.

Important:
- origin provenance must be copied into the operation;
- FOREGROUND_WEB origin produces `ADVISORY_ROUTE`;
- trusted origin may produce `TRUSTED_CURRENT_LOCATION_ROUTE`.

Do not persist the coordinates as a Place unless an explicit product reason exists.

## 9. Reroute is not PlanVersion mutation

A fresh current-location route:
- updates the in-transit navigation/read model;
- may update ETA/risk;
- does not rewrite Activity place/order;
- does not create a new PlanVersion just because the user took a different street.

Only if the destination/remaining Journey must change should normal Guardian/replan apply.

## 10. Provider truth

Reroute provider result must keep exact provenance:
- LIVE_PROVIDER_CAPTURE if truly live;
- CAPTURED_REPLAY / SEALED_REAL_REPLAY if replay;
- LAB fixture if lab.

Do not call replay live.

One route operation per semantic origin/target/location generation; repeated taps reuse it.

## 11. Freshness

Location used for reroute should be fresh.

Suggested:
- <= 5 min;
- accuracy <= 100 m for meaningful reroute;
- stricter if creating verified deviation.

A stale location should never launch an apparently current reroute.

## 12. Arrival interaction

If trusted location becomes near the target:
- R37/R48 arrival CTA remains the path;
- R56 should stop talking about deviation.

Do not auto-ARRIVE merely because reroute ends at target.

## 13. ETA / commitment risk

After a grounded current-location route is available:
- compare reroute duration + current time with next protected commitment/readiness;
- reuse R55 style slack semantics.

If FOREGROUND_WEB:
- risk is advisory;
- no authoritative drift Event solely from location.

If trusted device:
- material verified route deviation may create one Event and hand to Guardian.

## 14. Event semantics

Suggested material event:
- event_type: `ROUTE_DEVIATION` or existing compatible mobility event;
- provenance: `SYSTEM_DERIVED`;
- derivation: `SYSTEM_DERIVED_TRUSTED_LOCATION_FACT`;
- payload includes:
  - location observation id;
  - source;
  - accuracy;
  - distance_to_route_m;
  - active JourneyLeg id;
  - geometry source;
  - reroute fact/operation id if available;
  - affected commitment if material.

FOREGROUND_WEB must not create this authoritative event.

## 15. Guardian handoff

For verified material deviation:
- same Guardian;
- same standing mission;
- no separate NavigationAgent.

External Agent may decide whether the remaining Journey needs:
- replan;
- skip/reorder;
- discovery;
- transaction change.

The deterministic route layer only says:
> current route/ETA no longer safely fits.

## 16. No external-model dependency for core R56

Deviation math and current-location reroute do not require an LLM.

If external Agent is unavailable after a verified material deviation:
- honest `OPERATOR_EXTERNAL_AGENT_BLOCKED`.

Do not let deterministic fallback choose itinerary changes.

## 17. R52 quiet UX

Possible primary Needs-you:
- “Recalculate from here” for advisory location;
- approval if recovery later needs one.

Do not interrupt for small route noise.

If the user explicitly opens the Journey while EN_ROUTE, the transit card can be visible without a push notification.

## 18. Offline

Offline snapshot may store the latest transit projection:
- state;
- target;
- last location timestamp/source class;
- last reroute summary;
- captured_at.

Do not store unnecessary precise location history in the offline snapshot.

## 19. Privacy

Keep raw location retention bounded to existing LocationObservation semantics.

Do not expose coordinates in normal UI.

Default copy:
> “You may be off the planned route.”

Advanced/debug may show distance/provenance.

## 20. Focused tests

Only tests proving the product capability:

1. not EN_ROUTE -> transit INACTIVE.
2. no location -> LOCATION_UNAVAILABLE.
3. stale location -> LOCATION_STALE.
4. missing route geometry -> ROUTE_SHAPE_UNAVAILABLE, no fake deviation.
5. foreground point near route -> ON_ROUTE/advisory normal.
6. foreground point far from route -> ADVISORY_DEVIATION, no Event.
7. trusted fresh precise points crossing threshold -> VERIFIED_DEVIATION.
8. one noisy trusted point does not create material deviation if persistence rule requires two.
9. current-location reroute uses exact observation coordinates without creating a Place.
10. replay route result keeps replay provenance.
11. live route result only says live when provider really did.
12. duplicate current-location reroute reuses semantic operation.
13. reroute changes ETA/read model but not PlanVersion.
14. trusted material reroute risk -> one normal Guardian Event.
15. foreground advisory risk -> no Guardian Event.
16. near-target trusted location yields arrival-ready instead of route-deviation attention.
17. TypeScript + focused In-Transit Reroute Playwright.

Do not rerun historical campaigns.

## 21. One bounded R56 product experiment

Use one fresh Journey with:
- Operator ON;
- one active route with usable geometry if available;
- current activity EN_ROUTE.

Preferred product proof does **not** pretend trusted physical presence if no device-attestation path is available.

### Preferred advisory experiment
1. authenticated traveller uses normal “I’m leaving” -> EN_ROUTE;
2. submit one FOREGROUND_WEB location through the real product location endpoint at a point meaningfully away from the active route;
3. transit projection becomes ADVISORY_DEVIATION;
4. no Event / no Guardian;
5. user taps exactly once: “Recalculate from here”;
6. route operation uses the submitted coordinates as ephemeral origin;
7. one real provider call if available, otherwise one explicit captured replay;
8. route becomes REROUTE_READY with honest provenance;
9. Activity remains EN_ROUTE;
10. active PlanVersion unchanged;
11. stop.

If a real trusted Edge/Location attestation path is available and can be exercised honestly, a verified experiment is also valid:
- two trusted observations;
- VERIFIED_DEVIATION;
- one material Event if downstream risk exists;
- Guardian once.

Do not manufacture DEVICE_ATTESTED by changing a FOREGROUND_WEB row.

Valid outcomes:
- `IN_TRANSIT_REROUTE_ADVISORY_READY`
- `IN_TRANSIT_VERIFIED_DEVIATION`
- `IN_TRANSIT_REROUTE_PROVIDER_DEGRADED`
- `IN_TRANSIT_ROUTE_SHAPE_UNAVAILABLE`
- `IN_TRANSIT_LOCATION_UNAVAILABLE`
- `IN_TRANSIT_BRAIN_BLOCKED_AFTER_VERIFIED_RISK`

## Stop condition

Stop after one in-transit location either:
- produces an honest advisory reroute from the traveller’s current location; or
- produces one verified deviation through a genuine trusted location path.

End-user capability:

> **“If I stray from the route while I’m already travelling, I don’t have to restart the trip or work out a new route myself. CityNexus can recalculate from where I am, update the risk, and keep carrying the same Journey forward — without pretending browser GPS is stronger evidence than it really is.”**
