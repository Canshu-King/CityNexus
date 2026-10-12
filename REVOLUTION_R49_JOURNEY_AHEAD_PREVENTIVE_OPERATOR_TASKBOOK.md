# REVOLUTION R49 — Journey Ahead / Preventive Operator

## Product-direction gate

This task is governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

The required product answer is:

> **CityNexus newly learns to look ahead across the remaining Journey, detect credible future failure modes before they reach the current stop, and prepare or execute preventive recovery early enough that the traveller may never experience the disruption.**

If implementation becomes “add a resilience page” or “prove old predictive code”, stop and correct course.

## Starting truth

R48 is complete at `2639729cc5e4c30d378dd7106ee1df3def5105f8`.

R48 proved the Journey Operator can continuously carry a traveller through:
- departure;
- travel;
- arrival;
- activity start;
- completion;
- automatic handoff to the next activity;
- next-leg route/readiness;
- persistent Guardian enrollment.

Do not rerun R33-R48 historical closures.

## Existing capabilities to connect — do not reimplement

The repository already has:
- `JourneyResilienceSnapshot`;
- `build_resilience_snapshot()`;
- future-activity risk scoring;
- commitment buffer/slack analysis;
- mobility/weather exposure components;
- counterfactual simulations;
- predictive-only Event semantics;
- `run_preemptive_guardian()`;
- R43-R48 Operator / Brain / Discovery / Transactional execution / Continuous flow.

The missing capability is product integration and continuous horizon control.

Today the normal watch scope is intentionally bounded to current + next activities. Predictive analysis exists separately and is not yet one visible part of the continuous Operator.

R49 must make the Operator proactively protect the remaining Journey without corrupting execution truth.

## 1. Journey Ahead projection

Add one Operator section:

`ahead`

It should summarize the **remaining Journey horizon**, not just current/next.

Suggested states:

- `CLEAR`
- `WATCHING_FUTURE`
- `FUTURE_RISK_FOUND`
- `PREVENTION_PLANNING`
- `PREVENTION_READY`
- `WAITING_FOR_APPROVAL`
- `PREVENTION_APPLIED`
- `FUTURE_RISK_UNCERTAIN`
- `PROVIDER_DEGRADED`

Example:

```json
{
  "state": "FUTURE_RISK_FOUND",
  "headline": "A later stop may become risky.",
  "horizon": {
    "remaining_activity_count": 4,
    "lookahead_until": "..."
  },
  "top_risk": {
    "activity_id": "...",
    "title": "...",
    "risk_kind": "FORECAST_WEATHER_EXPOSURE",
    "starts_at": "...",
    "lead_time_minutes": 185,
    "confidence": "GROUNDED"
  },
  "recommended_action": "PREPARE_RECOVERY"
}
```

Normal UI must not expose raw resilience score formulas by default.

## 2. Remaining-Journey horizon

R49 should reason over all nonterminal future activities inside a bounded product horizon.

Suggested v1:
- current local day + next overnight transition;
- or up to the next 12 hours;
- whichever is smaller/larger according to existing temporal shape conventions.

Do not scan the entire multi-week trip every Guardian pulse.

The horizon must be deterministic and testable.

## 3. Risk must be grounded enough to matter

Predictive does not mean imaginary.

A future risk may come from:
- provider forecast;
- provider-backed venue opening conflict;
- frozen mobility slack compression;
- protected commitment buffer erosion;
- reservation/transport timing conflict;
- explicit known future closure;
- other source-linked World Context.

Do not convert:
- model hunch;
- generic “might rain”;
- synthetic estimate

