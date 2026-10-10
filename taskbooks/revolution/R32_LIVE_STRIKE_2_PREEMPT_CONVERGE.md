# R32 Live Strike 2 — Preempt + Converge

## Mission

Run **one** clean external live strike against the latest remote head of:

    gpt/revolution-r32-autonomous-recovery-mesh

Do not reset to `5ea964b7` or `0885b105`.

The first R32 strike is historical NOT_PROVEN evidence.  Do not rewrite or
reinterpret its checkpoint.  This second strike exists because the first one
found real architecture gaps and those gaps have now been hardened in product
code, harness, verifier, and CI.

## Revolution claim under test

The claim is no longer merely:

    an Agent can recover from a disruption.

The claim is:

    an external Agent may already be thinking under R1,
    reality may advance to R2 underneath it,
    the server preempts stale R1 work without retargeting it,
    an independent Agent B may reason under R2,
    and only current R2 authority may cause at most one mutation.

Model strategy remains free.

Server truth and authority do not.

## What GPT has already changed

Do not spend the run re-reviewing these unless the live strike falsifies them.

1. Runtime preemption

   - Before every external model call, Runtime checks the exact AgentRun
     RecoveryEpoch.
   - After every external response, Runtime checks again **before executing any
     returned tool call**.
   - If reality advanced, the run receives a durable
     `recovery_epoch_guard / SUPERSEDED / RECOVERY_EPOCH_SUPERSEDED` step.
   - The stale response is discarded.  The run is never silently retargeted.

2. Real external-response barrier

   - The R32 harness starts the real WB2api call first.
   - It holds the model response at the Runtime boundary.
   - Shock B may be injected only after Agent A's actual provider invocation is
     recorded.
   - A and B must each have one pre-release provider invocation.
   - The harness records provider call start/finish and response release facts.

3. Source-state receipt

   Before the strike, the harness records:

   - git head;
   - tracked dirty state;
   - SHA-256 for the critical R32 source files.

   A dirty tracked tree cannot PROVE the strike.

4. Epoch-pure collective authority surface

   For an epoch-bound recovery proposal, final collective authority only sees:

       current OPEN RecoveryEpoch
       + same trigger_event_id
       + PRESENTED non-alias proposal siblings

   It must not include:

   - legacy NULL-epoch setup proposals;
   - R1 siblings;
   - R2 proposals for another independent trigger merely because they share a
     parent plan.

5. Exact authority lineage

   An algorithmic UNANIMOUS_DOMINANCE receipt now carries the exact
   `source_agent_run_id` inherited from the proposal that discovered the
   future.

   A successful mutation audit records:

   - receipt id/mode;
   - R2;
   - decision epoch;
   - material world epoch;
   - candidate surface fingerprint;
   - candidate surface scope;
   - candidate surface recovery epoch;
   - candidate surface trigger;
   - authority provenance.

6. Non-vacuous verifier

   Missing stale approvals, continuations, R1 proposals or R1 receipts remain
   NOT_PROVEN coverage.  An empty set is never positive proof.

   The v3 verifier distinguishes:

   - required dimensions for the causal path actually exercised;
   - coverage dimensions not exercised in that path.

   Any CONTRADICTED dimension still contradicts the overall strike.

## Pre-strike fixture facts

`run_r32_live.py` now configures these through normal HTTP product APIs before
Shock A exists:

- both Journey members publish the same explicit standing `garden=true`
  preference;
- the owner sets a finite AUTONOMOUS delegation envelope with
  `auto_accept_replan=true`, bounded cost/loss/schedule drift, protected
  C3/C4 commitments, no automatic commitment management, no degraded-provider
  authority, and no automatic critical-event authority.

These are standing facts, not post-shock approvals.

Do not change them after seeing the model's behavior.

Do not submit collective clarification responses.

Do not approve a pending action.

If the server still requires a human decision, leave it waiting and report
NOT_PROVEN for autonomous convergence.

## Mandatory clean-start gate

Before calling the model:

    git fetch
    git checkout gpt/revolution-r32-autonomous-recovery-mesh
    git pull --ff-only
    git status --porcelain --untracked-files=no

Tracked status must be empty.

Do not edit code and then run the strike from an uncommitted tree.

Do not manually construct evidence rows.

## Execute the live strike

Use the configured WB2api/Hermes external runtime that is already available in
the local environment.

Run:

    cd backend
    uv run python run_r32_live.py --output output/r32-live-strike-v2.json

The harness itself owns the timing.

