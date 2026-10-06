# Revolution R36 — Phase-Adaptive Guardian

## Why this is the next product capability

R35 proved that one bounded Guardian pulse can acquire fresh open-world evidence and remain honestly quiet when reality is compatible. The next product problem is not another verifier or another pulse. The current Autopilot treats every ACTIVE Journey as if the traveller were in the same operational situation: one fixed enrollment interval and one full sensing path refresh weather, mobility, live venue context, TravelerTwin, resilience, standby maintenance, and Guardian evaluation.

A real travel guardian must behave differently before departure, while approaching the next activity, in transit, during an activity, between activities, and overnight. This is a product capability because it changes whether the system is timely when help matters and quiet/cheap when it does not.

## R36 objective

Introduce a server-owned, deterministic **Journey phase controller** that derives an operational phase from the active plan, execution truth, Journey timezone, and the freezeable execution clock. The phase controller must drive Autopilot scheduling and sensing scope. It must never grant action authority.

Target phases:

- PRE_TRIP
- APPROACHING_NEXT
- IN_TRANSIT
- IN_ACTIVITY
- BETWEEN_ACTIVITIES
- OVERNIGHT
- JOURNEY_COMPLETE
- UNKNOWN

The exact names may change if code conventions demand it, but the semantics must remain inspectable and deterministic.

## Non-negotiable authority boundary

Keep `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.

Phase is **control-plane context, not world truth**. It may:
- choose the effective pulse interval;
- choose which active-plan activities are worth checking;
- choose a bounded look-ahead horizon;
- skip expensive provider work when it cannot affect the near-term Journey;
- annotate GuardianPulse evidence/trace so the UI and tests can explain why a check ran.

Phase must not:
- create or resolve disruption facts by itself;
- authorize a replan, booking, cancellation, payment, or plan mutation;
- convert simulated/estimated location or schedule state into LIVE_PROVIDER provenance;
- override Agent gateway/delegation/collective authority;
- infer physical arrival from wall-clock time alone.

Any recovery still requires the existing provider/Event/Agent/authority path.

## Code already landed with this taskbook

`backend/app/agent/guardian_phase.py` contains the deterministic phase-policy kernel. Integrate it rather than reimplementing phase semantics inside `autorun.py`.

## Required integration

### 1. Phase-aware due calculation

Replace the effective fixed-only cadence in Autopilot with:

`effective_interval = min(enrollment.interval_seconds, phase_policy.interval_seconds)`

where the enrollment interval remains a user/operator ceiling. Do not silently rewrite the stored enrollment row on each phase change.

`next_due_seconds()`, `_due()`, and the worker loop must use the same phase-policy computation so status and execution cannot disagree.

Recommended policy intent:
- APPROACHING_NEXT / IN_TRANSIT: urgent cadence (about 30 s)
- IN_ACTIVITY: moderate cadence (about 120 s)
- BETWEEN_ACTIVITIES: active cadence (about 90 s)
- PRE_TRIP: low cadence (about 300 s)
- OVERNIGHT: very low cadence (about 900 s)
- JOURNEY_COMPLETE: no further automatic pulse

Tests must use the freezeable `execution_clock`; do not sleep.

### 2. Phase-aware sensing scope

Extend live context watch with an optional explicit activity-id scope or equivalent server-owned selector.

Rules:
- never check terminal activities;
- APPROACHING_NEXT: check the next relevant venue and at most one immediately following venue;
- IN_TRANSIT: check destination + one following activity;
- IN_ACTIVITY: check current activity only when fresh venue reality can still matter, plus next activity;
- BETWEEN_ACTIVITIES: next + one following;
- PRE_TRIP: bounded upcoming horizon, not every activity of a multi-day trip;
- OVERNIGHT: next-day leading activities only;
- UNKNOWN: conservative bounded scope, never the whole trip by accident.

Weather/mobility collection should likewise avoid unrelated all-trip work where practical. Preserve exact provider binding and fresh-evidence rules from R34/R35.

### 3. Pulse evidence and product surface

Persist the derived phase in the GuardianPulse result, e.g.

```json
{
  "phase": {
    "phase": "APPROACHING_NEXT",
    "reason_code": "NEXT_ACTIVITY_WITHIN_APPROACH_WINDOW",
    "current_activity_id": null,
    "next_activity_id": "...",
    "monitored_activity_ids": ["...", "..."],
    "lookahead_minutes": 180,
    "effective_interval_seconds": 30
  }
}
```

Expose this through the existing latest-pulse projection. The traveller-facing Live Recovery surface may use ordinary copy such as “Watching your next stop closely” but must not dump internal enums.

### 4. Execution truth beats inferred clock phase

If execution truth says an activity is IN_PROGRESS / ARRIVED / EN_ROUTE, prefer that over schedule inference. Clock-only inference may choose monitoring urgency/scope but must not claim real-world arrival or completion.

If evidence is contradictory, return UNKNOWN/conservative policy and preserve the contradiction in evidence.

### 5. No-op discipline

R35 fixed OPPORTUNITY_WINDOW leakage. Preserve it. A phase transition is not itself a recovery trigger and must not start a Hermes AgentRun.

No event + compatible provider facts => no AgentRun, no proposal, no mutation.

## Tests required before any live closure

Add focused tests for at least:

1. PRE_TRIP -> APPROACHING_NEXT as frozen time crosses the window.
2. explicit EN_ROUTE execution truth wins over clock-only inference.
3. IN_ACTIVITY monitors current + next but not distant future venues.
4. OVERNIGHT does not refresh the whole multi-day plan.
5. effective cadence changes without rewriting enrollment.interval_seconds.
6. UNKNOWN/contradictory state is conservative and authority-neutral.
7. phase transition alone starts zero AgentRuns and creates zero mutation.
8. R35 opportunity isolation remains green.
9. existing live-context exact provider-binding/opening-hours tests remain green.
10. TypeScript and Live Recovery focused Playwright remain green if UI copy changes.

Do not spend the run rebuilding broad verifier coverage. Use the narrow regression set plus the directly affected existing suites.

## One bounded R36 live closure — only after tests are green

Do **not** rerun R33, R34, or R35 and do not replay the R35 Journey.

The R36 live closure must prove the new capability, not repeat “pulse is all clear”:

- create/use one fresh Journey whose frozen/test setup demonstrates a meaningful phase boundary in deterministic tests;
- for live closure, use the real current execution phase of that fresh Journey (do not fake physical travel);
- execute at most one bounded Autopilot cycle with live providers after integration;
- receipt must show the derived phase, selected activity scope, effective cadence, fresh provider provenance for any provider actually called, AgentRun count, and mutation count;
- if the real phase does not produce a material disruption, `ALL_CLEAR` / `NO_MATERIAL_CHANGE` is an acceptable truthful result;
- do not retry weather/closure/provider calls to manufacture a mutation;
- if provider access is unavailable, report BLOCKED/PARTIAL honestly and stop. No second live cycle.

This is not a rerun of R35: acceptance is phase-derived **scheduling/scope correctness** plus preserved authority boundaries, not whether a disruption happens.

## Deliverable

Commit code, focused tests, and `REVOLUTION_R36_PHASE_ADAPTIVE_GUARDIAN_RESULT.md` to this same branch and push. The result must distinguish deterministic test proof from the single live receipt.

Do not rewrite historical R33-1 BLOCKED, R34 NO_MATERIAL_CHANGE, or R35 ALL_CLEAR/limitation records.
