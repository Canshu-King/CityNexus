# REVOLUTION R55 — Live Progress Drift / Catch-Up Operator

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

## User capability — put this sentence at the top of the result

> **CityNexus can now tell when the real trip is drifting away from the planned schedule — because the traveller actually left, arrived, started, or finished late — and automatically protect the rest of the Journey. It absorbs harmless lateness quietly, warns only when downstream commitments are threatened, and hands material drift to the same Operator for catch-up or replanning.**

If this becomes “show a lateness badge” or “run more schedule validators”, stop and correct course.

## Starting truth

R54 is complete at `fca6b6a581abb50357a172d69b988f4bc562929f`.

R54 proved:
- conflicting travel facts can remain explicitly contested;
- dependent automation freezes while reality is unresolved;
- unrelated execution continues;
- one bounded user resolution resumes the normal Journey;
- Guardian starts only after authoritative truth exists.

Do not rerun R33-R54 historical closures.

## Existing capabilities to connect

Already present:
- authoritative execution milestones from R42/R48:
  - actual_departed_at / en_route_at
  - actual_arrived_at / arrived_at
  - actual_started_at / started_at_actual
  - completed_at_actual
  - execution truth provenance
- exact frozen JourneyLeg / mobility evidence;
- current/next Journey flow;
- protected Commitments;
- resilience commitment buffers;
- Guardian / Operator;
- R49 future-risk projection;
- R52 Needs-you;
- R45 collective authority;
- R46 discovery;
- R47 transactions.

The gap:

**actual execution timestamps are currently history, not a continuous progress signal. CityNexus does not yet propagate “we are now 35 minutes behind” into the remaining Journey.**

## 1. First-class Progress Drift projection

Add one server-owned product projection:

`progress`

Suggested states:
- `ON_SCHEDULE`
- `AHEAD`
- `MINOR_DRIFT`
- `RECOVERABLE_DRIFT`
- `COMMITMENT_AT_RISK`
- `CATCH_UP_PLANNING`
- `CATCH_UP_READY`
- `NEEDS_ATTENTION`
- `UNKNOWN_PROGRESS`

Example:

```json
{
  "state": "COMMITMENT_AT_RISK",
  "drift_min": 32,
  "basis": {
    "activity_id": "...",
    "milestone": "COMPLETED",
    "planned_at": "...",
    "actual_at": "...",
    "truth_kind": "OPERATOR_CONFIRMED_EXECUTION"
  },
  "next_risk": {
    "commitment_id": "...",
    "activity_id": "...",
    "slack_before_min": 25,
    "slack_after_min": -7
  },
  "headline": "You’re running about 32 minutes behind. Your train connection is now at risk."
}
```

This is a read model until a material drift event is explicitly persisted.

## 2. Drift must come from real execution truth

Authoritative drift sources:
- OPERATOR_CONFIRMED_EXECUTION
- DEVICE_LOCATION_VERIFIED_EXECUTION

Do not use:
- SIMULATED_STATE_TRANSITION for live product proving;
- clock alone;
- planned end passed while activity status is still ACTIVE;
- model estimate.

For an IN_PROGRESS activity after planned end:
- you may say `RUNNING_LONG` / projected risk;
- do not claim an exact final drift until another authoritative milestone exists.

## 3. Milestone comparison

Use the nearest authoritative actual milestone.

Suggested mapping:
- EN_ROUTE: compare actual_departed_at to server-owned planned leave basis if grounded;
- ARRIVED: compare actual_arrived_at to planned arrival/start window;
- IN_PROGRESS: compare actual_started_at to activity.start_at;
- COMPLETED: compare completed_at_actual to activity.end_at.

Prefer COMPLETED for downstream catch-up because it gives a concrete new origin-in-time.

Allow negative drift (ahead of schedule), but do not create recovery for being early unless a venue/commitment rule makes early arrival problematic.

## 4. Propagate drift through real remaining slack

