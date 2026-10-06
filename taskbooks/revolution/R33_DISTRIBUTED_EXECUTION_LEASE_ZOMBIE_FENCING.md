# R33 Revolution — Distributed Execution Lease & Zombie Worker Fencing

## Status

R32 is frozen and closed as PROVEN.

Base commit for this branch:

    d3064f869feedd16e8c843efbb38b29e218d2b55

R32 final evidence remains immutable. Do not rerun or rewrite R32 as part of
this task.

R33 is a new architecture boundary.

## Why R33 exists

R32 proved that two real external AgentRuns can reason concurrently while
server-owned Journey reality advances from R1 to R2, and that stale R1 thought
cannot spend R2 authority.

That proof still lives inside one server process/runtime ownership domain.

The current AgentRun model binds a run to a RecoveryEpoch, but it has no durable
server-owned execution lease generation. The current autorun worker is also
process-global/in-memory.

That leaves a harder distributed-systems question unanswered:

> What happens if the worker process that owns an AgentRun dies while a real
> provider call is in flight, a second process takes over, and the old worker
> later returns as a zombie with a valid-looking model response?

R33 must make process identity irrelevant to authority.

## Revolution claim

CityNexus must maintain two independent server-owned generations:

1. **RecoveryEpoch** — which world/reality generation is current.
2. **ExecutionLease** — which worker/run generation currently owns the right to
   execute that mission lineage.

A model/tool action is spendable only when **both** generations are current.

Formally:

    LEGAL_SPEND =
        current_recovery_epoch(run.recovery_epoch_id)
        AND
        current_execution_lease(run.execution_lease_id,
                                run.execution_lease_generation)

Neither PID, thread name, hostname, process memory, HTTP connection nor model
response arrival order is authority.

## R33 target scenario

The end-state live strike must exercise this exact class of failure:

1. Worker A is a real separate OS process.
2. Server durably grants A execution lease generation L1.
3. A creates/binds a durable AgentRun and starts a real WB2api/Hermes provider
   call under current RecoveryEpoch R1.
4. The provider request is observably in flight.
5. Worker A is hard-killed before its provider response can be spent.
6. L1 expires or is explicitly reclaimed by a server-owned lease transition.
7. Worker B, a different OS process, atomically acquires generation L2 > L1.
8. B resumes/restarts the same mission lineage from durable server state.
9. B may independently reason and, if authority permits, execute at most one
   legal mutation.
10. The delayed result belonging to A/L1 is later delivered or replayed through
    the real runtime boundary.
11. Server rejects A/L1 with typed
    `AGENT_EXECUTION_LEASE_SUPERSEDED` before any model-selected tool can spend
    authority.
12. Zombie A cannot:
    - mutate Journey state;
    - create a current proposal/receipt;
    - consume an approval;
    - resume a continuation;
    - renew or steal L2;
    - mint another lease generation merely by checking staleness;
    - mint a RecoveryEpoch merely by checking lease staleness.
13. B/L2 remains the only spendable execution owner.
14. Across crash + takeover + zombie return, active-reality mutation cardinality
    is still zero-or-one.

If Journey reality also changes during takeover, both fences must operate
independently. Passing one fence never compensates for failing the other.

## Non-goals

Do not turn this into:

- another R32 replay;
- a process-local mutex;
- a Python `threading.Lock` solution;
- "PID is authority";
- "the newest response wins";
- an in-memory worker registry;
- a prompt that tells the model which tools to call;
- deterministic Agent fallback;
- human approval fabrication;
- retry-until-green orchestration.

The lease must be durable and server-owned.

## Preferred durable model

Exact schema names may change if the codebase gives a strong reason, but the
semantics below are mandatory.

Prefer a new persisted model such as:

    AgentExecutionLease

with fields equivalent to:

    id
    mission_id
    journey_id
    generation
    owner_worker_id
    status
    acquired_at
    heartbeat_at
    expires_at
    released_at
    superseded_by_lease_id
    recovery_epoch_id_at_acquire

Recommended statuses:

    ACTIVE
    EXPIRED
    SUPERSEDED
    RELEASED

Add explicit lease identity to AgentRun, preferably:

    execution_lease_id
    execution_lease_generation
    worker_id

A run without a durable lease must not become an authority-bearing distributed
run.

### Database invariants

The database, not process memory, must enforce or atomically serialize:

- monotonic generation per mission execution lineage;
- at most one ACTIVE current lease for that lineage;
- takeover generation strictly greater than prior generation;
- old lease cannot become ACTIVE again after supersession/release;
- stale heartbeat cannot renew a superseded generation;
- takeover records durable predecessor lineage.

Use a transaction/CAS/unique constraint pattern suitable for the current
database layer.

A process-local lock may reduce local contention but may never be the deciding
authority.

## Worker identity

Every worker process must have an explicit opaque `worker_id`.

It may include a random boot UUID and diagnostics such as PID, but PID itself is
never the authority token.

The durable lease id/generation is the authority-bearing execution identity.

Useful diagnostic fields:

    worker_id
    boot_id
    pid
    hostname

are allowed, but verifier logic must not infer authority from them.

## Lease acquisition

Create a narrow server module, e.g.

    backend/app/agent/execution_lease.py

with explicit operations similar to:

    acquire_execution_lease(...)
    renew_execution_lease(...)
    current_execution_lease(...)
    validate_execution_lease(...)
    release_execution_lease(...)
    take_over_expired_execution_lease(...)

Exact API may differ.

### First acquire

First acquisition creates L1 and returns a durable receipt.

### Heartbeat

Only the exact ACTIVE lease can renew itself.

Heartbeat must not create a new generation.

A heartbeat from L1 after L2 exists must return typed supersession.

### Expiry

Expiry is a server-time fact.

A lease past `expires_at` is not spendable even if no takeover has happened
yet.

Prefer validation semantics that treat time expiry as immediately non-spendable
and make the later takeover transition durable/auditable.

### Takeover

Takeover must be atomic.

Two replacement workers racing after L1 expiry may not both obtain current
execution authority.

Exactly one wins L2.

The loser receives a typed non-current result and may retry discovery, but may
not create L3 just because it lost the race.

## Typed fence

Introduce one canonical machine code:

    AGENT_EXECUTION_LEASE_SUPERSEDED

A stale/expired lease spend should expose facts equivalent to:

    code
    stale_execution_lease_id
    stale_execution_lease_generation
    current_execution_lease_id
    current_execution_lease_generation
    stale_worker_id
    current_worker_id
    reason

Do not collapse this into generic TOOL_ERROR.

The distinction matters:

> Provider/model execution may have succeeded while execution authority was
> revoked.

Persist the typed fence as an AgentRunStep / audit fact just as R32 persists
`RECOVERY_EPOCH_SUPERSEDED`.

## Where the fence must live

Do not validate only at worker startup.

Execution-lease freshness must be checked at every authority boundary where a
zombie could return after takeover.

At minimum:

1. immediately before each external model call;
2. immediately after each external model response and before interpreting/
   executing returned tool calls;
3. inside AgentToolGateway before any tool dispatch;
4. before approval/continuation resume spends authority;
5. before mutation commit.

R33 should prefer one shared validator rather than subtly different lease rules
at each call site.

### Two-dimensional fence

For an authority-bearing Gateway call, both checks must pass:

    validate_execution_lease_binding(...)
    validate_recovery_epoch_binding(...)

Do not open a new lease while validating stale work.

Do not open a new RecoveryEpoch while validating a stale lease.

Both stale checks must be causally inert.

## AgentRun semantics

A distributed run should carry its exact execution lease.

Recommended terminal status for a zombie-fenced run:

    SUPERSEDED

with failure/reason code:

    AGENT_EXECUTION_LEASE_SUPERSEDED

Do not retarget an existing AgentRun from L1 to L2.

Takeover should create a successor run or a clearly explicit durable handoff
whose lineage is machine-visible.

Preferred invariant:

> AgentRun identity is immutable; a different execution lease generation gets a
> different AgentRun identity.

That mirrors the R32 rule that an old AgentRun is never retargeted to a new
RecoveryEpoch.

## Mission lineage

The server must be able to reconstruct:

    Mission
      -> L1
      -> AgentRun A
      -> crash/expiry
      -> L2
      -> AgentRun B
      -> terminal result

If B continues work started by A, that continuation is from durable mission /
server state, not A's in-memory conversation buffer.

Do not make the model response itself the recovery source of truth.

## Approval / continuation interaction

R28 already established durable continuation semantics.

R33 must not regress them.

If A/L1 created a legitimate pending approval before crashing:

- the approval remains bound to its original durable authority facts;
- takeover must not duplicate the pending action;
- B/L2 may resume only through an explicit server-owned continuation path that
  validates both current execution lease and current RecoveryEpoch;
