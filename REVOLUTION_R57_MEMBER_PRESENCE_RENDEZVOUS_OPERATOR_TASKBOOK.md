# REVOLUTION R57 — Member Presence & Rendezvous Operator

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

Before touching code, keep this sentence visible:

> **CityNexus newly learns to keep each traveller's shared position separate on a group Journey, notice when the group has split, tell each member who is still on track for the next shared stop, and guide the current member back toward a grounded rendezvous without exposing anyone else's raw coordinates or pretending browser location is trusted device evidence.**

If this turns into “add `traveler_id` to a table”, “draw multiple dots”, “build a location verifier”, or “prove R56 again”, stop and correct course.

## Starting truth

Start from Revolution branch:

`gpt/revolution-r33-open-world-journey-adaptation`

Pre-taskbook implementation checkpoint:

`299b236403f3c608e0097fa9c194edf65e7d73e3`

R56 is not the task. It already gives a single EN_ROUTE traveller:
- a current-leg route projection;
- advisory vs attested location authority;
- point-to-polyline deviation;
- a current-location Route Session;
- commitment-risk projection;
- a visible “Recalculate from here” action.

GPT additionally closed three R56 seams before this baton:
1. one continuous verified deviation now creates one incident rather than one Event per GPS sample/reroute tap;
2. the deviation Event targets the current EN_ROUTE activity while the downstream protected commitment remains an explicit risk;
3. strict-auth browser reroute now sends the signed traveler bearer on the foreground `/location` POST as well as the reroute POST, and a focused Playwright contract pins the visible route.

Do **not** reopen R33-R56 historical closures.

## Relay preflight — validate GPT's R56 seam fixes, then move on

Do not re-open R56 design.

Before starting R57, run exactly this focused preflight from the latest branch:

```bash
git fetch origin
git checkout gpt/revolution-r33-open-world-journey-adaptation
git reset --hard origin/gpt/revolution-r33-open-world-journey-adaptation

cd backend
python -m pytest -q tests/test_in_transit_reroute.py

cd ../frontend
npm run typecheck
npx playwright test e2e/r56-in-transit-reroute.spec.ts --project=chromium
```

What this preflight is checking:
- same continuous trusted deviation does not create an Event per GPS sample;
- the deviation Event's causal activity is the current EN_ROUTE stop, not the downstream protected stop;
- a resolved incident can later recur as a new incident;
- R56 uses the shared execution clock for freshness;
- strict-auth foreground location capture carries the signed Traveler bearer;
- the subsequent reroute carries the same signed bearer and exact observation id;
- the UI shows a grounded new ETA while saying the active plan stayed unchanged.

No real external model call is required.
No live route provider call is required.
Do not rerun R33-R55.

If one of these focused tests fails, repair the actual integration without weakening the authority/provenance semantics. Once green, **start R57 immediately**.

## The product gap

Today `LocationObservation` is Journey-scoped.

That is tolerable for one traveller. It is ambiguous for a shared Journey:

- Alice shares a position;
- Bob shares a newer position;
- a Journey-level “latest location” no longer answers **whose position** it is;
- the Operator can accidentally reason about the wrong person;
- a shared Journey cannot truthfully say who is late, who is together, or who needs a route back to the group.

R45 already knows the members.
R56 already knows how to route from an ephemeral current coordinate.
R57 connects them.

This is a product capability, not a schema cleanup.

---

# 1. Durable member-bound location truth

A new location observation created in authenticated mode must be bound server-side to the signed Traveler principal.

Minimum durable truth:
- `journey_id`;
- `traveler_id` (server resolved, not caller supplied);
- optionally the in-force `journey_member_id` snapshot if useful;
- source / accuracy / captured_at remain unchanged.

Migration/compatibility:
- existing historical rows may remain unbound/null;
- an unbound row must never be attributed to a named group member;
- legacy unauthenticated single-traveller demo behavior may continue;
- a **shared** Journey must not infer member identity from “latest Journey row” when auth is unavailable.

