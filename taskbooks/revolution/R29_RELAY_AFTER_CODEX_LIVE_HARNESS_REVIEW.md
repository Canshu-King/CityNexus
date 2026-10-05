# Revolution Relay — R29 Live Harness Review and Final Execution

## Binding state

Branch:

`gpt/revolution-r29-disagreement-mediation`

GPT relay HEAD at handoff:

`5048d61224e54649b5eea6e5b4d2aad6c732c69f`

Codex's last push before this review:

`035f0ef0a058cec8b660c7111f8b25a8a7fd4225`

That push was useful, but it did **not** close R29. It added a bounded live harness that stopped at mediator resume and a search-limit prompt improvement. There was still no committed final R29 result or machine verdict.

## What GPT changed after reviewing the Codex push

### 1. `--full-r29` now means full R29

`backend/run_r29_live.py` now runs:

```text
external Agent round 1
  -> authenticated preference-driven disagreement
  -> MEDIATION_REQUIRED
  -> external mediator Agent
  -> server-proven mediation progress
  -> renewed member round
  -> first renewed answer remains WAITING_FOR_MEMBERS
  -> second renewed answer RESOLVES
  -> resolved child
  -> external Agent accept_replan
  -> approval boundary
  -> Journey OWNER approval
  -> same-run continuation
  -> R29 machine verdict
```

It no longer stops immediately after mediator resume.

The continuation mode now actually binds the supplied existing DB instead of accepting a DB argument and silently using another configured database.

### 2. Approval identity is role-derived, never array-derived

The harness resolves the Journey OWNER from durable `JourneyMember.role`.

It never assumes `required_member_ids[0]` is the approver.

### 3. Round-1 disagreement must be preference-driven

The harness no longer manufactures disagreement with `options[0]` vs `options[1]`.

For each required member it reads the server-owned:

`candidate_options[*].member_fits[member_id].effective_fit`

and chooses that member's maximum-fit grounded proposal.

If both members independently prefer the same proposal, the strike fails honestly with:

> provider-backed setup did not produce genuine preference-driven disagreement

Do not patch around that by assigning different proposal IDs manually. Use a better bounded world.

### 4. Renewed compromise is selected only after the mediator run

The harness never supplies a compromise ID to the external model.

After the mediator has opened round 2, human transport considers only proposal IDs that the server stored in:

`mediation_progress.improved_option_ids`

and chooses the strongest fairness receipt among those improved options.

### 5. Social-authority lock is now truly on the mutation core

The earlier Journey lock was enforced at Agent Gateway, which still left a direct REST/core mutation seam.

GPT centralized the lock in:

`app.collective_mediation.journey_has_unresolved_collective_mediation`

and added it to:

`collective_mutation_gate`

Therefore a direct plan selection/replan acceptance path cannot turn an algorithmic `COMPROMISE_AVAILABLE` result into authority while explicit disagreement remains unresolved.

The Gateway uses the same shared lock implementation.

### 6. The machine verdict became stricter

`r29_machine_verdict.py` now additionally proves:

- a real configured external Agent opened round 1;
- each relevant member's round-1 answer is a maximum-fit proposal under that member's server-computed `member_fits`;
- those independent best choices genuinely diverge.

This prevents a scripted harness from manufacturing a fake disagreement and still earning PROVEN.

### 7. Final report generation is fail-closed

`run_r29_live.py --full-r29` writes:

`REVOLUTION_R29_LIVE_DISAGREEMENT_MEDIATION_RESULT.md`

**only when** the generated R29 machine verdict has:

`summary.overall = PROVEN`

A failed strike must not produce a success report.

The report explicitly keeps these truth boundaries:

- signed Journey principals are not proof of two physical humans on two devices;
- no physical travel is claimed;
- the compromise was not supplied to the model.

## Additional static red-team after Codex's no-op push

GitHub still showed no new remote R29 commit after Codex reported testing/pushing; the branch remained on GPT's prior handoff commit. Treat that as an up-to-date/no-op push, not as proof of live closure.

GPT then tightened two remaining proof/authority seams:

### A. Tie-broken disagreement no longer counts

Round 1 now requires each relevant member to have **one unique maximum-fit grounded proposal**.

A tied best set is not a proven preference conflict and the live harness fails closed instead of using proposal-id ordering as a hidden tie-breaker.

The machine verdict now requires the same uniqueness.

Commits:

- `58ec07816f89658e8a9eb414b8621631ab62af1a`
- `379a452fd1cc431d21169ef51b9748590784b5a9`

### B. Renewed consent remains bound to the exact selected plan until consumed

A second seam remained after the renewed round became `RESOLVED`: the general unresolved-mediation lock cleared before the selected compromise was actually activated.

GPT added `pending_resolved_mediation_selection` and changed the core mutation gate so:

- renewed member consent authorizes exactly the selected proposal/PlanVersion;
- a sibling plan is still denied while that selected proposal remains PRESENTED and its plan remains a CANDIDATE;
- the exact selected plan can consume the resolved decision;
- after the selected proposal is accepted / no longer a live candidate, the old decision does not permanently lock future Journey work.

Commits:

- `185ccc682ae14428eb9376907d9c5c3b3c5b5c1c`
- `f7ed8997e06a6da83cfb747218d264d1a8c147be`
- `9daac1e899d198138d0614aee6e0faa4b5fcf397`
- `69f0663605c31152ce1074e4eec0eae3476d5d57` — expires renewed consent if the active base plan has changed before consumption.

Do not weaken these if focused tests reveal a real integration mismatch.

### C. Renewed human consent outranks algorithmic compromise ranking

After renewed consent resolves, the exact selected plan now carries pending social authority until consumed.

A remaining edge case was that the current fairness classifier might still prefer a sibling compromise B while the same relevant members explicitly chose A. That would invert the authority model by allowing algorithmic ranking to overrule renewed human consent.

GPT fixed the core gate so:

- sibling B remains denied by `COLLECTIVE_MEDIATION_SELECTED_PLAN_REQUIRED`;
- exact selected A is allowed once hard feasibility/authority checks pass;
- the returned classification is `RENEWED_COLLECTIVE_CONSENT`;
- stale renewed consent still expires if its base plan no longer matches active reality.

Commits:

- `906e35020f26c33cc35dfbcd20a8f38c35aec3a5`
- `5048d61224e54649b5eea6e5b4d2aad6c732c69f`

This is a hard social-authority invariant. Do not "fix" a failing test by restoring algorithmic ranking above renewed human consent.

## Codex Phase A — validate the current GPT HEAD

Do not rerun unrelated historical suites.

```bash
git fetch origin
git checkout gpt/revolution-r29-disagreement-mediation
git reset --hard origin/gpt/revolution-r29-disagreement-mediation
git rev-parse HEAD
git status --short

cd backend
python -m compileall -q app run_r29_live.py scripts/r29_machine_verdict.py

python -m pytest -q \
  tests/test_r29_disagreement_mediation.py \
  tests/test_r28_authenticated_member_principal.py \
  tests/test_r28_durable_approval_continuation.py
```

Then:

```bash
cd ../frontend
npm run typecheck
npm run build
npx playwright test e2e/r28-collective-decision-surface.spec.ts --project=chromium
```

Fix only real current-HEAD defects.

Do not weaken:

- `NON_REGRESSING_PARETO_BOUNDARY_WITH_STRICT_IMPROVEMENT`;
- renewed two-member consent;
- core `collective_mutation_gate` mediation lock;
- preference-driven round-1 proof;
- external-Agent proof.

## Codex Phase B — run the strike now

Use the already-working local WB2api/provider setup.

Run:

```bash
cd backend
python run_r29_live.py --full-r29
```

Interpret the exit code literally:

- `0` — R29 machine verdict is PROVEN;
- `2` — setup failed before Agent;
- `3` — causal live strike failed;
- `4` — strike reached the verifier but R29 is not PROVEN.

Do not relabel 2/3/4 as success.

## If the mediator cannot open round 2

If output status is:

`MEDIATOR_DID_NOT_OPEN_RENEWED_ROUND`

inspect only:

- the mediator AgentRun;
- its tool steps;
- the persisted mediator clarification;
- the exact search/replan failure.

Do not start another general review.

If the bounded provider world genuinely has no discoverable non-regressing compromise, improve the **test world**, not the machine verdict:

- use a provider-backed real candidate;
- keep real Place/provider identity;
- keep canonical opening/cost/mobility authority;
- never inject a hand-built proposal into the Agent;
- never tell the Agent the desired compromise ID.

The R29 success path requires the Agent to discover and propose the better future through normal tools.

A truthful `UNRESOLVED` remains valid product behavior, but it is not the preferred R29 PROVEN demonstration.

## On PROVEN

The harness should leave:

- `REVOLUTION_R29_LIVE_DISAGREEMENT_MEDIATION_RESULT.md`
- `output/revolution-r29-live-20261005/R29_MACHINE_VERDICT.json`

Commit those together with only any real product fixes required by the strike.

Verify the generated JSON says:

```text
summary.overall = PROVEN
```

Then **stop R29**.

No R29.1.
No Checkpoint D/E.
No additional receipt pass.

## Revolution intent

The target is not more infrastructure.

The target is one real causal proof that CityNexus can do this:

> two authenticated travelers independently prefer different grounded futures; an external Agent recognizes the conflict, creates a genuinely better future without stealing authority, the same people renew consent, and autonomous execution resumes only after they converge.

Run that now.
