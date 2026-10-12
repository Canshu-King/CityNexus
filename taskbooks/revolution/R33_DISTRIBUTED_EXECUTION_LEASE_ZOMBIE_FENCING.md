# Revolution R33 — Distributed Execution Lease + Zombie Worker Fencing

## Status

R32 is closed as **PROVEN** within its stated replay-backed WB2api/Hermes,
non-physical-travel truth boundary.

R33 begins from:

    d3064f869feedd16e8c843efbb38b29e218d2b55

on branch:

    gpt/revolution-r33-distributed-execution-fencing

Do not reopen R32 unless a concrete regression invalidates its proof.

## Why R33 exists

R32 proved that server-owned **RecoveryEpoch** generations prevent stale model
responses from spending authority after the world changes.

That is not enough for distributed execution.

Current product state still has this gap:

- `AgentRun` persists run identity and `recovery_epoch_id`;
- Runtime creates a RUNNING AgentRun and commits it before external model I/O;
- Gateway validates the bound AgentRun and RecoveryEpoch;
- there is **no durable worker owner / lease / fence generation** on Agent
  execution.

Therefore this unresolved race exists:

1. Worker A owns an AgentRun on current R2.
2. Worker A makes a real provider request or pauses before Gateway dispatch.
3. Worker A dies or becomes partitioned.
4. Worker B decides the work is dead and takes over while R2 is still current.
5. Worker B performs the legitimate recovery.
6. Worker A later resumes with a response that is still valid for current R2.

RecoveryEpoch cannot reject A here because the world did not change.

R33 must prove that **execution ownership itself is server-owned, durable and
fenced**.

The core invariant is:

> Current world generation is necessary but not sufficient authority.
> A worker must also hold the current execution lease generation.

## Absorb the good Qoder work, do not copy it blindly

The repository already contains a strong claim/lease pattern in:

    backend/tests/test_qoder_ord0340_claim_lease.py

and the matching plan-generation claim code in `backend/app/main.py`.

Useful proven ideas to reuse:

- a live lease blocks competing execution;
- an expired lease may be atomically taken over;
- takeover does not delete the durable receipt;
- a resurrected old holder cannot write over the winner;
- ownership is checked again at the final write, not only at claim time;
- a second SQLite connection is used to prove durability rather than trusting
  process memory.

R33 must lift those ideas to Agent execution.

Do **not** reuse the plan-generation `IdempotencyKey` row as the Agent lease.
Agent execution has different lineage, longer runtime, heartbeats, multiple
tool steps and authority-bearing mutations.

## Two independent generations

R33 must make these concepts explicit and independent:

### Reality generation

    RecoveryEpoch.generation

Answers:

> Which server-owned world was this reasoning based on?

### Execution generation

    AgentExecutionLease.generation

Answers:

> Which worker currently owns the right to act for this execution lineage?

A tool may spend authority only if both are current.

Expected binding:

    AgentRun
      -> exact RecoveryEpoch
      -> exact AgentExecutionLease generation

A stale value on either axis must fail before a tool handler can mutate state.

## Recommended durable model

Prefer a separate durable lease-generation table over mutating ownership fields
in-place on `AgentRun`.

Suggested shape (names may vary if the implementation has a stronger reason):

    AgentExecutionLease
      id
      journey_id
      mission_id
      recovery_epoch_id
      execution_key
      generation
      holder_token
      status
      acquired_at
      heartbeat_at
      lease_deadline
      released_at
      release_reason
      superseded_by_lease_id

Where:

- `execution_key` deterministically identifies one mission + one RecoveryEpoch
  execution lineage;
- generation starts at 1 and increases monotonically per execution_key;
- exactly one lease for an execution_key may be ACTIVE;
- old generations are never deleted or retargeted;
- takeover closes the old generation as FENCED/EXPIRED and creates generation
  N+1;
- every AgentRun belongs to one immutable lease id/generation.

Suggested AgentRun additions:

    execution_lease_id
    execution_lease_generation
    execution_holder_token

Do not let a new worker continue writing into the old worker's AgentRun.

On takeover:

- old AgentRun becomes FENCED (or another explicit terminal stale-execution
  state);
- new worker gets a **new AgentRun**;
- both runs may share mission + RecoveryEpoch lineage;
- their execution lease generations must differ.

This preserves exact worker/run causality instead of merging two processes into
one trace.

## Database invariants

Required database-level invariants:

1. one ACTIVE lease per execution_key;
2. unique (execution_key, generation);
3. generation increases on takeover;
4. an ACTIVE lease has a holder token and deadline;
5. terminal lease generations are immutable history;
6. an AgentRun cannot point to a lease for another mission/journey/epoch;
7. a fenced AgentRun cannot return to RUNNING;
8. takeover must be atomic under two independent DB connections.

Use a partial unique index for the ACTIVE lease if SQLite supports the shape
cleanly, analogous to RecoveryEpoch's one-OPEN invariant.

Do not rely on a process-local mutex as proof.

## Lease timing

Do not use a magic sleep-only ownership rule.

Production lease duration must come from an explicit server setting or a
documented derivation from existing provider/runtime budgets.

