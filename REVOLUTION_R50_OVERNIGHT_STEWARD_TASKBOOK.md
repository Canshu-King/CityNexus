# REVOLUTION R50 — Overnight Steward & Adaptive Morning Briefing

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

Required product answer:

> **CityNexus newly learns to stay responsible for a multi-day Journey overnight: it closes out the day from real execution outcomes, updates the Traveler Twin with bounded soft evidence, watches tomorrow while the traveller sleeps, and wakes them with a prepared next-day briefing instead of making them restart trip management every morning.**

If this turns into a nightly report generator, stop and correct course.

## Starting truth

R49 is complete at `0a12754815e1ed9107608f170ad51ac8586d01fe`.

R49 proved:
- current activity can remain IN_PROGRESS while a farther future activity is tracked independently in Journey Ahead;
- predictive-only risk does not become a current incident;
- GET Operator remains read-only;
- one external Agent run may honestly end NO_FEASIBLE_RECOVERY.

Do not rerun R33-R49 historical closures.

## Existing capabilities to connect

Already present:
- R48 continuous execution flow;
- R49 Journey Ahead;
- R36 OVERNIGHT phase;
- Guardian Autopilot;
- Traveler Twin and `learn_from_journey()`;
- idempotent outcome-event consumption into soft preference evidence;
- next-move/readiness/route;
- notifications;
- offline snapshot.

Critical gap:
- Twin learning is mostly triggered when the entire Journey completes;
- OVERNIGHT is a control-plane phase, not a user-facing stewardship loop;
- morning preparation is not a first-class Operator capability.

## 1. Overnight Steward state

Add one Operator section:

`overnight`

Suggested states:
- `INACTIVE`
- `DAY_CLOSING`
- `LEARNING_FROM_TODAY`
- `WATCHING_TOMORROW`
- `MORNING_READY`
- `MORNING_NEEDS_ATTENTION`
- `OVERNIGHT_PROVIDER_DEGRADED`
- `OVERNIGHT_BRAIN_BLOCKED`

Overnight must not become a new execution authority.

## 2. Entering overnight mode

Enter only when all are true:
- Journey ACTIVE;
- no Activity is EN_ROUTE / ARRIVED / IN_PROGRESS;
- there is a future nonterminal activity on a later local date;
- local time is in the existing overnight window or the prior local day is effectively complete.

Do not auto-complete an unfinished activity because the clock passed midnight.

If an Activity is still IN_PROGRESS at 00:30:
- R48 foreground remains authoritative;
- overnight steward stays inactive or NEEDS_ATTENTION.

## 3. Day boundary identity

Create a stable server-owned local-day identity:
- journey_id;
- local date;
- active plan version generation.

One local day should close once.

Repeated overnight pulses must not:
- relearn the same outcomes repeatedly;
- resend the same morning briefing;
- reacquire the same facts without expiry/material change.

## 4. Learn today before planning tomorrow

At a valid day close, call the existing bounded learning path over actual JourneyOutcomeEvents.

Prefer reusing `learn_from_journey()`; do not create a second preference learner.

Important:
- only existing eligible voluntary/explicit signals become learned evidence;
- system-induced recovery actions must not become user preference;
- strategic skips already marked non-learning remain non-learning;
- explicit preferences continue to override learned soft evidence.

Record:
- Twin snapshot before;
- new consumed outcome ids;
- Twin snapshot after;
- which learned dimensions changed.

User-facing copy:
> “I learned that you tended to prefer indoor stops today.”

Do not claim:
> “You definitely prefer indoor activities.”

## 5. Learning may influence tomorrow, but never silently rewrite it

New Twin evidence may be supplied to:
- tomorrow’s Agent reasoning;
- R49 preventive ranking;
- R46 discovery intent;
- candidate scoring.

It must not by itself:
- mutate PlanVersion;
- cancel bookings;
- skip activities;
- change commitments.

If a learned preference makes a preventive change attractive:
- normal Agent/authority flow applies.

## 6. Tomorrow horizon

Build a next-day preparation projection covering at least:
- first 2-3 nonterminal activities of the next local day;
- first exact route/launch requirement;
- venue readiness;
- active commitments/reservations;
- R49 future risks;
- required departure time if grounded.

Do not scan the entire remaining trip every overnight pulse.

## 7. Morning briefing

The user should wake to one concise Operator briefing:

> **Good morning — I’ve prepared today’s trip.**
> First stop: Tsukiji at 09:00
> Leave around 08:18
> Route: 22 min
> Weather: light rain after 14:00
> One thing to watch: outdoor garden later
> I’m already watching it.

