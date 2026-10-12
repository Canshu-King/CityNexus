# R18 implementation sketch — shortest path

## 1. Fix Trip Studio evidence acquisition, not the gate

Current Trip Studio:
- loads `plan.mobility_evidence_json`;
- checks reordered adjacent pairs against that frozen matrix;
- fails when a pair is missing.

Add a helper roughly shaped as:

```text
capture_preview_mobility(
  journey,
  base_plan,
  requested_order,
  existing_snapshot
) -> PreviewMobilitySnapshot
```

Behavior:
- derive required pairs;
- reuse fresh matching facts;
- capture only missing pairs through current live mobility provider;
- persist a separate preview snapshot/receipt;
- never rewrite `base_plan.mobility_evidence_json`.

Then evaluate Trip Studio against the preview snapshot.

## 2. Reuse current mobility provider APIs

Do not invent a new provider client.

Find and reuse the same route capture path used by:
- real plan generation;
- recovery/replan;
- Guardian incident snapshots.

The preview path should emit the same fact shape so existing deterministic feasibility can consume it.

## 3. Make cost-status semantics explicit

When constructing preview facts:
- carry provider mode;
- carry `paid_mode` / equivalent deterministic classification if available;
- carry `cost_status`, amount, currency;
- only assign KNOWN_FREE from a deterministic no-fare mode contract;
- paid unknown remains UNKNOWN.

Do not "fix" R17 by deleting `UNKNOWN_MOBILITY_COST`.

## 4. Materialize shadow plans minimally

Do not create a new large persistence subsystem if PlanVersion can express this safely.

Possible minimal shape:
- PlanVersion status/source or explanation marks `STANDBY_COUNTERFACTUAL`;
- parent_plan_version_id points to active plan;
- never set `journey.active_plan_version_id`;
- explanation stores:
  - counterfactual simulation ID;
  - trigger type;
  - evidence snapshot ID;
  - expiry;
  - feasibility result.

If current status enum cannot represent standby cleanly, add the smallest explicit model needed rather than overloading ACTIVE/CANDIDATE ambiguously.

## 5. Use counterfactual simulations as demand signals

For each top counterfactual:
- inspect `plan_changes`;
- derive needed replacement Places / adjacency pairs;
- determine missing canonical facts/mobility;
- acquire only what blocks a feasible standby.

This is where R15 VOI logic should be reused.

## 6. Integrate live forecast into strategy explanation, not fake scoring

Add an evidence-backed forecast exposure component with raw provenance.

Do not create fake "weather_quality=0.87" numbers.

Prefer:
- precipitation probability at scheduled time;
- weather code;
- outdoor exposure boolean;
- threshold relation;
- source observation ID.

Any normalized risk score must be derivable and explained.

## 7. Test the R17 exact blocker

Add a regression matching the failed Nara pivot:
- base active plan has frozen edges A->B->C;
- hypothetical order needs A->C;
- A->C absent from base snapshot;
- preview path captures live/fake-provider A->C into NEW preview snapshot;
- deterministic gate evaluates it;
- active base snapshot remains unchanged.

Also test missing/unknown paid cost still blocks.

## 8. Do not wait on weather for completion

Close REVOLUTION_A/B with safe live weather if necessary.

If live weather happens to produce a threshold crossing, continue to C/D.
Do not rerun dozens of cities only to manufacture drama.
