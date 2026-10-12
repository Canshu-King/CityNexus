# Revolution Relay — R28 Checkpoint B

## Baton owner

**Codex local validation.**

GPT has stopped writing core files at this checkpoint. Validate and repair this exact branch before any new feature work.

## Binding

- branch: `gpt/revolution-r28-implementation`
- checkpoint B head: `ed7b18b74d462276e952c2b025a1199b9083d6af`
- Codex checkpoint A fix accepted at: `1876e2855fe1d5cf53ebdb85731c4fa0ee1c635c`
- R28 taskbook: `taskbooks/revolution/REVOLUTION_R28_AUTHENTICATED_COLLECTIVE_CONTINUITY_TASKBOOK.md`

Read the taskbook, but **do not restart architecture work**. This checkpoint is already an implementation.

## Review of your previous push

Your `1876e28` fix is accepted.

- The explicit flushes in the R28 fixture correctly repair SQLite FK ordering in the test setup.
- Restoring the unversioned V1 catalog to the six pinned legacy tools matches the existing `agent-mcp/citynexus_mcp/schemas.py::V1_TOOL_NAMES` contract.
- You did not weaken `WAITING_FOR_APPROVAL`, `AgentPendingAction`, or automatic continuation.

Do not revisit those changes unless a concrete regression test now fails.

## What GPT added after your push

### 1. Crash-window continuation recovery

A normal approval continuation was not enough. There was a real crash seam:

`approval consumed + mutation committed -> process dies -> pending row still RESUMING`

A retry previously hit `CONSUMED` and returned 409 forever.

Checkpoint B now:

- reconciles a consumed `accept_replan` from durable `ReplanProposal.status == ACCEPTED` + `Journey.active_plan_version_id`;
- lets a consumed approval finalize the same pending lineage instead of blindly failing;
- scans approved/consumed `PENDING|RESUMING` continuations at FastAPI startup;
- never fabricates success from a local flag.

Files:
- `backend/app/agent/continuation.py`
- `backend/app/main.py`

### 2. Authenticated human traveler principal

New:
- `backend/app/traveler_principal.py`
- `CITYNEXUS_TRAVELER_AUTH_SECRET`
- `CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS`

This is intentionally the smallest production-shaped auth seam, not a fake `member_id` header.

A signed short-lived bearer token contains the Traveler principal. The server then resolves:

`signed principal -> Traveler -> in-force JourneyMember -> role/capability`

Important:

- there is **no public endpoint that mints an arbitrary traveler token**;
- `issue_traveler_token()` is a trusted server/test/operator helper;
- production login/IdP can own issuance later;
- when the auth secret is configured, the existing collective-response and approval routes fail closed;
- when it is absent, legacy coursework/demo compatibility remains unchanged.

Strict mode proves:
- unauthenticated -> 401;
- authenticated non-member -> 403;
- withdrawn/lapsed member -> 403;
- OWNER token cannot answer an ADMIN member URL -> 403;
- ADMIN cannot approve the OWNER-bound Journey mutation -> 403;
- request/path `member_id` is not authority;
- approval receipt now exposes durable `approved_by`.

### 3. Real Gateway continuation test

Checkpoint A only had a monkeypatched dispatch test. Checkpoint B adds a real control:

`real reschedule_activity -> real server approval -> AgentPendingAction -> approve route -> real Gateway consume+mutation -> resumed step on same AgentRun`

No external model is needed for this mechanics test.

## First test pass

**Important:** make sure the shell does not carry a global traveler auth secret while running legacy regression tests.

From repo root:

```bash
git fetch origin
git checkout gpt/revolution-r28-implementation
git reset --hard origin/gpt/revolution-r28-implementation
git rev-parse HEAD
git diff --check 1876e2855fe1d5cf53ebdb85731c4fa0ee1c635c..HEAD

cd backend
unset CITYNEXUS_TRAVELER_AUTH_SECRET

python -m compileall -q app

python -m pytest -q tests/test_r28_durable_approval_continuation.py
python -m pytest -q tests/test_r28_authenticated_member_principal.py
```

Then focused regressions:

```bash
python -m pytest -q \
  tests/test_agent_authority_v2_actions.py \
  tests/test_gpt_agent_authority_v3.py \
  tests/test_agent_principal_boundary.py \
  tests/test_r27_member_surface.py \
  tests/test_r27_collective_mediation.py \
  tests/test_r27_truth_mesh_runtime.py \
  tests/test_r27_source_truth_bridge.py
```

Do not run a broad multi-hour suite until these are green.

## Things I specifically want you to attack

### A. Startup registration / import safety

The new continuation reconciliation is registered with FastAPI startup. Verify:
- app import succeeds;
- TestClient does not trigger an import cycle;
- no continuation runs before schema creation;
- a normal app boot with no pending rows is silent and fast.

### B. Real Gateway continuation

The new real test must prove:
- original pending step and resumed step share one `AgentRun.id`;
- approval becomes `CONSUMED`;
- pending action becomes `RESUMED`;
- mission/run become `COMPLETED`;
- no second model call exists.

If this test fails, fix the integration, not the test expectation, unless the expectation contradicts durable server truth.

### C. Crash/retry control

Add one focused test if the current suite does not already prove it:

- pending action is `RESUMING`;
- approval is already `CONSUMED`;
- proposal is already `ACCEPTED`;
- Journey active plan is the proposal's proposed plan;
- retry/reconciliation marks the pending action `RESUMED` without a second mutation.

This is the exact seam that motivated the new code.

### D. Human-principal attack controls

The new auth suite must stay strict when a secret is configured.

Do not “fix” failures by:
- trusting `member_id`;
- adding `X-Member-Id` as authority;
- exposing a public mint-any-traveler-token endpoint;
- making ADMIN gain `JOURNEY_UPDATE`;
- bypassing withdrawn/expired membership checks.

### E. Legacy compatibility

With `CITYNEXUS_TRAVELER_AUTH_SECRET` unset, existing coursework/demo tests should retain the old transport behavior. This compatibility mode must be described as **legacy local/demo**, not as authenticated identity.

## Do not touch

- Do not refactor WB2api/provider logic because of the old R27 transient first-call failure.
- Do not weaken collective fairness, C4, provider truth, or Gateway.
- Do not merge to `authority/mainline`.
- Do not spend time generating a large evidence package yet.
- Do not call a real external model just to validate continuation mechanics.

## Push-back contract

Fix only real failures and push to:

`gpt/revolution-r28-implementation`

Return:

1. new HEAD SHA;
2. exact commands run;
3. pass/fail count for each command;
4. any code changes you made and why;
5. whether the real Gateway continuation test passed;
6. whether the consumed-approval crash/retry control passed;
7. whether all human-principal negative controls passed;
8. whether any external model/API call was used (expected: **no**).

## Revolution next step after green

Do not start another backend hardening round on your own.

When Checkpoint B is green, baton returns to GPT. The next slice is deliberately product-facing:

**R28 collective waiting / member decision / approval UI surface.**

The Revolution objective remains:

> CityNexus must wait for real people, know exactly who answered, continue its own work afterward, and let the humans actually see that lifecycle.
