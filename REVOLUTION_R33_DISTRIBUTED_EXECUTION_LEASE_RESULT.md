# Revolution R33 — Distributed Execution Lease & Zombie Worker Fencing

## Current status

**FOUNDATION PROVEN / DISTRIBUTED LIVE CLAIM NOT YET PROVEN**

Branch:

`gpt/revolution-r33-distributed-execution-lease`

R32 frozen base:

`d3064f869feedd16e8c843efbb38b29e218d2b55`

R33 foundation CI head:

`f5386955fffba339a9d3b8d7fec3123071075b2d`

GitHub Actions:

**171 passed / 0 failed / 4 deprecation warnings**

No R33 live strike has been executed yet.

## What GPT already implemented

### Durable execution lease model

New model:

`AgentExecutionLease`

with durable fields for:

- mission lineage;
- Journey;
- monotonic generation;
- owner worker id;
- RecoveryEpoch snapshot at acquire;
- ACTIVE / EXPIRED / SUPERSEDED / RELEASED state;
- acquire / heartbeat / expiry / release timestamps;
- predecessor -> successor lease lineage.

Database invariants include:

- unique generation per mission;
- one ACTIVE lease per mission enforced by a partial unique index.

### AgentRun lease identity

`AgentRun` now has nullable R33 fields:

- `execution_lease_id`
- `execution_lease_generation`
- `worker_id`

Historical rows remain readable without fabricated retroactive leases.

### Existing-database compatibility

Both:

- `backend/db/schema.sql`
- `backend/app/db/session.py::ensure_schema`

know how to create/reconcile the new lease table and AgentRun fields.

The project does not use Alembic for this surface; the implementation follows
the repository's existing schema.sql + ensure_schema convention.

### Server lease core

New module:

`backend/app/agent/execution_lease.py`

currently provides:

- `acquire_execution_lease`
- `renew_execution_lease`
- `current_execution_lease`
- `latest_execution_lease`
- `validate_execution_lease_binding`
- `take_over_execution_lease`
- `release_execution_lease`

Canonical stale execution code:

`AGENT_EXECUTION_LEASE_SUPERSEDED`

Validation is deliberately causally inert: checking a stale lease never creates
a successor lease.

Takeover fences the predecessor before inserting its successor so the database
one-ACTIVE index, rather than a process lock, is the final concurrency arbiter.

### Deterministic lease tests

New file:

`backend/tests/test_r33_execution_lease.py`

proves:

- first acquire is generation 1;
- renewal keeps the same generation;
- takeover before expiry is rejected;
- expired L1 takeover creates L2;
- L1 becomes SUPERSEDED with durable successor lineage;
- zombie L1 validation produces typed
  `AGENT_EXECUTION_LEASE_SUPERSEDED`;
- stale validation does not mint L3;
- zombie heartbeat cannot renew after takeover;
- database rejects two ACTIVE leases for one mission;
- released lease is non-spendable;
- AgentRun can bind exact lease identity.

### CI

New workflow:

`.github/workflows/r33-narrow.yml`

runs the R33 lease tests together with the complete frozen R28-R32 safety gate.

Current result:

**171 passed / 0 failed**

## What is intentionally not implemented yet

The durable primitive exists, but R33's distributed claim is **not** proven.

Codex must still implement:

1. Runtime acquisition/binding of an execution lease before first provider call.
2. Lease validation immediately before every external model call.
3. Lease validation immediately after every provider response.
4. Lease validation inside AgentToolGateway before authority-bearing dispatch.
5. Lease validation on approval/continuation resume.
6. Typed durable `execution_lease_guard` AgentRunStep on supersession.
7. Immutable run identity across takeover: L2 must get a successor AgentRun,
   never retarget A/L1.
8. Worker heartbeat / expiry semantics integrated with actual worker execution.
9. Multi-process takeover race tests with independent DB sessions/processes.
10. Exactly-once mutation across worker death/takeover.
11. R33 multi-process live harness.
12. Real WB2api/Hermes barrier proxy.
13. Hard-kill Worker A after a real provider call starts.
14. Worker B L2 takeover.
15. Zombie A/L1 delayed response rejection before any model-selected tool.
16. R33 machine verifier and fresh evidence protocol.
17. One honest live strike.

## Critical architecture rule

Do not wire the new lease only into autorun.

The lease is a general Agent execution authority boundary.

The same validation primitive should protect:

- request-triggered Agent runs;
- Guardian/autopilot runs;
- continuation resumes;
- takeover runs.

Process-global locks remain optional local optimization only.

## Immediate next implementation slice

Codex should start with **Runtime + Gateway integration**, not the live harness.

The first new deterministic proof should establish:

    current RecoveryEpoch + current ExecutionLease -> tool allowed

    stale RecoveryEpoch + current ExecutionLease -> RECOVERY_EPOCH_SUPERSEDED

    current RecoveryEpoch + stale ExecutionLease
      -> AGENT_EXECUTION_LEASE_SUPERSEDED

    stale RecoveryEpoch + stale ExecutionLease
      -> no mutation, no new lease, no new RecoveryEpoch

Then prove provider-wait fencing:

    A/L1 starts provider request
    L2 takeover occurs while response is in flight
    A response returns
    response is discarded before any returned tool executes

Only after that deterministic seam is green should Codex build the actual
multi-process zombie-worker harness.

## Full taskbook

Read and follow:

`taskbooks/revolution/R33_DISTRIBUTED_EXECUTION_LEASE_ZOMBIE_FENCING.md`

That taskbook is authoritative for the R33 success bar.

## Revolution principle

R32 made stale **reality** powerless.

R33 must make stale **execution ownership** powerless.

A dead process may come back with a brilliant, valid model answer.

The answer is still worthless if its durable lease generation is no longer
current.
