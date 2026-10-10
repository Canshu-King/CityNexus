# Revolution Relay — R28 FINAL LIVE CLOSURE

## Baton owner

**Codex — final local validation + one bounded real external-Agent closure.**

This is **not Checkpoint D**. Do not open another review/hardening loop after this file.

GPT has frozen feature work. First validate the exact implementation. If the focused gates are green, run one fresh closure. If the machine verdict is not PROVEN, stop on the exact blocker instead of stitching a success story.

## Binding

- branch: `gpt/revolution-r28-implementation`
- implementation HEAD before this handoff document: `facca7c89b8283c93f61375b821db81b95983c71`
- original R28 contract: `taskbooks/revolution/REVOLUTION_R28_AUTHENTICATED_COLLECTIVE_CONTINUITY_TASKBOOK.md`
- prior product-surface gate: `taskbooks/revolution/R28_RELAY_CHECKPOINT_C_CODEX_VALIDATION.md`
- binding R27 capability evidence: real WB2api/Hermes-compatible chain `cn:glm-5.3-flash -> cn:deepseek-v4.1-flash`
- keep `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`

### Important note about the previous “push”

When GPT received the message that Checkpoint C was tested and pushed, GitHub still showed the branch exactly at the prior GPT SHA `8956af82fe925510caf00342dad388b680c64572` with no new commit/ref.

That is consistent with **tests green + no fixes + git push = Everything up-to-date**, but it is not an auditable test receipt by itself.

Do not waste a commit just to manufacture history. Simply rerun the focused gates below on the current HEAD and record the exact commands/counts in the final result.

## What GPT found and fixed after Checkpoint C

The R28 implementation still lacked one taskbook-mandated P0 seam: execution-state transitions could still be narrated as physical execution.

### 1. Durable execution truth

New:

- `backend/app/execution/truth.py`
- `ExecutionTruthAttestation`
- truth projected through shared JourneyTwin/Edge NOW state
- truth persisted in Activity metadata history and JourneyOutcomeEvent payload

Allowed semantics:

- `SIMULATED_STATE_TRANSITION`
- `OPERATOR_CONFIRMED_EXECUTION`
- `DEVICE_LOCATION_VERIFIED_EXECUTION`

Rules:

- no attestation body => **SIMULATED_STATE_TRANSITION**
- operator-confirmed => requires signed in-force Journey member + explicit `operator_confirmed=true`
- ordinary browser foreground coordinates **cannot** promote themselves to device/location verified
- current `FOREGROUND_WEB` source is deliberately rejected for `DEVICE_LOCATION_VERIFIED_EXECUTION`
- the device/location tier remains fail-closed until a genuinely attested ingestion source exists

Do not weaken this to make a demo look physical.

### 2. Principal-bound location evidence

Strict auth mode binds a foreground location submission to the signed traveler/member and records:

`journey.location.recorded`

This is useful evidence, but it is still not hardware attestation.

### 3. Approval principal history

Strict authenticated approval now records:

`agent.action_approval.principal_bound`

The audit contains member id, role, auth method and signed traveler actor. This lets a verifier prove the human transport identity without trusting a URL/body id.

### 4. Machine closure verifier

New:

`backend/scripts/r28_machine_verdict.py`

Usage:

```bash
cd backend
python scripts/r28_machine_verdict.py --run-id <FINAL_APPROVAL_SUSPENDED_AND_RESUMED_RUN_ID> --output <OUTPUT_JSON>
```

Exit code is 0 **only** when overall verdict is PROVEN.

It checks machine state for:

- terminal AgentRun mutation outcome;
- non-local configured runtime identity;
- durable AgentPendingAction RESUMED;
- original gated step + later approved executed step on the same AgentRun;
- approval create/approve/consume ordering;
- authenticated approver principal binding;
- exact resumed request id matching the acceptance audit;
- selected ReplanProposal ACCEPTED;
- Journey active PlanVersion == accepted proposal plan;
- every required collective response bound to authenticated traveler audits;
- at least two distinct authenticated human actors in the collective decision;
- every non-selected collective proposal terminally rejected/invalidated/expired;
- active C4 commitment preserved on the active plan;
- execution transition truth labels;
- aggregate `transport_caller_principal_authentication`.

Do not hand-edit `R28_MACHINE_VERDICT.json`.

## Phase 1 — final focused validation

From repo root:

```bash
git fetch origin
git checkout gpt/revolution-r28-implementation
git reset --hard origin/gpt/revolution-r28-implementation
git rev-parse HEAD
git status --short
git diff --check 42c5cc0dba4493b9ce13a47a76956bf49c768e70..HEAD
```