Do not add sleeps keyed to model tool names.

Do not wait for a particular model tool call before Shock B.

Do not prescribe a tool sequence in the prompt.

Do not replace an external provider failure with deterministic Agent output.

### Required causal chronology

The machine evidence must show:

1. Shock A creates R1.
2. Agent A is durable RUNNING and bound R1.
3. A's real external provider call has been invoked.
4. Shock B materially changes recovery reality.
5. R1 becomes SUPERSEDED and R2 becomes OPEN.
6. Agent B is durable RUNNING and bound R2.
7. B's real external provider call has been invoked.
8. Responses are released.
9. A terminates with a live typed
   `RECOVERY_EPOCH_SUPERSEDED` guard step.
10. No stale A tool response mutates R2.
11. B independently chooses its strategy from current product state.

## Desired convergence path

The fixture is intentionally aligned so the server has an opportunity to prove
algorithmic collective authority without fake human input.

If B discovers one currently dominant legal future and chooses to execute it,
a successful path should produce:

    Agent B / R2
      -> R2 proposal
      -> current epoch+trigger authority surface
      -> UNANIMOUS_DOMINANCE
      -> R2 authority receipt
      -> receipt.source_agent_run_id == Agent B
      -> standing delegation policy ALLOW_AUTO
      -> exactly one mutation
      -> accepted plan becomes active

Do not force this path.

If B instead legitimately concludes NO_ACTION/UNRESOLVED or the server
requires humans, preserve that result.

"Mutation happened" is not itself success.

"Mutation did not happen" is not itself failure.

The causal authority chain is the test.

## Focused deterministic regression

After the live strike, run the current R32 narrow regression **once** on the
same committed head, using the test set in:

    .github/workflows/r32-narrow.yml

Capture an honest receipt such as:

    output/r32-focused-regression-v2.json

with:

- exact command or workflow-equivalent description;
- exit_code;
- passed;
- failed;
- raw output path.

Do not invent the count.  Use the actual pytest result.

## Machine verdict

Run the v3 verifier against the new checkpoint and the actual regression
receipt:

    uv run python scripts/r32_machine_verdict.py \
      output/r32-live-strike-v2.json \
      --regression output/r32-focused-regression-v2.json \
      --output output/R32_MACHINE_VERDICT_V2.json

Do not use the historical v1 checkpoint as input to the v3 verifier and then
claim it was a new strike.

## Interpretation

### R32 may be called PROVEN for this causal path only if

Every v3 `required_dimensions` entry is PROVEN and there are zero
CONTRADICTED dimensions.

If a mutation occurred, required proof automatically expands to include:

- current_surface_epoch_pure;
- arrival_order_not_authority;
- authority_provenance_mode_accurate.

Optional coverage such as stale approval continuation can remain explicitly
NOT_PROVEN without being relabelled as success.

### R32 must remain NOT_PROVEN if, for example

- A does not terminalize from the live run;
- source state is not traceable/clean;
- either real provider invocation was not made before release;
- B never obtains current authority and the current path does not otherwise
  satisfy the required dimensions;
- current candidate surface cannot be tied to R2 and the exact trigger;
- focused regression is not green.

### R32 is CONTRADICTED if, for example

- A/R1 executes a mutation after R2 exists;
- an R1 approval is consumed after R2;
- a current receipt borrows A's stale run lineage;
- more than one mutation commits;
- a mutation uses a stale/wrong-epoch authority receipt;
- harness fabricates post-shock human authority while claiming autonomous
  convergence.

## Evidence to commit

Commit the new evidence separately from product hardening:

- `backend/output/r32-live-strike-v2.json`
- `backend/output/R32_MACHINE_VERDICT_V2.json`
- `backend/output/r32-focused-regression-v2.json`
- focused raw pytest output if useful
- an updated R32 result report section describing the second strike

Do not overwrite the first strike artifacts.

## Stop condition

If the v2 strike is NOT_PROVEN, do not immediately start a third ceremonial
rerun.

Read the exact NOT_PROVEN dimensions, identify one product/harness cause, and
report it.

If the next fix would prescribe the Agent's strategy merely to make the
verifier green, stop instead.

## Revolution principle

Parallel reasoning is allowed.

Stale authority is not.

A model may be wrong, slow, creative, or unfinished.

The server must still know which reality is current, which proposal belongs to
which run, which social decision is authoritative, and which single mutation is
legal.

Do not optimize for a pretty demo.

Prove that CityNexus remains coherent while the world changes underneath its
Agents.
