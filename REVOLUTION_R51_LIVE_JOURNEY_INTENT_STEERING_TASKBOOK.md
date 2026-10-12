# REVOLUTION R51 — Live Journey Intent Steering

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

## User capability — write this sentence at the top of the implementation result

> **The traveller can now redirect the running Journey in natural language — “I’m tired, make the rest of today easier”, “less walking tonight”, “the kids want ramen” — and CityNexus turns that into a scoped, temporary Journey intent that the existing Operator can plan, coordinate, approve, execute, and automatically expire without corrupting long-term preferences.**

If the work becomes “add a chat box”, “add another mission endpoint”, or “prove semantic compiler again”, stop and correct course.

## Starting truth

R50 is complete at `e658b1db0167fe2d1906ad55bf62058291bf3989`.

R50 proved:
- the same Journey Operator survives a local-day boundary;
- the same standing mission and Autopilot enrollment persist;
- morning briefing prepares Day 2;
- Twin learning is conservative and does not invent a preference;
- unknown route remains unknown.

Do not rerun R33-R50 historical closures.

## Existing capabilities to connect — do not reimplement

Already present:
- free-text Agent/Copilot command intake;
- semantic compiler with entities / constraints / capabilities / effective time;
- JourneyMission;
- standing Operator mission;
- planning preferences;
- Traveler Twin;
- R43 approval;
- R44 brain continuity;
- R45 collective coordination;
- R46 open-world discovery;
- R47 transaction execution;
- R48 continuous flow;
- R49 future horizon;
- R50 overnight continuity.

The product gap:

**Free text is currently treated mostly as a one-shot command/mission. There is no durable, explicit concept of a temporary user intent that steers the already-running Journey Operator for a bounded scope and then expires.**

## 1. First-class Journey Intent

Create a durable server-owned `JourneyIntent` / semantic equivalent.

This is not a global Preference and not a new JourneyMission runtime.

Suggested fields:
- id
- journey_id
- created_by_traveler_id / member_id
- source_text
- intent_kind
- scope_kind
- scope_start_at
- scope_end_at
- target_activity_ids
- constraints_json
- capabilities_json
- preference_hints_json
- status
- semantic_fingerprint
- compiler/provider provenance
- created_at
- superseded_at / expired_at / cancelled_at

Suggested statuses:
- ACTIVE
- NEEDS_CLARIFICATION
- SUPERSEDED
- EXPIRED
- CANCELLED
- SATISFIED

## 2. Temporary means temporary

Examples:

> “I’m tired. Make the rest of today easier.”

Default scope:
- rest of current local day.

> “Less walking for the rest of the trip.”

Scope:
- remaining Journey.

> “Tomorrow morning keep it relaxed.”

Scope:
- next local morning/day-part.

> “I want ramen next.”

Scope:
- next meaningful stop / bounded near-term horizon.

Do not silently turn these into permanent Traveler Twin preferences.

A JourneyIntent may later contribute to Twin learning only if the user explicitly confirms it as a durable preference or existing bounded outcome learning rules independently support it.

## 3. Semantic compiler owns meaning, server owns scope truth

Reuse `compile_semantic_envelope()`.

The external semantic model may extract:
- personal-assistance intent;
- constraints;
- capabilities;
- temporal language;
- preference hints;
- entities.

The server must resolve:
- local date/time boundaries;
- current/next activity ids;
- valid member identity;
- actual Journey horizon;
- exact scope expiration;
- whether clarification is required.

The model must not invent:
- activity ids;
- coordinates;
- prices;
- route times;
- booking status;
- execution truth.

## 4. Intent kinds

Keep v1 bounded.

Suggested:
- PACE
- WALKING_LIMIT
- FOOD_PREFERENCE
- INDOOR_OUTDOOR
- REST_BREAK
- BUDGET_TIGHTENING
- TIME_CONSTRAINT
- INTEREST
- ACCESSIBILITY_NEED
- GENERAL_GOAL

Do not try to build a universal ontology.

Use existing semantic/capability structures when possible.

## 5. Hard capability vs temporary preference

Critical distinction:

> “My knee is injured; I can’t use stairs.”

