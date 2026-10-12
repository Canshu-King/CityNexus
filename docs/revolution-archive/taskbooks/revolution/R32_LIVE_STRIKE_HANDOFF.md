# R32 Live Strike Handoff — Concurrent Shock, Independent Agents, One Reality

## Read first

Base this work on the latest remote head of:

    gpt/revolution-r32-autonomous-recovery-mesh

Do not reset to the original Codex R32 commit.

GPT post-push hardening has already closed several deterministic holes:

- recovery reality no longer changes merely because an equivalent Event gets a new UUID;
- DETECTED -> ACKNOWLEDGED workflow churn does not create a new RecoveryEpoch;
- a material severity/scope/incident change still does;
- recovery binding validation recomputes current reality itself;
- one OPEN epoch is enforced in ORM tests as well as production schema;
- old epoch authority/proposals leave the current executable surface on supersession;
- losing concurrent epoch creation no longer performs a whole-Session rollback;
- approval creation checks current recovery epoch;
- final mutation rechecks recovery epoch after collective/world preflight;
- internal Gateway calls bind the exact AgentRun instead of guessing the latest run for a mission;
- recovery proposals are stamped with epoch at row creation and carry source_agent_run_id;
- runtime and approval continuation preserve RECOVERY_EPOCH_SUPERSEDED as a typed terminal result;
- legacy SQLite pending-action CHECK is upgraded to allow SUPERSEDED;
- human and algorithmic decision-epoch provenance are now distinct and mode-accurate.

Do not reopen those points unless the remote CI or the live strike falsifies them.

## Status entering this strike

R30 live recovery: already proven under its documented truth boundary.

R31 E/W/S integrity: deterministically closed and remotely gated.

R32: deterministic core only.

Therefore R32 must NOT be called PROVEN until a new concurrency-sensitive live strike runs.

## What this strike must prove

The live experiment is causal, not choreographed:

    shock A
      -> server opens R1
      -> external Agent A starts under R1

    while A is still a live recovery attempt:
      shock B changes decision-material reality
      -> server supersedes R1 and opens R2
      -> external Agent B starts under R2

Then allow both Agents to continue without telling either one which tool to call.

Required facts:

1. Agent A is a configured external model execution, not a deterministic substitute.
2. Agent B is independently a configured external model execution.
3. R1 and R2 are server-created; neither is model-supplied.
4. Shock B materially changes the recovery reality fingerprint.
5. A remains durably bound to R1.
6. B remains durably bound to R2.
7. A cannot mint a current proposal, authority receipt, approval, or mutation after R2 exists.
8. A's stale authority-bearing attempt is typed RECOVERY_EPOCH_SUPERSEDED, not TOOL_ERROR, FAILED_EXTERNAL, or generic PARTIAL.
9. Any R1 PRESENTED proposal is retired from the current candidate surface.
10. Any R1 authority receipt is durably invalidated.
11. B may discover a distinct future, an equivalent future, or no executable future; arrival order is not authority.
12. Equivalent A/B futures deduplicate by semantic plan identity while retaining discovery lineage.
13. Distinct current R2 futures remain distinct candidates.
14. Current collective authority is computed only over current executable facts.
15. If current R2 needs human tradeoff, the correct terminal state may be WAITING_FOR_MEMBERS / UNRESOLVED.
16. If current R2 yields legal current authority, at most one plan transition commits.
17. A stale approval cannot be silently transferred to R2.
18. An unrelated approval must not be burned by A losing the recovery race.
19. R28 exactly-once continuation invariants still hold.
20. Final evidence names the exact winning/losing RecoveryEpoch, AgentRun, Proposal, Receipt, Approval and mutation audit chain where they exist.

## How to create concurrency without scripting strategy

Do NOT coordinate on a model tool name such as:

    wait until A calls inspect_journey
    then inject B
    force A to call request_replan
    force B to call accept_replan

That would only prove the harness script.

Instead coordinate on server-owned lifecycle facts.

Acceptable synchronization examples:

- start A and wait until its AgentRun row is durably RUNNING and bound to R1;
- if needed, use a test-only external-response barrier outside the model prompt so the server knows A is still in flight;
- inject shock B through the existing server-owned provider replay boundary;
- assert R2 exists before releasing/continuing A;
- launch B independently after R2 exists.

The barrier may control timing.

It may NOT prescribe Agent A's or B's strategy or tool order.

## External runtime requirement

Use the configured external runtime path.

If one configured model times out and another configured external model legitimately continues, record that exactly as R30 did.

Do not replace a failed external call with:

- deterministic fallback Agent output;
- prerecorded tool calls;
- copied AgentRun rows;
- hand-authored proposal/authority events.

External-provider failure is allowed as an honest outcome.

A concurrency architecture claim is not.

## Shock truth boundary

Use the existing server-owned provider replay fixture unless a real provider is deliberately available.

Name it honestly:

    SERVER_OWNED_PROVIDER_REPLAY_FIXTURE

Do not call it a public-network live incident.

Physical travel remains NOT PROVEN.

The experiment is about autonomous recovery concurrency, not proving that a traveler physically experienced the disruption.

## Recommended strike shape

### Phase 0 — clean current baseline

Create/reset a real Journey through normal product surfaces.

Record:

- Journey id;
- active plan id;
- current activity id;
- initial recovery reality fingerprint;
- no unexpected open RecoveryEpoch from prior test residue.

### Phase A — Shock A / R1

Inject a decision-material provider-replay shock through normal server-owned fixture ingestion.

Call the normal recovery orchestration surface that creates/joins R1.

Record:

- shock A Event/ProviderObservation ids;
- incident fingerprint;
- R1 id + generation + recovery reality fingerprint.

Start external Agent A normally.

Wait only until the server proves:

    AgentRun A.status == RUNNING
    AgentRun A.recovery_epoch_id == R1

Do not wait for a chosen tool call.

### Phase B — Shock B / R2

While A remains in flight, inject an independent decision-material shock B.

Shock B must change actual recovery semantics, not merely:

- Event UUID;
- captured_at;
- ACK state;
- irrelevant provider observation.

Prove:

    fingerprint(R2) != fingerprint(R1)
    R1.status == SUPERSEDED
    R2.status == OPEN
    R1.superseded_by_recovery_epoch_id == R2.id

Record retirement of any R1 current proposal/receipt if A happened to create one before B.

### Phase C — Agent B

Start external Agent B after R2 exists.

Prove:

    AgentRun B.recovery_epoch_id == R2

Do not tell B what A did.

Do not ask B to beat A.

### Phase D — Release/continue A and B

Let both proceed strategy-neutrally.

The server, not the prompt, decides what is stale.

If A performs no authority-bearing operation after supersession, that is acceptable but does not by itself prove the stale-spend boundary. In that case add a separate deterministic race assertion against A's already-bound run/proposal/approval; do not alter A's prompt to make it hit the boundary.

If A naturally reaches an authority-bearing call after R2, capture the typed RECOVERY_EPOCH_SUPERSEDED result.

### Phase E — convergence

If R2 has a legal executable future:

- allow normal E/W/S authority;
- allow approval if product policy requires it;
- commit at most one final mutation.

If there is no legal current future:

- preserve UNRESOLVED / clarification / member wait honestly.

Do not manufacture UNANIMOUS_DOMINANCE.

Do not manufacture human responses.

## Machine verifier

Create a new R32 verifier rather than editing R30 verdict semantics.

Suggested dimensions:

    recovery_epoch_server_owned
    r1_opened_from_shock_a
    agent_a_external_and_bound_r1
    shock_b_material_not_storage_churn
    r1_superseded_by_r2
    agent_b_external_and_bound_r2
    stale_agent_authority_refused
    stale_result_typed_superseded
    r1_candidates_removed_from_current_surface
    r1_receipts_invalidated
    current_surface_epoch_pure
    semantic_dedupe_not_uuid_dedupe
    arrival_order_not_authority
    approval_not_retargeted
    exactly_one_or_zero_legal_plan_transition
    no_duplicate_continuation_side_effect
    inherited_r28_exactly_once
    authority_provenance_mode_accurate
    truth_boundary_honest

Verdict vocabulary:

    PROVEN
    NOT_PROVEN
    CONTRADICTED

Do not make the expected successful strategy a verifier condition.

## Acceptance

R32 may be called PROVEN only if:

- the new live strike really exercised concurrent recovery generations with configured external Agent execution;
- all causal machine dimensions required by the actual path are PROVEN;
- zero safety/authority contradictions exist;
- deterministic R28-R32 regression remains green afterward.

A correct UNRESOLVED product outcome can still prove the concurrency architecture if the server facts demonstrate that stale work was refused and current authority remained coherent.

"Plan accepted" is not synonymous with "R32 proven."

## Revolution principle

The point is no longer to prove that an Agent can recover once.

The point is to prove that CityNexus can keep thinking while reality changes again.

Agents may explore in parallel.

Truth may advance underneath them.

Only current reality gets authority.

Only current authority may mutate.

That is the R32 Revolution claim.
