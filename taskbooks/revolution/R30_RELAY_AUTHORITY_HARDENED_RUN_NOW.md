# R30 Relay — Authority Hardened; Run Now, Fix Only the First Real Failure

## Branch

\`gpt/revolution-r30-consent-epoch-shock-recovery\`

This relay supersedes earlier R30 taskbooks for execution order.

## Status

Codex again reported "tested and pushed", but the R30 branch still showed no Codex commit after the previous GPT relay. GPT therefore continued the product work directly.

Do not spend another cycle explaining push behavior.

Do not redesign R30.

Pull current remote HEAD and execute it.

---

# Additional authority hardening GPT completed

## A. Stale authority releases the old selected-plan lock, but cannot transfer the choice to the algorithm

Core rule now:

\`\`\`text
fresh resolved consent
  -> may bind one selected plan

stale resolved consent
  -> remains historical evidence
  -> no longer monopolizes the mutation slot

BUT

post-stale recovery with only COMPROMISE_AVAILABLE
  -> may NOT be chosen by the algorithm
  -> COLLECTIVE_STALE_CONSENT_RENEWAL_REQUIRED

post-stale recovery with current UNANIMOUS_DOMINANCE
  -> may proceed without pestering humans again
\`\`\`

Relevant commits include:

- \`7b1851495f58745fe9b0defa139fd4383f7f0ca9\`
- \`a8e4a3b4f2d597a6d59c34493e6061e4317cf232\`

This closes the opposite failure mode from the earlier stale-lock deadlock.

The product must do neither:

- deadlock behind expired consent;
- nor silently inherit authority to choose a new compromise.

## B. Successful mutation now persists its collective authority classification

\`replan.accepted\` audit now carries \`collective_authority\`.

This lets the machine verifier distinguish:

- genuinely unanimous no-reconsent recovery;
- fresh renewed human authority;
- algorithmic compromise that should not have been allowed.

## C. Verifier Case B is now strict and valid

Commit:

\`413cc2ee5b30aa2d12f3b5a2293b82bbe752be15\`

No fresh collective round is no longer automatically NOT_PROVEN.

It is PROVEN only when the final post-shock accepted mutation has a durable audit proving:

\`classification == UNANIMOUS_DOMINANCE\`

Any other no-round path remains unproven.

## D. Fresh E2/W2 child is revalidated immediately before mutation

Commits:

- \`ee8ce744fd28fa579c9aa6a1263f32fabce66b17\`
- \`2ab498ba91b9d93bafb04e30c28ec00044883374\`

Previously \`_collective_resolution_for_child\` revalidated semantic E but not physical W.

Now:

\`\`\`text
fresh human E2/W2
  -> resolved child
  -> before accept:
       recompute E
       recompute W
  -> if reality changed again:
       COLLECTIVE_CONSENT_WORLD_EPOCH_STALE
\`\`\`

A validated fresh resolved child may authorize the new recovery plan even though the old E1/W1 authority is stale.

Without a validated fresh child, a post-stale compromise remains blocked.

## E. Event acknowledgement churn no longer changes W

Commits:

- \`5f4d7008c5e15a47fc84dc8006ee0946f6dd2507\`
- \`676c55c1256be0315088b464073b3362b201a4fe\`

World epoch now treats:

\`\`\`text
DETECTED -> ACKNOWLEDGED
\`\`\`

as the same ACTIVE physical incident.

Only actual semantic incident-state changes, such as resolution, may change W.

This prevents a freshly renewed E2/W2 from expiring merely because Guardian acknowledged the same closure before final accept.

---

# Codex must now execute, not review

Synchronize:

\`\`\`bash
git fetch origin
git checkout gpt/revolution-r30-consent-epoch-shock-recovery
git reset --hard origin/gpt/revolution-r30-consent-epoch-shock-recovery
git rev-parse HEAD
git status --short
\`\`\`

Run:

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

GPT could not execute the repository in its environment because direct GitHub network access is unavailable there.

Therefore local validation is Codex's job.

If compilation or a narrow test fails:

1. fix the first real defect;
2. preserve the authority contracts above;
3. rerun the narrow command;
4. commit the fix.

No repository-wide audit.

---

# Then run the full strike

\`\`\`bash
python run_r30_live.py --full-r30
\`\`\`

The harness is expected to prove:

\`\`\`text
renewed E1/W1
  -> unrelated provider refresh leaves W unchanged
  -> targeted server-owned closure hits consent-relevant Place
  -> E remains equal
  -> W changes
  -> normal old accept route fails closed
  -> durable collective.mutation.denied exists
  -> old proposal never ACCEPTED
  -> stale authority releases old selected-plan lock
  -> external recovery Agent runs

  -> if current result is UNANIMOUS_DOMINANCE:
       no fresh human round
       normal approval/continuation
       accepted audit proves unanimous authority

  -> otherwise:
       fresh current collective authority
       authenticated relevant-member responses
       E2/W2
       resolved child revalidates E2/W2 again
       normal OWNER approval
       exactly-once continuation

  -> R30 machine verdict
\`\`\`

## Exit handling

### Exit 0 / overall PROVEN

R30 is complete.

Write only:

\`REVOLUTION_R30_CONSENT_EPOCH_SHOCK_RECOVERY_RESULT.md\`

Commit the result + live evidence + machine verdict.

Push.

STOP.

No R30.1.

### Exit 3

This is a causal live failure.

Fix only the first failure.

### Exit 4

Read:

\`output/revolution-r30-live-20261006/R30_MACHINE_VERDICT.json\`

Fix only the first NOT_PROVEN / CONTRADICTED claim.

Do not weaken the verifier.

---

# Non-negotiable Revolution boundaries

Do not:

- delete old consent to escape a stale-authority problem;
- manually edit E/W hashes;
- directly insert the trusted closure Event;
- treat DETECTED -> ACKNOWLEDGED as new physical reality;
- let COMPROMISE_AVAILABLE inherit authority after E1/W1 became stale;
- claim no-reconsent success without a durable UNANIMOUS_DOMINANCE mutation audit;
- reuse E1 member responses as E2;
- skip E2/W2 revalidation at the resolved child;
- substitute deterministic fallback for the required external recovery Agent;
- weaken R28 exactly-once / C4 / continuation invariants.

The R30 product truth is now precise:

> Human permission is valid only for the meaningfully relevant world it was granted in. When that world changes, expired permission neither executes nor blocks recovery. The system may continue without asking again only when the current shared decision is genuinely unanimous; otherwise fresh human authority is required and is revalidated again at the final mutation boundary.


---

# GPT addendum — CI, independent fresh authority, and denial transaction isolation

This addendum is newer than the body above.

## Fresh responses may not be manufactured by a global fairness optimum

Commits:

- \`124edfd465db00da2ac215971ad536199fad4135\`
- \`815ea5b2e5b2cf9a294b4a8ea60a9c283ffeab2d\`

The R30 harness no longer picks one globally "fair" compromise and submits that
answer for every relevant member.

For every fresh required member it now independently derives that member's
unique maximum \`effective_fit\` over grounded acceptable options.

Automated strike closure is permitted only when:

\`\`\`text
every relevant member has one unique grounded maximum
AND
all independently derived maxima are the same proposal
AND
the persisted authenticated response from each member matches its own maximum
\`\`\`

If the independent maxima differ, the harness must stop rather than manufacture
consensus. That is a real unresolved human trade-off, not a test failure to
paper over.

The machine verifier independently recomputes this property from persisted
candidate options, member fits, responses and authenticated response audits.

## A denied mutation may not burn an approval receipt

Commits:

- \`432ff691c5dd6becca6604f44fbcd9f7ca545452\`
- \`92b41ba7e324f9102cc98d926e3c0ea0d6f68902\`

A transaction bug was found after inspecting the Agent approval flow.

\`consume_action_approval()\` flushes \`APPROVED -> CONSUMED\` before the actual
replan reaches the collective gate. The earlier denial audit helper committed
on that same Session, so it could accidentally make this true:

\`\`\`text
mutation rejected
BUT
approval receipt permanently CONSUMED
\`\`\`

That is now forbidden.

The denial helper now:

\`\`\`text
capture immutable denial facts
-> rollback the refused action transaction
-> open an independent Session
-> persist only collective.mutation.denied
-> commit only that audit
\`\`\`

A regression test proves that the approval remains \`APPROVED\` with no
\`consumed_at\`, while the denial audit survives durably.

## Branch-local narrow CI now exists

Workflow:

\`.github/workflows/r30-narrow.yml\`

Initial runs exposed only a CI packaging mistake: this backend is a flat-layout
application, not an editable setuptools package.

The workflow has been corrected to install the existing locked environment with:

\`uv sync --extra dev --no-install-project\`

It then runs:

\`\`\`text
python -m compileall -q app run_r30_live.py scripts/r30_machine_verdict.py

python -m pytest -q
  tests/test_r29_disagreement_mediation.py
  tests/test_r28_authenticated_member_principal.py
  tests/test_r28_durable_approval_continuation.py
\`\`\`

A green CI run is evidence only for narrow deterministic regression safety.
It is NOT R30 live proof and does not replace:

\`python run_r30_live.py --full-r30\`

## Codex execution order

1. Pull the latest remote branch, not any SHA named earlier in this taskbook.
2. Check the latest \`R30 narrow validation\` GitHub Actions result.
3. If red, inspect the first failing compile/test assertion and fix exactly that.
4. If green, do not rerun a broad suite.
5. Run \`python run_r30_live.py --full-r30\` in the configured local external-Agent environment.
6. Fix only the first causal live failure / first machine-verdict blocker.
7. Stop only at \`R30_MACHINE_VERDICT.summary.overall == PROVEN\`.


---

# GPT addendum — E1 authority is now real, and push must be machine-proven

This addendum supersedes all older execution/push instructions in this relay.

## Why any old local R30 strike must be rerun

The canonical R30 branch advanced after the previous reported Codex push.

More importantly, R30 authority semantics changed:

- post-shock E2/W2 was already required to prove independent authenticated
  member convergence;
- pre-shock E1/W1 now has the same rule.

The older harness selected one global-fairness compromise and submitted it for
every member during the renewed pre-shock round. That could create a signed
record without proving that the automated principals independently converged.

That is no longer allowed.

Current rule:

    mediator may improve / narrow the grounded decision surface
    -> each relevant member gets its own server-grounded fit
    -> each member must have one unique acceptable maximum
    -> those independent maxima must be the same proposal
    -> each authenticated persisted response must match that member's maximum
    -> only then may E1/W1 be called renewed collective authority

If the maxima still differ, stop. Do not restore the global-fairness shortcut.
That means the human trade-off is still real.

The same independent-authority helper and the same machine-verifier concept now
cover both E1/W1 and E2/W2.

A regression test explicitly proves that the R30 harness refuses to manufacture
consensus when two members independently prefer different futures.

## Current deterministic validation

The branch-local GitHub Actions R30 narrow validation is green with:

    48 passed / 0 failed

Do not spend local Codex time repeating the same broad deterministic review.

## PROVEN now generates the closeout automatically

A successful:

    python run_r30_live.py --full-r30

now writes all required closeout content from machine truth:

- output/revolution-r30-live-20261006/R30_LIVE_CHECKPOINT.json
- output/revolution-r30-live-20261006/R30_MACHINE_VERDICT.json
- REVOLUTION_R30_CONSENT_EPOCH_SHOCK_RECOVERY_RESULT.md

Do not hand-write a competing result document.

## A push is not complete until the remote SHA is proven

New verifier:

    backend/scripts/r30_delivery_gate.py

After the PROVEN strike, commit the three generated artifacts and push them to
the canonical R30 branch.

Exact delivery sequence:

    git fetch origin
    git checkout gpt/revolution-r30-consent-epoch-shock-recovery
    git reset --hard origin/gpt/revolution-r30-consent-epoch-shock-recovery
    git rev-parse HEAD
    git status --short

    cd backend
    python run_r30_live.py --full-r30

Only continue if the command exits 0 and the machine verdict says PROVEN.

Then:

    cd ..
    git add \
      output/revolution-r30-live-20261006/R30_LIVE_CHECKPOINT.json \
      output/revolution-r30-live-20261006/R30_MACHINE_VERDICT.json \
      REVOLUTION_R30_CONSENT_EPOCH_SHOCK_RECOVERY_RESULT.md

    git commit -m "r30: prove consent-epoch shock recovery live"
    git push origin HEAD:refs/heads/gpt/revolution-r30-consent-epoch-shock-recovery

Then run:

    cd backend
    python scripts/r30_delivery_gate.py

Success is not "git push returned 0".

Success is the delivery-gate JSON proving all of these simultaneously:

    ok == true
    branch == gpt/revolution-r30-consent-epoch-shock-recovery
    machine_verdict_overall == PROVEN
    checkpoint_status == R30_PROVEN
    working_tree_clean == true
    all three artifacts tracked == true
    remote_matches_local == true
    remote_head == local_head

If remote_matches_local is false, the delivery is not complete.

If origin advanced while the local strike was running, do not force-push and do
not simply move old evidence onto new code. Pull the new code and rerun the
causal strike because live evidence is code-version specific.

## If the new E1 rule blocks the strike

If the strike stops because the pre-shock mediator round still leaves different
independent member maxima:

Do not weaken the authority rule.

Do not make every member submit the global fairness winner.

Instead fix the scenario / normal mediator path so the external Agent produces
a genuinely grounded improved future on which the relevant members
independently converge, then rerun.

That is the Revolution contract:

A signed response is not proof that the system respected human authority if the
test harness chose the answer for the human.

## Stop condition

R30 closes only when:

    R30_MACHINE_VERDICT.summary.overall == PROVEN

and:

    r30_delivery_gate.py -> ok == true

At that point STOP. Do not create R30.1.