Do not accept `traveler_id`, `member_id`, role, or display name from the location POST body as authority.

## Negative controls

Prove:
1. OWNER token posts -> observation binds OWNER traveler.
2. ADMIN/COLLABORATOR token posts -> binds that exact traveler.
3. caller cannot body-forge another traveler/member.
4. withdrawn/expired member cannot create current group presence.
5. a location row from another Journey cannot be used here.
6. an old unbound row cannot become another member's position by recency.

---

# 2. One-shot sharing, not background surveillance

R57 does not introduce continuous hidden tracking.

Current browser behavior is already a good boundary:
- user explicitly presses a location/rendezvous action;
- browser requests location;
- one observation is sent.

Keep that model.

Do not:
- poll Geolocation in the background;
- start a watchPosition loop;
- persist a high-frequency trail;
- imply “live tracking” if the product only has one fresh sample.

Suggested user language:
- “Shared 2 min ago”
- “Location not shared”
- “Share my current location”

Not:
- “Tracking Alice”

---

# 3. Group Presence projection

Add a first-class Operator section, suggested name:

`group_presence`

It must be viewer-aware.

Suggested states:
- `SINGLE_TRAVELLER`
- `MEMBER_LOCATION_MISSING`
- `GROUP_LOCATION_STALE`
- `TOGETHER`
- `GROUP_SPLIT_ADVISORY`
- `RENDEZVOUS_TARGET_READY`
- `RENDEZVOUS_ROUTE_READY`
- `SHARED_COMMITMENT_AT_RISK`
- `MEMBER_IDENTITY_UNAVAILABLE`

Example:

```json
{
  "state": "GROUP_SPLIT_ADVISORY",
  "headline": "One traveller is still about 14 min from the next shared stop.",
  "viewer_member_id": "...",
  "rendezvous": {
    "activity_id": "...",
    "title": "Nara Craft Museum",
    "place_id": "...",
    "basis": "NEXT_SHARED_PLAN_ACTIVITY"
  },
  "members": [
    {
      "member_id": "...",
      "display_name": "You",
      "is_viewer": true,
      "presence": "SHARED_RECENTLY",
      "shared_age_seconds": 45,
      "authority": "ADVISORY_FOREGROUND",
      "eta_to_rendezvous_min": 8
    },
    {
      "member_id": "...",
      "display_name": "Sam",
      "is_viewer": false,
      "presence": "SHARED_RECENTLY",
      "shared_age_seconds": 92,
      "authority": "ADVISORY_FOREGROUND",
      "eta_to_rendezvous_min": 14
    }
  ]
}
```

Normal projection must not expose:
- latitude;
- longitude;
- raw browser coordinates;
- another member's location observation payload;
- another member's device token;
- another member's signed traveler token.

Observation ids do not need to be exposed to other members either.

---

# 4. Define “together” conservatively

When at least two current members have fresh, sufficiently precise observations, CityNexus may derive a coarse group state.

Suggested advisory split threshold:
- `max(250m, combined_accuracy * 3)`

But:
- use real geodesic/member-to-member separation or grounded route semantics;
- do not compare only city/place labels;
- stale or imprecise rows are UNKNOWN, not “together”;
- one member with no fresh location is `MEMBER_LOCATION_MISSING`, not off-route.

For FOREGROUND_WEB samples this remains an **advisory** group inference.

Do not create a Guardian/Event solely because two browser coordinates are apart.

---

# 5. Grounded rendezvous target — do not invent a meetup point

R57 v1 does not invent a midpoint in a park.

Resolve a rendezvous target from existing Journey truth, in this order:

1. next shared protected C3/C4 activity with an exact Place;
2. otherwise next common active-plan activity with an exact Place;
3. otherwise `RENDEZVOUS_TARGET_UNAVAILABLE`.

The rendezvous target belongs to the existing Journey.

A regroup route does **not** create a new PlanVersion.

