# Revolution R15 — Truth-Seeking Autonomous Operator

## The point of R15

R14 proved that CityNexus can behave strategically across multiple fresh cities:
- the Agent inspects live state;
- discovers real provider Places;
- changes search/place strategy after blockers;
- generates plans;
- uses real mobility;
- requests/accepts replans;
- completes Journeys.

But much of the final selection success still relied on the explicit Revolution-Lab escape hatch:

`COURSEWORK_ESTIMATED_FACTS` + `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=true`.

That experiment was useful. It is now complete.

R15 must remove that crutch from the success path.

The next Revolution is not “estimate better.” It is:

> The Agent decides which truth it needs, actively hunts/corroborates that truth, abandons dead evidence paths, and gets a real plan across the normal authority boundary with canonical provider-backed facts.

## Hard success boundary

For the R15 success Journey:

`CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`

must be in force before generation/selection.

An `ESTIMATED_AGENT` fact may influence strategy/search priority, but it may NOT make the success plan selectable.

The selected plan's used Places must have the canonical facts required by the ordinary authority gate.

No sealed demo envelope. No golden fixture. No copied plan. No manual database promotion.

## Phase 0 — bounded c9 runtime preflight

Before R15 product work, perform exactly one fresh live Agent command from `c9e3a2aa` or the current descendant:
- domestic primary: `cn:glm-5.3-flash`;
- fallback: `cn:deepseek-v4.1-flash`;
- verify a real tool call or final content;
- if the first call is reasoning-budget exhausted, verify same-model 2400-token retry;
- record elapsed wall time.

If this works, move immediately to R15.

If it fails, fix only what blocks the real mission. Do not spend the round building another model-runtime harness.

## Phase A — pick a genuinely fresh city

Do not use the R14 success cities as the final success case:
- Chongqing
- Chengdu
- Kunming
- Guilin
- Wuhan
- Nanjing

Also do not fall back to Beijing/Suzhou/Gongshan/Nara golden/history scenarios as the final proof.

Start from a natural-language user intent and a fresh disposable Journey.

The Agent may choose the city if that is useful, but the city must enter through the normal real-city resolver/discovery path.

## Phase B — turn estimates into search strategy, not authority

Keep `estimate_place_facts`, but change its role.

Allowed uses:
- predict which missing fact is decision-sensitive;
- rank which Place is worth investigating next;
- estimate whether a source hunt is worth the time;
- compare candidate strategies;
- decide when to abandon a Place.

Forbidden use in the R15 success path:
- turning an estimated opening/cost into selection authority;
- allowing `COURSEWORK_ESTIMATED_FACTS` to cross select.

Persist the estimate as strategy evidence only.

## Phase C — build a truth-seeking evidence loop

The Agent needs a bounded loop that can choose and execute a next evidence action.

At minimum:
1. inspect Journey/Twin/catalogue;
2. identify top candidate strategies;
3. identify the missing canonical fact that can change feasibility/ranking;
4. choose an acquisition route;
5. execute it;
6. evaluate whether canonical truth improved;
7. either continue, pivot to a new Place/source, or stop.

Persist a compact decision trace:
- candidate plan/place;
- missing fact;
- expected decision impact;
- chosen evidence action;
- result/provenance;
- next strategy.

This is a value-of-information loop, not bulk crawling.

## Phase D0 — fix the source-approval identity boundary first

Before allowing the Agent to hunt official sources, repair the current binding semantics.

Today the Agent gateway can pass `source_url` into `acquire_place_facts`, and the downstream requested binding path can label that caller-supplied URL as `OPERATOR_VERIFIED / OPERATOR_CONFIRMED_EXACT_PROVIDER_ENTITY`. That label is not legitimate when the caller is the model.

Required separation:
- true human/operator approval must come from a human-bound route/receipt, not from an AgentToolCall argument;
- an URL already attached to the exact Overpass/Nominatim entity may be classified `PROVIDER_BOUND_EXACT_URL`;
- an Agent-supplied/search-supplied URL starts as candidate-only;
- promotion to canonical authority requires deterministic corroboration.

Add a regression proving:
`AgentToolCall(source_url=arbitrary_url)` cannot create an `OPERATOR_VERIFIED` fact binding.

This is a truth-boundary blocker for R15, not an optional cleanup.

## Phase D — autonomous source discovery and corroboration

R13/R14 operator-provided bindings are valid evidence boundaries, but R15 success should not depend on a human pasting the final source URL.

Add/complete at least one general source path such as:

```text
exact provider entity
 -> website/contact tag from Overpass/Nominatim
 -> safe fetch
 -> same-entity corroboration
 -> official page / official ticket endpoint
 -> opening/cost extraction
 -> canonical promotion
```

or:

```text
exact provider entity
 -> bounded search candidate
 -> domain/entity corroboration against provider identity
 -> official source
 -> canonical promotion
```

Search snippets themselves remain `SEARCH_CANDIDATE`.

Do not build a universal crawler. One or two strong, general corroboration routes are enough.

If a source cannot be corroborated quickly, pivot.

## Phase E — retire manual “truth completion” as the experiment driver

The Agent should NOT receive a hand-curated list of exact official URLs for the final success run.

Human input may still:
- choose/approve the user mission;
- observe the run;
- approve a replan at the existing authority boundary.

Human input should NOT:
- pre-author the itinerary;
- pre-bind every Place to an official page;
- directly write canonical opening/cost into the DB.

## Phase F — fact-driven planner remains real

Preserve R14's strategy improvements:
- actual user intent changes candidate choice;
- actual live mobility changes route quality;
- actual budget/opening facts change feasibility/ranking;
- no static magic `metrics_list` should masquerade as measured real-city quality.

If any old demo-era ranking scaffold still drives the success case, remove/contain it inline.

## Phase G — require a real authority upgrade

Before select, prove for every used non-anchor Place:
- exact provider identity;
- canonical opening truth sufficient for the Journey date/time;
- canonical cost truth sufficient for budget logic, including known-free when truly free;
- provenance/source class;
- capture timestamp.

The plan must become selectable with:

`CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.

Then call the normal select endpoint and read back the active PlanVersion.

This is the core R15 closure.

## Phase H — execute, disrupt, adapt

Do not stop at selection.

Start the Journey and advance real activities.

Introduce one meaningful disruption that affects the active plan:
- venue closes/unavailable;
- user changes walking tolerance;
- weather pushes indoor/outdoor strategy;
- commitment/arrival timing changes;
- live provider constraint changes.

Require a persisted AgentRun to:
1. inspect Journey;
2. inspect Twin;
3. identify the affected fact/constraint;
4. choose a replan strategy;
5. request/propose the replan;
6. cross the real Gateway/authority boundary;
7. activate the replacement plan.

For the replacement plan, do not re-enable estimate authority. If a new Place needs facts, the Agent must acquire/corroborate them or choose another Place.

Then execute the revised Journey to `COMPLETED`.

## Phase I — runtime must be bounded

Do not accept multi-hour synchronous waits as normal.

If the domestic model path can still hang during the R15 mission:
- preserve streaming finish_reason/usage metadata;
- distinguish reasoning budget exhaustion from provider-empty/content-filter cases;
- enforce a user-facing total AgentRun wall-clock budget;
- keep per-request read timeout bounded;
- compact large tool results before sending them back to the model.

Do the minimum necessary for reliable autonomous operation. Runtime plumbing is not the product milestone.

## Anti-ORD rules

- one capability branch;
- one final report;
- inline blocker fixes;
- no micro-ORDs;
- no branch-per-bug;
- no report-only recut;
- no “same city, same estimate envelope, one more completed Journey” as progress;
- no spending the majority of the round on test archaeology.

## Success levels

### REVOLUTION_A — truth-seeking loop
Agent chooses a decision-sensitive UNKNOWN, finds/corroborates a real source, and improves canonical truth without a human pasting the final answer.

### REVOLUTION_B — authority closure
Fresh unseeded Journey reaches a selectable real plan with `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`; every used Place has canonical authority facts and every used edge has eligible live/provider mobility.

### REVOLUTION_C — adaptive completion
REVOLUTION_B + real trip starts + meaningful disruption + persisted Agent strategy/replan + authority-approved replacement plan + revised Journey COMPLETED, still with estimate authority OFF.

### REVOLUTION_D — transfer
Repeat the core truth-seeking/authority-closure loop in a second fresh city without city-specific source/planner code.

Target C. Push for D if external sources/runtime permit.

## Final report

One file:

`REVOLUTION_R15_TRUTH_SEEKING_OPERATOR_RESULT.md`

It should contain only the facts needed to prove the capability:
- base/final SHA;
- runtime preflight;
- city and user intent;
- discovered real catalogue;
- Agent evidence decisions;
- source candidates and corroboration results;
- canonical fact promotions;
- pivots/abandoned paths;
- initial selected plan;
- live used-edge provenance;
- disruption;
- AgentRun/tool sequence;
- replan/approval lineage;
- final Journey/Twin;
- estimate-authority setting proving it remained false;
- focused tests + candidate-vs-base regression delta;
- genuine external blockers.

## Success sentence

R15 closes when this is a machine fact:

> CityNexus can enter a fresh city with only a user's intent, decide what real-world truth it still needs, autonomously find or abandon evidence sources, promote corroborated facts into canonical authority, select a real plan without the estimate escape hatch, adapt after disruption, and complete the revised Journey.

That is the next Revolution.
