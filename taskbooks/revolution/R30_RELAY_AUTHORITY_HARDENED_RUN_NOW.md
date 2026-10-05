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
