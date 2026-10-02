# R22 implementation sketch — shortest path

## 1. Keep the current opportunity primitives

Reuse:
- `_twin_snapshot().context.opportunity_window`;
- `OpportunityWindow`;
- `evaluate_window_replacement`;
- current real-city discovery/search;
- `acquire_place_facts`;
- runtime Valhalla capture;
- current replan PlanVersion materialization;
- Gateway/approval.

Do NOT build OpportunityEngineV2.

## 2. Create a bounded positive trigger

Smallest honest path:
- when Autopilot/Twin sees `available_minutes >= configured_min`;
- no higher-priority unresolved event exists;
- current plan + next protected commitment are stable;

create/reuse one SYSTEM_DERIVED event:
`event_type=OPPORTUNITY_WINDOW`

Payload:
- active_plan_version_id;
- current routing key;
- opens_at;
- must_depart_by;
- available_minutes;
- next commitment/activity semantic key;
- Twin snapshot_at.

Use a stable fingerprint to dedupe.

When the window disappears or the parent plan changes, resolve/expire the opportunity event.

## 3. Let Agent candidate search remain open-world

No Place ID in the mission.

Good trace:
```text
inspect_journey
inspect_twin
search_city_services
acquire_place_facts
[maybe another bounded search/acquisition]
request_replan
list_replans
accept_replan
```

The exact trace may vary.

Do not hardcode the candidate or expected tool sequence.

## 4. Extend request_replan minimally for opportunity candidate hints

`AgentToolCall.place_ids` already exists.

For `OPPORTUNITY_WINDOW` only:
- optionally pass 1-3 candidate Place IDs;
- add them to the request signature/idempotency facts;
- server validates same-city provider-backed rows;
- replan generator uses them as the bounded candidate pool.

Extend `ReplanGenerateRequest` only if necessary.

Do not trust caller-supplied opening/cost/travel.

## 5. Add F4_OPPORTUNITY_INSERTION to existing replan generation

This family has no removed disrupted activity.

Materialization:
- preserve executed/current prefix;
- insert one optional VISIT into the window;
- preserve the future C4/fixed anchor;
- re-use existing semantic-key/commitment remap logic;
- construct fresh live mobility for current->candidate and candidate->anchor;
- retime only mutable future rows if needed;
- fail closed if any truth is missing.

The proposal diff should explicitly say:
- added activity/place;
- no removed protected activity;
- cost delta;
- end-time drift;
- opportunity window evidence;
- mobility snapshot ID.

## 6. Do not call direct replace_activity for final success

It currently contains legacy mock/cost semantics.

If Codex touches it at all, regression:
- provider-backed replacement Place uses canonical cost evidence;
- live runtime mobility;
- unknown cost cannot become zero.

But preferred path is no dependency on it.

## 7. Event lifecycle fix

At accepted replan/standby:
- if the trigger's Journey impact is fully addressed, set event status RESOLVED and resolved_at;
- store resolution reason in payload/audit;
- do not erase the original event.

For OPPORTUNITY_WINDOW:
- accepted insertion => CONSUMED/RESOLVED;
- NO_ACTION may resolve that specific window with reason DECLINED_BY_AGENT;
- parent plan/window change invalidates it.

## 8. Strong ACTIVE NO_ACTION control

Do not use a COMPLETED Journey.

Use ACTIVE state and a real opportunity window.

The model must have a genuine choice and still decline.

Machine contract:
`completion_contract.kind = NO_ACTION`
and active_plan_version_id unchanged.

## 9. conclude_recovery hygiene

Tool schema max reason = 500.

Before dispatch, compact a model-generated reason to <=500 or teach the tool wrapper description clearly enough that the model reliably stays within bounds.

Keep the full human-readable narrative in run.outcome/final text, not tool args.

## 10. Focused regressions

Add direct R22 tests:
1. opportunity signal dedupes for same plan/window.
2. higher-priority open disruption suppresses positive opportunity mission.
3. candidate already in active plan rejected.
4. canonical unknown opening/cost blocks insertion.
5. both live route legs required.
6. F4 proposal increases activity count by one.
7. C4 commitment preserved.
8. opportunity event resolves after accepted insertion.
9. ACTIVE NO_ACTION leaves plan unchanged.
10. direct replace_activity cannot use mock/legacy truth if touched.

Then run the existing R21 focused suite once.

No new harness.