Do not simply add `drift_min` to every future timestamp and call it truth.

For each future activity / protected commitment, calculate remaining slack using:
- authoritative actual milestone time;
- exact frozen JourneyLeg durations where available;
- planned durations of not-yet-executed activities only as plan assumptions;
- schedule gaps;
- commitment start;
- safety buffer.

Expose which pieces are:
- actual execution truth;
- frozen provider mobility;
- plan assumption.

If required edge is unknown:
- risk may be UNKNOWN_PROGRESS / NEEDS_ROUTE;
- do not invent travel time.

## 5. Harmless drift should be absorbed quietly

Example:
- current activity ends 12 min late;
- next stop has 35 min slack.

Result:
- `MINOR_DRIFT`
- no Event
- no AgentRun
- Operator may say:
  > “You’re about 12 minutes behind, but the next protected stop is still safe.”

Autonomy UX means not every lateness becomes an interruption.

## 6. Material drift threshold

Materiality is not a fixed “>15 min = incident”.

Material drift exists when grounded progress causes one of:
- protected commitment slack < required safety buffer;
- next activity becomes infeasible under exact edge + current time;
- reservation/departure anchor becomes unreachable;
- downstream window violation;
- explicit hard Journey constraint breach.

Use server feasibility/commitment semantics.

A 40-minute delay with 90 minutes buffer may be harmless.
A 10-minute delay before a tight train can be material.

## 7. Persist one execution-drift Event only when material

Suggested event:
- type: `EXECUTION_DRIFT` or existing compatible schedule-delay type;
- provenance: `SYSTEM_DERIVED_EXECUTION_FACT`;
- payload includes exact actual milestone truth ref and affected future activity/commitment.

Do not label it provider weather/closure.

Stable fingerprint:
- journey
- authoritative milestone truth
- affected protected target
- drift generation

Repeated pulses must not duplicate it.

## 8. Guardian handoff

Once material drift is grounded:
- enter the normal Guardian/Operator recovery path;
- external Agent decides the catch-up strategy.

Possible strategies the Agent may choose:
- preserve all stops if feasible;
- shorten/skip a flexible future stop;
- reorder;
- use R46 to find a closer alternative;
- protect the train/booking;
- propose a transactional change through R47.

Do not hard-code:
if late -> skip next activity.

## 9. No external-model dependency for detection

R55 detection and materiality must work without model credentials.

Fresh product proof may honestly end:
- drift detected;
- protected commitment at risk;
- Guardian attempts recovery;
- external planning Agent unavailable -> BRAIN_BLOCKED.

That still proves R55.

Do not let deterministic fallback choose a catch-up plan.

## 10. R48 continuous flow integration

R48 remains the foreground journey lifecycle.

Example while user completes A late:

**Now**
A completed.

**Progress**
You’re 28 minutes behind the original plan.

**Next**
B is still reachable.

or:

**Progress**
Your 17:40 train is now at risk.
CityNexus is working on the rest of the day.

Do not create a separate “drift dashboard”.

## 11. R49 integration

Progress drift should become a real input to Journey Ahead.

If a future C/D activity becomes at risk because current execution ran late:
- R49 ahead should see `EXECUTION_DRIFT_EXPOSURE`;
- do not mislabel it weather/mobility provider degradation.

## 12. R52 Needs-you integration

Only interrupt the traveller if:
- recovery requires approval;
- a hard choice is unavoidable;
- route truth is missing and explicit check is required;
- external Agent is blocked and user action can materially help.

Do not create:
> “You are 8 minutes late — OK?”

No useless acknowledgements.

## 13. R51 temporary intent interaction

A temporary intent like:
> “Take it easy today”

may intentionally increase schedule drift tolerance for flexible activities.

But it must not weaken:
- train commitments;
- bookings;
- C4 anchors;
- collective authority.

The Agent can trade flexible schedule against the intent; server hard constraints remain.