- old A/L1 can never consume the approval after L2 takeover;
- there must be exactly one continuation side effect.

This can be a deterministic R33 test even if the first live strike does not
exercise the approval branch.

## Autorun / Guardian

The current autorun worker uses process-global/thread-local coordination.

R33 must make a multi-process deployment safe.

At minimum, two independent processes calling worker/pulse logic against the
same database must not both own current execution authority for one mission
lineage.

Do not treat `_cycle_lock` or `_worker_lock` as the R33 solution.

They remain local implementation conveniences only.

## Migration / compatibility

Preserve existing R28-R32 behavior.

Do not silently make old historical AgentRun rows invalid for read APIs.

If existing rows lack lease identity, distinguish:

- legacy historical/read-only records;
- new R33 distributed authority-bearing runs.

Do not fabricate leases retroactively for old evidence.

Any migration/default strategy must be explicit and tested.

## Phase A — deterministic lease core

Before any multi-process live work, build a focused deterministic gate proving:

1. first acquire creates generation 1;
2. renewal preserves generation;
3. only current lease can renew;
4. expired lease is non-spendable;
5. takeover creates exactly generation 2;
6. L1 cannot reactivate;
7. simultaneous takeover race yields one winner;
8. stale validation does not create generation 3;
9. released lease is non-spendable;
10. one ACTIVE lease invariant survives transaction rollback/retry.

Prefer actual concurrent DB sessions for race tests.

## Phase B — Runtime and Gateway fence

Add deterministic tests proving:

- AgentRun persists lease id/generation before first provider call;
- pre-provider lease loss stops before external call;
- lease loss while provider is in flight discards the returned model response;
- no returned tool executes after lease supersession;
- Gateway rejects exact stale run/lease with typed code;
- recovery-current + lease-stale => reject;
- lease-current + recovery-stale => reject;
- both-current => normal path;
- stale lease validation creates neither a new lease nor new RecoveryEpoch.

## Phase C — exactly-once crash/takeover

Build deterministic/integration coverage for:

- A creates a proposal before crash, B takeover cannot accidentally duplicate
  equivalent future;
- if B commits mutation, A/L1 cannot commit after waking;
- if A had a pending approval, B takeover does not duplicate continuation;
- lease takeover cannot turn arrival order into authority;
- only current lease can create an authority-bearing proposal/receipt after
  takeover.

## Phase D — actual multi-process harness

This is mandatory before R33 may be called PROVEN.

Threads are not sufficient.

Use separate OS processes, preferably `subprocess` or `multiprocessing`
with independent SQLAlchemy sessions and independent runtime instances.

Recommended harness shape:

    backend/run_r33_live.py

### Provider barrier

Do not monkeypatch one in-process model method and call that "multi-process".

Prefer a small local HTTP barrier/proxy owned by the harness:

    Worker process
      -> local R33 barrier proxy
      -> real configured WB2api/Hermes endpoint

The proxy may:

- observe a real provider request;
- forward it to the configured real provider;
- record provider-returned response;
- hold the HTTP response before returning it to the worker;
- later release or replay that response under parent coordinator control.

The proxy controls timing only.

It must not:

- modify model content;
- inject tool calls;
- choose Agent strategy;
- fabricate authority.

If a simpler design proves the same process boundary honestly, document why.

## Phase E — zombie live strike

The live strike should prove this chronology:

### A / L1

1. fresh committed source receipt;
2. Worker A process starts with worker_id WA;
3. WA atomically acquires L1;
4. A AgentRun is durable and bound to L1 + current R1;
5. real WB2api provider request begins;
6. provider response is held outside Runtime.

### Crash

7. parent hard-kills Worker A process;
8. database still contains A/L1 durable envelope;
9. no in-process cleanup is relied upon to release authority;
10. L1 becomes expired/non-spendable by server time.

### B / L2 takeover

11. Worker B process starts with worker_id WB;
12. WB atomically takes over with L2 > L1;
13. exactly one L2 is ACTIVE;
14. B uses a new AgentRun identity;
15. B is bound to L2 and current RecoveryEpoch;
16. B independently invokes real WB2api/Hermes.

B remains strategy-neutral.

If current standing authority allows a legal mutation, B may execute it.

If a genuine human boundary remains, stop honestly.

### Zombie return

