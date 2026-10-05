# Revolution Relay — R29 Final Strike After UI Validation

## Current state

Binding branch:

`gpt/revolution-r29-disagreement-mediation`

GPT-reviewed code HEAD before this baton:

`9ab4e9e92ee5f8309b563ef0c2778e7d3a92cf89`

Codex's last push was:

`05657a8576d613f2ae2f9365a1876d655f49a60f`

Codex's push is accepted as useful focused progress, but **R29 is not closed**. There is still no committed:

- `REVOLUTION_R29_LIVE_DISAGREEMENT_MEDIATION_RESULT.md`
- generated `R29_MACHINE_VERDICT.json`

Do not claim closure until the live causal chain exists and the machine verdict is PROVEN.

## What GPT found in the Codex push

### Good

Codex added:

- a server-owned mediation-lineage fallback in `gateway.py`;
- a Playwright scenario for disagreement -> mediation -> renewed round -> approval.

The lineage fix is directionally correct and keeps the Journey-level lock tied to durable `source_mission_id`.

### UI false green that GPT corrected

The first R29 UI test jumped from **one round-2 response** directly to approval.

That bypassed the exact R29 invariant we are trying to prove: the same relevant members must renew consent after explicit disagreement.

GPT replaced the test so it now proves:

1. round 1 reaches disagreement;
2. mediator auto-resumes;
3. the fresh decision surface contains the old options plus a materially new compromise;
4. OWNER selects the compromise;
5. UI remains `1/2 WAITING_FOR_MEMBERS` and no approval appears;
6. the session changes to the ADMIN signed principal;
7. ADMIN independently selects the compromise;
8. only then does the resolved child reach the approval boundary;
9. ADMIN can see approval but cannot approve an OWNER-only change;
10. the session returns to OWNER;
11. OWNER approval sends the OWNER bearer and continuation resumes.

Commit:

`8492e5347b50845ddfd9720f6504e6204985a5a2`

### Fairness progress was still too permissive

The progress gate previously allowed a candidate when one fairness metric improved even if another protected fairness metric regressed badly.

GPT tightened it to:

`NON_REGRESSING_PARETO_BOUNDARY_WITH_STRICT_IMPROVEMENT`

A candidate must:

- not reduce the best prior minimum-member-fit boundary;
- not increase the best prior maximum-regret boundary;
- not increase the best prior unacceptable-member count;
- and strictly improve at least one of those boundaries.

Commit:

`38641a13d53c59c08657fc464c2323e3f908e90e`

Regression test:

`7194c117b63dfc5865f516196ea82ea240379b1c`

### External mediator prompt precedence was ambiguous

The generic Agent rule said `HUMAN_TRADEOFF_REQUIRED -> request_collective_decision`.

For a mediator child, that could cause the external model to immediately re-ask the unchanged first-round questionnaire and hit `MEDIATION_NO_PROGRESS`.

GPT changed prompt precedence:

- ordinary shared mission: trade-off may immediately go to collective decision;
- disagreement mediator: **first create measurable decision-surface progress** using search/fact/planning/replan tools;
- only after CityNexus exposes progress may it open the renewed member round.

Commit:

`9ab4e9e92ee5f8309b563ef0c2778e7d3a92cf89`

## Phase A — validate current HEAD, not the old Codex SHA

Run only these first:

```bash
git fetch origin
git checkout gpt/revolution-r29-disagreement-mediation
git reset --hard origin/gpt/revolution-r29-disagreement-mediation
git rev-parse HEAD
git status --short

cd backend
python -m compileall -q app scripts/r29_machine_verdict.py

python -m pytest -q \
  tests/test_r29_disagreement_mediation.py \
  tests/test_r28_authenticated_member_principal.py \
  tests/test_r28_durable_approval_continuation.py
```

Frontend:

```bash
cd ../frontend
npm run typecheck
npm run build
npx playwright test e2e/r28-collective-decision-surface.spec.ts --project=chromium
```

Do not weaken the new two-principal UI test if it fails. Fix the actual API/client timing or state projection.

Do not loosen the non-regressing progress policy to make fixtures easier.

## Phase B — one real R29 strike

Do not add another synthetic checkpoint.

Use a fresh disposable DB and the already-working external Agent chain.

Required causal chain:

```text
real external Agent
  -> grounded round-1 trade-off
  -> request_collective_decision
  -> signed member A chooses option A
  -> signed member B chooses option B
  -> MEDIATION_REQUIRED
  -> Journey-level social-authority lock active
  -> mediator child
  -> real external Agent resumes mediator
  -> search / acquire / plan / replan through normal tools
  -> materially new grounded candidate
  -> non-regressing fairness boundary + strict improvement
  -> request_collective_decision round 2
  -> POST_DISAGREEMENT_REQUIRES_RENEWED_MEMBER_CONSENT
  -> signed member A selects the improved compromise
  -> still WAITING_FOR_MEMBERS
  -> signed member B independently selects the same compromise
  -> RESOLVED
  -> social-authority lock clears
  -> resolved child
  -> real external Agent calls accept_replan
  -> approval boundary
  -> signed authorized approval
  -> same AgentRun deterministic continuation
  -> improved compromise ACCEPTED exactly once
```

The mediator must not be handed:

- proposal IDs;
- member answers;
- the desired compromise;
- a scripted tool sequence.

The setup may deliberately choose a bounded provider-backed world where a real third compromise is discoverable.

## Phase C — machine closure

Use the final resolved-child AgentRun:

```bash
cd backend
python scripts/r29_machine_verdict.py \
  --run-id <FINAL_AGENT_RUN_ID> \
  --output R29_MACHINE_VERDICT.json
```

Required:

```text
summary.overall = PROVEN
exit code = 0
```

If the verdict is not PROVEN, report only the exact failed verdict item and causal blocker. Do not start a new review pass.

## Final delivery

Commit:

- `REVOLUTION_R29_LIVE_DISAGREEMENT_MEDIATION_RESULT.md`
- generated `R29_MACHINE_VERDICT.json`
- the validated Playwright test;
- any real fixes required by the live strike;
- bounded replay instructions.

Do not commit secrets, bearer tokens, local provider config, or disposable DBs.

## Stop rule

If the R29 machine verdict is PROVEN, stop R29.

No R29.1.
No Checkpoint D/E.
No evidence treadmill.

The Revolution target is now very precise:

> CityNexus must not merely notice disagreement. It must improve the choice set without stealing social authority, return the improved future to the same people, and only execute after they genuinely converge.
