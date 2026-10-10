# R30 Relay — Validate GPT Live Harness, Then Finish Machine-PROVEN Closure

## Current branch

`gpt/revolution-r30-consent-epoch-shock-recovery`

GPT has continued advancing the branch after repeated Codex no-op pushes.

Read current remote HEAD, not an older local copy.

## New product changes since the previous relay

### Physical shock relevance is no longer Activity-ID-only

Commit:

`4e56e3b7b9802a1575efbb37a58a34f1880a02ba`

The material-world basis now treats a Journey Event as relevant when it intersects the selected future by:

- exact candidate Activity id;
- the same physical Place / CityService through another plan-local Activity row;
- an explicit server-owned payload Place identity.

This matters because provider events normally target the ACTIVE PlanVersion, while renewed consent still points at a CANDIDATE PlanVersion.

R30 must follow physical meaning, not plan-local row identity.

### Duplicate factual churn does not automatically stale consent

The same commit semantically deduplicates projected Event / ProviderObservation facts.

Two equivalent provider retries must not change the world epoch merely because the database has two rows.

### Regression test upgraded

Commit:

`947359aac7e38090a371b1d8350c95e227e124e7`

The R30 shock test now deliberately uses:

- one Activity row on the ACTIVE base plan;
- another Activity row on the selected CANDIDATE plan;
- both rows point at the same physical Place;
- the shock targets the ACTIVE row.

The candidate consent must still become world-stale.

That is the real product contract.

## New R30 live checkpoint harness

Commits:

- `2f7ebf055e31c062c3a85c249f05cb4889d4fd94`
- `db62cb819640471a4b68f23dd57714ad4ff08891`

File:

`backend/run_r30_live.py`

The second commit fixes an important false-positive risk: W1 and W2 are now projected over the exact same fit-subject scope.

## What the harness does now

```text
fresh R28 setup
  -> real configured round-1 external Agent
  -> genuine server-fit-driven disagreement
  -> real configured external mediator
  -> materially improved grounded future
  -> same relevant authenticated Journey principals renew consent
  -> persist semantic E1 + material-world W1
  -> STOP before consent is consumed

  -> change CitySignalFixture to DISRUPTED
  -> run normal server-owned signal ingestion seam
  -> trusted provider-replay Events are produced
  -> W2 is recomputed
  -> core mutation gate must return
       COLLECTIVE_CONSENT_WORLD_EPOCH_STALE
     while diagnostic hard feasibility is held true
  -> normally resume the old resolved child / approval path
  -> assert old selected proposal was NOT accepted

  -> launch a fresh configured external recovery Agent
  -> checkpoint whether it opened a fresh collective round
```

It writes:

`output/revolution-r30-live-20261006/R30_LIVE_CHECKPOINT.json`

## Truth boundary

The shock path currently uses the server-owned deterministic provider replay fixture.

That means:

- trusted Event creation is performed by the normal CityNexus signal pipeline;
- the harness does NOT hand-write Event rows;
- event provenance may be PROVIDER_VERIFIED inside the bounded provider adapter;
- upstream transport provenance remains REPLAY;
- do not describe it as a live public-network weather/traffic capture.

The external Journey Agents must still be the real configured runtime.

This is a deliberate truthful boundary, not a weakness to hide.

---

# Codex: first action

Synchronize.

```bash
git fetch origin
git checkout gpt/revolution-r30-consent-epoch-shock-recovery
git reset --hard origin/gpt/revolution-r30-consent-epoch-shock-recovery
git rev-parse HEAD
git status --short
```

Then run only:

```bash
cd backend

python -m compileall -q app run_r30_live.py

python -m pytest -q   tests/test_r29_disagreement_mediation.py   tests/test_r28_authenticated_member_principal.py   tests/test_r28_durable_approval_continuation.py
```

GPT could not execute these locally.

If something fails, repair the first real defect.

Do not revert the contracts to make an old test happy.

---

# Then run the checkpoint strike

```bash
python run_r30_live.py --full-r30
```

