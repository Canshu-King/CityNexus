# REVOLUTION R48 — Continuous Journey Day Operator

## Product-direction gate

This task is governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

The required product answer is:

> **CityNexus newly learns to carry the traveller continuously from one activity to the next across the day: departure, arrival, activity start, completion, next-stop handoff, route/readiness refresh, and ongoing Guardian monitoring become one continuous Operator experience instead of isolated API actions.**

If implementation becomes “add arrive/begin/complete buttons” or “prove R42 again”, stop and correct course.

## Starting truth

R47 is complete at `53656c8f17f857c0f56629876ee7bf8ba365068a`.

R47 proved:
- approved recovery can compile a frozen transactional saga;
- one user approval can resume exact server-owned execution;
- sandbox booking + commitment work completes through normal commerce services;
- no second model call is needed;
- Operator returns to WATCHING only after operational completion.

Do not rerun R33-R47 historical closures.

## Existing capabilities to connect — do not reimplement

The repository already has:
- R36 phase projection;
- R37 presence projection;
- R38 readiness;
- R39 launch origin;
- R41 exact route session;
- R42 confirmed departure;
- activity transitions:
  - EN_ROUTE
  - ARRIVED
  - IN_PROGRESS
  - COMPLETED
- completion automatically advances `journey.current_activity_id` to the next nonterminal activity;
- Guardian / Operator / World Context;
- notifications;
- offline snapshot.

The gap is continuity.

Today the traveller can confirm departure, but arrival/begin/complete are still mostly raw execution endpoints. The Operator does not yet carry the user through the whole lifecycle.

## 1. Continuous Journey Flow projection

Create one server-owned product projection that merges:
- current Journey status;
- current activity status;
- R36 phase;
- R37 presence;
- R38 readiness;
- route state;
- next activity;
- operator state.

Suggested product states:

- `PREPARING_TO_LEAVE`
- `LEAVE_NOW`
- `ON_THE_WAY`
- `ARRIVAL_READY`
- `ARRIVED`
- `READY_TO_BEGIN`
- `IN_ACTIVITY`
- `READY_TO_COMPLETE`
- `BETWEEN_STOPS`
- `NEXT_STOP_PREPARING`
- `DAY_COMPLETE`
- `NEEDS_ATTENTION`

This projection is not a new execution authority.

## 2. Minimal human confirmations

The normal journey should feel like one continuous conversation.

Suggested actions:

- “I’m leaving” -> existing R42 strong depart path
- “I’m here” -> existing arrive transition
- “Start” -> existing begin transition
- “Done” -> existing complete transition

Do not create new shadow state fields.

Each action must use the existing execution truth gate.

For authenticated traveller UI:
- explicit actions should use `OPERATOR_CONFIRMED_EXECUTION`;
- no silent fallback to SIMULATED.

## 3. Presence-aware arrival suggestion

R37 presence can help decide when to show “I’m here”.

Rules:
- NEAR_TARGET may enable/surface arrival CTA;
- VERIFIED_AT_TARGET may provide stronger evidence if it truly satisfies the existing trusted location gate;
- FOREGROUND_WEB remains advisory and cannot auto-write ARRIVED;
- location unavailable must never block a manual authenticated arrival confirmation.

Never:
- proximity alone -> ARRIVED;
- clock says activity started -> ARRIVED;
- route ETA elapsed -> ARRIVED.

## 4. Begin suggestion

After ARRIVED:
- show “Ready to start?”;
- allow one explicit authenticated begin confirmation.

If product policy later permits trusted-device auto-begin, that is a future slice.

R48 v1 should keep begin human-confirmed.

## 5. Completion suggestion

While IN_PROGRESS:
- use planned end time only to suggest completion;
- do not auto-complete on clock.

Suggested states:
- before planned end -> IN_ACTIVITY
- around/after planned end -> READY_TO_COMPLETE

The CTA is:
**Done**

Completion must use the existing strong execution transition.

## 6. Automatic next-stop handoff after completion

This is the critical R48 value.

After one activity completes:
- existing server already activates the next activity and advances `current_activity_id`;
- R48 must immediately rebuild:
  - Next Move
  - launch/current origin semantics
  - route requirement
  - readiness
  - departure activation
  - Guardian monitored activity scope
  - offline snapshot

The user should not need to leave/reopen the Journey or manually “start next activity setup”.

Example:
> “Museum done. Next: Nara Park at 14:20. I’m checking the route now.”

If an exact edge already exists:
> “Next stop is 16 min away. Leave by 13:54.”

If it does not:
> “I need to check the route to your next stop.”
and surface the normal R41 explicit route action if product policy requires explicit acquisition.

## 7. Route origin after first activity

Do not reuse the initial R40 planned launch origin once execution has progressed.

For activity N -> N+1:
- completed/current activity exact Place is the normal route origin;
- fresh location may help if explicitly chosen/current;
- old hotel/arrival launch contract must not teleport the route origin backward.

This should naturally reuse R39 precedence.