If the group genuinely needs a different destination, normal Agent/discovery/replan owns that later decision.

---

# 6. Per-member route identity

Reuse the R41/R56 Route Session.

Each member route must be semantically bound to:
- Journey;
- that member/traveler;
- that member's exact LocationObservation generation;
- rendezvous Place;
- mode.

Do not let Bob reuse Alice's route just because origin coordinates happen to be close.

A route from:
`location-observation:<alice-row>`
and one from:
`location-observation:<bob-row>`
are distinct semantic operations.

Keep provider provenance exactly as R56 does.

No mock/replay result may become live truth.

---

# 7. User action: “Guide me to the group”

The primary R57 action should operate for the current signed viewer.

Suggested flow:

1. shared Journey screen shows group presence;
2. viewer sees the grounded next shared stop;
3. viewer presses **“Guide me to the group”** / **“带我去集合点”**;
4. product requests one fresh foreground position from that viewer;
5. server binds it to that viewer;
6. one Route Session runs from that observation to the rendezvous Place;
7. user receives ETA/route provenance;
8. active PlanVersion remains unchanged.

Do not let Alice request a route *as Bob*.

Do not require another LLM call for this deterministic navigation operation.

---

# 8. Shared commitment risk

Once member-specific grounded route durations exist, CityNexus may say a named member is likely to miss the rendezvous/shared commitment.

Use:
- member's current grounded route duration;
- next shared commitment start;
- existing safety buffer semantics.

For FOREGROUND_WEB:
- advisory only;
- no authoritative Event/Guardian solely from browser location.

For genuine trusted member location:
- a material risk may create one normal Event and wake the same Guardian;
- incident identity must represent the continuous member-risk episode, not every observation id.

Suggested stable incident identity:
- Journey;
- member/traveler;
- rendezvous/commitment;
- active plan / current Journey epoch.

Do not put observation id or reroute operation id in the *incident identity*. They are evidence inside it.

---

# 9. Multi-member Event causality

If a trusted member-specific group risk becomes material:

Event causal target:
- the member-specific travel leg / current member movement that is creating the risk, if representable;
- downstream shared commitment stays an explicit affected commitment.

Do not silently target an unrelated activity merely because it is the protected stop.

One continuous incident -> one open Event -> one Guardian handoff.

After it is RESOLVED, a genuinely later recurrence may create a new Event.

---

# 10. Member withdrawal and membership changes

If a member leaves/is removed/expires:
- they disappear from current group-presence coordination;
- their old observations remain historical evidence, not current group truth;
- no new route/risk is computed for them.

Do not delete history to make the read model simple.

---

# 11. Privacy-preserving UI

Add a visible shared-Journey card on Live / Operator.

The normal user should see something like:

> **Group**
>
> You · 8 min to Nara Craft Museum
>
> Sam · 14 min to Nara Craft Museum
>
> Mina · location not shared
>
> **Guide me to the group**

If a browser sample is advisory, say so quietly:
> “Times use locations each traveller chose to share.”

Do not show:
- exact coordinates;
- raw accuracy numbers by default;
- observation ids;
- provider JSON;
- a map pin for another member unless a future explicit sharing policy allows it.

Advanced/debug surfaces may expose provenance, not secrets.

---

# 12. Viewer-specific authority

The Operator projection must know who is reading.

Two signed browser contexts viewing the same Journey should see:
- same group/rendezvous facts;
- different `is_viewer`;
- self action only for their own member;
- no ability to submit/route as the other member.

Do not trust a browser-selected member id.

---

# 13. Offline projection

Offline may retain:
- group state;
- rendezvous title;
- per-member coarse state / ETA;
- source authority class;
- captured_at / freshness.

Offline must not persist other members' raw coordinates.

---

# 14. No new “RendezvousAgent”

Use existing:
- JourneyMember;
- LocationObservation;
- Route Session;
- Operator;
- Guardian;
- collective/approval machinery if an itinerary change becomes necessary.