## 14. Shared Journey

For a shared trip, one member’s late execution may affect everyone.

If the Journey’s shared current activity is delayed:
- shared progress truth is Journey-level;
- a catch-up plan that changes shared activities still uses R45 collective authority.

Do not turn lateness into owner override.

## 15. Reality conflict integration

If the downstream commitment time is contested under R54:
- do not calculate a precise commitment-at-risk result from the contested time;
- progress state should say truth is unresolved;
- dependent catch-up waits.

No fake precision.

## 16. Transaction protection

R47 actions depending on a catch-up plan still obey normal approval and transaction saga rules.

Do not cancel/rebook merely because drift exists.

## 17. Operator timeline

Useful durable moments:
- “Activity finished 28 min later than planned”
- “Next stop still safe”
- “Train buffer dropped below safety margin”
- “Catch-up planning started”
- “Recovery ready”
- “Schedule protected”

No minute-by-minute noise.

## 18. Focused tests

Only tests proving the product capability:

1. confirmed start 20 min late -> grounded drift.
2. SIMULATED milestone does not prove live drift.
3. completion 30 min late becomes stronger downstream basis.
4. negative drift can be AHEAD without recovery.
5. late completion + ample slack -> MINOR/RECOVERABLE, no Event.
6. small delay + tight C4 commitment -> COMMITMENT_AT_RISK.
7. unknown route -> no fabricated downstream slack.
8. contested reservation time from R54 -> no precise risk decision.
9. same milestone/risk -> one Event only.
10. material drift -> normal Guardian handoff.
11. no external runtime -> honest brain blocked, no deterministic catch-up.
12. current completed execution truth remains unchanged during recovery.
13. R49 ahead receives execution-drift exposure.
14. R45 authority still applies to shared recovery.
15. GET /operator progress is read-only.
16. TypeScript + focused Progress Drift Playwright.

Do not rerun historical campaigns.

## 19. One bounded R55 product experiment

Use one fresh Journey with at least 3 activities and one future protected commitment.

Keep exact route evidence for the relevant next edge.

Execute Activity A normally with authenticated execution truth, but use the deterministic execution clock so its authenticated completion occurs later than A.end_at.

Preferred shape:
- A planned end: 14:00
- actual authenticated Done: 14:28
- future protected commitment around B/C has less than 28 min absorbable slack.

Sequence:
1. Operator ON.
2. A reaches IN_PROGRESS through normal strong execution.
3. authenticated Done at controlled later clock.
4. Activity A becomes COMPLETED; cursor advances normally.
5. Progress Drift derives +28 min from actual completion.
6. server computes future slack from exact known facts.
7. if commitment materially at risk, create exactly one drift Event.
8. Guardian receives it.
9. if external Agent unavailable, stop honestly at `OPERATOR_EXTERNAL_AGENT_BLOCKED`.
10. current/new Activity execution truth is not mutated by the recovery attempt.
11. stop.

Do not:
- manually insert the drift Event;
- rewrite Activity planned times to manufacture the result;
- change commitment after seeing outcome;
- retry with a bigger delay for a prettier closure.

Valid outcomes:
- `PROGRESS_DRIFT_ABSORBED`
- `PROGRESS_DRIFT_CATCH_UP_READY`
- `PROGRESS_DRIFT_TRIGGERED_RECOVERY`
- `PROGRESS_DRIFT_BRAIN_BLOCKED`
- `PROGRESS_DRIFT_ROUTE_UNKNOWN`
- `PROGRESS_DRIFT_REALITY_CONTESTED`

## Stop condition

Stop after one authoritative execution milestone is propagated into the remaining Journey and either safely absorbed or handed once to the existing recovery path.

End-user capability:

> **“If I run late during the trip, I don’t have to recalculate the rest of the day myself. CityNexus notices from what actually happened, knows what is still safe, protects the commitments that are not, and only bothers me when a real decision is needed.”**
