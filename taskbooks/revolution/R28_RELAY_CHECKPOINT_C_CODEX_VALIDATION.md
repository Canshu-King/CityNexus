# Revolution Relay — R28 Checkpoint C

## Baton owner

**Codex local validation and bounded integration fixes.**

GPT has frozen feature work at this checkpoint. Validate the exact branch first. Do not restart the architecture and do not launch another backend-only hardening round.

## Binding

- branch: `gpt/revolution-r28-implementation`
- Codex Checkpoint B push accepted at: `42c5cc0dba4493b9ce13a47a76956bf49c768e70`
- GPT product-surface implementation head before this handoff document: `9a6c2287be61582c43c0de4ac62d27d8deb313a3`
- full R28 contract: `taskbooks/revolution/REVOLUTION_R28_AUTHENTICATED_COLLECTIVE_CONTINUITY_TASKBOOK.md`

## Review of your previous push

Your Checkpoint B test expansion is accepted.

In particular:

- expired member controls are now explicit;
- OWNER/ADMIN path impersonation is attacked in both directions;
- body-forged `member_id/traveler_id` is rejected by schema/boundary;
- tampered and expired signed credentials are rejected;
- process restart after `approval CONSUMED + mutation committed` is covered;
- the same AgentRun is proven to suspend, survive the human wait, and resume without another model call;
- replay after a successful continuation is read-only and returns the durable RESUMED receipt instead of inventing another mutation.

Do not remove those tests.

## What GPT added after your push

Checkpoint C moves R28 out of “backend truth only” and into a visible product lifecycle.

### A. Pending-decision server read model

`GET /api/v1/journeys/{journey_id}/missions/pending` now projects, in one response:

- authenticated viewer principal/member/role when strict traveler auth is enabled;
- collective required members and response progress;
- server-derived candidate options with human-place labels;
- whether the current viewer already answered;
- durable `AgentPendingAction` / approval state;
- whether this exact viewer is allowed to approve.

When `CITYNEXUS_TRAVELER_AUTH_SECRET` is configured, this read is identity-bound. No token -> 401.

Legacy/demo mode remains compatible, but member display names are deliberately withheld there.

### B. Browser traveler session seam

New:

`frontend/src/lib/travelerSession.ts`

The browser stores **only the opaque signed bearer** in:

`sessionStorage["citynexus.traveler.bearer"]`

No browser-stored `member_id` or role is treated as authority.

`cityNexusApi` now sends that bearer on:

- pending mission reads;
- collective member answers;
- Agent approval.

### C. Collective decision UI

`JourneyClarificationPanel` now visibly renders:

- “group decision required”;
- N/M member progress;
- each required member’s answered/waiting state;
- server-grounded candidate place labels;
- a short trade-off statement from server fairness facts;
- current member identity/role resolved by the server;
- answer controls only when the server says this browser maps to a required member;
- read-only state when there is no authenticated member session.

Stable test anchors:

- `collective-decision`
- `collective-progress`
- `collective-member`
- `collective-option`

### D. Durable approval UI

When the AgentRun is `WAITING_FOR_APPROVAL`, the same panel now shows:

- that the original Agent task is suspended rather than finished;
- approval status;
- continuation status;
- an Approve CTA only when the server projects `viewer_can_approve=true`;
- copy explicitly stating that approval resumes the saved pending action rather than asking the model to decide again.

Test anchors:

- `collective-approval`
- `collective-approve`

### E. Local signed-token helper

`backend/scripts/issue_traveler_token.py`

This is a local trusted-process helper only. It is **not** an HTTP mint endpoint.

With `CITYNEXUS_TRAVELER_AUTH_SECRET` in the environment:

```bash
cd backend
python scripts/issue_traveler_token.py --traveler-id <TRAVELER_UUID>
```

Use the returned bearer only for local validation. Do not commit tokens.

### F. Playwright product contract

New:

`frontend/e2e/r28-collective-decision-surface.spec.ts`

It proves the visible collective and approval states and asserts that answer/approval HTTP requests carry the signed traveler bearer.

## First pass — backend

From repo root:

```bash
git fetch origin
git checkout gpt/revolution-r28-implementation
git reset --hard origin/gpt/revolution-r28-implementation
git rev-parse HEAD
git diff --check 42c5cc0dba4493b9ce13a47a76956bf49c768e70..HEAD

cd backend
unset CITYNEXUS_TRAVELER_AUTH_SECRET

python -m compileall -q app scripts/issue_traveler_token.py

python -m pytest -q \
  tests/test_r28_authenticated_member_principal.py \
  tests/test_r28_durable_approval_continuation.py

python -m pytest -q \
  tests/test_agent_authority_v2_actions.py \
  tests/test_gpt_agent_authority_v3.py \
  tests/test_agent_principal_boundary.py \
  tests/test_r27_member_surface.py \
  tests/test_r27_collective_mediation.py \
  tests/test_r27_truth_mesh_runtime.py \
  tests/test_r27_source_truth_bridge.py
```

If a focused test fails, fix the integration. Do not delete the new identity/read-model semantics to preserve an outdated assertion.

## Second pass — frontend

```bash
cd frontend
npm run typecheck
npm run build
npx playwright test e2e/r28-collective-decision-surface.spec.ts --project=chromium
```

The new Playwright file intentionally mocks only the server state needed to verify rendering and HTTP auth propagation. Backend identity and continuation truth are independently covered by the Python suite above.

## Third pass — actual local signed-session smoke

Do this without an external model.

Use any existing local Journey with an OWNER/ADMIN member pair (the R27/R28 fixture or a bounded local DB fixture is fine).

Start the backend with a random process-only secret of at least 32 bytes:

```bash
export CITYNEXUS_TRAVELER_AUTH_SECRET='<random-32+-byte-local-secret>'
```

Mint one OWNER token and one ADMIN token with `backend/scripts/issue_traveler_token.py`.

For two separate browser contexts, inject the appropriate bearer before loading CityNexus:

```js
sessionStorage.setItem("citynexus.traveler.bearer", "<token>")
```

Minimum smoke assertions:

1. OWNER context pending read returns server-resolved OWNER viewer.
2. ADMIN context pending read returns server-resolved ADMIN viewer.
3. A browser cannot make itself the other member by changing DOM/path/body.
4. In a collective WAITING state, both browsers show the same N/M progress but mark a different “you”.
5. After one member answers, the other context observes N/M change by polling/reload.
6. Only a server-authorized approval viewer sees/enables the approval CTA.
7. No token is ever written to git, screenshots, JSON evidence, or taskbook.

If building a full genuine collective fixture for this smoke would require re-running the whole R27 city/provider scenario, **do not do that yet**. Backend truth + Playwright product contract is sufficient for Checkpoint C. The real external-Agent closure comes after this checkpoint.

## Things to attack

Pay special attention to:

- TypeScript duplicate/merged contract mistakes;
- JSX narrowing around `item.collective` / `item.continuation`;
- strict-auth pending read returning 401 in the browser when the session bearer is absent;
- legacy mode accidentally leaking member display names;
- mobile overflow in the Copilot panel at 360/390/412 px;
- polling causing duplicate member answers or duplicate approvals;
- approval replay creating another mutation;
- the old NativeMissionTimeline approval button: it now also uses the signed bearer through the shared API method and must continue to work in legacy mode.

## Do not do

- Do not expose an HTTP endpoint that mints arbitrary traveler tokens.
- Do not store role/member identity in localStorage and trust it.
- Do not add `X-Member-Id` authority.
- Do not grant ADMIN `JOURNEY_UPDATE` just to make the button appear.
- Do not touch WB2api/provider fallback because of R27’s old transient first strike.
- Do not call a real external model during Checkpoint C.
- Do not merge to `authority/mainline`.
- Do not create a large evidence package yet.

## Push-back contract

Push necessary fixes/tests to:

`gpt/revolution-r28-implementation`

Return:

1. new HEAD SHA;
2. exact backend commands and pass counts;
3. exact frontend commands and pass counts;
4. any code changes and why;
5. `npm run typecheck` result;
6. `npm run build` result;
7. focused Playwright result;
8. whether the local signed-session smoke was run and what was proven;
9. confirmation that no external model/API was called;
10. any remaining blocker, named by exact file/function.

## What happens after Checkpoint C

Baton returns to GPT.

If C is green, R28 gets **one** final live closure:

- fresh shared Journey;
- real configured external Agent;
- two signed member sessions;
- real collective trade-off;
- both authenticated responses;
- same AgentRun suspends at approval;
- authenticated owner approval;
- automatic resume on the same durable lineage;
- UI visibly reflects the lifecycle;
- execution truth is labeled simulation unless real-world presence is actually proven.

No more backend-review treadmill after that. The purpose of C is to make the live closure short and decisive.
