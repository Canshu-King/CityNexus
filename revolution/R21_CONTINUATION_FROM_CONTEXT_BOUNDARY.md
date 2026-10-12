# R21 continuation — From hidden trigger to autonomous future synthesis

Do NOT restart R21.

The context-boundary checkpoint is accepted as an intermediate proof.

Continue from the current local R21 worktree.

## Step 1 — publish current local code

Push the local commit named in the checkpoint (`0946a6fb` or its current descendant) to:
`origin/codex/revolution-realtrip-recovery`.

Verify the remote head and record the full SHA.

Only after that continue product implementation.

## Step 2 — verify strategy-neutral mission envelope

Inspect the actual post-checkpoint code and prove:
- mission payload no longer contains an ordered `activate_standby` / `request_replan` recovery script;
- allowed tools still include both under the autonomy envelope;
- system/user mission text does not expose trigger ID or prescribe the recovery action.

If the local patch already did this, do not rewrite it.

## Step 3 — remove implicit latest-event strategy under ambiguity

Keep the single-event convenience if safe.

But when multiple actionable events exist and the Agent omits `trigger_event_id`:
- do NOT silently bind to the newest event;
- return `EVENT_SELECTION_REQUIRED` with compact event choices, OR use an explicit deterministic priority policy with reason codes.

For the strongest R21 proof, prefer explicit model event selection after `inspect_twin`.

This preserves the context boundary:
the server exposes facts, the model chooses strategy.

## Step 4 — make mission completion stateful

Do not let:
`inspect -> list_replans -> prose`
automatically look equivalent to a resolved recovery mission.

Use the smallest server-owned completion contract that can distinguish:
- mutation executed;
- approval pending;
- NO_ACTION chosen;
- unresolved/stopped early.

Do not build a new Agent framework.

## Step 5 — main product run must stop using mock/simulated truth

Create/use a fresh disposable real-city Journey with:
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`;
- canonical Place truth;
- live Valhalla mobility;
- at least one truthful user/provider event or constraint;
- real Hermes-compatible GLM runtime.

The disposable DB is fine.
Mock mobility is not.

## Step 6 — require materially different futures

Before the main event, expose at least two genuinely different executable outcomes.

Examples:
- DROP optional stop;
- RETIME/KEEP;
- REPLACE with canonical grounded Place.

If two branches materialize to the same activity/order/time outcome, dedupe them and do not count them as multiple futures.

## Step 7 — make the portfolio intentionally insufficient

Use a truthful event/constraint that no prepared branch fully solves.

Do not say "request a replan" in the mission.

The natural mission should describe only the actual traveler problem, e.g.:

"The traveler reports that the current route is no longer workable and the protected commitment must still be met. Recover the trip safely within the existing budget and authority."

The model must discover:
- current event;
- current portfolio;
- why existing futures are insufficient;
- that it should call `request_replan`.

## Step 8 — synthesize a new truth-grounded future

Reuse existing CityNexus capabilities:
- request_replan;
- search_city_services;
- acquire_place_facts;
- generate_plans;
- live mobility capture;
- list_replans;
- accept_replan.

No FutureSynthesisService.

If the first proposal lacks canonical truth, the Agent may acquire facts or pivot.

The wrapper must not make that choice.

## Step 9 — compare and govern

After fresh proposal creation, the model must compare:
- existing standby branches;
- new proposal;
- current-plan continuation.

Then choose a CityNexus tool.

Gateway remains final authority.

Do not auto-accept merely because a proposal exists.

## Step 10 — close product behavior

For the main success:
- mutation/approval through Gateway;
- new active PlanVersion;
- actual HTTP execution state machine;
- Journey COMPLETED;
- Twin consistent;
- used edges hard-eligible live provider facts.

Run a second small control:
- irrelevant/low-severity truthful event;
- model inspects;
- explicit machine-visible NO_ACTION;
- active plan unchanged.

## Time allocation

- 70% real product path;
- 20% focused debugging/tests;
- 10% evidence/report.

No ORD loop.
No branch-per-bug.
No R21.1.
No report-only checkpoint.

## Final success sentence

R21 closes only when this is machine fact:

> With no trigger identity or recovery recipe leaked in the mission, a real model discovered the relevant live event, recognized that the prepared futures were insufficient, synthesized a new truth-grounded future through existing CityNexus tools, crossed Gateway authority, and completed the revised trip; on an irrelevant control event, the same strategy surface correctly chose no action.
