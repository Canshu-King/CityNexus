# Revolution R26 — Behavioral Closure Strike

## Objective

Close the missing link:

```text
human answer
-> explicit mission intent
-> governed server action
-> different physical execution
```

Do NOT add R27 capability yet.

## Phase 0 — preserve the existing good machinery

Keep:
- decision_sensitivity receipt;
- CLARIFICATION_REQUIRED;
- WAITING_FOR_USER;
- server-derived options;
- stale fingerprint;
- THIS_JOURNEY default;
- parent/child mission;
- authority inheritance;
- provider-fact vs human-value distinction.

Do not rewrite these.

## Phase A — run clarification at the actionable decision epoch

For the final proof, advance the fresh Journey until W1 itself is the current Activity in ACTIVE state and has not departed.

Then create/run the R26 mission.

The question compares:
- TAKE_NOW = current W1;
- TAKE_LATER = later W2.

This means the user answer can be enacted immediately without a new future-intent scheduler.

## Phase B — add one bounded Agent action for clarified execution

Preferred tool name:

`apply_clarified_horizon_choice`

It is NOT a generic arbitrary skip tool.

Inputs:
- journey_id;
- mission_id;
- decision option/strategy only if needed.

The server derives:
- parent clarification;
- exact option mapping;
- current explicit mission answer;
- W1 activity identity;
- later W2;
- current active plan.

For `DEFER`, require:
1. child mission has parent_mission_id;
2. parent clarification was answered TAKE_LATER;
3. child CURRENT_EXPLICIT_MISSION.strategy == DEFER;
4. decision fingerprint/current plan is still compatible;
5. current activity is exactly the server-derived W1;
6. W1 is optional, not C3/C4, not locked;
7. no unavoidable booking/payment/loss exceeds mission authority;
8. W2 remains GROUNDED_FEASIBLE;
9. scarce-resource conflict still holds.

The model does not provide an activity ID.

## Phase C — reuse the existing skip transition

Refactor the current skip handler into a shared internal helper instead of copying its logic.

Conceptual shape:

`_skip_current_activity(... actor_type, reason, mission_id, clarification_id)`

Existing HTTP user skip uses:
- actor_type USER;
- ordinary user reason.

R26 clarified defer uses:
- actor_type AI_AGENT or SYSTEM_WITH_EXPLICIT_USER_CHOICE;
- reason `CLARIFIED_DEFER_FOR_LATER_OPTION`;
- mission/clarification provenance.

Preserve:
- protected/locked guards;
- outcome event;
- audit;
- cursor transition;
- offline/Twin refresh.

Do not let the model skip arbitrary activities.

## Phase D — actual mobility after skipping W1

This is mandatory.

If skipping W1 changes actual adjacency:
- identify the actual execution origin;
- identify next non-skipped W2;
- capture a fresh runtime provider edge for origin -> W2;
- require hard-eligible truth;
- persist the receipt as an execution override / actual-edge receipt;
- keep the frozen PlanVersion mobility evidence immutable.

Use existing runtime mobility capture.

Choose the smallest existing persistence surface; do NOT create a mobility subsystem.

The next depart must be blocked if:
- the plan edge is no longer the actual edge;
- and no valid live execution override exists.

Twin/inspection should expose the actual edge used after the skip.

## Phase E — completion semantics must match mutation

After successful clarified DEFER:
- Agent should conclude `MUTATION_EXECUTED`, not `NO_ACTION`;
or the runtime should derive the mutation contract from the tool trace.

A child mission with explicit DEFER must NOT be allowed to close as a successful `NO_ACTION` while W1 remains executable/current.

Add a fail-closed check.

## Phase F — primary live proof

Fresh provider-backed Journey.

At decision time:
- W1 is current;
- W2 later;
- both GROUNDED_FEASIBLE;
- each individually affordable;
- combined resource exceeds optional budget;
- no explicit preference before clarification.

Real Agent:
1. inspect_journey;
2. inspect_twin;
3. CLARIFICATION_REQUIRED.

User:
- TAKE_LATER;
- THIS_JOURNEY.

Child Agent:
1. inspect;
2. apply_clarified_horizon_choice;
3. mutation receipt;
4. machine-valid completion.

Required machine facts:
- W1 = SKIPPED;
- skip reason references clarification;
- active PlanVersion unchanged;
- direct actual origin->W2 live provider edge captured;
- W1 optional consumed cost = 0;
- W2 current;
- no booking/reservation invented.

Then:
- depart/arrive/begin/complete W2;
- complete remaining Journey;
- final Journey COMPLETED.

Final execution history must NOT contain W1 completed.

## Phase G — opposite answer control

Comparable fresh Journey with same hard facts.

User answers TAKE_NOW.

Required:
- W1 is NOT skipped;
- W1 executes normally;
- its actual consumed cost is reflected;
- the later horizon/resource state recomputes from the reduced budget.

It is acceptable for W2 to be skipped/declined later if resource truth requires it.

The important proof:
`TAKE_NOW` and `TAKE_LATER` produce materially different execution histories.

## Phase H — negative guards

Focused regressions:
1. model cannot apply clarified choice without parent answer;
2. stale clarification cannot mutate;
3. TAKE_LATER cannot skip protected/locked W1;
4. loss/booking beyond authority blocks or requires normal approval;
5. direct post-skip mobility capture failure rolls back the skip;
6. no hard-eligible post-skip edge => depart blocked;
7. DEFER prose/NO_ACTION without execution effect is not closure;
8. TAKE_LATER -> W1 SKIPPED, W2 current;
9. TAKE_NOW -> W1 remains/executed;
10. generic skip still behaves exactly as before;
11. behavioral skip does not become learned dislike evidence;
12. R20-R26 focused lineage passes once at end.

## Anti-ORD rules

- no R26.1;
- no R27 yet;
- no new planner;
- no new memory framework;
- no new future-intent scheduler;
- no duplicate skip state machine;
- no mutation of frozen plan evidence;
- no report series.

## Final artifact

Update the existing:

`REVOLUTION_R26_DECISION_CRITICAL_CLARIFICATION_RESULT.md`

Add a section:
`Behavioral Closure Addendum`.

Do not create a second R26 result file.

## Closure sentence

> CityNexus did not merely ask the right human-value question and remember the answer; the answer changed the governed execution reality. TAKE_LATER caused the current optional activity to be skipped under server authority, a new direct live route was grounded, the scarce resource was preserved, and the later chosen experience actually executed; the opposite answer produced a different physical trip.