The deterministic layer may answer:
> who shared where, how fresh it is, how long to the grounded common stop, and whether that threatens a commitment.

The external Agent still owns judgment if the *Journey itself* must change.

---

# 15. Focused tests only

Prove the capability, not history:

1. signed OWNER location binds OWNER.
2. signed second member location binds second member.
3. forged member/traveler input cannot rebind the observation.
4. unbound legacy row does not become named member presence.
5. stale member row -> missing/stale, not split.
6. two fresh nearby advisory members -> TOGETHER.
7. two fresh separated advisory members -> GROUP_SPLIT_ADVISORY, no Event.
8. exact coordinates absent from normal group projection.
9. rendezvous selects next shared protected exact Place.
10. no exact shared target -> target unavailable, no invented midpoint.
11. Alice route uses Alice observation; Bob route cannot consume it.
12. two member route sessions stay distinct.
13. regroup route does not mutate PlanVersion.
14. browser advisory risk -> no Guardian Event.
15. genuine trusted material member risk -> one Event / one Guardian handoff.
16. repeated trusted samples in same continuous incident reuse Event.
17. removed member no longer participates in current projection.
18. TypeScript + one focused Playwright with two signed browser contexts.

Do not rerun R33-R56 campaigns.

---

# 16. Focused Playwright product contract

Use two browser contexts:
- OWNER bearer;
- second member bearer.

Minimum visible proof:

1. both contexts open the same shared Journey;
2. each sees themselves marked “You”;
3. OWNER shares a location -> only OWNER's member state updates;
4. second member shares another location -> second member state updates independently;
5. neither response contains the other member's raw coordinates;
6. group becomes advisory split/together as appropriate;
7. current viewer presses “Guide me to the group”;
8. the request uses that viewer's bearer and that viewer's fresh observation;
9. ETA appears;
10. plan remains unchanged.

Mock provider response is acceptable for this Playwright contract if clearly test-only. Backend provider/provenance boundaries are tested separately.

---

# 17. One bounded R57 product experiment

No historical campaign.

Use one fresh shared Journey with two authenticated in-force members.

Preferred honest experiment:

1. both members use separate signed sessions;
2. each explicitly shares one FOREGROUND_WEB location;
3. locations are meaningfully separated;
4. Operator shows `GROUP_SPLIT_ADVISORY`;
5. no authoritative Event / Guardian is created;
6. server resolves one real existing Journey stop as rendezvous;
7. exactly one member presses “Guide me to the group”;
8. exactly one current-location route operation is attempted;
9. live provider if truly configured, otherwise an explicit captured replay / honest unavailable outcome;
10. route result is visible to that member;
11. raw coordinates are not shown to the other member;
12. active PlanVersion unchanged;
13. stop.

Valid outcomes:
- `MEMBER_RENDEZVOUS_ADVISORY_READY`
- `MEMBER_RENDEZVOUS_PROVIDER_DEGRADED`
- `MEMBER_RENDEZVOUS_TARGET_UNAVAILABLE`
- `MEMBER_LOCATION_MISSING`
- `MEMBER_IDENTITY_UNAVAILABLE`

If a genuine trusted multi-member location source is available, a verified material-risk experiment is valid, but do not manufacture `DEVICE_ATTESTED` / `LOCATION_ATTESTED`.

---

# 18. Stop condition

Stop when a fresh shared Journey can truthfully answer:

> **“Whose location is this, who is still away from the next shared stop, and can you guide *me* back to the group without exposing everyone else's coordinates?”**

Do not turn R57 into:
- a map-redesign round;
- background family tracking;
- another verifier campaign;
- a full social network;
- automatic arbitrary meetup-place invention.

End-user capability:

> **“When our group gets separated, CityNexus no longer mixes our locations together. It can tell each of us who still needs to catch up and guide the right person back to the next shared stop, while keeping precise positions private and keeping browser GPS honest.”**