### Backend

Use the correct backend environment and keep external model calls OFF for this phase.

```bash
cd backend
unset CITYNEXUS_TRAVELER_AUTH_SECRET

python -m compileall -q app scripts/issue_traveler_token.py scripts/r28_machine_verdict.py

python -m pytest -q \
  tests/test_r28_authenticated_member_principal.py \
  tests/test_r28_durable_approval_continuation.py \
  tests/test_r28_execution_truth.py

python -m pytest -q \
  tests/test_agent_authority_v2_actions.py \
  tests/test_gpt_agent_authority_v3.py \
  tests/test_agent_principal_boundary.py \
  tests/test_r27_member_surface.py \
  tests/test_r27_collective_mediation.py \
  tests/test_r27_truth_mesh_runtime.py \
  tests/test_r27_source_truth_bridge.py \
  tests/test_v12_authoritative_trip_execution.py
```

Fix real integration defects only. If the new execution-truth tests expose an existing test that expected raw HTTP transitions to mean “physical”, update that expectation to the truthful semantic rather than deleting the truth label.

### Frontend

```bash
cd ../frontend
npm run typecheck
npm run build
npx playwright test e2e/r28-collective-decision-surface.spec.ts --project=chromium
```

Also spot-check 360/390/412 px for no horizontal overflow in the open Copilot collective panel. Do not start a visual redesign.

### Gate

Do **not** proceed to the live external Agent if any of these focused gates fail.

Push only necessary fixes to the same branch.

## Phase 2 — fresh R28 closure setup

Only after Phase 1 is green.

Create a **fresh disposable runtime DB**. Do not reuse the R27 runtime DB as the closure database.

Configure:

- the normal successful WB2api/Hermes-compatible external Agent chain from R27;
- a fresh random `CITYNEXUS_TRAVELER_AUTH_SECRET` of at least 32 bytes;
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`;
- credentials only in the disposable process environment, never in files/package.

Create one fresh shared Journey with:

- OWNER traveler/member;
- ADMIN traveler/member;
- both `MEMBER_IN_FORCE`;
- materially different journey-scoped preferences (garden vs museum/craft is fine);
- at least one real active C4 commitment;
- at least two materially different `GROUNDED_FEASIBLE` proposal shapes.

### World-fact efficiency

R28 is **not** another provider expedition.

Reuse the working R27 collective/fairness/world-fact machinery and product-supported captured real-provider truth where available.

Do not manually invent opening hours, costs, mobility, member fit, proposal ids or candidate ids.

Do not repeatedly rerun Overpass/Valhalla/source research unless the fresh Journey genuinely lacks the two grounded options required for acceptance.

One bounded live acquisition retry is acceptable if needed. Do not redesign WB2api/provider reliability because R27's first API call once failed transiently and immediately succeeded on retry.

## Phase 3 — signed human sessions

Mint tokens only in the trusted local process:

```bash
cd backend
python scripts/issue_traveler_token.py --traveler-id <OWNER_TRAVELER_ID>
python scripts/issue_traveler_token.py --traveler-id <ADMIN_TRAVELER_ID>
```

Use separate browser/API contexts.

The browser session seam is:

```js
sessionStorage.setItem("citynexus.traveler.bearer", "<SIGNED_BEARER>")
```

Never store or commit the tokens.

Before the positive path, run one bounded impersonation control:

- OWNER bearer on ADMIN collective member path => 403
- or ADMIN bearer on OWNER path => 403

Then stop attacking auth; the negative suite already covers the rest.

## Phase 4 — one real external Agent collective strike

Use the **normal product Agent command/runtime**, not `AgentToolGateway` called manually.

The external Agent may be told the Journey problem/objective, but do **not** hand it:

- a correct proposal id;
- a member answer;
- a selected candidate id;
- a fixed tool sequence.

Required first-stage result:

1. the real external Agent inspects the shared Journey;
2. sees the distinct member context;
3. discovers/requests the genuine shared trade-off;
4. invokes the server-owned collective decision boundary;
5. the mission reaches `WAITING_FOR_MEMBERS`.

At this point capture one concise UI receipt if practical:

- N/M progress;
- both member states;
- current signed member identity;
- server-derived option labels.

No screenshot may contain bearer tokens or credentials.

## Phase 5 — two independently authenticated responses

Use the normal collective response HTTP route twice:

1. first signed member => still `WAITING_FOR_MEMBERS`;
2. second signed member => `RESOLVED` and server-created child mission.

Both responses must be for the same server clarification/decision epoch.

Do not mutate baseline TravelerTwin/preferences as a substitute for the answer.

## Phase 6 — real Agent reaches approval boundary

Resume the server-created child mission through the **normal mission resume route**, so the configured external Agent chooses the next action.

Required result:

- real external model selects the server-resolved proposal through normal tools;
- `accept_replan` reaches `REQUIRE_CONFIRMATION` or `REQUIRE_STEP_UP`;
- runtime persists one `AgentPendingAction`;
- the same AgentRun becomes `WAITING_FOR_APPROVAL`;
- AgentRun/mission completion timestamps remain null while suspended;
- **the model loop stops here**.

Record this AgentRun id. This is the `--run-id` for the machine verifier.

There must be no `citynexus-local-agent` retry and no second manually assembled `accept_replan` call.

## Phase 7 — authenticated approval auto-resumes the SAME run

With the signed OWNER session, use the normal approval route.

Before clicking/posting, the UI should show the approval surface only for the authorized viewer.

Required result:

```text
same AgentRun
  original accept_replan -> approval required
  durable AgentPendingAction
  authenticated owner approval
  server auto-resume
  later accept_replan step with approval_id
  executed=true
  proposal ACCEPTED
  AgentPendingAction RESUMED
  same AgentRun COMPLETED