17. deliver/replay A's already-computed provider response through the stale L1
    execution path, or use a controlled zombie-worker continuation that proves
    the same spend attempt;
18. Runtime/Gateway records typed
    `AGENT_EXECUTION_LEASE_SUPERSEDED`;
19. A stale model response is discarded before any returned tool executes;
20. A performs zero current mutation.

### Final state

21. L1 terminal non-current;
22. L2 is current during B execution and later RELEASED/terminalized as
    appropriate;
23. no L3 exists merely because A checked staleness;
24. no extra RecoveryEpoch exists merely because A checked lease staleness;
25. at most one active-reality mutation occurred;
26. if B mutated, mutation lineage names B + L2 + current RecoveryEpoch +
    current authority receipt;
27. no post-crash human authority was fabricated.

## Optional harder combined strike

Only after the lease-only live strike works, and only if it can be added without
turning R33 into retry theater:

- A holds L1/R1;
- Worker A dies;
- material Shock B advances reality to R2;
- Worker B takes L2/R2;
- zombie A returns with L1/R1.

Then A fails both dimensions independently:

    stale execution lease
    stale recovery epoch

The server should preserve enough evidence to show which fence rejected the
spend first while also proving both facts were stale.

Do not require this combined case for the first R33 delivery if it would obscure
the core execution-lease proof.

## Machine verifier

Create:

    backend/scripts/r33_machine_verdict.py

Never reuse R32 overall logic by copy/paste without adapting the claim.

Expected required dimensions should include equivalents of:

- strike_source_state_traceable
- strike_freshness_attested
- multi_process_workers_proven
- execution_lease_server_owned
- one_active_lease_per_lineage
- lease_generation_monotonic
- worker_a_real_external_and_bound_l1
- worker_a_process_hard_killed
- l1_expired_or_superseded
- worker_b_takeover_l2
- worker_b_real_external_and_bound_l2
- zombie_a_typed_fenced
- zombie_response_discarded_before_tool
- zombie_no_mutation
- stale_lease_validation_causally_inert
- recovery_epoch_fence_preserved
- exactly_one_or_zero_legal_mutation
- no_duplicate_continuation_side_effect
- no_post_crash_human_authority_fabrication
- truth_boundary_honest
- verifier_source_traceable

If B mutates, additionally require:

- B/current-lease/current-epoch proposal lineage;
- current authority receipt sourced from B;
- B/current-lease owns the only legal mutation;
- B terminal state consistent.

Any observed stale-lease mutation is CONTRADICTED.

## Fresh evidence protocol

Carry forward the R32 lesson: stale evidence has no authority.

R33 live artifact must have its own protocol string, e.g.

    R33_DISTRIBUTED_LEASE_ZOMBIE_FENCING_V1

and must machine-attest:

- source head;
- fetched remote head;
- exact equality;
- clean tracked tree;
- unique strike id;
- strike start time;
- output did not preexist;
- critical source hashes;
- verifier identity.

Historical R32 artifacts must never be renamed into R33 evidence.

## CI

Create a narrow R33 workflow rather than broad unrelated CI.

It should include the existing R32 frozen gate plus focused R33 tests.

Do not delete R32 tests to make R33 green.

R32 remains the inherited safety floor.

## Delivery discipline

Do not spend most of the task writing reports.

Priority order:

1. durable lease semantics;
2. Gateway/Runtime fencing;
3. deterministic race tests;
4. multi-process harness;
5. one honest live strike;
6. machine verdict;
7. compact report.

Do not repeatedly rerun a failing live strike.

One live attempt is enough to expose the next real architecture problem.

If live evidence is NOT_PROVEN or CONTRADICTED, preserve the black box and stop
unless the cause is a narrowly proven harness defect.

## R33 success bar

R33 is not PROVEN because "the replacement worker worked".

It is PROVEN only if the system demonstrates the dangerous order:

> old worker had a real external computation,
> old process lost execution ownership,
> new worker took over,
> old result came back,
> and the old result was still powerless.

That is the point.

## Revolution principle

R32 established:

> Reality can change while Agents think.

R33 must establish:

> The machine performing the thinking can die and be replaced while the system
> still knows exactly who is allowed to act.

A process is disposable.

A model response is disposable.

A worker identity is diagnostic.

Only durable server-owned generation fences may confer execution authority.

The Revolution is complete for this layer only when a zombie worker can return
with a perfectly valid model answer and still be unable to change the future.
