# Revolution Relay — R29 after Codex Phase 3

## Baton owner

**Codex: validate the tightened R29 authority model, add the missing UI contract, then run one real disagreement-mediation strike.**

Branch:

`gpt/revolution-r29-disagreement-mediation`

GPT relay HEAD at this handoff:

`69331d107a33f93646afac2d1f1c9cc073d4d43a`

The previous Codex push was:

`fc31b22f85f45522e540d58a98999506c81034d2`

That push was useful and accepted as **Phase 2/3 progress**, not as R29 closure. It added:

- an HTTP disagreement integration fixture;
- `MEDIATION_NO_PROGRESS`;
- progress-gate tests;
- authority-envelope inheritance coverage.

No R29 live result or R29 machine verdict existed at that push.

## What GPT found after the Codex push

The Codex progress gate was directionally correct, but three live-product authority seams remained.

### 1. A regenerated row could still look too much like progress

A proposal id is not a new social future.

GPT tightened `mediation_progress_gate` so:

- same place/tag shape is not new merely because it has a new proposal id;
- the gate compares against the strongest previous unacceptable-member boundary instead of the union of different losers;
- a third option that still sacrifices one traveler cannot look like progress simply because the two old options sacrificed different travelers;
- same-shape "improvement" fails closed until CityNexus carries an explicit changed-world-fact epoch.

Commits include:

- `70c72ca2806d9fc2578ba1a156659ec9d4afd6ab`
- `aa378fb1b136ee20974b8e090a64ceb68e2120c5`

### 2. A fair compromise was still at risk of becoming AI social authority

After explicit member disagreement, the server may later classify a new option as `COMPROMISE_AVAILABLE`.

That is recommendation evidence, not renewed consent.

GPT changed the product so:

- mediator missions cannot execute active-reality mutation tools before a later collective round resolves;
- the rule is enforced by Gateway, not only by the prompt;
- a new fair compromise is allowed to open a fresh `WAITING_FOR_MEMBERS` round even when the current algorithmic classification is `COMPROMISE_AVAILABLE`;
- the required member set is inherited from the original disagreement, not recomputed away;
- the fresh round carries policy:
  `POST_DISAGREEMENT_REQUIRES_RENEWED_MEMBER_CONSENT`.

Relevant commits:

- `c0589fbce1204bad59a852509f72bf522a2e29f0`
- `d531bb7ad41c4349d05d0d3b4c4231edec4a3fc3`
- `69de199daaa70ccdb980e56f8bd7870416b94cba`
- `b1e5991d4951f2442558aef19d91cdd83adc56bb`

### 3. Mission-scoped denial was not strong enough

A second Agent mission could otherwise try to route around the mediator.

GPT promoted unresolved disagreement to a **Journey-level social-authority lock**.

While a mediation lineage is unresolved:

- candidate search/acquisition/generation/replanning remains allowed;
- `request_collective_decision` remains allowed;
- `conclude_recovery(UNRESOLVED)` remains allowed;
- active-reality mutations are denied from **any Agent mission**, not merely the mediator child.

The lock clears only when the mediator descendant collective round reaches server-owned `RESOLVED`.

Relevant commits:

- `737210fd5c1294c43ec0012a9e980dd3b62d77ab`
- `3c8c751012d1214ffa6a1b3de2c989bb53b52152`

### 4. Preference non-mutation is now machine-provable

The mediator intent now persists the required members' journey-scoped preference baseline.

This lets a final verifier compare mediation-start state against closure state instead of trusting prose.

Relevant commits:

- `652acff32b514fd110c8cbe98ef0b24b53de5e99`
- `dc3dde5facf97d27bf5cce7b8a73cf2075905ae2`

### 5. GPT already added the R29 machine verifier

New:

`backend/scripts/r29_machine_verdict.py`

Latest verifier commit:

`69331d107a33f93646afac2d1f1c9cc073d4d43a`

It reuses the complete R28 verifier and additionally proves:

- genuine round-1 disagreement;
- distinct authenticated round-1 principals;
- no disputed round-1 proposal was laundered into the final result;
- real external mediator AgentRun;
- no pre-consent active-reality mediator mutation;
- final accepted proposal is an improved mediation option;
- JourneyMember preferences still match the mediation baseline;
- same relevant members authenticated again on round 2;
- Journey-level disagreement lock is actually released;
- all inherited R28 approval/C4/execution-truth invariants remain PROVEN.

Do not replace this with a prose checklist.

## Phase A — run only the tightened focused gates

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

If a focused failure exposes a real defect, fix it on this branch.

Do not weaken:

- Journey-level mediation lock;
- renewed member consent;
- same-shape no-progress refusal;
- member preference baseline;
- R28 same-run approval continuation.

Do not start a broad historical test expedition before these pass.

## Phase B — finish the UI contract

The product code already surfaces `collective-mediation`.

Add/extend Playwright coverage so the actual traveler surface proves:

1. member A selects option A;
2. member B selects option B;
3. UI explicitly says the members disagree and the Agent is mediating;
4. no old option is displayed as a winner;
5. after mediator progress, round 2 returns as a fresh N/M collective decision;
6. the new improved proposal is visibly present;
7. the UI does not claim it was already accepted;
8. after both members select the new compromise, the normal approval surface appears later in the causal chain.

Keep 360/390/412 px usable. Do not redesign unrelated UI.

Run:

```bash
cd frontend
npm run typecheck
npm run build
npx playwright test <R29_SPEC> --project=chromium
```

## Phase C — one real external-Agent strike

Use one fresh disposable DB.

Reuse the known-working WB2api/Hermes-compatible external Agent path. Do not turn this into provider research.

Required causal sequence:

```text
real external Agent
  -> sees shared Journey + separate member preferences
  -> discovers grounded human trade-off
  -> request_collective_decision round 1
  -> signed OWNER selects A
  -> signed ADMIN selects B
  -> MEDIATION_REQUIRED
  -> mediator child
  -> real external Agent resumes mediator child
  -> search/replan using normal CityNexus tools
  -> materially new + measurably improved grounded option surface
  -> request_collective_decision round 2
  -> POST_DISAGREEMENT_REQUIRES_RENEWED_MEMBER_CONSENT
  -> same relevant signed members answer again
  -> both select the new compromise
  -> server-resolved child
  -> real external Agent reaches accept_replan
  -> approval boundary
  -> same AgentRun WAITING_FOR_APPROVAL
  -> signed authorized approval
  -> deterministic same-run continuation
  -> new compromise ACCEPTED exactly once
```

The mediator must not receive:

- a hand-selected compromise proposal id;
- member answers;
- a prescribed tool sequence.

You may choose a bounded setup world where a real third compromise exists. Do not invent facts merely to make the verdict green.

## Phase D — machine verdict

Use the **final post-round-2 AgentRun id**:

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

Read every failed verdict item if it is not PROVEN.

Do not edit the JSON.

Do not patch around a failed causal proof with prose.

## Phase E — final delivery

Commit:

- `REVOLUTION_R29_LIVE_DISAGREEMENT_MEDIATION_RESULT.md`
- generated `R29_MACHINE_VERDICT.json`
- focused backend test evidence;
- R29 Playwright contract;
- bounded replay instructions;
- only real product fixes required by the strike.

The report must state separately:

- round-1 disagreement proven: yes/no;
- distinct authenticated principals: yes/no;
- real external mediator: yes/no;
- materially improved decision surface: yes/no;
- renewed human consent: yes/no;
- mediator mutation before consent: expected NO;
- preference mutation by mediation: expected NO;
- final same-run approval continuation: yes/no;
- physical travel: NOT PROVEN unless independently attested.

## Stop rule

If R29 machine verdict is PROVEN, **stop R29**.

Do not create R29.1, Checkpoint D/E, or another audit pass.

If not PROVEN, return the single causal blocker and the exact machine-verdict item.

## Revolution intent

The goal is not "the Agent found a mathematically fair option."

The goal is:

> two people disagree; CityNexus understands that disagreement as a social-authority boundary, creates a genuinely better grounded choice, gives authority back to the same people, and only then continues autonomous execution.

That is the R29 Revolution.
