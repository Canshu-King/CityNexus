# R48 Continuous Journey Day Operator

## Result

R48 is implemented on the existing R47 branch. The Operator response now exposes one read-only `flow` projection that connects the current activity, next activity, presence, departure readiness, exact frozen route edge, milestone action, and stable notification key.

The lifecycle remains server-owned and uses the existing endpoints:

`depart → arrive → begin → complete → automatic current_activity_id handoff`

Every UI lifecycle action sends `truth_kind=OPERATOR_CONFIRMED_EXECUTION` with `operator_confirmed=true` and the existing signed traveler bearer. Missing authentication continues to fail closed; projections never write activity state, infer arrival from clock/proximity, or acquire a route during GET.

## Route and handoff behavior

- After completing activity N, the flow projects activity N+1 as current immediately.
- The N→N+1 edge uses the previous completed activity's exact Place and the persisted `JourneyLeg`/frozen mobility fact.
- Exact edges expose duration and `must_leave_by`; missing edges expose `NO_TRAVEL_EDGE` so the existing route check action remains the next step.
- Activity incidents combined with unresolved Operator operations/collective attention project `NEEDS_ATTENTION` while completion remains available.
- Last activity completion leaves `Journey.status=COMPLETED`, `current_activity_id=None`, and `DAY_COMPLETE` with no recovery cursor.
- Offline snapshots capture `continuous_flow` as read-only data.
- Milestones reuse `NotificationEvent` dedupe via `milestone_notification_key`.

## Fresh R48 experiment

Experiment receipt: [backend/output/r48-continuous-journey-day-operator-v1.json](D:/moodle/CityNexus-Revolution-RealTrip-Recovery/backend/output/r48-continuous-journey-day-operator-v1.json)

The fresh two-step slice enabled Operator, executed all four authenticated transitions for activity A, and observed activity B as the automatic current activity. The exact A→B edge reported 14 minutes and a computed leave-by time. `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` was preserved.

## Verification

- `uv run pytest tests/test_continuous_journey.py -q` — 10 passed.
- `uv run pytest tests/test_r28_execution_truth.py tests/test_r28_authenticated_member_principal.py tests/test_departure_activation.py -q` — 24 passed.
- `uv run pytest tests/test_operator_projection.py tests/test_r43_operator_loop.py -q` — 11 passed.
- `npm run typecheck` — passed.
