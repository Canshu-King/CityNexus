# R32 Live Strike 2C-FRESH — Provenance Recovery + Exact-Run Causality

## Why this is a replacement, not 2D

The file previously committed as:

`backend/output/r32-live-strike-v2c.json`

is not a fresh 2C live strike.

The repository audit proves:

- it has the same Git blob SHA as
  `backend/output/r32-live-strike-v2b.json`;
- it is byte-for-byte identical to the historical 2B checkpoint;
- its embedded timestamp predates the 2C authorization taskbook;
- its embedded source head is the old 2B head;
- it lacks the exact-run provider binding fields and nine-path source receipt
  required by 2C.

Read:

`backend/output/R32_2C_PROVENANCE_AUDIT.json`

before doing anything else.

Therefore the original one-live-attempt 2C budget was not consumed. Exactly
one **2C-FRESH replacement** live attempt is authorized.

This is not 2D and is not permission for open-ended retrying.

## Revolution boundary

Do not optimize for a green label.

The experiment must prove that concurrent external thought remains subordinate
to durable server reality:

- every provider call belongs to one exact AgentRun;
- every AgentRun belongs to one exact RecoveryEpoch;
- a response computed under dead reality cannot spend current authority;
- stale validation cannot manufacture new reality;
- only current, server-owned authority can produce the one legal mutation.

Transport thread names are not identity.

Filename names are not evidence freshness.

A copied JSON is not a strike.

## Read first

Read all of:

- `REVOLUTION_R32_AUTONOMOUS_RECOVERY_MESH_RESULT.md`
- `backend/output/R32_2C_PROVENANCE_AUDIT.json`
- `taskbooks/revolution/R32_LIVE_STRIKE_2C_EXACT_RUN_CAUSALITY.md`
- this file

Do not edit or delete Strike 1, Strike 2, Strike 2B, or the invalid claimed
v2c files. They are historical audit material now.

## Fresh-source gate

Before the live command:

    git fetch origin
    git checkout gpt/revolution-r32-autonomous-recovery-mesh
    git pull --ff-only

Then verify:

    git rev-parse HEAD
    git rev-parse origin/gpt/revolution-r32-autonomous-recovery-mesh
    git status --porcelain --untracked-files=no

The two SHAs must be identical.

Tracked status must be empty.

Do not run the strike from a second stale worktree.

Do not run from detached HEAD.

Do not edit code between this equality check and the live command.

The harness now repeats these checks itself. It fetches the remote branch and
refuses live execution if local HEAD differs from the fetched remote HEAD.

A freshness-gate refusal occurs before the live strike begins. Correct the
checkout; do not bypass the gate.

## Fresh output identity

Use a new path that does not exist:

    backend/output/r32-live-strike-v2c-fresh.json

Do not delete or overwrite:

    backend/output/r32-live-strike-v2c.json

The harness refuses a pre-existing output path.

A valid fresh checkpoint must contain all of:

    strike_protocol == "R32_2C_FRESH_EXACT_RUN_CAUSALITY_V1"
    strike_id == source_receipt.strike_id
    strike_started_at == source_receipt.strike_started_at
    source_receipt.authorization_taskbook_commit
        == "03357b7c8f8a9a671c59113be71d6093fab04742"
    source_receipt.head_matches_remote == true
    source_receipt.git_head == source_receipt.remote_branch_head
    source_receipt.output_preexisted == false
    source_receipt.tracked_dirty_before_strike == false

The source receipt must contain hashes for all nine critical paths:

- `backend/run_r32_live.py`
- `backend/app/agent/runtime.py`
- `backend/app/recovery_epoch.py`
- `backend/app/agent/gateway.py`
- `backend/app/agent/signal_pipeline.py`
- `backend/app/agent/delegation_policy.py`
- `backend/app/collective_authority.py`
- `backend/app/main.py`
- `backend/scripts/r32_machine_verdict.py`

If any freshness field is absent, this is not valid 2C-FRESH evidence.

## Agent strategy remains unchanged

Do not alter the command in `run_r32_live.py`.

Do not prescribe a tool order.

Do not force:

- inspection sequence;
- request_replan;
- collective decision;
- accept_replan;
- mutation;
- no-action;
- or any other strategy.

Do not introduce deterministic fallback.

Do not fabricate authority.

Do not change member preferences or delegation policy after Shock A.

## Runtime preflight

The live process must prove before Agent execution:

- runtime type `HermesJourneyAgent`;
- provider key `hermes`;
- WB2api URL configured;
- WB2api key configured;
- semantic AI key absent;
- native Hermes not ready.

Any failure here must stop before the causal strike.

## Execute exactly one fresh live attempt

From `backend/`:

    uv run python run_r32_live.py \
      --output output/r32-live-strike-v2c-fresh.json

Once this command passes the fresh-source gate and begins product setup/live
execution, that is the one 2C-FRESH live attempt.

Do not rerun it automatically if the resulting artifact is NOT_PROVEN or
CONTRADICTED.

## Exact provider identity

Agent A's first held provider receipt must identify:

    agent_run_id == agent_a_run_at_barrier.id
    recovery_epoch_id == r1.id
    server_run_resolution == "EXACT_ONE_CURRENT_RUN"
    causal_slot == "A"
    provider_call_invoked == true

