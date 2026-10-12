# Revolution R23 — Adaptive Traveler Twin

## The leap

R23 turns R22 positive autonomy into adaptive autonomy.

Target behavior:

```text
Journey A executes real activities
  -> outcome/feedback evidence is persisted
  -> TravelerTwin derives bounded LEARNED_SOFT preference evidence
  -> evidence remains inspectable, decayable and clearable
  -> fresh Journey B / later opportunity exposes multiple grounded choices
  -> deterministic ranking changes because of learned evidence
  -> real Agent sees the TravelerTwin context
  -> Agent chooses a materially different grounded opportunity
  -> Gateway / canonical facts / live mobility remain authoritative
  -> explicit user preference can override or clear the learned bias
```

The system is learning a ranking preference, not discovering a hidden human truth.

## Hard human-agency invariants

- learned behavior is NEVER a hard constraint;
- learned behavior is NEVER a TravelerCapability;
- no medical/accessibility need may be inferred from dwell/skip/complete behavior;
- explicit user preferences and explicit mission intent always override LEARNED_SOFT;
- user can clear learned evidence;
- contradictory evidence must reduce certainty / expose conflict rather than silently overwrite;
- one activity completion cannot mint a strong permanent preference;
- disruption-forced behavior must not be treated as taste.

## Phase 0 — tiny R22 carry-forward fixes

Do these inline, then move on.

### 0A. Minimum positive-opportunity threshold

Before persisting `OPPORTUNITY_WINDOW`, require a bounded minimum available duration.

Preferred:
- explicit setting / named policy constant;
- default large enough to prevent trivial Agent wakeups;
- exact value documented and tested.

Do not hardcode city-specific timing.

### 0B. ACTIVE no-action control

Retain a focused test/runtime control:
- ACTIVE Journey;
- short or low-value opportunity;
- no plan mutation.

Do not spend the round repeating R22.

## Phase A — trustworthy learning evidence classes

Replace the current completion=preference shortcut.

Create a small evidence hierarchy.

### Strong evidence
Explicit feedback supplied by the traveler, e.g.:
- liked this experience;
- not interested in this kind of experience;
- explicit preference update.

Use existing OutcomeEvent infrastructure, adding narrow event types if needed.

Strong evidence may produce meaningful LEARNED_SOFT weight after one explicit signal.

### Medium evidence
Voluntary, choice-bearing behavior where there was a real alternative:
- traveler approved an optional opportunity;
- traveler rejected one grounded option and chose another;
- repeated selection of a category across separate Journeys.

This must be linked to the actual candidate/proposal/action history.

### Weak evidence
Execution-only telemetry may contribute only when it is genuinely choice-bearing.

Plain:
- ACTIVITY_COMPLETED
- ACTIVITY_SKIPPED

must NOT automatically mean like/dislike.

Suppress/discount evidence when:
- activity was protected/locked/C4;
- skip was caused by disruption/replan;
- activity completion had no meaningful alternative;
- event provenance says system recovery forced the outcome.

Persist:
- evidence class;
- direction;
- strength;
- confidence;
- source outcome IDs;
- Journey IDs;
- expiry.

## Phase B — use canonical category/tag vocabulary

Learned preference dimensions must be comparable with future candidate facts.

Use server-owned Place category/tags.

Preferred:
- canonical category + bounded interest tags;
- normalized aliases only where already defined;
- no free-form LLM-created personality dimensions.

Examples:
- museum;
- garden;
- craft;
- food;
- heritage;
- indoor/outdoor when backed by tags.

The model may explain evidence, but the dimension itself comes from server-owned vocabulary.

## Phase C — make contradictions honest

If evidence supports opposite directions:
- keep both evidence trails;
- expose a conflict;
- reduce effective learned weight or confidence;
- do not choose the latest row and pretend certainty.

Explicit user preference/mission intent must win over learned evidence.

If the user clears learned evidence:
- learned ranking effect disappears;
- explicit preferences stay untouched.

## Phase D — make learning causal in opportunity selection

R23 must prove more than "TravelerTwin JSON changed."

Extend the existing F4 opportunity path to accept a bounded candidate set and generate multiple grounded opportunity proposals when appropriate.

Current R22 behavior effectively consumes the first valid hinted Place.

For R23:
- allow 2-3 server-validated Place hints;
- each candidate independently requires canonical facts + both live mobility legs;
- materialize at most the bounded feasible set;
- score each using the same deterministic feasibility + verified preference fit;
- LEARNED_SOFT may affect preference-fit/ranking only;
- hard feasibility, commitments, cost and mobility remain unchanged authority.

Do not build a new recommendation engine.

## Phase E — persist the model-visible learning context in machine trace

The Agent system prompt already receives TravelerTwin soft context.

For proof and observability, make the persisted read surface expose a compact TravelerTwin summary as well.

