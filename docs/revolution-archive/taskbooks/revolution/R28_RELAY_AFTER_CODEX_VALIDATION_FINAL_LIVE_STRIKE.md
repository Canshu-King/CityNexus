# Revolution Relay — R28 After-Codex Validation: FINAL LIVE STRIKE

## Baton

**Codex: local validation + one bounded real external-Agent strike. No new audit loop.**

Binding branch: `gpt/revolution-r28-implementation`

GPT relay HEAD at handoff: `fd97783d0813377da4551cd2651854d6cff8a10c`

Prior Codex-visible push before this relay: `497b8c23a6619a87eb9dcc0d871724ec4c24c27d` (`backend/uv.lock` PyYAML dev-lock synchronization only).

The full closure contract remains:

- `taskbooks/revolution/R28_RELAY_FINAL_LIVE_CLOSURE_CODEX.md`
- `taskbooks/revolution/REVOLUTION_R28_AUTHENTICATED_COLLECTIVE_CONTINUITY_TASKBOOK.md`

Do not create Checkpoint D/E or R28.1.

## What GPT changed after your validation push

A live-Agent seam remained even though focused tests could be green.

The server-created collective child mission stores the authenticated human result in:

`resolved_intent.collective_decision.selected_proposal_id`

But the runtime's acceptance-completion guard previously recognized only explicit acceptance wording in `mission.user_text`. The actual collective child user text is intentionally generic:

> Resume the shared Journey using the server-resolved collective proposal and normal authority boundaries.

A real external model could therefore inspect the child mission, acknowledge the already-resolved choice in prose, and stop without calling `accept_replan`. That would recreate the R27 seam in a new form: humans decide correctly, but the Agent does not carry its own governed action to the approval boundary.

GPT fixed this directly:

1. `backend/app/agent/runtime.py`
   - extracts the server-owned collective `selected_proposal_id`;
   - treats that resolved collective choice as an acceptance-required mission when autonomy is executable;
   - tells the model not to reopen the social choice;
   - if the model tries to finish with prose, gives one bounded nudge to call `accept_replan` for exactly the server-selected proposal;
   - preserves `PLAN_ONLY` as non-mutating.

2. `backend/tests/test_r28_durable_approval_continuation.py`
   - pins the resolved-collective acceptance intent;
   - pins `PLAN_ONLY` as false.

Commits:

- `5bd6094871c70f323d6ade2013c60d594bfa16ea` — runtime fix
- `fd97783d0813377da4551cd2651854d6cff8a10c` — focused regression

## Phase A — validate only the relay delta

Do not rerun the whole historical harness first.

```bash
git fetch origin
git checkout gpt/revolution-r28-implementation
git reset --hard origin/gpt/revolution-r28-implementation
git rev-parse HEAD
git status --short

cd backend
python -m compileall -q app
python -m pytest -q tests/test_r28_durable_approval_continuation.py
```

If this fails, fix the real defect and push it. Do not weaken the selected-proposal or PLAN_ONLY boundary.

If green, continue immediately.

## Phase B — execute the existing FINAL LIVE CLOSURE

Continue from **Phase 2** of:

`taskbooks/revolution/R28_RELAY_FINAL_LIVE_CLOSURE_CODEX.md`

Do one fresh disposable R28 closure on the current HEAD.

Non-negotiable causal chain:

```text
real configured external Agent
  -> discovers collective trade-off
  -> request_collective_decision
  -> WAITING_FOR_MEMBERS
  -> signed OWNER response
  -> signed ADMIN response
  -> server RESOLVED child mission
  -> real external Agent resumes child
  -> server-selected proposal carried into accept_replan
  -> REQUIRE_CONFIRMATION / REQUIRE_STEP_UP
  -> same AgentRun WAITING_FOR_APPROVAL
  -> signed authorized human approval
  -> deterministic server continuation
  -> same AgentRun COMPLETED
  -> selected proposal ACCEPTED
  -> active PlanVersion changed
```

No operator-built second `accept_replan` call. No `citynexus-local-agent` replay. No deterministic prose substitute for the external Agent turn.

The post-approval continuation must not spend another model turn.

## Phase C — truth boundary

Do not claim physical travel.

Either:

- perform one safe ordinary execution transition and prove `SIMULATED_STATE_TRANSITION`; or
- perform no execution transition and explicitly state physical execution is NOT PROVEN.

Do not try to promote ordinary `FOREGROUND_WEB` coordinates to device-verified presence.

## Phase D — machine verdict and delivery

Run:

```bash
cd backend
python scripts/r28_machine_verdict.py \
  --run-id <FINAL_AGENT_RUN_ID> \
  --output R28_MACHINE_VERDICT.json
```

Required for R28 closure:

```text
summary.overall = PROVEN
exit code = 0
```

Then commit and push the non-secret final artifacts required by the original taskbook, especially:

- `REVOLUTION_R28_AUTHENTICATED_COLLECTIVE_CONTINUITY_RESULT.md`
- generated `R28_MACHINE_VERDICT.json`
- concise focused test output / replay instructions where appropriate

If those files already exist only locally from your previous run, verify they correspond to the **current causal run and current branch HEAD** before committing. Never retrofit an old verdict onto a new run.

Do not commit bearer tokens, auth secrets, WB2api keys, browser storage state, or secret environment dumps.

## Stop rule

If the machine verdict is PROVEN, **stop R28** and report:

- final HEAD;
- focused test result;
- real Agent run id;
- pending action id;
- approval id;
- accepted proposal id;
- verdict summary;
- result/verdict paths.

If it is not PROVEN, stop on the single exact causal blocker. Do not open another broad review pass.

## Revolution intent

R28 is not about proving that CityNexus can print a receipt.

It is about making the product genuinely capable of:

> waiting for multiple authenticated humans, remembering the decision as server truth, letting the external Agent carry that decision to a governed approval boundary, and continuing the same action after approval without a hidden human operator finishing the Agent's work.

Close that loop once, truthfully, then move on to the next Revolution.