may be a capability/accessibility constraint and may need stronger persistence/authority.

> “I’m tired today; less walking this afternoon.”

is a temporary Journey intent.

Do not flatten them into the same preference field.

Reuse existing TravelerCapability / Journey capability semantics for genuine capability statements.

## 6. Operator integration

Add `intent` / `active_intents` to the normal Journey Operator projection.

User-facing copy:

> “For the rest of today: keep things easier and reduce walking.”

Show:
- what CityNexus understood;
- how long it applies;
- whether it needs clarification;
- what it is currently doing about it.

User controls:
- Edit / replace
- Cancel
- “Make this a lasting preference” only if an explicit product path exists; do not do it automatically.

## 7. Intent should steer the standing Operator, not create a parallel Agent

When a new ACTIVE intent arrives:
- standing mission remains the same;
- Autopilot remains the same;
- Operator context gains the active intent;
- if the current/future plan already satisfies it, Operator may say so and take no action;
- if material change is needed, the existing Agent reasons and may use normal tools.

Do not create one long-lived mission per intent.

A short child mission/run for evaluating the intent is acceptable if it remains under the same Journey Operator lineage.

## 8. Intent evaluation

After persistence, evaluate:

1. Does the current plan already satisfy this intent?
2. If not, can a bounded replan satisfy it?
3. Are new open-world options needed?
4. Does it affect collective members?
5. Does it require transaction work?
6. Does it require user/collective approval?

This should naturally connect:
- R46 discovery;
- R45 collective;
- R43 approval;
- R47 transaction.

## 9. Example end-to-end behavior

User while activity A is IN_PROGRESS:

> “I’m tired. Make the rest of today easier and keep walking under 15 minutes between stops.”

CityNexus:
- parses PACE + WALKING_LIMIT;
- scope = rest of current local day;
- does not alter current A execution;
- checks B/C/D;
- if current plan violates the temporary limit:
  - Agent may discover closer alternatives;
  - request server-generated replan;
  - ask approval if needed;
- after approved execution:
  - Operator shows the new easier plan;
  - intent remains active until local day end;
- R50 overnight automatically expires it unless user asked for longer scope.

## 10. Expiry and overnight continuity

R50 is a major integration point.

At local day boundary:
- REST_OF_TODAY intents expire;
- NEXT_MORNING intents become active when their scope starts;
- REMAINING_JOURNEY intents persist;
- expired intent disappears from active planning context;
- morning briefing may mention:
  > “Yesterday’s ‘take it easy’ preference has ended.”

Do not carry a one-day mood into Day 2 by accident.

## 11. Supersession

User:

> “Actually, walking is fine now.”

or

> “Forget the relaxed pace — I want to fit more in.”

should be able to replace/supersede the relevant active intent.

Do not leave contradictory temporary intents simultaneously active if they target the same canonical dimension/scope.

Persist history for audit.

## 12. Clarification

If the user says:

> “Make it better.”

and the semantic result is too ambiguous to safely affect the plan:
- status = NEEDS_CLARIFICATION;
- Operator asks one concise question.

Example:
> “Do you mean less walking, a slower pace, or fewer stops?”

Do not start a replan based on vague intent.

External model may formulate the clarification; server owns the allowed scope/options.

## 13. Collective Journeys

One member saying:

> “I’m tired.”

is that member’s intent, not automatically the whole group’s preference.

Server must determine whether satisfying it would materially change the shared Journey.

If yes:
- R45 collective coordination/authority applies;
- other members see:
  > “Alex asked for less walking this afternoon. CityNexus found a shared adjustment and needs the group’s choice.”

Do not let owner status erase other members’ authority.

## 14. Intent and Twin

JourneyIntent is not Traveler Twin evidence by itself.

Rules:
- temporary intent can feed planning context immediately;
- do not increase Twin evidence_count merely because intent exists;
- explicit “remember this for future trips” may use an existing explicit Preference path;
- eventual voluntary outcome evidence may later teach the Twin through normal learning.

## 15. Agent context

Include active intents in:
- standing mission/Agent context;
- planning preference projection;
- R46 discovery prompts;
- R49 future prevention;
- R50 morning briefing when still in scope.