Acceptable checkpoint outcomes before final completion:

- `R30_RECOVERY_WAITING_FOR_FRESH_MEMBERS`
- `R30_RECOVERY_AGENT_RAN`

Anything before the W1 -> W2 core stale check is a blocker.

## If it fails before W1 is stored

Inspect only:

- final renewed-response code path;
- `material_world_basis`;
- `material_world_epoch` persistence.

Do not reopen R29.

## If W1 == W2 after provider replay shock

Inspect:

- signal-pipeline created Event ids;
- Event affected Activity;
- physical Place / CityService identity;
- selected candidate plan physical locations.

Do not manually alter W2.

Do not write Event rows from the harness.

## If semantic epoch stales before world epoch

Find what actual semantic decision input changed.

The post-consent provider shock should normally alter physical evidence, not member preferences or the option surface.

Do not reorder checks just to force a world-stale label if semantic reality truly changed first.

## If the normal old-consent continuation still ACCEPTS

This is a real authority bug.

Fix the mutation path so all acceptance routes pass through `collective_mutation_gate`.

Do not special-case `run_r30_live.py`.

## If external recovery does not act

Inspect the real AgentRun/tool trace.

Do not silently substitute deterministic recovery and call R30 external-agent recovery proven.

A deterministic fallback may remain a product fallback, but the Revolution live claim requires a configured external recovery AgentRun.

---

# Finish the second half

The GPT harness intentionally stops at a checkpoint after launching the post-shock external recovery Agent.

Codex now owns the final closure.

## Case A — fresh human trade-off remains

If the recovery creates a new `WAITING_FOR_MEMBERS` collective round:

1. record its recomputed `required_member_ids`;
2. prove they came from current decision relevance;
3. submit new authenticated responses;
4. prove none were copied from E1;
5. resolve the round;
6. persist E2 + W2;
7. resume the server-owned child;
8. use the normal OWNER approval path;
9. accept exactly one recovery proposal.

## Case B — new world has one clear acceptable future

If the recovery is unambiguous under existing authority:

1. do not manufacture a fresh collective round;
2. prove why no renewed member choice was needed;
3. continue through normal approval / mutation boundaries;
4. accept exactly one recovery future.

Either path is valid.

R30 is about selective authority, not forcing a questionnaire.

---

# Machine verifier

Create:

`backend/scripts/r30_machine_verdict.py`

Required claims:

1. R29 inherited social-authority invariants remain PROVEN.
2. real external round-1 Agent is evidenced.
3. real external mediator Agent is evidenced.
4. renewed authenticated consent produced E1/W1.
5. selected proposal was still pending before shock.
6. shock came through server-owned provider ingestion.
7. W2 differs from W1 for a decision-material reason.
8. semantic E did not change merely from irrelevant provider churn.
9. core mutation returned `COLLECTIVE_CONSENT_WORLD_EPOCH_STALE`.
10. old proposal did not become ACCEPTED.
11. no sibling consumed E1/W1 authority.
12. no superseded older consent resurrected.
13. real external post-shock recovery Agent is evidenced.
14. completed execution truth and protected commitments survived.
15. current decision-relevant member scope was recomputed.
16. if fresh responses were required, they are new authenticated responses.
17. E2/W2 were durably stored when fresh human authority was required.
18. exactly one recovery proposal was accepted.
19. the Journey continued.
20. unrelated observation churn leaves otherwise-current consent valid.

The verifier should inspect persisted facts, not trust harness prose.

---

# Final artifacts

Only after machine PROVEN:

- `output/revolution-r30-live-20261006/R30_MACHINE_VERDICT.json`
- `REVOLUTION_R30_CONSENT_EPOCH_SHOCK_RECOVERY_RESULT.md`

Then commit and push.

No R30.1.

## Revolution principle

The product property being proved is:

> human authority is bound to meaningfully relevant reality, not to a permanent proposal token; CityNexus can notice when that authority expires, refuse to spend it, recover autonomously, and ask people again only when their judgment is actually needed.
