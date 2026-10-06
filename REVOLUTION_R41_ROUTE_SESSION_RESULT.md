# CityNexus Revolution R41 — Route Session & On-Demand Mobility Edge

## Closure

- Source head: `efcb300296b3453977e83a5421182c3b4a2a96e7`
- Fresh Journey: `4af1efd7-1440-4f33-adf4-5493795643eb`
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- Closure status: `ROUTE_SESSION_READY`
- Active plan unchanged: `0133c4e6-05f4-5ef4-ad24-ff8e0cde4bf4`
- One `POST /routes/acquire`, one provider pair, one `ProviderCall`, no location observation

## Exact route session

- Operation: `2978de5d-8033-481d-8972-b070c2b6d455`
- Fingerprint: `9cba81e6296710475da62bda12b90c16129328378dcdc94f2b33b5ea6ccd54d7`
- Lifecycle: `QUEUED → RUNNING → COMPLETED`
- Outcome: `ROUTE_READY`
- Origin: `real-place-b47a20314c81d5a81381d4a4` (`なら工藝館`, user-confirmed planned origin)
- Target: `real-place-22cf72809897ff4c7f312fcf` (`依水園`)
- Mode: `WALK`
- Provider: `valhalla-http`, provenance `LIVE_PROVIDER_CAPTURE`
- Frozen `MobilityFact`: `b93e3856-fee1-451a-bd2a-743a284b10fa`, 22 minutes

The exact fact was consumed by the R39 launch edge and R38 readiness projection. Readiness returned `LAUNCH_ROUTE_READY`, route evidence `edge_match=true`, and `must_leave_by=2026-10-07T08:08:00+08:00` with a ten-minute safety buffer. The offline snapshot carries the last terminal route session under `route_session` and performs no provider capture.

## Implementation

- Durable `RouteAcquisitionOperation` model/table with stable semantic fingerprint and a partial unique index for open operations.
- Server-side target and grounded origin resolution; client cannot submit coordinates.
- Explicit provider capture only from the acquire command; GET, readiness, offline, and Guardian paths remain read-only.
- Exact `MobilityFact` persistence, provider call receipt, reusable completed-operation idempotency, and separate `UNAVAILABLE` versus `FAILED` outcomes.
- Execution UI adds a `Check route` action and user-facing ready/unavailable copy without exposing internal error details.

## Verification

- Focused regression: **49 passed**, 3 framework deprecation warnings.
- Python `compileall`: passed.
- Frontend TypeScript check: passed.
- Fresh live closure: passed; no Event, AgentRun, ReplanProposal, or plan mutation rows were created.

Machine receipt: [backend/output/r41-route-session-v1.json](D:/moodle/CityNexus-Revolution-RealTrip-Recovery/backend/output/r41-route-session-v1.json)
