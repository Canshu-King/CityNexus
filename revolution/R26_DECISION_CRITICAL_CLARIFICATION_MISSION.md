# Revolution R26 — Decision-Critical Clarification

## The leap

R25 proved strategic restraint.

R26 must prove epistemic restraint about human values.

Target behavior:

```text
ACTIVE Journey
  -> two grounded, fully feasible strategic options
  -> server facts are sufficient
  -> TravelerTwin / learned-soft preference is weak, conflicted or decision-sensitive
  -> real Agent inspects Journey/Twin/horizon
  -> server proves the decision would flip under plausible explicit user preference answers
  -> Agent does NOT guess
  -> one machine-visible CLARIFICATION_REQUIRED question is persisted
  -> user answers
  -> answer becomes explicit journey-scoped intent
  -> child/resumed mission continues from the same decision context
  -> ranking/TAKE_NOW/DEFER changes according to the answer
  -> Gateway remains authority
  -> Journey continues and COMPLETES
```

The opposite control is equally important:

```text
if the user answer would NOT change the action
=> do not ask
```

This is value-of-information over human intent.

## Hard human-agency rules

- explicit current Journey intent > explicit persisted preference > learned soft > neutral;
- learned soft may never silently become an explicit user statement;
- clarification answer is journey-scoped by default;
- cross-Journey memory requires an explicit separate "remember this" choice;
- factual unknowns must be resolved from providers, not offloaded to the user;
- health/accessibility/capability facts are never inferred through preference clarification;
- the model may propose a question, but the server decides whether the clarification is decision-critical and admissible;
- one unresolved clarification per decision epoch;
- no nagging loops.

## Phase 0 — tighten R25 strategic authority

### 0A. Horizon feasibility must be real

Upgrade horizon items to expose a deterministic feasibility contract.

For every current/future option used by strategic DEFER, compute or reuse:
- canonical opening compatibility;
- visit duration fit;
- route duration;
- safety buffer;
- commitment slack;
- cost truth;
- deterministic hard-feasibility result;
- reason codes.

Use the existing opportunity-window / feasibility code.

Do not invent a second feasibility engine.

A horizon item may be:
- GROUNDED_FEASIBLE;
- GROUNDED_INFEASIBLE;
- REVALIDATION_REQUIRED.

DEFER requires two individually GROUNDED_FEASIBLE options.

### 0B. Reserve unavoidable future cost

Optional budget must subtract:
- declared protected allocations;
- already consumed cost;
- known future committed/locked unavoidable monetary obligations.

It must NOT subtract:
- ordinary optional future activities merely because they appear on the active plan.

Expose budget basis in the Twin so the Agent does not infer it from prose.

## Phase A — deterministic decision-sensitivity receipt

Add a small read-only server calculation near the existing horizon/F4 preference surface.

Conceptually:

`decision_sensitivity(options, explicit_intent, learned_context) -> receipt`

Input:
- at most two materially different hard-feasible actions;
- current explicit mission preferences;
- persisted explicit preferences;
- learned soft evidence;
- cost/time/commitment facts.

Output:
- current top action;
- preference dimensions that distinguish the actions;
- current preference evidence class/confidence;
- counterfactual top action under bounded explicit preference answers;
- `decision_sensitive: true/false`;
- reason code.

No probability model required.

A decision is clarification-eligible only when:
1. hard facts do not already determine one action;
2. current explicit intent does not already answer the question;
3. learned/soft evidence is insufficient/conflicted;
4. plausible explicit answers would select different actions;
5. expected consequence is material enough to justify interrupting the user.

Do not ask because "confidence is below 0.8".
Ask because the answer changes the action.

## Phase B — machine-visible clarification contract

Do not create a new chat framework.

Use the existing JourneyMission lifecycle.

Smallest preferred server contract:
- add `CLARIFICATION_REQUIRED` to the typed mission completion outcomes;
- persist one compact clarification payload on the mission or in one small dedicated record;
- mission status becomes `WAITING_FOR_USER`;
- AgentRun completes cleanly with server_trace classification.

Clarification payload:
- clarification_id;
- decision_epoch / active_plan_version_id;
- question;
- 2-3 bounded options;
- preference dimension;
- action mapping preview, e.g. option A favors TAKE_NOW, option B favors DEFER;
- expires/stale condition;
- reason: DECISION_SENSITIVE_HUMAN_VALUE.

Do NOT expose hidden chain-of-thought.

The server must reject CLARIFICATION_REQUIRED when the sensitivity receipt says the answer would not alter the decision.

## Phase C — one-question discipline

The final question should be natural and short.

Example shape:

"You have enough budget for either the nearby garden now or the museum later, but not both. For this trip, which matters more: garden time now, or museum time later?"

Do not:
- ask for facts the server can fetch;
- ask multiple open-ended questions;
- ask the user to calculate budget/travel;
- mention internal score numbers unless useful.

The Agent may draft the language.
The server owns:
- available options;
- candidate IDs;
- sensitivity proof;
- allowed answer set.

