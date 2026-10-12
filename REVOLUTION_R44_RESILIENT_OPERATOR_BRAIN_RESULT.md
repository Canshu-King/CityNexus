# Revolution R44 — Resilient Operator Brain & Recovery Resume

## Product result

CityNexus now keeps an unresolved trip incident alive when its external planning brain is unavailable. The Journey remains under Operator watch, the same Event/incident fingerprint and RecoveryEpoch are retained, and a bounded worker retry can resume the original recovery mission without recreating the disruption, restarting Operator, or creating a second standing mission.

## Delivered loop

- Added durable `OperatorRecoveryResume` lineage for Journey, Event, RecoveryEpoch, standing/recovery mission, GuardianRun, active plan, material-world epoch, failure classification, bounded retry, safe-to-resume, and runtime owner.
- Added runtime candidate states `UNCONFIGURED`, `CONFIGURED_UNKNOWN`, `AVAILABLE`, and `TEMPORARILY_FAILED`. Credentials alone never claim availability.
- Added durable runtime ownership and zero-tool handoff. A provider may hand off only before a tool or approval boundary; after one, the run fails closed as `OPERATOR_BRAIN_UNSAFE_TO_FAILOVER`.
- Repeated Guardian pulses reuse the same blocked GuardianRun and incident lineage during backoff. Operator stays enabled and the user-facing projection says the problem was remembered.
- Due retries reuse the same RecoveryEpoch and recovery mission, then return through the existing Agent → replan/Gateway → approval → continuation chain.
- Added `brain` to `GET /api/v1/journeys/{journey_id}/operator` and rendered ordinary traveller copy in the Journey Operator card. Provider/error details stay in advanced durable state.

## Fresh product experiment

The one fresh Journey experiment is explicitly labelled `LAB_RUNTIME_AVAILABILITY_SIMULATION`.

1. Started Operator with `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.
2. Injected one normal `LAB_FIXTURE` closure through the provider fixture and Guardian pulse.
3. With no external runtime configured, received `OPERATOR_EXTERNAL_AGENT_BLOCKED`; one material Event and one GuardianRun were persisted, with a safe durable resume row.
4. A second pulse reused the same GuardianRun and Event while the server-owned retry window was active.
5. After the retry became eligible, a controlled adapter with the real Journey Agent result shape resumed the same recovery mission. No second standing mission, Event, or GuardianRun was created; Autopilot remained enabled.

Experiment outcome: `OPERATOR_BRAIN_RESUMED_RECOVERY`. This is a lab availability simulation, not a live DeepSeek/Hermes result. No deterministic recovery fallback was used.

## Validation

- `tests/test_operator_brain.py`: 6 passed.
- `tests/test_r44_resilient_operator_brain.py`: 3 passed.
- `tests/test_r43_operator_loop.py`: 3 passed.
- `compileall`: passed.
- Frontend TypeScript check: passed.
- R44 Playwright was attempted once and blocked before browser assertions because the configured launcher uses system Python 3.10, which lacks `enum.StrEnum`.

Artifact: `backend/output/r44-resilient-operator-brain-v1.json`