If route/venue facts are unavailable:

> “Your first stop is ready, but I still need a reliable route before I can tell you when to leave.”

Do not fabricate ETA.

## 8. Read-only overnight provider work

While Operator is enabled, overnight steward may autonomously perform bounded **read-only** preparation already permitted by the system:
- refresh expiring World Context facts;
- inspect venue readiness;
- inspect provider-backed route evidence;
- build resilience snapshot;
- use existing cached/frozen facts.

Do not automatically create paid bookings or mutate the plan at night.

If explicit route acquisition remains an operation requiring a product action under current policy:
- queue/surface “Route check needed” for morning;
- do not bypass R41 authority semantics.

If existing AgentPolicy explicitly allows bounded read-only provider acquisition, reuse it.

## 9. Preventive overnight recovery

R49 may identify a credible tomorrow risk overnight.

Allowed:
- model reasoning;
- discovery;
- proposal preparation.

Mutation still obeys:
- R43 approval;
- R45 collective authority;
- R47 transaction authority.

For non-urgent future risks, prefer preparing the decision for morning rather than waking the user.

For genuinely time-sensitive booking/commitment risk, existing notification priority rules may surface it.

Do not invent a “nighttime override”.

## 10. Morning activation

At the next local morning:
- same Operator remains enabled;
- same standing mission remains active;
- no user restart;
- R48 foreground flow should point to the first activity of the day;
- overnight state becomes MORNING_READY or MORNING_NEEDS_ATTENTION;
- morning briefing notification dedupes once per local day.

## 11. Multi-traveller journeys

For shared Journeys:
- one overnight steward per Journey;
- Twin learning remains per traveller from that traveller’s eligible evidence;
- shared morning briefing uses shared Journey facts;
- member-specific preference insights remain scoped to the correct traveller.

Do not merge everyone into one Twin.

## 12. Offline continuity

Offline snapshot should include:
- overnight state;
- day boundary date;
- Twin learning summary;
- tomorrow first activity;
- route/readiness summary;
- morning briefing captured_at.

Offline does not advance the day or trigger learning.

## 13. Focused tests

Only tests proving the new capability:

1. valid multi-day gap enters WATCHING_TOMORROW.
2. current IN_PROGRESS across midnight prevents false day close.
3. same local day closes idempotently.
4. eligible Day 1 outcome becomes Twin soft evidence before Journey completion.
5. non-learning/system outcome does not become preference.
6. explicit preference still overrides learned soft evidence.
7. new Twin evidence is available to tomorrow Agent/planning context.
8. Twin learning alone does not mutate active plan.
9. tomorrow projection selects next local-day activities.
10. morning briefing uses exact route only when grounded.
11. missing route never fabricates leave-by.
12. same morning briefing notification dedupes.
13. Operator/Autopilot remain same enrollment across night.
14. R49 future risk may remain visible in morning briefing.
15. shared Journey keeps per-member Twin evidence separate.
16. completed Journey does not open another overnight cycle.
17. TypeScript + focused overnight Playwright.

Do not rerun historical proof campaigns.

## 14. One bounded R50 product experiment

Use one fresh 2-day Journey.

Day 1:
- at least one real authenticated execution outcome eligible for bounded Twin learning;
- finish the final Day 1 activity without completing the whole Journey.

Advance using deterministic execution clock into overnight.

Prove:
1. Journey remains ACTIVE.
2. Operator remains enabled.
3. no activity is falsely auto-completed.
4. one day-close cycle consumes eligible Day 1 outcome evidence.
5. Traveler Twin changes only if genuine eligible evidence exists.
6. tomorrow first activity is projected.
7. morning briefing is created once.
8. same standing mission / Autopilot enrollment persists.
9. stop.

Do not force a Twin preference if the eligible outcome produces none.

Valid outcomes:
- `OVERNIGHT_STEWARD_MORNING_READY`
- `OVERNIGHT_STEWARD_ROUTE_NEEDED`
- `OVERNIGHT_STEWARD_NEEDS_ATTENTION`
- `OVERNIGHT_STEWARD_NO_NEW_LEARNING`
- `OVERNIGHT_STEWARD_PROVIDER_DEGRADED`

## Stop condition

Stop after one local-day boundary and next-morning handoff.

End-user capability:

> **“I can go to sleep without ending the trip. CityNexus keeps responsibility overnight, learns carefully from how today actually went, checks tomorrow, and is ready with the next day when I wake up.”**