Mark provenance clearly:
- USER_TEMPORARY_INTENT
- USER_STATED_CAPABILITY
- EXPLICIT_PREFERENCE
- LEARNED_SOFT

Do not blend them.

## 16. Intent authority

A natural-language statement can authorize **meaning**, not arbitrary mutation.

Example:

> “Make tonight easier.”

does not by itself authorize:
- cancelling a paid booking;
- exceeding cost bounds;
- changing a shared C4 commitment.

Normal R43/R45/R47 authority remains.

If the intent itself is an explicit command with valid scope:
> “Cancel tonight’s refundable museum booking.”

that still goes through exact object resolution + action policy + approval as already designed.

## 17. UI

Add one simple input to Journey Operator:

**Tell CityNexus what you need**

Examples:
- “I’m tired — slow down this afternoon.”
- “Less walking tonight.”
- “Find ramen for dinner.”
- “Tomorrow morning keep it indoors.”

After submit:

> “Got it — for the rest of today I’ll prioritize fewer stops and shorter walking.”

Then status:
- Checking your remaining plan
- Plan already fits
- Looking for alternatives
- Change ready for approval
- Applied
- Needs clarification

Do not expose semantic JSON.

## 18. Notifications

Do not notify merely because the user just submitted the intent in foreground UI.

Notifications are useful only if:
- asynchronous evaluation later finds an approval is needed;
- an intent will expire and user explicitly asked for reminder;
- a future-scoped intent becomes active.

Deduplicate by intent id + milestone.

## 19. Focused tests

Only tests that prove the new capability:

1. “rest of today” resolves in Journey local timezone.
2. temporary intent is persisted separately from global Preference/Twin.
3. semantic compiler cannot invent Activity ids.
4. ACTIVE intent enters Agent/planning context.
5. current IN_PROGRESS execution remains unchanged.
6. plan already satisfies intent -> no replan.
7. violated walking/pace intent can trigger Agent evaluation.
8. R46 discovery can be used to satisfy a scoped intent.
9. mutation still requires normal R43 authority.
10. booking side effects still use R47 transaction authority.
11. one member’s intent does not become group preference.
12. shared-plan effect enters R45 coordination.
13. ambiguous intent -> NEEDS_CLARIFICATION; no mutation.
14. same semantic submission dedupes.
15. contradictory newer intent supersedes older same-scope intent.
16. REST_OF_TODAY expires at R50 local day boundary.
17. REMAINING_JOURNEY persists overnight.
18. expired intent disappears from Day 2 planning context.
19. temporary intent alone does not create Twin evidence.
20. TypeScript + focused Intent Steering Playwright.

Do not rerun R33-R50 historical campaigns.

## 20. One bounded R51 product experiment

Use one fresh multi-activity Journey with Operator ON.

Keep current activity A IN_PROGRESS.

Submit exactly one authenticated natural-language intent through the new Operator product path:

> “I’m tired. Make the rest of today easier and keep walking low.”

Let the real semantic compiler/external model interpret it once.

Valid product flow:
1. intent persisted with bounded local-day scope;
2. current A remains IN_PROGRESS;
3. Agent checks future activities;
4. it may conclude current plan already satisfies intent, or request a replan/discovery;
5. normal authority applies;
6. Operator shows what it understood and what happened;
7. stop.

Do not change the wording repeatedly to force a replan.

Valid outcomes:
- `INTENT_STEERING_PLAN_ALREADY_FITS`
- `INTENT_STEERING_REPLAN_READY`
- `INTENT_STEERING_APPLIED`
- `INTENT_STEERING_NEEDS_CLARIFICATION`
- `INTENT_STEERING_NO_FEASIBLE_CHANGE`
- `INTENT_STEERING_BRAIN_BLOCKED`

## Stop condition

Stop after one natural-language steering experiment.

End-user capability:

> **“I can change my mind in the middle of the trip by talking normally. CityNexus understands how long that request should matter, uses it to steer the rest of the Journey, asks permission only where needed, and forgets the temporary preference when its scope ends.”**
