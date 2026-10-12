# Revolution R14 — Autonomous Strategy Engine

## The Revolution Lab principle

This line does not exist to make the existing planner incrementally cleaner.

The Lab exists to let CityNexus challenge its own architecture, give the agent strategy-level freedom, and create product capabilities that the authority line does not yet know how to express.

R13 proved that a fresh real city can be discovered, hydrated with official facts, routed with LIVE mobility, planned, selected, and shown in the real UI.

That is no longer the Revolution problem.

The Revolution problem is now:

> Can CityNexus decide for itself what evidence it still needs, which Places are worth investigating, which planning strategy to try, when to abandon a bad strategy, and how to build a better real trip from a zero-seed city without a human pre-authoring the solution?

Fact-driven ranking is only one component of this mission.

## Mission

Build a strategy-level autonomous trip engine for a fresh, unseeded city.

The engine must close this loop:

```text
natural-language user intent
  -> resolve fresh city
  -> discover broad real catalogue
  -> inspect current fact coverage
  -> agent chooses what evidence is worth acquiring
  -> acquire/corroborate exact real facts
  -> agent/planner generates multiple materially different strategies
  -> deterministic feasibility + authority gates reject unsafe/unproven options
  -> system learns from those rejections within the run
  -> agent chooses the next action: acquire more facts / change Places / change schedule / change strategy
  -> produce a fact-grounded selectable plan
  -> execute part of the trip
  -> introduce a meaningful disruption
  -> inspect live Journey/Twin
  -> generate and approve a grounded replan
  -> complete the revised journey
```

The product should no longer depend on a human knowing in advance which Places need manual fact binding.

## Non-negotiable architecture boundary

The agent gets more freedom at the strategy layer, not at the truth layer.

The agent may decide:
- which Places are promising;
- which missing facts have the highest value of information;
- which source candidates to investigate;
- which itinerary strategy to explore;
- when a strategy is failing and should be abandoned;
- which real constraints should drive a replan;
- which tool to call next.

The agent may NOT invent:
- provider identity;
- opening hours;
- ticket price;
- mobility;
- booking state;
- source provenance;
- authority approval.

Those remain deterministic/provider-backed facts.

This is the intended Revolution architecture:

```text
Agent = strategy / search / prioritization / adaptation
Deterministic core = truth / persistence / authority / safety
```

Do not collapse one into the other.

## Phase A — remove the demo-era planner skeleton

For provider-backed real-city planning, remove the dependency on:
- earliest-opening + place.id as the primary candidate ordering;
- greedy rotation as the main diversity mechanism;
- static `metrics_list` values as if they were measured plan quality.

Keep fixture/demo compatibility isolated if required.

Build a bounded strategy search instead. A beam search, branch-and-bound search, or similarly small bounded search is preferred over a giant framework.

Candidate construction should use actual evidence:
- traveler/user intent;
- Place category and real tags;
- verified opening windows;
- verified cost;
- LIVE travel burden;
- schedule slack;
- hard commitments;
- provider degradation;
- fact completeness;
- diversity.

No fabricated venue ratings.

## Phase B — value-of-information fact acquisition

Do not hydrate every Place blindly and do not require a human to preselect every official source.

For the current fresh city:
1. inspect all discovered visit-eligible Places;
2. estimate which missing fact, if acquired, could materially change plan feasibility or ranking;
3. choose the next bounded fact-acquisition action;
4. acquire/corroborate the fact;
5. re-evaluate the candidate space;
6. stop acquiring facts that no longer influence the plan.

Persist a compact decision trace:
- candidate Place;
- missing fact;
- why it matters;
- chosen acquisition action;
- outcome;
- whether ranking/feasibility changed.

This is the core Revolution behavior: the system decides what it needs to learn next.

## Phase C — autonomous source corroboration

R13 operator-bound URLs are a valid authority boundary but are not autonomous discovery.

Preserve explicit provenance classes:
- `OPERATOR_BOUND_EXACT_ENTITY`;
- `PROVIDER_BOUND_EXACT_URL`;
- `SEARCH_CANDIDATE`;
- `CORROBORATED_OFFICIAL_SOURCE` (only after exact entity/source corroboration).

Implement at least one real automatic path that can go from:
provider entity
-> provider website/contact tag or discovered candidate
-> exact source corroboration
-> official fact acquisition

without a human manually pasting the final source URL.

If a source cannot be corroborated, leave the fact UNKNOWN and change strategy instead of forcing promotion.

Do not attempt to build a universal web identity engine. Build one strong general path and move.

## Phase D — real preference-sensitive strategy generation

Use at least two materially different natural-language requests in the same fresh city.

Example:
- "quiet garden, heritage, long walks, low rush";
- "indoor craft, museums, less walking, compact route".