```

No external model call is allowed merely to perform the post-approval continuation.

Replaying the approval/read must not create another mutation.

## Phase 8 — execution truth control

Do **not** claim physical travel.

Preferred bounded proof:

- if one ordinary execution transition is safe/legal on the final Journey, perform exactly one normal transition with no truth body;
- read JourneyTwin back;
- prove `execution_truth.kind == SIMULATED_STATE_TRANSITION`;
- explicitly report real-world physical execution as **NOT PROVEN**.

If doing even one transition would disturb the closure state or C4 demonstration, perform **no** execution transition. The machine verifier is allowed to report that no physical execution was claimed; the focused execution-truth suite already proves the state machine semantics.

You may use `OPERATOR_CONFIRMED_EXECUTION` only for an actual signed person explicitly confirming the action. It is still not GPS proof.

Do **not** attempt to force `DEVICE_LOCATION_VERIFIED_EXECUTION` with ordinary `FOREGROUND_WEB` coordinates. The correct current response is 409 `LOCATION_OBSERVATION_NOT_DEVICE_VERIFIED`.

## Phase 9 — machine verdict

Run:

```bash
cd backend
python scripts/r28_machine_verdict.py \
  --run-id <FINAL_AGENT_RUN_ID> \
  --output R28_MACHINE_VERDICT.json
```

Required:

```text
summary.overall = PROVEN
exit code = 0
```

Read every non-PROVEN item before doing anything else.

If the verdict is CONTRADICTED or NOT_PROVEN:

- do not edit the JSON;
- do not add a prose exception;
- do not manually replay an Agent tool;
- either fix one real product defect and rerun the bounded closure from the appropriate point, or stop with the exact blocker.

## Phase 10 — final delivery

Produce:

- `REVOLUTION_R28_AUTHENTICATED_COLLECTIVE_CONTINUITY_RESULT.md`
- generated `R28_MACHINE_VERDICT.json`
- focused backend/frontend test output
- bounded replay instructions
- one concise UI capture/receipt if available
- disposable fresh DB in the local delivery package, with no credentials

The report must separately state:

- **Agent reasoning proven:** yes/no + exact run ids/tool steps
- **authenticated human decision proven:** yes/no
- **automatic continuation proven:** yes/no
- **Gateway mutation proven:** yes/no
- **execution simulation proven:** yes/no
- **real-world physical execution proven:** expected **NO** unless genuinely attested external evidence exists

Never use the phrase “physical execution proven” for rapid HTTP state transitions.

Commit only non-secret code/tests/report/verdict to:

`gpt/revolution-r28-implementation`

Do not commit:

- WB2api/API credentials;
- traveler bearer tokens;
- browser storage state containing tokens;
- raw secret environment values.

Push the final branch.

## Stop conditions

After this strike, stop.

Do not:

- open R28.1 / Checkpoint D/E;
- do another broad audit;
- migrate into a provider-reliability project because of one transient first-call failure;
- replace the external Agent with deterministic fallback prose;
- merge to `authority/mainline`.

Return the final HEAD, exact test counts, live Agent run id, machine verdict summary, and the path/package name.

The Revolution question is now binary and machine-checkable:

> Did CityNexus wait for two authenticated real member principals, let the real Agent reach its own governed approval boundary, and then continue that same pending Agent action automatically after authenticated approval — while telling the truth about simulated versus physical execution?

If yes, R28 is closed. If no, name the one exact blocker and stop.
