# R21 implementation sketch — shortest path

## 1. Neutralize the mission plan, do not remove it

Current problem:
`build_mission_plan()` inserts `arbitrate_standby -> activate_standby` before `request_replan`.

Smallest safe change:
- for autonomous disruption missions, replace both mutation-specific ordered steps with one neutral:
  `evaluate_recovery_options`, tool_name=None;
- keep allowed_tools unchanged;
- keep approval_required_tools unchanged;
- keep inspect steps first;
- keep authority boundary last.

The model still receives all actual tools through the API tool catalog.

Regression:
- mission payload contains no ordered `activate_standby` or `request_replan` step;
- allowed_tools still contains both when policy permits.

## 2. Keep the system prompt capability-neutral

The current system prompt says choose `activate_standby`, `request_replan`, or `NO_ACTION`.

That is acceptable as a capability statement.

For the strongest R21 proof, consider shortening it to:
"After inspection, choose the safest available CityNexus action within server policy; do not assume a standby is sufficient."

Do not add a recommended tool or branch.

## 3. Define material future difference

Add a compact deterministic fingerprint/summary based on:
- ordered Place IDs;
- scheduled start/end times;
- activity count;
- replacement/drop set.

Portfolio maintenance should prune exact material duplicates even if scenario labels differ.

Do not throw away distinct evidence/provenance; only collapse executable duplicates.

This will prevent route_plus_20 and route_plus_30 from masquerading as two different futures when they materialize identically.

## 4. Create one genuinely different branch

Reuse current counterfactual/replan materializer.

Good minimal combination:
- mobility standby = DROP optional visit;
- closure/replacement standby = REPLACE with a grounded alternative;
or
- mobility standby = DROP;
- schedule standby = RETIME/KEEP.

Do not add a special-case Nara branch.

## 5. Force portfolio insufficiency without synthetic facts

Use a truthful USER_REPORTED event/constraint not covered by existing branches.

Example:
- user says current museum is unavailable AND must keep a newly asserted hard commitment;
- or major delay + reduced walking tolerance.

Persist the user-observed constraint/event normally.

Do not encode "please request replan" in the text.

## 6. Real model run

Final mission text should be generic and natural.

Expected good traces are variable:
- inspect_journey -> inspect_twin -> activate_standby;
- inspect_journey -> inspect_twin -> request_replan -> list_replans -> accept_replan;
- inspect_journey -> inspect_twin -> final NO_ACTION.

Do not assert one exact sequence in the wrapper.

## 7. Fresh replan path already exists

Do not build FutureSynthesisService.

Reuse:
- request_replan;
- replan solver;
- search_city_services;
- acquire_place_facts;
- generate_plans where needed;
- live mobility capture;
- accept_replan.

R21 is orchestration intelligence over existing capabilities.

## 8. Fix ai_state semantics narrowly

Observed contradiction:
- real Hermes AgentRun executes;
- mission payload says `ai_state=DISABLED_BY_OPS`.

Adjust `ai_availability_state()` or mission projection so Hermes-compatible configured runtime is represented as available/active independently of native MCP state.

Regression only; no UI redesign.

## 9. Reconcile orphaned runs

At startup or before new run creation:
- find RUNNING missions/runs older than timeout with no live process ownership/heartbeat if such marker exists;
- mark INTERRUPTED/ABORTED;
- persist reason e.g. `PROCESS_RESTARTED_DURING_AGENT_RUN`.

Keep it deterministic and bounded.

## 10. Focused R21 regressions

Add direct tests:
1. autonomous recovery mission plan has no ordered mutation tool.
2. allowed_tools still include activate/replan under policy.
3. materially identical standby branches collapse/prune.
4. materially different branches remain.
5. insufficient portfolio permits request_replan.
6. model cannot activate incompatible/stale branch.
7. NO_ACTION leaves active reality unchanged.
8. synthesized proposal still requires normal Gateway.
9. stale RUNNING row reconciles.
10. ai_state reflects configured Hermes-compatible availability.

Then run the existing 39-test R20 focused suite once.

No new harness.