Agent B must identify:

    agent_run_id == agent_b_run_at_barrier.id
    recovery_epoch_id == r2.id
    server_run_resolution == "EXACT_ONE_CURRENT_RUN"
    causal_slot == "B"
    provider_call_invoked == true

`thread` is diagnostic only.

`AnyIO worker thread` is acceptable.

If the exact durable IDs are absent, do not reinterpret a thread label as
identity.

## Required concurrency chronology

The harness controls only lifecycle timing:

1. standing authority configured before Shock A;
2. Shock A opens R1;
3. A becomes durable RUNNING on R1;
4. real A provider request begins;
5. A response is held outside Runtime;
6. Shock B materially changes server reality;
7. R1 becomes SUPERSEDED and R2 becomes current;
8. B becomes durable RUNNING on R2;
9. real B provider request begins;
10. B response is held;
11. exact A/R1 and B/R2 provider receipts are present;
12. both responses are released.

No model tool name is part of the barrier contract.

## Stale A must die before tool execution

A's first response was born under R1.

After R2 exists, Runtime must reject that response before executing any
model-selected tool.

Required live evidence:

- A gets a durable `recovery_epoch_guard` step;
- decision/code is `RECOVERY_EPOCH_SUPERSEDED`;
- `model_response_discarded == true`;
- A terminates `SUPERSEDED`;
- no tool contained in the stale response executes after the guard;
- A executes no mutation.

Do not depend on what tool names A happened to return.

## Stale validation is causally inert

If B commits R2 before A reaches the stale guard:

- A/R1 still receives typed supersession;
- A's stale check must not create R3;
- no new RecoveryEpoch may exist unless separate material reality or genuinely
  fresh authorized work justifies it.

A stale run is allowed to discover that it is stale.

It is not allowed to create the next world by performing that discovery.

## B remains autonomous

B chooses its own legal strategy.

If B reaches a genuine human-authority boundary, leave it there.

Do not inject:

- member responses;
- approvals;
- step-up receipts;
- selected proposal IDs;
- or policy changes.

A legal no-mutation outcome may remain NOT_PROVEN.

## If B mutates

A successful autonomous mutation must prove:

    B exact AgentRun
      -> exact R2
      -> B-sourced R2 proposal
      -> same-R2 same-trigger candidate authority surface
      -> UNANIMOUS_DOMINANCE
      -> R2 authority receipt
      -> receipt.source_agent_run_id == B.id
      -> standing delegation permits execution
      -> exactly one executed mutation
      -> active plan == accepted proposal plan
      -> R2 status == COMMITTED
      -> R2 close_reason == REPLAN_ACCEPTED
      -> B status == COMPLETED
      -> B completion_contract.kind == MUTATION_EXECUTED

After R2 is COMMITTED from B's mutation:

- B must not request another model turn only for prose;
- B must not self-supersede because it changed reality legally.

Mutation with R2 still OPEN is a contradiction.

B self-supersession caused only by its own legal R2 commit is a product
contradiction.

## Exactly once

A may mutate zero times.

B may mutate zero or one time.

The strike may commit at most one active-reality mutation total.

More than one is CONTRADICTED.

## Regression

After the single fresh live attempt, run the exact test list from
`.github/workflows/r32-narrow.yml` on the same source head.

Write new files:

    backend/output/r32-focused-regression-v2c-fresh.json
    backend/output/r32-focused-regression-v2c-fresh.txt

Record the actual count from that exact run.

Do not copy the previous `152 passed` receipt.

## Machine verdict

Run:

    uv run python scripts/r32_machine_verdict.py \
      output/r32-live-strike-v2c-fresh.json \
      --regression output/r32-focused-regression-v2c-fresh.json \
      --output output/R32_MACHINE_VERDICT_V2C_FRESH.json

The verifier is v4 and freshness is a required dimension.

A valid new artifact must have:

    strike_freshness_attested == PROVEN
    strike_source_state_traceable == PROVEN
    verifier_source_traceable == PROVEN

before any later product claim can be called PROVEN.

## Evidence delivery

Commit only new fresh evidence plus a result-report addendum:

- `backend/output/r32-live-strike-v2c-fresh.json`
- `backend/output/r32-focused-regression-v2c-fresh.json`
- `backend/output/r32-focused-regression-v2c-fresh.txt`
- `backend/output/R32_MACHINE_VERDICT_V2C_FRESH.json`
- new `Strike 2C-FRESH` section in
  `REVOLUTION_R32_AUTONOMOUS_RECOVERY_MESH_RESULT.md`

Do not overwrite or rename old evidence.

## Stop condition

After the one valid fresh live execution:

If PROVEN:
- commit evidence;
- report the exact required dimensions;
- do not inflate truth beyond provider-replay / non-physical-travel scope.

If NOT_PROVEN:
- commit native black box;
- state the first unexercised causal boundary;
- stop.

If CONTRADICTED:
- commit native black box;
- state the first durable invariant violation;
- stop.

Do not launch 2D automatically.

Do not modify the prompt and rerun.

## Revolution principle

The Revolution is not a sequence of filenames that eventually says PROVEN.

It is the ability to tell, with durable server evidence, exactly:

- what source code ran;
- when this attempt began;
- which external call belonged to which AgentRun;
- which AgentRun belonged to which reality generation;
- whether the response remained spendable;
- where authority came from;
- whether mutation happened exactly once;
- and why stale work could not alter the future.

Evidence provenance is part of the architecture.

A copied old black box is history, not a new experiment.
