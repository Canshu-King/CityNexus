# R30 Final Relay — Run the Causal Strike, Fix Only Real Failures, Close on Machine PROVEN

## Branch

\`gpt/revolution-r30-consent-epoch-shock-recovery\`

Remote HEAD before this relay:

\`c21c44f62d101537bbb99faf359e085e85f21856\`

Use the current remote HEAD if newer.

## Status correction

Codex again reported "tested and pushed", but GitHub showed no Codex commit beyond GPT's prior relay.

Do not spend another turn explaining the no-op push.

GPT has continued the engineering work directly so Codex can now focus on local execution and real integration defects.

---

# What GPT added in this round

## 1. Targeted server-owned provider shock

Commits include:

- \`c9de11c3de3f1e839e176ee87e3e8eee46e4d0a0\`
- \`fe0a103547a32ceffe3f5b39f40b094c063091bb\`
- \`d4e5c612b001d72a39fcc92e3406afd75158d857\`
- \`61fbdfb6ada940ade43b74952819425d1f923964\`

The provider fixture can now name one existing canonical Place as a bounded physical disruption scope.

The server:

- validates that the Place exists;
- validates that it belongs to the Journey city;
- creates the trusted Event itself;
- assigns \`PROVIDER_VERIFIED\`;
- emits a \`CLOSURE\`;
- keeps upstream fixture transport truthfully labelled REPLAY;
- does not let the harness assign an Event id or trusted provenance.

The world epoch recognizes:

- exact Activity identity;
- equivalent physical Place / CityService identity across plan-local Activity rows;
- explicit \`scope_place_id\` / \`target_place_id\`.

The harness now targets an actual \`fit_subject_place_id\` from the renewed-consent option.

Therefore the R30 shock is causally about the future the humans consented to.

## 2. Durable stale-authority denial evidence

Commits include:

- \`fae0073c48d345342eb51b2620d09c2483d9fcd9\`
- \`008a71e3b649d8168d4e0bca63208ea30366fadb\`
- \`de984f1264ffc386cc375092ba7831826ce9aa6a\`

Both plan-selection and replan-accept mutation callers now persist:

\`collective.mutation.denied\`

before returning 409.

For a world-stale denial the audit carries:

- semantic E resolved/current;
- material W resolved/current;
- mutation kind;
- target PlanVersion;
- proposal id where relevant;
- machine reason code.

The harness now spends old E1/W1 through the normal public accept route.

It requires:

\`COLLECTIVE_CONSENT_WORLD_EPOCH_STALE\`

and verifies the old proposal did not become ACCEPTED.

This is durable product evidence, not harness narration.

## 3. Unrelated provider churn live control

Commit:

\`8e3e41c2a809569b2b3386d5424c185178dd87ca\`

Before the material shock, the harness performs a normal unrelated provider refresh and recomputes W.

Required:

\`before_epoch == after_epoch\`

Only then does the targeted shock run.

This proves R30 is semantic staleness, not "any provider write invalidates consent."

## 4. Stale consent releases the selected-plan lock

Commits:

- \`a063a6e52c518541f8f216e8b6b9a542081c794e\`
- \`fcee94feec69b589fbdc38fa9574f51b18b3c645\`

A real state-machine deadlock was found and fixed.

Old behavior:

\`\`\`text
resolved consent exists
  -> every mutation must target old selected plan
  -> world changes
  -> old selected plan is stale and rejected
  -> every recovery plan is still rejected because it is not old selected plan
\`\`\`

That made recovery impossible.

New rule:

> only fresh resolved authority may monopolize the selected-plan mutation slot.

The old stale consent remains historical truth, but no longer blocks a new recovery future from entering current collective governance.

The old selected plan itself still receives the exact stale-consent denial.

A regression test proves a current unanimously dominant recovery candidate is not blocked by stale historical consent.

## 5. R30 machine verifier

Commits:

- \`a2112e7d95aebd1e5e4e2e1ab10d2aee40096001\`
- \`bfed64f29f57f0c793dda93fe27f8925e42cc6db\`

File:

\`backend/scripts/r30_machine_verdict.py\`

It treats the checkpoint only as an entity/database index.

It re-reads persisted product truth for:

- E1/W1 durable binding;
- external round-1 Agent;
- external mediator;
- trusted targeted closure Event;
- core \`collective.mutation.denied\`;
- semantic E parity during W change;
- W1 -> W2 change;
- old proposal not accepted;
- external post-shock recovery Agent;
- fresh authenticated authority if required;
- E2/W2 durability if required;
- inherited R28 exactly-once closure when final run id is supplied;
- unrelated-observation stability control.

Missing tail evidence yields NOT_PROVEN, never synthetic success.

## 6. Live harness now runs through final closure

Commit:

\`c21c44f62d101537bbb99faf359e085e85f21856\`

\`backend/run_r30_live.py\` now attempts the entire causal story.

If post-shock recovery opens a fresh collective round:

1. read its newly recomputed \`required_member_ids\`;
2. choose only a uniquely best jointly acceptable grounded option;
3. submit new signed responses for exactly those members;
4. do not reuse E1 responses;
5. require the final response to create a new resolved child;
6. use the in-force Journey OWNER for approval;
7. continue through the normal durable Agent approval path.

If no fresh collective round is needed:

- use the external recovery Agent's normal approval path;
- do not manufacture human re-consent.

The harness then automatically runs the R30 machine verifier.

Exit behavior:

- 0 only when \`R30_PROVEN\`;
- 4 when the causal run progressed but machine closure is still incomplete;
- 3 on live execution failure.

---

# Codex first action

Synchronize exactly once.

\`\`\`bash
git fetch origin
git checkout gpt/revolution-r30-consent-epoch-shock-recovery
git reset --hard origin/gpt/revolution-r30-consent-epoch-shock-recovery
git rev-parse HEAD
git status --short
\`\`\`

Then run only the narrow validation first.

\`\`\`bash
cd backend

python -m compileall -q \
  app \
  run_r30_live.py \
  scripts/r30_machine_verdict.py

python -m pytest -q \
  tests/test_r29_disagreement_mediation.py \
  tests/test_r28_authenticated_member_principal.py \
  tests/test_r28_durable_approval_continuation.py
\`\`\`

If GPT introduced a real syntax/test defect, fix it narrowly and commit it.

Do not reopen R28 or R29.

Do not do a repository-wide review.

---

# Then run the actual Revolution strike

\`\`\`bash
python run_r30_live.py --full-r30
\`\`\`

The harness itself now runs the verifier.

Inspect:

\`output/revolution-r30-live-20261006/R30_LIVE_CHECKPOINT.json\`

and:

\`output/revolution-r30-live-20261006/R30_MACHINE_VERDICT.json\`

## If exit = 0 and overall = PROVEN

R30 is complete.

Write only:

\`REVOLUTION_R30_CONSENT_EPOCH_SHOCK_RECOVERY_RESULT.md\`

with:

- final remote SHA;
- exact strike command;
- external round-1 run id;
- external mediator run id;
- E1/W1;
- targeted provider Event id + scope Place;
- denial audit id;
- E2/W2 if fresh authority was required;
- external post-shock recovery run id;
- final recovery run id;
- machine summary;
- explicit truth boundary:
  - provider shock transport = server-owned deterministic REPLAY fixture;
  - external Journey Agents = configured external runtimes;
  - physical travel = NOT PROVEN.

Commit artifacts and push.

Then STOP R30.

No R30.1.

## If exit = 4

Read \`R30_MACHINE_VERDICT.json\`.

Fix only the first NOT_PROVEN / CONTRADICTED causal claim.

Examples:

### No targeted shock

Inspect:

- selected \`fit_subject_place_ids\`;
- canonical Place city;
- \`signals.created_event_ids\`;
- Event payload \`scope_place_id\`.

Do not manually insert Event rows.

### Semantic E changed during shock

Find the actual decision-surface change.

Do not reorder the machine checks just to obtain a W-stale label.

### No denial audit

The old proposal must be attempted through the normal accept route.

Do not accept direct gate invocation as closure evidence.

### Recovery plan blocked by old selected consent

That is the stale-lock regression.

The old resolved authority must be recomputed for freshness before enforcing selected-plan exclusivity.

Do not delete historical consent rows.

### No external recovery Agent

Inspect the persisted AgentRun.

Do not claim deterministic Guardian fallback as the Revolution external-agent proof.

### Fresh collective round remains WAITING

Inspect:

- current \`required_member_ids\`;
- candidate fairness/member fit;
- whether there is one unique jointly acceptable grounded choice.

If the human trade-off is still genuinely open, do not force the harness to invent consensus. Improve the recovery decision surface or report the real blocker.

### Final R28 verifier fails

Fix only the inherited exactly-once / approval / commitment / continuation defect it names.

Do not weaken R28 to close R30.

---

# Revolution stop condition

R30 is not about passing more tests.

R30 is complete only when the machine can prove this product truth:

\`\`\`text
people give renewed authority E1/W1
  -> unrelated evidence churn does nothing
  -> a decision-material physical fact changes
  -> E stays semantically the same
  -> W changes
  -> old authority is refused at the real mutation boundary
  -> stale consent stops monopolising recovery
  -> an external Agent recovers the Journey
  -> only currently relevant humans are asked again if needed
  -> fresh E2/W2 authority is created if needed
  -> exactly one recovery mutation continues the Journey
\`\`\`

That is the Revolution boundary.

Do not turn it back into a receipt project.