The lease must support heartbeat renewal because one Agent run can span
multiple model turns.

Minimum heartbeat boundaries:

- before external provider call;
- after provider return / before response is admitted to Runtime;
- before Gateway dispatch;
- after durable tool-step commit when continuing;
- before any authority-bearing mutation.

A worker whose lease renewal fails must terminalize/fence itself and must not
keep reasoning.

## Claim protocol

The first worker must atomically claim generation 1 before the first external
model call.

If an unexpired ACTIVE lease exists:

- competing worker must not execute;
- return/record a typed in-flight refusal with current holder/generation and
  retry-after information.

If the ACTIVE lease is expired:

- takeover must use a conditional database write;
- exactly one contender wins;
- old lease becomes FENCED/EXPIRED;
- new generation N+1 becomes ACTIVE;
- old AgentRun is durably fenced;
- a new AgentRun is created for the winner.

Two simultaneous reclaimers must not both win.

## Fence token semantics

Do not make lease ownership a one-time admission check.

The worker must carry exact lease identity into all execution boundaries.

At minimum the server must validate:

    bound AgentRun id
    bound RecoveryEpoch id
    bound execution lease id
    bound execution lease generation
    bound holder token
    lease status ACTIVE
    lease deadline not expired

before:

- accepting a provider response back into Runtime;
- executing any model-selected tool;
- especially any mutation-capable Gateway handler.

Use a typed error such as:

    EXECUTION_LEASE_FENCED

or a similarly explicit stable code.

Do not reuse `RECOVERY_EPOCH_SUPERSEDED` for lease loss. These are different
causes.

The durable stale result should identify:

- stale AgentRun;
- stale lease id/generation;
- current lease id/generation;
- RecoveryEpoch id;
- whether a model response was discarded before Gateway use.

## Critical zombie rule

A zombie worker may wake after takeover while its RecoveryEpoch is still
current.

That is the discriminating R33 case.

It must fail solely because its **execution lease generation** is stale.

Required result:

    world generation: still current
    execution generation: stale
    mutation authority: denied

This must be proven separately from the R32 world-supersession path.

## Worker takeover semantics

Do not attempt to resume hidden model chain-of-thought or in-memory provider
continuation state from a dead process.

A takeover worker starts fresh from durable server state:

- mission;
- RecoveryEpoch;
- current Journey;
- persisted prior AgentRun/steps as audit history if useful.

The replacement gets a new AgentRun and new lease generation.

The model may choose a different strategy than the dead worker.

That is acceptable.

Only server facts and current authority matter.

## Phase A — deterministic lease kernel

Before any live model strike, implement and prove with two independent database
connections:

### L1 live holder excludes contender

Generation 1 ACTIVE and unexpired.

A second claimant must not create an AgentRun or execute provider/tool work.

### L2 expired holder is reclaimable

Generation 1 expires.

One contender takes generation 2.

Old lease stays durable and fenced.

### L3 two reclaimers race

Two independent connections attempt takeover.

Exactly one generation-2 ACTIVE winner exists.

No generation 3 may appear from the race.

### L4 zombie cannot renew

Generation-1 holder attempts heartbeat after generation 2 exists.

It receives typed fencing and cannot extend the old deadline.

### L5 zombie cannot dispatch read tool

Even `inspect_journey` from the stale holder is rejected before handler
execution.

This proves the fence is an execution boundary, not only a mutation rule.

### L6 zombie cannot dispatch mutation

Old holder attempts `accept_replan` or another active-reality mutation while
RecoveryEpoch is still current.

Must receive `EXECUTION_LEASE_FENCED`.

No side effect.

### L7 winner may act

Generation-2 AgentRun can inspect and use Gateway normally under the same
RecoveryEpoch.

### L8 no ownership resurrection

After generation 2 completes/releases, generation 1 can never become ACTIVE
again.

Historical ownership is immutable.

## Phase B — Runtime integration

Refactor Runtime so worker ownership is not implicit in Python call stack.

Required lifecycle:

1. durable execution lineage resolved;
2. lease generation claimed;
3. new AgentRun created bound to lease + RecoveryEpoch;
4. run + lease committed before provider call;
5. provider response admission revalidates both reality and lease;
6. every Gateway dispatch revalidates both;
7. mutation completion releases lease terminally;
8. failure/partial/human-boundary paths release or retain lease according to an
   explicit state machine;
9. process death simply leaves an expiring ACTIVE lease; no special in-memory
   cleanup is required for correctness.

Do not let `finally:` cleanup be the only thing that makes ownership safe.

## Phase C — process-death integration proof

Use a real subprocess or otherwise genuinely independent process boundary
against the same SQLite DB.

Do not prove process death using two functions sharing one Python object.

Required sequence:

1. process A claims execution generation 1 and durably creates AgentRun A;
2. A reaches a controlled boundary after the lease is durable;
3. terminate A without graceful release;
4. verify through another connection that generation 1 remains ACTIVE until
   expiry;
5. after expiry, process B atomically takes generation 2;
6. B creates AgentRun B on the same mission + RecoveryEpoch;
7. B performs at least one real Gateway operation;
8. a resurrected/simulated zombie A using its original run + lease token is
   refused by exact execution-generation fencing;
