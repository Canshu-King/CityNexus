# Revolution R20 — Autonomous Branch Arbitration

## The leap

R19 proved CityNexus can maintain and safely activate a grounded standby branch.

R20 must prove the Agent can operate over a branching future without becoming the authority.

Target behavior:

```text
one ACTIVE reality
  + 2-3 fresh grounded STANDBY futures
  + one real persisted event
        |
        v
configured real Agent wakes
  -> inspect Journey
  -> inspect Twin + standby portfolio
  -> inspect current trigger/event
  -> reason over compatibility / freshness / deltas
  -> choose exactly one:
       A. activate compatible standby
       B. request fresh replan
       C. NO_ACTION
        |
        v
deterministic trigger contract
  -> Gateway policy
  -> optional approval
  -> atomic activation if allowed
  -> execution continues
```

The model chooses strategy.
The server owns truth, trigger compatibility and authority.

## Phase 0 — publish R19 before touching R20

The local R19 code commit named in the uploaded report is not yet reachable on GitHub.

Before implementation:
1. confirm local HEAD contains the R19 code and result;
2. push the R19 code/report commits to `origin/codex/revolution-realtrip-recovery`;
3. verify the remote SHA;
4. record local and remote SHA;
5. remain on the R19 code branch.

Do NOT check out the R20 taskbook carrier branch over the R19 worktree.

Read this taskbook using `git show origin/gpt/revolution-r20-autonomous-branch-arbitration-20261001:<path>`.

Then implement R20 on top of the published R19 code.

## Hard invariants

- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`;
- one and only one current ACTIVE reality;
- STANDBY never bypasses Gateway;
- generic plan select never activates STANDBY;
- model prose is never authority;
- model cannot write Journey.active_plan_version_id;
- trigger compatibility is deterministic and machine-readable;
- stale/expired/parent-invalid standby fails closed;
- a counterfactual simulation is not itself a real trigger.

## Phase A — machine-readable trigger contract

Every standby must carry a compact explicit trigger contract.

Minimum useful fields:
- `scenario_type`;
- `allowed_event_types`;
- affected activity/place/semantic scope;
- provenance classes allowed for activation;
- severity/threshold requirements when relevant;
- base/current PlanVersion identity;
- source counterfactual/simulation ID.

Examples:

Weather standby:
```json
{
  "scenario_type": "WEATHER_SHIFT",
  "allowed_event_types": ["WEATHER"],
  "affected_place_ids": ["..."],
  "allowed_provenance": ["PROVIDER_VERIFIED", "SYSTEM_DERIVED"]
}
```

Closure standby:
```json
{
  "scenario_type": "PLACE_CLOSURE",
  "allowed_event_types": ["CLOSURE", "SERVICE_UNAVAILABLE"],
  "affected_place_ids": ["..."],
  "allowed_provenance": ["PROVIDER_VERIFIED", "USER_REPORTED"]
}
```

Do not let "actionable" alone mean "compatible".

## Phase B — deterministic trigger matcher

Add one shared function, conceptually:

`standby_trigger_match(standby, event, current_plan) -> MatchResult`

It must verify:
- event type;
- affected scope;
- provenance allowance;
- parent/current plan relation;
- freshness;
- any threshold/severity contract.

Return named refusal reasons.

Required negative machine proof:

```text
WEATHER_SHIFT standby
+ CLOSURE event
=> STANDBY_TRIGGER_MISMATCH
```

Required positive machine proof:

```text
PLACE_CLOSURE standby for Place X
+ USER_REPORTED/PROVIDER_VERIFIED CLOSURE affecting Place X
=> trigger-compatible, then proceed to Gateway
```

Do not duplicate this logic inside the Agent tool and activation endpoint.

## Phase C — maintain at least two useful grounded branches

Do not make the final Agent test a one-option multiple-choice exam.

Before the trigger:
- have at least two fresh, authoritative, non-current STANDBY branches;
- branches must represent materially distinct failure modes;
- both must be internally feasible and truth-grounded;
- at least one must be semantically incompatible with the final trigger.

Preferred shape:
- one WEATHER_SHIFT branch;
- one PLACE_CLOSURE or MOBILITY_SHIFT branch.

If the counterfactual engine cannot naturally materialize the second branch, improve the existing R19 materializer just enough to support it.
Do not create a parallel solver.

## Phase D — real model branch arbitration

Create/execute a persisted Agent mission after the real Event exists.

The mission prompt must NOT contain:
- the correct standby plan ID;
- the expected tool sequence;
- "choose plan X".

It may say, in substance:

"Inspect the current Journey, Twin, event and available standby portfolio. Choose the safest truthful next action within the mission/policy bounds."

Required real configured model:
- `controller=configured_agent_runtime`;
- provider/model = current GLM/DeepSeek/Hermes-compatible runtime;
- persisted AgentRun + AgentRunSteps.

Expected available strategies:
1. inspect Journey;
2. inspect Twin/portfolio;
3. inspect current Event if not already included;
4. choose compatible standby and call `activate_standby`;
5. or call `request_replan` if no branch is suitable;
6. or return NO_ACTION when event is irrelevant.

The wrapper must not hardcode `activate_standby` merely because a portfolio exists.

## Phase E — compact compatibility information, not answer leakage

The Agent may receive server-owned portfolio summaries such as:
- plan ID;
- trigger family;
- compatibility with current event: MATCH / NO_MATCH / STALE;
- expiry;
- key changes;
- cost delta;
- schedule drift;
- protected commitment result.

It must not receive a hidden "recommended_plan_id" that makes the decision tautological.

If compatibility is exposed, it must be deterministic server output, not LLM-generated.

## Phase F — Gateway remains final authority

When the model calls `activate_standby`:
1. re-run trigger match;
2. verify parent is still current;
3. verify evidence freshness;
4. re-run canonical authority + feasibility;
5. evaluate autonomy/policy;
6. ALLOW_AUTO or REQUIRE_CONFIRMATION;
7. consume approval if required;
8. atomically supersede/activate;
9. remap cursor/commitments;
10. persist lineage to the trigger Event and AgentRun.

A correct model choice may still be refused by policy.
That is a successful authority boundary, not an Agent failure.

## Phase G — finish the product path

After successful activation in the disposable lab:
- continue the real HTTP execution state machine;
- complete remaining activities;
- reach Journey `COMPLETED`;
- final Twin must agree with the activated branch;
- old active plan remains retired/superseded;
- unused standby remains standby/retired according to current policy.

Be explicit that this is product-state execution in a disposable lab, not a claim that a human physically visited the places.

## Phase H — branch usefulness after activation

Once one standby becomes active:
- invalidate/retire sibling standbys whose parent is the old active plan;
- optionally rebuild only high-value branches against the new active plan on the next Autopilot pulse.

Do not allow a portfolio anchored to a superseded reality to survive as READY.

## Aggressive stretch — conflicting signals

If the core path closes early, test one multi-signal situation:

```text
CLOSURE on Place X
+
mobility delay elsewhere
+
2-3 fresh branches
```

Require the Agent to choose:
- the branch that actually addresses the dominant current constraint;
- or fresh replan if no branch covers both.

Do not invent a new risk model.
Use existing deterministic evidence and policy.

## Anti-ORD rules

- one capability branch;
- one final result report;
- no R20.1/R20.2 carousel;
- no new solver;
- no new event bus;
- no branch-per-trigger;
- no giant test framework;
- no proving the same generic-select refusal ten ways;
- no waiting for bad weather to make progress.

## Success levels

### REVOLUTION_A — semantic branch authority
Trigger contracts are machine-readable and mismatched events cannot activate a standby.

### REVOLUTION_B — real Agent arbitration
REVOLUTION_A + at least two fresh grounded standby branches + real configured model independently chooses standby vs replan vs no-action from live state.

### REVOLUTION_C — governed autonomous mission control
REVOLUTION_B + the chosen action crosses Gateway/approval correctly, activation is atomic, sibling branches are reconciled, and the revised Journey reaches COMPLETED.

### REVOLUTION_D — multi-signal branch reasoning
REVOLUTION_C + the real Agent correctly handles concurrent distinct live/user-observed signals without wrapper hardcoding.

Target C.
Push D only after C is machine fact.

## Final report

One file:
`REVOLUTION_R20_AUTONOMOUS_BRANCH_ARBITRATION_RESULT.md`

Include:
- R19 published remote SHA;
- R20 base/final code SHA;
- report SHA separately;
- active Journey;
- at least two pre-trigger standby branches;
- trigger contracts;
- final Event and provenance;
- negative trigger-mismatch receipt;
- real Agent provider/model;
- AgentRun ordered tool steps;
- evidence that prompt did not include correct plan ID;
- Gateway/approval result;
- old/new plan lineage;
- sibling standby disposition;
- final Journey/Twin;
- direct R20 regression tests + prior focused suite result.

## Success sentence

R20 closes when this is a machine fact:

> CityNexus had several truthful futures prepared before disruption, a real model independently identified which future actually matched the current reality, deterministic trigger authority prevented semantically wrong branches from activating, Gateway governed the mutation, and the Journey continued to completion.
