# Revolution R28 — Authenticated Collective Continuity Result

## Verdict

`PROVEN`

Machine verdict: 14 `PROVEN`, 0 `NOT_PROVEN`, 0 `CONTRADICTED`.

- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- Agent runtime: `hermes / cn:glm-5.3-flash`
- mobility: live `valhalla-http` through `https://valhalla1.openstreetmap.de`
- execution truth: `SIMULATED_STATE_TRANSITION`
- physical presence/device execution: **not claimed**

The result proves the product/API state machine and authenticated human-in-the-loop continuation. It does not claim that a traveler physically moved in the real world.

## Fresh disposable closure run

- database: `backend/r28-live-73d141526faecc05.sqlite3`
- Journey: `308da14a-bc5f-4ff8-9caa-a6bbd8b10063`
- owner Traveler: `a901ab43-926e-49db-85f1-0804cbfc4061`
- admin Traveler: `34c2ebe8-affb-4da1-9c7e-0f65b11af216`
- owner JourneyMember: `134c94e5-df32-4069-a895-3c497553ebcd`
- admin JourneyMember: `2cfde9df-f799-40b8-95ff-70f2b9dfdcb0`
- C4 commitment: `R28-C4-ANCHOR`
- first AgentRun: `3b4d6b01-5a0c-4047-a4c7-af5f86361944`
- resumed AgentRun: `f9ee60be-4137-44a5-9b3d-fa94cb10599a`

The owner and admin had separate non-empty journey-scoped preferences (`garden` and `museum`). The active Journey had two materially different server-derived grounded proposals and a system-derived opportunity event. The Agent mission did not contain candidate IDs, member answers, event IDs, or a prescribed recovery sequence.

The catalog rows came from the captured provider-backed Nara world used as the setup source; they were copied into a new disposable DB without hand-inventing facts. Mobility for the active plan and proposals was captured through the live Valhalla path.

## Authenticated collective sequence

1. The real Agent inspected the shared Journey and member-aware Twin.
2. The server exposed two grounded proposals with a material member trade-off.
3. The Agent returned the decision to the members; the parent mission became `WAITING_FOR_MEMBERS`.
4. Owner and admin each answered through their own signed traveler bearer. Audit rows bind each response to the corresponding authenticated Traveler and JourneyMember.
5. The aligned responses resolved the collective decision and created the child mission.
6. The resumed Agent inspected the resolved server-owned decision and produced the governed proposal acceptance.
7. Gateway created `ActionApproval`; the owner approved it through the signed principal route.
8. Approval was consumed exactly once and the pending action resumed on the same AgentRun lineage. The resumed tool step was `MUTATION_EXECUTED`.
9. The selected proposal became the active PlanVersion; the non-selected sibling became terminally invalidated/rejected.

Approval receipt:

- approval: `1b0d40b8-90b4-4cb3-8c70-b56448916ac3`
- selected proposal: `b88c11b1-e52c-4747-a67e-2b63b3a8972f`
- accepted plan: `d3caebd0-6c70-4732-b511-0c241021bc73`
- approval status: `CONSUMED`

## Final execution

The accepted plan’s three activities all passed the normal HTTP state machine:

`depart -> arrive -> begin -> complete`

Final database state:

- Journey: `COMPLETED`
- active PlanVersion: `d3caebd0-6c70-4732-b511-0c241021bc73`
- current activity: `null`
- all three accepted-plan activities: `COMPLETED`
- protected C4 activity: `COMPLETED`
- every execution event: `SIMULATED_STATE_TRANSITION`

This explicit execution label preserves the R28 evidence boundary: API state-machine completion is not physical-world completion.

## Narrow fixes made during closure

1. `backend/run_r28_live.py` now handles the product’s post-activation `ACTIVE -> EN_ROUTE` execution predecessor instead of silently skipping the first activity and attempting to depart the second activity.
2. `backend/scripts/r28_machine_verdict.py` no longer passes the fact field `status` twice into `_verdict()`; the facts are now named `run_status`, `approval_status`, and `collective_status`.

## Evidence scope

The machine receipt proves **two distinct signed, in-force Journey member principals** made the collective responses and that the authorized OWNER principal approved the gated mutation. The closure harness minted those short-lived HMAC bearer credentials inside a trusted local operator process.

Therefore this R28 closure proves the CityNexus principal boundary, member separation, authorization policy, durable wait/resume lineage, and exactly-once mutation path. It does **not** prove internet-grade identity verification, nor does it prove that two physically distinct people manually operated two browsers. A production identity provider can replace the local signer without changing the JourneyMember authority seam.

## Bounded replay prerequisites

The committed harness contains no credentials and no machine-specific user path. A local replay must provide:

- `CITYNEXUS_WB2API_CONFIG` -> local WB2api `config.json` containing the operator's API credential;
- optionally `CITYNEXUS_R28_SOURCE_DB` -> captured provider-backed R27 source DB (defaults to `backend/r27-agent-closure-20261005.sqlite3` when present locally).

Neither credential material nor the disposable runtime DB is committed.

## Verification

- R28 authenticated principal / durable continuation / execution-truth focused tests: `22 passed`
- machine verdict: `PROVEN (14/14)`
- `git diff --check`: passed
- Python compile check for the live harness and verdict script: passed
- prior Relay UI contract and Playwright checks remain on this branch; no WB2api/provider changes were made.

Machine receipt: [R28_MACHINE_VERDICT.json](output/revolution-r28-live-20261005/R28_MACHINE_VERDICT.json)