Preferred:
- add compact learned preference context to `inspect_journey` or `inspect_twin`;
- include dimension, direction, effective weight/confidence, source class and conflict;
- do not dump full historical text.

This allows the AgentRun receipt to prove exactly what learned context the model saw.

## Phase F — real A/B learning proof

Use at least two Journey phases with the SAME traveler.

### Baseline
Before learned evidence:
- create a fresh truthful opportunity with at least two materially different real candidates;
- both candidates canonical and live-mobility feasible;
- record deterministic scores/ranking.

Do not require a specific random model choice for the baseline; the server ranking receipt is enough.

### Learning
Execute/record real outcome + explicit/choice-bearing feedback from Journey A.

Process/refresh TravelerTwin.

Record:
- evidence row IDs;
- evidence class;
- strength/confidence;
- learned snapshot.

### Adaptive run
Fresh Journey B or later independent window:
- same traveler;
- multiple grounded candidates;
- no Place ID in mission;
- Agent sees learned soft context;
- deterministic F4 ranking changes materially because of the learned preference;
- real Agent chooses/accepts a grounded candidate consistent with that evidence;
- live mobility + Gateway remain normal.

No candidate may be made infeasible just to force the desired learned choice.

The choice difference must come from preference evidence, not a hidden hard constraint.

## Phase G — explicit override control

Prove human agency.

After learned evidence prefers category A:
- add explicit Journey/user preference for category B or explicit dispreference for A;
- recompute planning context.

Required:
- explicit preference dominates learned soft;
- learned evidence remains visible as history/conflict;
- ranking/action follows explicit intent;
- no deletion of user preference history to make the test pass.

Alternative strong control:
- clear learned evidence through the existing learned-clear boundary;
- ranking returns to neutral/explicit-only behavior.

Best result proves both override and clear.

## Phase H — optional cross-Journey transfer

Preferred success uses a new Journey with the same traveler.

This proves TravelerTwin is actually cross-Journey memory, not a local plan score.

Do not hardcode Nara candidate names in production code.

A second city is a stretch, not mandatory if real provider conditions make it expensive.

## Phase I — R22 selective-autonomy control

Include one cheap ACTIVE control:
- window below threshold -> no opportunity Event;
or
- valid window but all grounded candidates are low-value/weak-fit -> Agent NO_ACTION.

This closes the R22-D behavioral gap without reopening R22.

## Anti-learning mistakes

Do NOT:
- infer accessibility/health capability from behavior;
- turn "completed museum" directly into "likes museums";
- treat one skip as category rejection;
- let LLM prose write a Preference row directly;
- let LEARNED_SOFT bypass canonical facts;
- let learned evidence change budget/authority/policy;
- invent opaque embedding/personality scores.

No new vector-memory framework.
No recommender-system rewrite.

## Success levels

### REVOLUTION_A — trustworthy adaptive memory
Outcome evidence produces inspectable, bounded LEARNED_SOFT state without the completion=liking shortcut; explicit intent overrides it.

### REVOLUTION_B — causal planner adaptation
REVOLUTION_A + at least two fully grounded opportunity candidates rank differently after learned evidence, while hard feasibility facts remain identical.

### REVOLUTION_C — real Agent acts better because it learned
REVOLUTION_B + real configured Agent on a fresh ACTIVE Journey sees the learned TravelerTwin context, chooses/accepts the newly preferred grounded opportunity, crosses Gateway and executes it.

### REVOLUTION_D — reversible human-controlled learning
REVOLUTION_C + explicit contradictory preference or clear-learned action reverses/suppresses the learned effect, and an ACTIVE no-action/short-window control avoids unnecessary mutation.

Target C/D.

## Final report

One file:

`REVOLUTION_R23_ADAPTIVE_TRAVELER_TWIN_RESULT.md`

Include:
- R22 base/current SHA;
- R23 final code SHA;
- traveler ID;
- Journey A and Journey B IDs;
- raw relevant outcome event IDs;
- learned preference evidence rows;
- evidence class / strength / confidence / expiry;
- TravelerTwin before/after snapshots;
- baseline grounded candidate set;
- adaptive grounded candidate set;
- same candidate hard facts before/after;
- deterministic ranking delta attributable to preference fit;
- real Agent provider/model;
- AgentRun tool steps;
- model-visible TravelerTwin summary;
- chosen Place canonical facts;
- live mobility;
- Gateway/approval;
- final execution;
- explicit override / clear control;
- ACTIVE opportunity no-action control;
- focused regressions + previous R22 suite delta.

## Success sentence

R23 closes when this is a machine fact:

> CityNexus did not merely optimize a trip from static preferences; it cautiously learned a reversible soft preference from real traveler evidence, that learning materially changed the next grounded opportunity ranking and real Agent decision, and explicit human intent could still override or erase the learned bias.
