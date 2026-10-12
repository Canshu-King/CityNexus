# Revolution R25 — Strategic Horizon Steward

## The leap

R22: seize one good opportunity.
R23: adapt opportunity ranking from TravelerTwin.
R25: reason across the remaining trip instead of greedily optimizing the current window.

Target behavior:

```text
ACTIVE Journey
  -> current opportunity window W1
  -> known later window W2 inside the same remaining trip
  -> bounded grounded candidate set for both windows
  -> finite optional budget / time envelope means not all opportunities can be taken
  -> TravelerTwin + explicit intent + real provider facts define relative value
  -> real Agent compares TAKE_NOW vs DEFER
  -> if later option is materially better:
       current W1 resolved as deliberate NO_ACTION / DEFER
       optional budget remains unspent
       later W2 becomes current
       Agent grounds/revalidates the chosen later candidate
       Gateway governs
       candidate executes
  -> Journey COMPLETED
```

This is not prediction of the external world.
It is strategy over currently known server facts.

## Hard truth boundaries

- estimate authority false for final success;
- current and later candidates use exact provider-backed Place rows;
- opening/cost truth remains canonical;
- any mobility used for execution is live/provider-backed and revalidated when the window becomes current;
- future-window planning evidence must be labeled as planning evidence, never disguised as future live traffic truth;
- protected commitments remain deterministic authority;
- learned preferences only rank; they never expand budget, policy, commitment or approval authority;
- explicit user intent wins over learned memory.

## Phase 0 — close two memory correctness blockers inline

### 0A. Idempotent evidence ingestion

Fix `learn_from_journey()` so reprocessing the same outcome events does not rejuvenate evidence.

Required:
- source outcome IDs are deduped;
- no new evidence => created_at/expiry/effective strength stay unchanged;
- new independent outcome => aggregate exactly once;
- repeated HTTP replay is idempotent.

### 0B. Bounded reinforcement and contradiction

Independent same-direction evidence across separate Journeys may strengthen LEARNED_SOFT, but with a cap.

Use a simple inspectable function, for example:
- evidence count;
- decayed per-evidence strength;
- bounded aggregate;
- explicit contradiction / opposite learned direction reduces net effect.

Do not create embeddings, latent personality vectors or a Bayesian framework.

Persist enough provenance to explain the aggregate.

## Phase A — close the real Agent causal-choice bridge

Before long-horizon work, prove one strong current-window comparison.

Create two fully grounded F4 candidates A/B:
- both exact provider identity;
- both canonical opening/cost;
- both two-leg live mobility;
- both hard feasible;
- neither hidden by a hard constraint.

Use the SAME candidate facts under two TravelerTwin states:
1. neutral / learned cleared;
2. learned preference active.

Run the real configured Agent for both comparable windows/Journeys.

Required:
- no Place ID in mission;
- Agent sees compact TravelerTwin context;
- server exposes both candidate proposals;
- model-selected proposal changes when learned context changes;
- hard feasibility remains unchanged;
- the changed model decision is recorded in AgentRun steps.

This closes the missing R23 causal bridge without a separate R23.1.

## Phase B — expose a bounded remaining-horizon opportunity view

Do not build a new planning framework.

Reuse current:
- active PlanVersion;
- C4 commitments;
- OpportunityWindow;
- F4 candidate truth;
- standby/counterfactual read-model ideas.

Add a small read-only horizon projection to JourneyTwin / Agent inspection.

At most:
- current window;
- next one or two future windows that can be derived deterministically from the remaining schedule / commitments.

For each future window expose only facts the server can prove:
- window start/end boundary;
- source activity/anchor;
- optional budget remaining at baseline;
- known candidate summaries if already grounded;
- fact freshness;
- whether mobility is planning-only/stale/current.

Do not manufacture a future incident or claim future traffic.

## Phase C — bounded opportunity portfolio

For at most two windows, allow a tiny portfolio of grounded candidate opportunities.

Each portfolio item:
- window ID;
- Place ID;
- canonical category/tags;
- opening/cost status;
- expected visit duration;
- planning route evidence;
- local deterministic fit;
- preference breakdown;
- resource consumption:
  - cost delta;
  - minutes consumed;
  - remaining budget after choice;
  - remaining slack after choice.

The portfolio is read-only strategy evidence until a window is current.

When the later window becomes current:
- recapture/revalidate live mobility;
- re-run F4/full feasibility;
- only then may it activate.

## Phase D — strategic defer decision

Create a real scenario with two windows.

Constraint:
- both W1 and W2 have individually feasible grounded opportunities;
- optional budget or schedule slack is insufficient to take both;
- W1 candidate is acceptable but lower value under current TravelerTwin;
- W2 candidate is materially better under the same learned preference.

The real Agent at W1 must be allowed to choose:
- TAKE_NOW;
- DEFER / NO_ACTION.