## 8. Incident continuity during transitions

Guardian must remain active while:
- EN_ROUTE;
- ARRIVED;
- IN_PROGRESS;
- BETWEEN_STOPS.

If a disruption occurs during an activity or between stops:
- normal R43-R47 Operator recovery takes over;
- after recovery, R48 resumes the continuous flow from current execution truth.

Do not create a separate “day loop Agent”.

The Journey Operator is the Agent.

## 9. Activity completion and pending operations

Do not advance into a false “all good” state if:
- transactional recovery is PARTIALLY_APPLIED;
- collective authority is waiting;
- Operator needs attention;
- next activity has a blocker.

Completion of the current activity can still be real execution truth, but the next-stop handoff should surface NEEDS_ATTENTION instead of pretending next travel is ready.

## 10. Notifications

Reuse NotificationEvent.

Useful cues:
- “You’re near your stop. Confirm when you arrive.”
- “Ready to start?”
- “Your planned activity window is ending. Mark it done when you’re finished.”
- “Next stop: …”

Deduplicate by activity + milestone band.

Do not notify every minute.

## 11. User-facing Journey strip

Add one compact live strip/card that always answers:

1. Where am I in the Journey?
2. What should I do next?
3. What will CityNexus do after I act?

Example:

**On the way to 依水園**
22 min route · arrival expected around 09:00
[I'm here]

After arrival:

**At 依水園**
Ready when you are
[Start]

During:

**Visiting 依水園**
Planned until 10:15
[Done]

After completion:

**Next: Nara Park**
I’m checking the next route.

The user should not need separate Guardian, Route, Next Move, execution pages to understand the day.

## 12. Day completion

When the last activity completes:
- Journey.status becomes COMPLETED through existing code;
- Operator flow state = DAY_COMPLETE;
- Autopilot should stop creating new recovery work for a completed Journey;
- final timeline shows Journey completed;
- learning/twin update continues through existing path.

Do not invent more tasks after completion.

## 13. Authority invariants

R48 may intentionally write execution state only after valid strong confirmation:
- ARRIVED
- IN_PROGRESS
- COMPLETED

Allowed supporting writes:
- JourneyOutcomeEvent
- AuditLog
- NotificationEvent
- Offline snapshot

Forbidden automatic writes from clock/presence alone:
- ARRIVED
- IN_PROGRESS
- COMPLETED

Forbidden:
- plan mutation merely to advance execution;
- AgentRun just to move to the next activity;
- route provider call from GET projection.

Keep `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.

## 14. Focused tests

Only tests needed for the continuous user loop:

1. EN_ROUTE -> ON_THE_WAY.
2. NEAR_TARGET shows ARRIVAL_READY but does not write ARRIVED.
3. manual authenticated “I’m here” -> ARRIVED.
4. missing auth fails closed; no SIMULATED fallback.
5. ARRIVED -> READY_TO_BEGIN.
6. authenticated Start -> IN_PROGRESS.
7. clock after planned end -> READY_TO_COMPLETE but not COMPLETED.
8. authenticated Done -> COMPLETED.
9. completion advances current_activity_id to next activity.
10. next activity automatically gets fresh Next Move/readiness projection.
11. old launch contract does not override previous/completed activity origin.
12. next exact mobility fact is reused when available.
13. missing route surfaces explicit route check, not fake ETA.
14. Guardian remains enabled through all milestones.
15. incident during IN_ACTIVITY can enter existing Operator recovery and later return to flow.
16. last activity completion -> DAY_COMPLETE.
17. completed Journey stops future autonomous recovery work.
18. TypeScript + focused continuous-day Playwright.

Do not rerun R34-R47 proof campaigns.

## 15. One bounded R48 product experiment

Use one fresh Journey with at least 2 activities.

No need for random disruption.

This is a continuity product experiment.

Preferred sequence:

1. Operator ON.
2. first activity has a grounded route/readiness.
3. authenticated “I’m leaving”.
4. one authenticated “I’m here”.
5. one authenticated “Start”.
6. one authenticated “Done”.
7. server advances to activity 2.
8. R48 immediately surfaces activity 2 as next and recomputes next-step readiness/route state.
9. stop after proving the handoff.

Do not fake physical location.
The arrival action can be operator-confirmed if authenticated.

Do not auto-advance arrival/begin/complete from time.

Valid outcomes:
- `CONTINUOUS_JOURNEY_HANDOFF_READY`
- `CONTINUOUS_JOURNEY_NEXT_ROUTE_NEEDED`
- `CONTINUOUS_JOURNEY_BLOCKED_AUTH`
- `CONTINUOUS_JOURNEY_NEEDS_ATTENTION`

Do not rerun for a prettier route result.

## Stop condition

Stop after one full activity lifecycle and successful handoff to the next activity.

The end-user capability must be obvious:

> **“I no longer manage each stop as a separate workflow. CityNexus stays with me from leaving, to arriving, to doing the activity, to finishing it, and immediately takes care of what comes next.”**
