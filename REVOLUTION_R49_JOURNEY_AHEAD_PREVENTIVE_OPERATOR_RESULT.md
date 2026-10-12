# R49 Journey Ahead / Preventive Operator

## Result

R49 adds a bounded, read-only `ahead` projection to `GET /api/v1/journeys/{id}/operator`. It looks across nonterminal future activities inside a 12-hour horizon, ranks risks using lead time, protected commitment, booking exposure, route slack, and actionability, and carries a stable identity built from journey, activity, risk class, provider evidence, and material world epoch.

The existing R48 `flow` remains the foreground execution projection. Predictive-only Events are excluded from the current material incident query, so a forecast cannot move the current activity or change execution truth. The GET path only reads the persisted resilience snapshot, Guardian status, and brain status; it does not call providers or mutate state. `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` remains preserved.

## Fresh R49 experiment

Receipt: [backend/output/r49-journey-ahead-preventive-operator-v1.json](D:/moodle/CityNexus-Revolution-RealTrip-Recovery/backend/output/r49-journey-ahead-preventive-operator-v1.json)

- A current activity was `IN_PROGRESS`; B was next; C was a future forecast-risk activity.
- Operator was enabled with `PLAN_ONLY` autonomy.
- A captured provider forecast and a predictive-only Weather Event targeted C.
- The external Agent was invoked once. It returned `NO_FEASIBLE_RECOVERY`, a valid governed outcome under the lab fixture.
- The current activity remained `IN_PROGRESS`; the Operator incident stayed `null`.
- `ahead` selected C, remained `WATCHING_FUTURE` at 419 minutes of lead time, exposed grounded provider evidence, and retained `predictive_only=true` / `read_only=true`.
- No current execution transition or preventive mutation occurred.

## Verification

- `uv run pytest tests/test_journey_ahead.py tests/test_continuous_journey.py tests/test_operator_projection.py -q` — 29 passed.
- `uv run python -m compileall -q app` — passed.
- `npm run typecheck` — passed.
- `git diff --check` — passed.
- Added `frontend/e2e/r49-journey-ahead.spec.ts` to assert current flow and future-risk strip coexist.

## Files

- `backend/app/agent/journey_ahead.py`
- `backend/app/operator_projection.py`
- `frontend/src/api/citynexus.ts`
- `frontend/src/features/execution/LiveRecovery.tsx`
- `frontend/src/styles.css`
- `backend/tests/test_journey_ahead.py`
- `frontend/e2e/r49-journey-ahead.spec.ts`