9. winner facts remain unchanged.

The test must read durable state through another connection/process.

## Phase D — real WB2api zombie strike

Only after A-C are green, perform one live external-model strike.

The final Revolution scenario should keep the RecoveryEpoch constant so R32
cannot accidentally do the work for R33.

Suggested choreography:

1. configure standing authority before execution;
2. open current RecoveryEpoch R1;
3. Worker A claims execution lease generation 1 and starts a real WB2api call;
4. hold A's provider response outside Runtime;
5. **do not create a new RecoveryEpoch**;
6. let A's lease expire / fence generation 1;
7. Worker B takes generation 2 for the same mission + R1 and creates AgentRun B;
8. B starts a real WB2api call;
9. release B and let it act strategy-neutrally;
10. after B has established ownership, release zombie A's old provider response;
11. A must be rejected with `EXECUTION_LEASE_FENCED` before any returned tool
    executes;
12. if B mutates, at most one mutation may commit.

This is the core R33 proof:

> same current world, different execution generation.

Do not inject Shock B in the discriminating strike.

If the world changes, the result may exercise R32 rather than R33.

## Live authority discipline

Keep the R32 rules:

- no deterministic model fallback;
- no forced tool sequence;
- no post-start fabricated member response;
- no automatic human approval;
- no retargeted receipt;
- no prompt instruction to mutate.

B may choose not to mutate.

A legal NOT_PROVEN path is preferable to a scripted PROVEN demo.

If mutation occurs it must still satisfy current RecoveryEpoch and collective
authority invariants inherited from R32.

## Exactly-once after takeover

A zombie and winner may never both commit.

Verifier must count the complete active mutation surface:

- accept_replan
- activate_standby
- replace_activity
- reschedule_activity
- create_booking
- cancel_refundable_booking
- request_commitment_change
- apply_clarified_horizon_choice

At most one executed mutation total for the execution lineage.

## New machine verifier

Create:

    backend/scripts/r33_machine_verdict.py

Do not weaken R32 verifier to fit R33.

Required dimensions should include at least:

- source_state_traceable
- fresh_strike_attested
- one_active_lease_per_execution_key
- lease_generation_monotonic
- live_holder_excludes_contender
- expired_lease_takeover_exactly_once
- replacement_run_distinct_from_old_run
- replacement_same_recovery_epoch
- zombie_world_still_current
- zombie_execution_generation_stale
- zombie_provider_response_discarded
- zombie_gateway_authority_refused
- zombie_cannot_renew
- winner_gateway_authority_valid
- winner_only_mutation_authority
- exactly_one_or_zero_mutation
- old_lease_never_reactivated
- no_post_takeover_duplicate_side_effect
- inherited_r32_authority_integrity
- truth_boundary_honest

Empty evidence must remain NOT_PROVEN.

Any durable invariant violation must make overall CONTRADICTED.

## Evidence provenance

Reuse the R32 lesson.

Fresh R33 live evidence must carry:

- protocol version;
- unique strike id;
- start timestamp;
- local HEAD;
- fetched remote branch HEAD;
- clean tracked state;
- source hashes for every lease/runtime/gateway/model/schema/verifier file;
- exact lease ids/generations;
- exact AgentRun ids;
- exact RecoveryEpoch id;
- process ids or explicit worker ids where applicable.

An old artifact renamed as R33 is invalid evidence.

## Schema / compatibility

Do not silently repurpose:

- RecoveryEpoch generation as worker lease generation;
- IdempotencyKey claim_token as global Agent worker identity;
- AgentRun id as a renewable lease token.

These have different lifetimes and semantics.

Any migration must preserve existing R28-R32 history and existing AgentRun
reads.

## Regression gate

R33 must retain the complete R28-R32 focused suite.

Add a new narrow workflow or extend the current one only if naming remains
clear.

At minimum run:

- all R32 deterministic tests;
- new lease-kernel tests;
- Runtime fencing tests;
- Gateway fencing tests;
- multiprocess takeover tests;
- R33 verifier adversarial tests.

Do not spend most of the task repeatedly rerunning unrelated full frontend
suites.

## Stop conditions

### Deterministic blocker

If lease takeover cannot be made atomic across two SQLite connections without
breaking existing write semantics, stop and report the exact DB limitation.

Do not fake distributed safety with a process mutex.

### Live NOT_PROVEN

If the real WB2api strike fails to reach the discriminating same-epoch zombie
boundary, preserve the black box and stop.

### CONTRADICTED

If the zombie performs any tool after losing the lease, or both generations
commit side effects, stop immediately and preserve evidence.

Do not retry by changing the prompt.

## Revolution principle

R32 proved:

> old reality cannot spend new authority.

R33 must prove:

> old execution ownership cannot spend current authority.

A model response can be correct.

Its RecoveryEpoch can still be current.

Its proposal can even be semantically good.

If the worker that produced it lost the lease, none of that matters.

The server must be able to say:

> You are thinking about the right world, but you are no longer the worker
> allowed to act in it.

That is the next Revolution boundary.