## Phase D — resume through parent/child mission linkage

JourneyMission already has `parent_mission_id`.

Use it.

When the user answers:
- validate clarification is still current;
- verify active plan/decision epoch has not changed;
- persist answer as CURRENT_EXPLICIT_MISSION preference by default;
- create/resume a child mission linked to the parent;
- carry the original authority envelope;
- do not widen autonomy/cost/loss bounds.

If the context changed while waiting:
- mark clarification stale;
- recompute before acting.

## Phase E — scope of learned memory

Default answer scope:
`THIS_JOURNEY`.

Optional explicit user choice:
`REMEMBER_FOR_FUTURE_TRIPS`.

Only the latter may write cross-Journey explicit preference/evidence.

Do not silently turn a one-trip clarification into permanent TravelerTwin memory.

## Phase F — real R25-style strategic proof

Construct one real two-option horizon where:
- W1 and W2 are both canonical and fully hard-feasible;
- both individually affordable;
- shared resource means both cannot be taken;
- current learned-soft context is weak/conflicted/near-tied;
- no current explicit mission preference resolves it.

The real configured Agent should:
1. inspect;
2. see decision sensitivity;
3. choose/request clarification instead of TAKE_NOW or DEFER.

Required:
- no active PlanVersion mutation;
- no optional resource spend;
- no hidden reservation;
- one persisted clarification.

Then supply a real user answer favoring W2.

Resume through parent/child mission.

Required:
- CURRENT_EXPLICIT_MISSION now dominates learned context;
- Agent/server chooses DEFER;
- W1 remains unused;
- when W2 becomes current, revalidate current truth/mobility;
- execute normally;
- Journey COMPLETED.

## Phase G — reverse-answer A/B

Use the same hard facts in a cloned/fresh comparable Journey.

Answer favoring W1.

Required:
- resumed strategy changes to TAKE_NOW (or equivalent W1-consistent action);
- no server fact changed merely to force the result.

This proves the clarification actually controls behavior.

## Phase H — do-not-bother control

Create a second decision where:
- one action is hard-dominant;
or
- both plausible user answers yield the same action;
or
- explicit mission already resolves the preference.

The Agent/server must NOT ask.

Machine receipt:
- `decision_sensitive=false`;
- no clarification row/payload;
- normal action or NO_ACTION continues.

This is mandatory.

## Phase I — provider-fact control

Create a case where the uncertainty is opening/cost/mobility, not preference.

The Agent must:
- acquire/revalidate provider facts;
- NOT ask the user "is this place open?" or "how much does it cost?".

Human clarification is only for human values.

## Phase J — stale clarification

If:
- active plan changes;
- option becomes unavailable;
- evidence expires;
- Journey cursor passes the window;

before the user answers:
- clarification becomes STALE;
- answer cannot mutate old context;
- server recomputes.

No zombie questions.

## Anti-ORD rules

- one capability branch;
- one final result report;
- no R26.1;
- no new generic chat system;
- no LLM confidence framework;
- no recommender rewrite;
- no user-survey flow;
- no asking questions merely to appear interactive;
- no broad suite after every patch.

## Success levels

### REVOLUTION_A — decision-critical uncertainty
Server proves a real grounded decision is sensitive to a human value preference and distinguishes that from missing world facts.

### REVOLUTION_B — selective clarification
REVOLUTION_A + real Agent produces one server-validated CLARIFICATION_REQUIRED outcome and does not ask in a non-sensitive control.

### REVOLUTION_C — clarification changes real behavior
REVOLUTION_B + user answer is persisted as current explicit Journey intent, child/resumed mission chooses the corresponding strategy, Gateway remains authoritative, and the Journey executes to completion.

### REVOLUTION_D — reversible collaborative autonomy
REVOLUTION_C + opposite answer flips the strategy under comparable hard facts, plus a factual-uncertainty control uses provider acquisition instead of asking the user.

Target C/D.

## Final report

One file:

`REVOLUTION_R26_DECISION_CRITICAL_CLARIFICATION_RESULT.md`

Include:
- base/final SHA;
- R25 feasibility/budget invariant fixes;
- Journey / active plan / traveler;
- the two hard-feasible actions;
- decision sensitivity receipt;
- TravelerTwin learned evidence/conflict;
- real Agent provider/model;
- parent AgentRun;
- exact machine-visible clarification payload;
- user answer + scope;
- child mission linkage;
- explicit mission preference projection;
- resumed AgentRun tool trace;
- Gateway/authority result;
- final execution;
- opposite-answer A/B;
- do-not-bother control;
- provider-fact control;
- focused regression delta.

## Success sentence

R26 closes when this is a machine fact:

> CityNexus recognized that the missing information was not another provider fact but the traveler's own value judgment, asked exactly one question because the answer could change the plan, resumed the same governed mission with that explicit answer, changed its strategy accordingly, and stayed silent when asking would not have changed anything.