into authoritative preventive mutation when `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.

Model reasoning may rank/interpret risks, but the risk basis remains server-owned evidence.

## 4. Predictive-only is not a material incident

Critical semantic boundary:

A forecast risk that has not happened yet must remain predictive.

Do not:
- mark current activity disrupted;
- create a normal CLOSURE/WEATHER Event that claims reality already changed;
- change execution state.

Use existing predictive-only Event semantics or a clearly equivalent server-owned future-risk record.

User copy:
> “Rain is forecast during your outdoor stop later.”

Not:
> “Your outdoor stop is disrupted.”

## 5. Prevention trigger

Do not launch preventive recovery for every nonzero risk score.

Use a server-owned materiality gate.

A preventive recovery is justified only when:
- evidence is sufficiently grounded/current;
- impact is on a future nonterminal activity;
- lead time is still actionable;
- protected commitments or feasibility are materially threatened;
- prevention can still change the outcome.

Examples:
- severe rain forecast 3h before outdoor activity;
- route delay compresses a C4 transfer buffer below safe threshold;
- future venue exact opening fact conflicts with scheduled arrival.

Low confidence / low impact:
- keep WATCHING_FUTURE.

## 6. External Agent owns prevention strategy

Once server says the future risk is actionable, external Hermes/DeepSeek owns:
- interpreting the risk in Journey/Twin context;
- deciding whether to intervene now;
- choosing a preventive strategy;
- deciding whether open-world discovery is needed;
- deciding whether a replan / booking action should be requested.

Server owns:
- evidence;
- feasibility;
- authority;
- proposal;
- transaction execution.

Do not hard-code:
if rain -> move indoor.

## 7. Use R46 when optionality is weak

If preventive planning finds no/one grounded option:
- R46 open-world recovery discovery may expand the solution space before failure occurs.

This is a major intended integration.

Example:
> “Heavy rain is likely during your outdoor stop. I’m looking now for indoor alternatives nearby so I don’t have to scramble later.”

## 8. Use R45 for group futures

If a preventive change affects multiple travellers:
- R45 collective Operator takes over;
- members may decide before the disruption happens;
- existing collective authority remains required.

Do not let predictive urgency bypass group authority.

## 9. Use R47 for preventive transactions

If an approved preventive recovery needs booking work:
- R47 frozen transaction saga executes it.

Example:
- reserve indoor replacement before cancelling the outdoor booking.

Do not call a predicted risk “prevented” until required operational work is terminal.

## 10. Continuous Day Operator integration

R48 must continue uninterrupted while R49 watches ahead.

Current activity flow remains:
- ON_THE_WAY / IN_ACTIVITY / etc.

Ahead projection is separate context:
> “You’re at the museum now. I’m also watching the 15:00 park visit; rain risk is rising.”

A future-risk recovery must not hijack current execution state unless it actually changes the current activity.

## 11. Prevention status after action

After preventive recovery succeeds:
- mark the predictive risk as prevented/handled using existing server semantics;
- preserve the original forecast evidence;
- show what changed.

User copy:
> “I moved the outdoor stop earlier before the rain window. Your afternoon plan is protected.”

If the forecast later disappears:
- do not pretend the earlier decision was based on certainty;
- timeline should show it was a preventive action from forecast evidence.

## 12. Lead-time-aware urgency

Expose user-facing urgency based on time to affected activity.

Suggested:
- >4h: WATCHING_FUTURE
- 4h..90m: FUTURE_RISK_FOUND
- 90m..30m: PREVENTION_READY/urgent
- <30m: handoff toward normal reactive Guardian if risk becomes actual/current

Do not rely only on risk score.

Time and ability to act matter.

## 13. Durable preventive lineage

One predictive risk must have stable identity across pulses.

Fingerprint at least:
- journey;
- affected activity;
- risk class;
- source observation/event lineage;
- material world epoch.

Repeated pulses should update/reuse the same predictive lineage, not create alert spam.

If evidence materially changes:
- new generation is allowed.

## 14. Notifications

Reuse NotificationEvent.

Only notify when:
- future risk crosses a meaningful action threshold;
- a preventive plan needs approval;
- prevention succeeds/fails.

Do not notify every forecast refresh.

Examples:
> “I spotted a likely problem later today and prepared a safer option.”

> “I handled the later booking change. Your current stop is unchanged.”

## 15. Operator timeline

Add future-looking milestones:

- “Watching the rest of your day”
- “Forecast risk found for 15:00 park visit”
- “Checking alternatives”
- “Preventive plan ready”
- “Approved”
- “Replacement booked”
- “Future risk handled”
- “Continuing current activity”

This is not a developer resilience report.

## 16. Predictive execution boundary

R49 may autonomously:
- observe;
- build resilience snapshot;
- simulate;
- reason;
- discover;
- prepare proposal.

Mutation/booking still obeys:
- AgentPolicy;
- ActionApproval;
- collective authority;
- R47 transaction authority.

No special “predictive override”.

## 17. Focused tests

Only tests that prove the new preventive product capability:

1. current/next flow remains unchanged while ahead horizon includes farther activities.
2. future risk identity is stable across equivalent pulses.
3. low-confidence risk stays WATCHING_FUTURE.
4. grounded future risk enters FUTURE_RISK_FOUND.
5. predictive risk does not mutate execution truth.
6. predictive-only Event is not treated as current material disruption.
7. actionable lead time may start external Agent prevention.
8. model chooses strategy; server still owns feasibility/authority.
9. R46 discovery can expand preventive options.
10. R45 collective authority still applies to group preventive changes.
11. R47 transaction completion required before prevention is marked complete.
12. repeated pulses do not duplicate preventive AgentRuns.
13. stale/materially changed forecast opens new generation rather than reusing unsafe authority.
14. R44 brain outage preserves preventive recovery lineage.
15. current R48 continuous flow continues while prevention works in background.
16. completed Journey stops future-ahead monitoring.
17. TypeScript + focused Journey Ahead Playwright.

Do not rerun R34-R48 historical campaigns.

## 18. One bounded R49 product experiment

Use one fresh Journey with at least 3 activities.

Keep activity A as current/in-progress.

Create one clearly labelled LAB_FIXTURE or captured provider forecast affecting activity C, not A/B.

Sequence:

1. Operator ON.
2. R48 flow shows activity A normally.
3. Journey Ahead scan sees future activity C risk.
4. predictive risk remains explicitly future/predictive.
5. external Agent decides whether prevention is warranted.
6. if needed, it may use R46 discovery and normal replan.
7. if approval is required, ask once through R43.
8. if sandbox booking work is needed, R47 may execute it.
9. current activity A remains untouched.
10. after preventive success, Operator shows current flow + ahead handled state.
11. stop.

Do not:
- convert forecast into fake current incident;
- change A just to make the experiment visible;
- repeat forecast/provider/model until prevention succeeds.

Valid outcomes:
- `JOURNEY_AHEAD_PREVENTION_APPLIED`
- `JOURNEY_AHEAD_PREVENTION_READY`
- `JOURNEY_AHEAD_WATCHING_FUTURE`
- `JOURNEY_AHEAD_PROVIDER_DEGRADED`
- `JOURNEY_AHEAD_BRAIN_BLOCKED`
- `JOURNEY_AHEAD_NO_SAFE_PREVENTION`

## Stop condition

Stop after one future-risk experiment while the current activity remains active.

The end-user capability must be obvious:

> **“CityNexus isn’t only reacting to the stop I’m on. While I’m enjoying this one, it is already watching the rest of the day and can fix a credible future problem before I ever run into it.”**