Success path:
- Agent inspects horizon;
- sees that taking W1 would consume the scarce resource needed for W2;
- emits a typed machine decision to leave W1 empty;
- current active plan stays unchanged;
- W1 signal becomes resolved with a reason such as `DEFERRED_FOR_HIGHER_VALUE_HORIZON`;
- no fake reservation or hidden hard lock is inserted.

This is a strategic no-action, not lack of candidates.

## Phase E — execute the later opportunity

Advance execution normally until W2 is current.

Then:
- refresh canonical facts if stale;
- capture current live inbound/outbound mobility;
- generate F4 candidates;
- real Agent selects the high-value option;
- Gateway approval/authority remains normal;
- execute inserted activity;
- preserve commitments;
- Journey COMPLETED.

The proof must show the earlier defer preserved enough budget/time to make this later action possible.

## Phase F — explicit human override reverses the strategy

Use the same horizon scenario.

Add explicit user intent that favors W1 or rejects W2.

Required:
- explicit input suppresses contradictory LEARNED_SOFT;
- Agent chooses TAKE_NOW at W1 or otherwise follows the explicit strategy;
- later W2 is then legitimately unavailable due consumed resource, or is declined;
- no machine preference is allowed to overrule the explicit instruction.

This is a strategic A/B, not merely a JSON conflict field.

## Phase G — no phantom future truth

Future-window projections must distinguish:
- CURRENT_LIVE_EVIDENCE;
- FROZEN_PLAN_EVIDENCE;
- PLANNING_ONLY_PROVIDER_CAPTURE;
- STALE / REVALIDATION_REQUIRED.

Do not call a future route "live at that future time".

At activation time, the current window must use fresh/live evidence under the existing authority rules.

## Phase H — keep the opportunity set bounded

No city-wide future crawl.

Preferred:
- max 2 future windows;
- max 2 candidates per window;
- value-of-information acquisition only for candidates that could change the decision.

No new optimizer framework.

## Phase I — one second-city stretch

If Nara closes the main path early, run one fresh unseeded city with:
- no city-specific production code;
- same TravelerTwin;
- one strategic TAKE_NOW vs DEFER decision.

Stretch only. Do not block main closure on provider noise.

## Anti-ORD rules

- one capability branch;
- inline fixes;
- one final report;
- no R25.1 / R25.2;
- no branch-per-control;
- no replaying R20-R23 as the main work;
- broad focused regression once at the end, not every patch;
- at least 70% effort on product/runtime capability.

## Success levels

### REVOLUTION_A — causal adaptive choice
A real configured Agent chooses differently between two equally grounded current-window candidates solely because TravelerTwin context changes.

### REVOLUTION_B — horizon awareness
REVOLUTION_A + Agent inspection exposes a bounded remaining-horizon opportunity view with truthful evidence classes and resource consumption.

### REVOLUTION_C — strategic deferral
REVOLUTION_B + real Agent deliberately declines a feasible current opportunity to preserve scarce budget/time for a better later grounded opportunity, then later revalidates and executes that opportunity.

### REVOLUTION_D — human-controlled temporal strategy
REVOLUTION_C + an explicit user preference reverses the TAKE_NOW/DEFER strategy while all hard facts remain otherwise comparable.

Target C/D.

## Final report

One file:

`REVOLUTION_R25_STRATEGIC_HORIZON_STEWARD_RESULT.md`

Include:
- base/final SHA;
- memory idempotency fix proof;
- repeated-evidence aggregate formula/provenance;
- causal current-window Agent A/B;
- TravelerTwin states;
- current + future horizon projection;
- candidate facts for W1/W2;
- exact optional budget/time envelope;
- real Agent provider/model;
- W1 tool trace and strategic defer receipt;
- W1 plan unchanged proof;
- W2 revalidation/live mobility;
- W2 proposal/Gateway/approval;
- execution to completion;
- explicit override A/B;
- prior-suite regression delta.

## Success sentence

R25 closes when this is a machine fact:

> CityNexus no longer greedily optimizes whichever opportunity is in front of it; it can use truthful future-window and TravelerTwin context to preserve scarce resources for a better later experience, then revalidate and execute that choice when it becomes current, while explicit human intent can reverse the strategy.


## Mandatory precedence correction

For soft opportunity ranking, the effective precedence must be machine-visible:

```text
CURRENT_EXPLICIT_MISSION
>
EXPLICIT_PERSISTED_PREFERENCE
>
LEARNED_SOFT
>
NEUTRAL
```

A current Journey mission preference must not be ignored merely because learned interest rows exist.

Implement this at the preference/ranking surface, not by promoting a soft mission preference into a hard constraint.

Add a focused regression where:
- TravelerTwin learned preference favors A;
- current mission explicitly favors B;
- A and B remain hard-feasible;
- ranking/Agent decision follows B.
