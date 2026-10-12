# R32 Live Strike 2B — Isolated Black-Box Retry

## Why this retry is allowed

Strike 2 is an honest `NOT_PROVEN` and remains immutable evidence.

It stopped before Shock B at:

    A_EXTERNAL_RESPONSE_BOUNDARY

A post-strike code review found a concrete harness/environment ambiguity:

- `/agent/commands` performs semantic command interpretation before the
  configured Journey Agent runtime;
- `_deepseek_client()` activates whenever an ambient
  `CITYNEXUS_AI_API_KEY` or `DEEPSEEK_API_KEY` exists;
- the old R32 configuration set the WB2api/Hermes variables but did not clear
  those ambient semantic-AI credentials;
- therefore a local shell with an unrelated AI key could execute or block on a
  different external provider before `HermesJourneyAgent._complete()` was
  ever reached.

Because `gated_complete()` records `provider_call_invoked=True` before the
actual WB2api network request, the Strike 2 symptom is more consistent with
"the Hermes Agent boundary was never reached" than with "WB2api merely replied
slowly".

This is a harness-isolation fix, not a model-strategy change.

## Hardening already on the branch

Before this retry, GPT added and CI proved:

1. R32 clears ambient `CITYNEXUS_AI_API_KEY` and `DEEPSEEK_API_KEY`.
2. R32 disables native-Hermes routing for this experiment.
3. A pre-strike runtime receipt must prove:
   - `HermesJourneyAgent` selected;
   - WB2api URL/key configured;
   - semantic AI key absent;
   - native Hermes not ready.
4. Abort paths now release the barrier, restore the monkeypatch and emit the
   actual partial durable state:
   - setup;
   - authority setup;
   - R1/R2 reached so far;
   - AgentRuns/steps;
   - thread state;
   - barrier/provider-call receipts;
   - responses/exceptions;
   - current DB snapshot.
5. The verifier identifies its own exact SHA-256/git head.
6. A generic failure marker may not erase a contradiction already supported by
   durable evidence.
7. Per-Agent provider invocation and the full A+B concurrent barrier are
   separate proof dimensions.

The deterministic R32 workflow is green at hardening baseline
`d5a0df422b23c22665eb28884fbb2be6f78ccf4a`.
A later documentation-only commit may be the branch head; always use the latest
remote branch.

## Do not modify strategy

Do **not** change the Agent command.

Do **not** add a required tool order.

Do **not** add a wait for a particular tool name.

Do **not** force `request_replan`, `accept_replan`, collective mediation or
any other model action.

Do **not** enable deterministic Agent fallback.

Do **not** change the standing preference or autonomy envelope after seeing the
result.

The only new variable versus Strike 2 is experimental isolation/observability.

## Clean start

    git fetch
    git checkout gpt/revolution-r32-autonomous-recovery-mesh
    git pull --ff-only
    git status --porcelain --untracked-files=no

Tracked status must be empty.

Read:

- `REVOLUTION_R32_AUTONOMOUS_RECOVERY_MESH_RESULT.md`
- `taskbooks/revolution/R32_LIVE_STRIKE_2_PREEMPT_CONVERGE.md`
- this file

Do not overwrite either historical live artifact:

- `backend/output/r32-live-strike-final.json`
- `backend/output/r32-live-strike-v2.json`

## Run one isolated live attempt

From `backend/`:

    uv run python run_r32_live.py --output output/r32-live-strike-v2b.json

Important exit semantics:

- exit 0 = harness reached its normal terminal checkpoint;
- exit 2 = harness produced an automatic `NOT_PROVEN` black-box checkpoint.

If exit 2 occurs, **do not hand-edit the JSON** and do not synthesize a smaller
failure envelope.  The committed file must be the exact harness output.

No second 2B attempt in the same task.

## Causal chronology to inspect

The desired experiment remains strategy-neutral:

1. clean committed source;
2. runtime preflight selects WB2api/Hermes and excludes ambient semantic AI;
3. Shock A opens R1;
4. Agent A is durable and R1-bound;
5. A's real WB2api call is invoked;
6. Shock B materially changes reality and opens R2;
7. R1 becomes SUPERSEDED;
8. Agent B is durable and R2-bound;
9. B's real WB2api call is invoked;
10. only then are held responses released;
11. A's stale response is rejected by server freshness before Gateway mutation;
12. B freely chooses its current strategy;
13. any mutation must derive solely from current R2 authority.

If the harness stops earlier, use the partial black-box state to name the exact
boundary.  Do not infer later dimensions.

## Authority rules remain unchanged

The fixture's two members already publish aligned standing preferences before
Shock A.

The owner already grants a finite standing AUTONOMOUS envelope before Shock A.

After Shock A:

- no collective clarification response from the harness;
- no user approval from the harness;
- no step-up;
- no retargeted old approval;
- no copied receipt.

If the server creates a PENDING approval, leave it pending.  That is
`NOT_PROVEN` autonomous convergence, not a reason to impersonate a person.

If a mutation occurs, the evidence must prove:

    Agent B
      -> R2
      -> B-sourced R2 proposal
      -> current RecoveryEpoch + same-trigger authority surface
      -> UNANIMOUS_DOMINANCE
      -> R2 authority receipt
      -> receipt.source_agent_run_id == Agent B
      -> standing delegation ALLOW_AUTO
      -> exactly one committed mutation

A mutation without that chain is not success.

## Regression

Do not spend most of the run re-auditing deterministic code.

After the one live attempt, run the focused suite once using the exact list in
`.github/workflows/r32-narrow.yml`.

Write the actual receipt to:

    backend/output/r32-focused-regression-v2b.json

and raw output to:

    backend/output/r32-focused-regression-v2b.txt

Record actual passed/failed counts.  Do not copy `142 passed` unless that is
what this exact head actually produces.

## Machine verdict

Run the current committed verifier:

    uv run python scripts/r32_machine_verdict.py \
      output/r32-live-strike-v2b.json \
      --regression output/r32-focused-regression-v2b.json \
      --output output/R32_MACHINE_VERDICT_V2B.json

Before accepting the verdict, verify:

- `source_receipt.tracked_dirty_before_strike == false`;
- `runtime_preflight.selected_openai_compatible_hermes == true`;
- `runtime_preflight.semantic_ai_api_key_configured == false`;
- `runtime_preflight.native_hermes_ready == false`;
- `evaluator_receipt.tracked_dirty == false`;
- evaluator SHA/head are present.

The strike source head and evaluator head may differ only if the evaluator was
legitimately hardened after the strike.  If so, report both explicitly.

## Verdict discipline

### PROVEN

Only if every `required_dimensions` item is PROVEN and no dimension is
CONTRADICTED.

### NOT_PROVEN

Use when a causal boundary was not exercised or the current Agent legitimately
stopped for authority/human input.

### CONTRADICTED

Use when durable evidence shows the claimed invariant was violated, including
stale authority, wrong run lineage, multiple mutations or fabricated post-shock
human authority.

A `failure` field never launders an already observed contradiction.

## Evidence commit

If the run produces files, commit:

- `backend/output/r32-live-strike-v2b.json`
- `backend/output/r32-focused-regression-v2b.json`
- `backend/output/r32-focused-regression-v2b.txt`
- `backend/output/R32_MACHINE_VERDICT_V2B.json`
- one new Strike 2B section in the R32 result report

Do not rewrite Strike 1 or Strike 2 evidence.

## Stop condition

This task contains exactly one live retry.

If 2B is NOT_PROVEN, stop after the evidence commit and report the exact first
failed causal boundary plus the black-box facts that distinguish the likely
cause.

Do not perform a 2C retry automatically.

Do not modify the prompt merely to get further through the verifier.

## Revolution principle

Revolution is not "more retries".

It is replacing hidden orchestration assumptions with explicit server-owned
causality.

An external model is allowed to be slow, surprising or wrong.

The system must still prove:

- which external runtime actually ran;
- which reality generation each Agent belongs to;
- whether a provider call really started;
- whether a response became stale before use;
- which proposal generated authority;
- and why at most one current mutation was legal.

A failed experiment with a complete black box is more valuable than a green
demo with an invisible precondition.