The top candidate must materially differ for reasons grounded in:
- actual Place categories/tags;
- actual route time;
- actual opening windows;
- actual cost;
- actual user preference evidence.

The explanation must say what changed and why.

No static fake precision.

If a score dimension has no real evidence, mark it neutral/unknown and explain that limitation.

## Phase E — allow the engine to fail fast and pivot

The agent/strategy engine must be allowed to abandon:
- a Place with stubbornly unresolvable facts;
- a source candidate that cannot be corroborated;
- an itinerary whose LIVE mobility is too costly;
- a schedule with poor slack;
- a city-specific provider dead end.

Do not spend the round proving the same blocker repeatedly.

Persist the pivot reason and move.

A successful Revolution run should contain at least one example of the system changing its own search/planning strategy because the previous path was weak.

## Phase F — disruption and live replan

After selecting and starting the generated trip, introduce a meaningful disruption that invalidates or materially weakens the current plan.

Then require:
1. persisted AgentRun;
2. first tool action inspects live Journey/Twin;
3. agent identifies the affected constraints/facts;
4. agent chooses whether to acquire new facts, swap Place, or alter schedule;
5. deterministic planner generates the replan;
6. authority explicitly approves/selects the replacement plan;
7. old/new PlanVersion lineage is preserved;
8. execution continues to Journey COMPLETED.

This closes the strategy loop in a live trip rather than only at creation time.

## Phase G — second-city transfer test

The first city may be Nara for continuity, but R14 does not close on Nara alone.

After the engine works, run one second unseeded city with:
- no city-specific planner code;
- no manually authored itinerary;
- no copied Journey;
- no golden fixture.

The second-city result may be less polished, but it must prove the same strategy loop can start and adapt.

If the second city fails, the engine should produce a useful strategy-level reason, not just "422".

## Japanese parser work is subordinate

The `d075a4cd` fix is correct for the observed mixed paid/free page but not a full parser.

Add bounded coverage for:
- full-width digits and separators;
- prefixed JPY symbols;
- adult/general vs child/student/companion/free exceptions;
- optional service / rental / annual-pass amounts near admission;
- ambiguous default audience => UNKNOWN rather than cheapest incidental amount.

Prefer a small audience-aware parser.

Do not spend the majority of R14 here.

## Anti-ORD rules

- one capability branch;
- one main result report;
- inline fixes for mission blockers;
- no branch-per-bug;
- no R14.1/R14.2 recut carousel;
- no report-only round;
- no repeated replay of R13 just to prove it still works;
- no broad historical red-light archaeology unless R14 creates a new regression;
- no static score polish presented as Revolution.

## Time allocation

Aim for:
- 65% implementation + real execution;
- 20% focused debugging/tests;
- 10% second-city transfer;
- 5% final evidence/report.

If review/evidence work becomes the majority, stop and return to the mission.

## Success levels

### REVOLUTION_A — strategy-aware planner
Real user intent materially changes candidate generation/ranking using actual provider facts and LIVE mobility. Static `metrics_list` no longer drives real-city quality.

### REVOLUTION_B — self-directed evidence loop
A fresh city run demonstrates the system itself choosing a high-value missing fact/source to investigate, changing strategy after the result, and producing a selectable real plan without a human pre-authoring all fact bindings.

### REVOLUTION_C — autonomous adaptive trip
REVOLUTION_B plus:
- real trip starts;
- meaningful disruption occurs;
- persisted agent inspects live state and chooses a replan strategy;
- authority approves a new plan;
- revised trip reaches Journey COMPLETED.

### REVOLUTION_D — transfer
REVOLUTION_C behavior, or the core self-directed evidence/strategy loop, is demonstrated in a second unseeded city without city-specific planner code.

Target C. Push for D if runtime/provider conditions permit.

Do not stop at A and write a victory report.

## Final deliverable

One report:

`REVOLUTION_R14_AUTONOMOUS_STRATEGY_RESULT.md`

It must contain:
- base/final SHA;
- city/cities;
- natural-language user intents;
- initial discovered catalogue;
- strategy decisions and pivots;
- value-of-information acquisition decisions;
- source provenance classes;
- candidate strategies;
- score provenance;
- selected plan;
- LIVE used-edge provenance;
- disruption;
- AgentRun + ordered tool calls;
- replan lineage + approval;
- final Journey/Twin state;
- second-city transfer result;
- focused tests and candidate-vs-base delta;
- only genuine remaining external blockers.

## Success sentence

R14 is successful when this sentence is a machine fact:

> CityNexus can enter an unseeded city with only a user's intent, decide what it needs to learn, acquire or abandon facts strategically, construct and explain a real plan, adapt that plan after the trip changes, and complete the revised journey without a human pre-authoring the solution.

That is the Revolution target.
