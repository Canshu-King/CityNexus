# Revolution R22 — Autonomous Opportunity Capture

## The leap

R15-R21 taught CityNexus to:
- seek truth;
- recover after disruption;
- prepare futures;
- arbitrate branches;
- synthesize a new recovery future.

R22 must stop being purely defensive.

The new product behavior is:

```text
truth-grounded ACTIVE Journey
  -> execution/recovery creates a real free-time window
  -> Twin exposes a bounded OpportunityWindow
  -> system recognizes the window as actionable positive capacity
  -> real configured Agent wakes without a user prescribing a candidate
  -> Agent inspects Journey/Twin/preferences
  -> Agent searches real city Places
  -> Agent chooses whether the window is worth filling
  -> if yes:
       acquire canonical opening/cost facts
       capture live current->candidate->next-commitment mobility
       deterministic opportunity-window feasibility
       materialize an ADDITIVE candidate PlanVersion
       Gateway/approval
       activate
       execute added activity + remaining protected journey
  -> Journey COMPLETED
  -> if no grounded candidate is good enough:
       explicit NO_ACTION, active plan unchanged
```

This is positive autonomy:
not "survive the trip",
but "improve the trip when reality creates room".

## Hard truth boundaries

- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`;
- no mock mobility in the final success;
- no `metadata.cost_minor -> 0` shortcut;
- canonical opening/cost required for the added Place;
- exact provider-backed Place identity;
- live/provider-backed inbound AND outbound mobility;
- protected commitments remain deterministic authority;
- Agent may decide whether an opportunity is worth pursuing, but may not invent opening, cost, route, price or approval.

## Phase 0 — close R21 binding in minutes, not hours

Before R22 code:
- ensure remote `codex/revolution-realtrip-recovery` head is current;
- append one concise post-closure-hardening note to the canonical R21 SYNTHESIS report naming `cd1e5dd...` as current hardened code head;
- keep the canonical report filename;
- do not create another R21 report series.

Then move on.

## Phase A — make OpportunityWindow a first-class positive signal

Twin already exposes `context.opportunity_window`.

Use that existing deterministic state.

An opportunity is eligible for autonomous consideration only when:
- Journey is ACTIVE;
- there is a future protected/anchored commitment or explicit remaining journey boundary;
- `available_minutes` exceeds a bounded configurable minimum;
- mobility evidence to the next commitment is known/non-degraded enough for evaluation;
- no unresolved higher-priority disruption requires recovery first.

Represent the positive trigger in the smallest honest way.

Preferred path:
- a SYSTEM_DERIVED `OPPORTUNITY_WINDOW` Event (or equivalent persisted signal) whose payload contains only server-derived facts:
  - opens_at;
  - must_depart_by;
  - available_minutes;
  - next commitment/activity identity;
  - source Twin snapshot / active PlanVersion;
  - current execution location identity.

This event is not an external-world claim; it is a server-derived planning opportunity.

Deduplicate it per active plan/window/anchor so Autopilot does not spam identical opportunities.

## Phase B — wake the real Agent on positive capacity

Reuse Guardian/Autopilot/AgentRun machinery.

The standing mission may say, naturally:

"Use genuinely free time to improve the trip when a grounded option fits, but preserve the protected commitments, budget and truthful provider facts."

Do NOT:
- name a Place;
- name a tool sequence;
- tell the model it must fill the window.

The Agent must be free to choose:
- pursue opportunity;
- NO_ACTION because the window is too weak;
- NO_ACTION because available options are not worth the risk/cost;
- stop when facts cannot be grounded.

## Phase C — open-world discovery

For a viable window, the Agent should:
1. inspect Journey/Twin;
2. inspect traveler preferences / current trip context available through existing surfaces;
3. search the current city using `search_city_services`;
4. avoid Places already present in the active plan;
5. shortlist only a bounded few candidates;
6. acquire canonical facts for high-value candidates only.

Reuse R15 value-of-information discipline.

Do not hydrate the whole city.

A candidate must have:
- exact provider identity;
- canonical opening for the actual visit window;
- canonical cost or known-free truth;
- real duration evidence / bounded product duration;
- user preference/category evidence when available.

If facts remain UNKNOWN and decision-sensitive, either acquire or abandon.

## Phase D — live two-leg mobility

A positive insertion is only real if both sides are routable.

For each final candidate capture:
- current execution position -> candidate;
- candidate -> next protected commitment / next fixed activity.

Use live Valhalla/runtime mobility.

Persist one frozen opportunity mobility snapshot with:
- both edges;
- minutes;
- mode;
- route provenance;
- fact quality;
- cost status;
- captured_at / expires_at.

Paid unknown remains UNKNOWN and blocks auto execution.

Do not use `MockMobilityProvider`.

## Phase E — deterministic OpportunityWindow fit

Reuse:
- `OpportunityWindow`;
- `evaluate_window_replacement`;
- existing feasibility gate.

The deterministic candidate check must account for:
- inbound travel;
- visit duration;
- outbound travel;
- opening window;
- monetary cost;
- safety buffer;
- next protected commitment;
- current budget remaining.

A model saying "it fits" is irrelevant.

Persist explicit rejection reasons for failed candidates.

## Phase F — additive future, not replacement-by-subtraction

R22 main success must increase the executable plan's content.

Create one small new candidate family in the EXISTING replan/materialization path, conceptually:

`F4_OPPORTUNITY_INSERTION`

It inserts a new optional activity into the verified free window.

Requirements:
- parent = current active PlanVersion;
- all previously retained activities/commitments remain semantically preserved;
- added Place was not already in the active plan;
- activity count increases by one vs the pre-opportunity baseline;
- new JourneyLegs are built from the frozen opportunity mobility evidence;
- total cost/duration/budget/slack recomputed from actual branch truth;
- full-plan deterministic feasibility passes.

Do NOT build a new OpportunityPlanner framework.

## Phase G — how the Agent nominates candidates

Reuse the current tool surface.

The cleanest bounded extension is:
- allow `request_replan` / existing replan request to accept optional server-validated `place_ids` as candidate hints for an `OPPORTUNITY_WINDOW` trigger;
- candidate IDs must come from existing provider-backed Place rows;
- the server treats them as candidate inputs, never authority;
- generate_replan still performs canonical truth, mobility and feasibility.

If another small reuse path is cleaner, use it.

Do not add a new generalized synthesis service.

## Phase H — governed activation

When the additive proposal is ready:
- Agent compares it with leaving the window empty;
- Agent may call `accept_replan`;
- Gateway/policy may ALLOW_AUTO or REQUIRE_CONFIRMATION;
- approval, if required, remains user-bound;
- active plan switches atomically;
- event/opportunity signal becomes CONSUMED/RESOLVED for this Journey;
- sibling old-parent standby futures reconcile.

The Agent never writes the Journey pointer.

## Phase I — execute the positive addition

Do not stop when the new PlanVersion activates.

Drive:
- depart;
- arrive;
- begin;
- complete;

for the inserted activity, then continue to the protected/fixed remaining activity.

Final:
- Journey COMPLETED;
- Twin READY;
- added Place appears in actual execution history;
- all actual used edges hard eligible;
- protected commitment preserved.

## Phase J — stronger NO_ACTION control on ACTIVE journey

Run a second ACTIVE Journey/window control.

Examples:
- only 25 minutes are free;
- all grounded candidates exceed travel budget;
- best candidate has unresolved opening/cost;
- preference fit is weak and risk/buffer cost is not justified.

The real model should:
- inspect;
- optionally search a bounded set;
- conclude NO_ACTION;
- active PlanVersion remains unchanged.

This proves positive autonomy is not "always fill empty time".

## Phase K — small lifecycle repairs

Inline only:

1. Replan/standby trigger events that are fully handled by an accepted plan transition should become non-actionable for the Journey:
   - status RESOLVED or equivalent;
   - resolved_at;
   - resolution reason e.g. JOURNEY_ADAPTED.
   Preserve original event truth/provenance.

2. Bound `conclude_recovery.reason` before tool dispatch so a correct model conclusion does not burn extra turns on schema-length errors.

Do not expand either into a subsystem rewrite.

## Explicit R22 prohibition — unsafe direct replace shortcut

Do NOT use the current direct `replace_activity(replacement_place_id=...)` path for the final live opportunity result while it still:
- reads legacy metadata cost;
- uses MockMobilityProvider.

Either:
- avoid it and use the grounded replan path (preferred), or
- first upgrade that path to the same canonical/live truth contract.

No truth regression for convenience.

## Anti-ORD rules

- one capability branch;
- one final report;
- inline blocker fixes;
- no R22.1/R22.2 carousel;
- no new planner framework;
- no new event bus;
- no city-specific Place names in production code;
- no bulk fact crawling;
- no reporting a search result as an opportunity before both live route legs and canonical facts exist.

## Success levels

### REVOLUTION_A — positive capacity awareness
A healthy ACTIVE Journey produces a server-derived opportunity signal from a real OpportunityWindow without a disruption event being fabricated.

### REVOLUTION_B — open-world grounded opportunity
REVOLUTION_A + real model independently searches a real city and grounds a NEW Place not already in the active plan with canonical facts and two-leg live mobility.

### REVOLUTION_C — additive autonomous improvement
REVOLUTION_B + deterministic window/full-plan feasibility passes, an additive new PlanVersion is governed through Gateway, the added activity actually executes, protected commitments survive, and Journey COMPLETES.

### REVOLUTION_D — selective positive autonomy
REVOLUTION_C + a second ACTIVE control window causes the same real model to deliberately choose NO_ACTION because the available opportunity is not worth or not safe to take.

Target C/D.

## Final report

One file:

`REVOLUTION_R22_AUTONOMOUS_OPPORTUNITY_CAPTURE_RESULT.md`

Include:
- R21 canonical pointer + current hardened SHA;
- R22 base/final code SHA;
- fresh Journey/city;
- opportunity signal source and window facts;
- Agent provider/model;
- neutral standing/mission text;
- ordered model-selected tools;
- discovered candidates;
- VOI/fact acquisition pivots;
- chosen new Place identity;
- canonical opening/cost provenance;
- inbound/outbound live mobility;
- deterministic opportunity-fit receipt;
- additive PlanVersion diff;
- Gateway/approval;
- event/opportunity resolution;
- execution transitions;
- final Journey/Twin;
- ACTIVE NO_ACTION control;
- focused regressions + prior-suite delta.

## Success sentence

R22 closes when this is a machine fact:

> CityNexus did not merely recover from a bad trip; while the Journey was still running, it noticed a real free-time opportunity, autonomously discovered and grounded a new real-world experience, proved with live mobility and deterministic constraints that the experience safely fit, governed the addition through Gateway authority, executed it, and also knew when a different free window was better left empty.
