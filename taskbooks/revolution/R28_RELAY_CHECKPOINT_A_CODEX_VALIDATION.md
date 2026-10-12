# Revolution Relay — R28 Checkpoint A

## Baton owner

**Codex local validation.**

GPT has stopped writing core files at this checkpoint. Do not redesign R28 from scratch. Validate this exact branch first.

## Branch / binding

- branch: `gpt/revolution-r28-implementation`
- R28 taskbook base: `30dcba5f0d9cfa7d4a6d47fab64df82c1ffb8b34`
- checkpoint head at handoff: `df789374fb34a874e01393211a3bcaf8a4c27b57`
- R27 delivery ancestor: `ab49ca066a0fead7949f9d4a99ab310c91b3361d`

Read first:

`taskbooks/revolution/REVOLUTION_R28_AUTHENTICATED_COLLECTIVE_CONTINUITY_TASKBOOK.md`

## What GPT implemented

Checkpoint A attacks only the durable approval-continuation seam.

New behavior:

1. A model-selected mutating tool that returns `REQUIRE_CONFIRMATION` or `REQUIRE_STEP_UP` plus a server approval id is persisted as `AgentPendingAction`.
2. The originating AgentRun and JourneyMission become `WAITING_FOR_APPROVAL`; they are not terminal and do not get a completion timestamp.
3. The model loop stops immediately instead of spending another turn or hitting the repetition guard.
4. The normal approval route automatically resumes only actions that came from a durable AgentRun continuation.
5. Resume uses a stable server-owned request id `agent-resume-<pending_action_id>`, reuses the Gateway/idempotency/approval-consumption boundaries, and appends the resumed tool step to the **same AgentRun**.
6. A successful resume marks the pending action RESUMED and completes the same run/mission.
7. Direct/manual tool approvals with no AgentPendingAction retain the old two-step behavior, so existing authority tests should not be silently rewritten.

Touched files:

- `backend/app/agent/continuation.py` (new)
- `backend/app/agent/runtime.py`
- `backend/app/db/models.py`
- `backend/app/main.py`
- `backend/db/schema.sql`
- `backend/tests/test_r28_durable_approval_continuation.py` (new)

No R27 collective fairness/provider/C4 logic was intentionally weakened.

## Run these tests first

From the repository root / correct backend environment:

```bash
cd backend
python -m compileall -q app
python -m pytest -q tests/test_r28_durable_approval_continuation.py
python -m pytest -q   tests/test_agent_authority_v2_actions.py   tests/test_gpt_agent_authority_v3.py   tests/test_agent_principal_boundary.py   tests/test_r27_member_surface.py
```

Then run the focused R20-R27 lineage suite you used for the R27 closure if it is available locally, but do **not** spend the round on broad unrelated suites before the checkpoint tests are green.

Also run:

```bash
git diff --check 30dcba5f0d9cfa7d4a6d47fab64df82c1ffb8b34..HEAD
```

## What to fix locally if it fails

Fix real integration defects on this branch. Typical acceptable fixes:

- import/circular-import mistakes;
- SQLAlchemy model/schema mismatch;
- SQLite existing-database boot/migration issue;
- incorrect status/timestamp assertion;
- Gateway result shape mismatch;
- existing approval tests accidentally changed by auto-resume;
- concurrency/idempotency bug exposed by a test.

Do **not**:

- remove the durable pending-action concept just to make old tests pass;
- revert `WAITING_FOR_APPROVAL` back to COMPLETED/PARTIAL;
- reintroduce a manual `citynexus-local-agent` retry as the closure;
- call the external model again merely to resume an already-approved action;
- change WB2api/provider configuration because of the old transient R27 first-call strike.

## Add two local integration controls if feasible

After the supplied tests pass, add/execute:

1. **real Gateway resume control**: a genuine AgentRun reaches an approval boundary, approval POST causes exactly one mutation without a second model call, and the same run gains the resumed step.
2. **process/retry control**: after approval is durable, replaying the approval/resume path must not create a second mutation. A 409 replay refusal is acceptable if the first mutation is durable and unique.

Do not use a real external model for the first control if a deterministic fake model can select the action; we are testing continuation mechanics here, not re-proving GLM.

## What to push back

Push only necessary fixes/tests to:

`gpt/revolution-r28-implementation`

Then report:

- new HEAD SHA;
- exact test commands;
- pass/fail counts;
- any remaining blocker with exact file/function;
- whether `AgentRun -> pending action -> approval -> resumed step -> mutation` is queryable on one durable lineage.

Once that is pushed, baton returns to GPT for Phase C review and the next R28 slice (human principal binding).
