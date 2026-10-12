# R32 GPT Implementation Map — Where to Cut First

This map is implementation guidance, not a second spec. The authoritative goal
remains R32_AUTONOMOUS_RECOVERY_MESH_CONCURRENT_SHOCKS.md.

## 0. Important semantic distinction before coding

Do NOT reuse R31's plan-specific material_world_epoch as the sole identity of a
Journey-wide RecoveryEpoch.

R31 W answers:

    "Is this exact authority for this exact future still grounded in the same
     decision-material physical world?"

R32 RecoveryEpoch answers:

    "Which server-owned recovery generation is this autonomous work part of?"

Those are related but not identical.

A RecoveryEpoch may contain multiple candidate plans, each with its own strict
R31 E/W/S receipt validation.

Recommended: define a separate server-owned recovery-reality projection from
the active Journey plus the currently actionable decision-material event set.
Do not call it material_world_epoch if its semantics differ.

## 1. Data model entry points

File:

    backend/app/db/models.py

Existing useful anchors:

    Journey
    JourneyMission
    AgentRun
    AgentPendingAction
    ActionApproval
    CollectiveAuthorityReceipt
    ReplanProposal
    Event

Add a durable RecoveryEpoch model.

Suggested minimum:

    id
    journey_id
    generation
    active_plan_version_id_at_open
    recovery_reality_fingerprint
    status
      OPEN
      SUPERSEDED
      COMMITTED
      ABANDONED
    opened_at
    closed_at nullable
    superseded_by_recovery_epoch_id nullable
    close_reason nullable
    triggering_event_ids_json

Prefer:

    UNIQUE(journey_id, generation)

and a database-enforced invariant preventing two OPEN epochs for one Journey.

For SQLite, a partial unique index is acceptable if it is also represented in
schema.sql / ensure_schema compatibility.

Do not rely only on a Python process lock.

## 2. Bind the authority-bearing chain

Add nullable legacy-compatible recovery_epoch_id to the exact rows that can
carry a recovery attempt toward mutation:

    AgentRun
    ReplanProposal
    CollectiveAuthorityReceipt
    ActionApproval
    AgentPendingAction

Legacy rows may remain NULL.

For a new R32 recovery flow, NULL must fail closed at the authority-bearing
boundary rather than being silently treated as current.

Mission ancestry may remain useful context, but do not make it the only epoch
carrier.

## 3. Schema/migration locations

Files:

    backend/db/schema.sql
    backend/app/db/session.py

session.py already carries compatibility migrations for:

    action_approvals.authority_receipt_id
    agent_pending_actions.authority_receipt_id
    collective_authority_receipts

Follow that pattern.

Do not duplicate semantic rules in migration code. Migration code owns physical
shape and safe legacy defaults only.

## 4. Recovery reality projection

Create a small dedicated module, suggested:

    backend/app/recovery_epoch.py

Do not bury orchestration generation semantics inside collective_authority.py.

Suggested pure/server-owned responsibilities:

    recovery_reality_basis(session, journey)
    recovery_reality_fingerprint(basis)
    current_open_recovery_epoch(session, journey_id)
    ensure_recovery_epoch(session, journey)
    supersede_recovery_epoch(session, journey, reason)
    validate_recovery_epoch_binding(...)

The basis should be deterministic and compact.

Candidate inputs:

- Journey active_plan_version_id;
- current_activity_id where execution semantics require it;
- currently actionable decision-material Events;
- provider incident fingerprints / canonical scope identities;
- event type/severity/status only where they actually affect recovery.

Avoid:

- observation timestamps that do not change meaning;
- raw provider payload blobs;
- random UUID churn;
- Agent output;
- model confidence.

Irrelevant observation churn must not create a new epoch.

## 5. Provider/event boundary

File:

    backend/app/agent/signal_pipeline.py

Useful anchors already exist:

    incident_fingerprint(...)
    SignalPipelineResult.created_event_ids
    Event creation with server-owned provider/provenance
    set_fixture_state(...)

Do not let the fixture or caller directly write RecoveryEpoch rows.

The pipeline should continue to own provider/event truth.

A higher server-owned orchestration layer should decide whether the resulting
current event set changes the recovery reality and therefore supersedes the
open RecoveryEpoch.

This keeps:

    provider truth
    != recovery orchestration
    != collective authority

as separate responsibilities.

## 6. AgentRun binding

File:

    backend/app/agent/runtime.py

The normal external Agent path creates AgentRun inside DeepSeekJourneyAgent.run:

    run = AgentRun(...)

Bind the current server RecoveryEpoch here before the first external model call.

Persist it before the model call, just like the current run envelope is already
committed before external execution.

The model must never receive a trusted ability to choose another epoch id.

The run-start audit should expose the bound recovery_epoch_id and generation.

Also update unavailable/skipped run creation consistently so read models do not
lie about whether a run was part of a recovery generation.

## 7. Proposal binding

File surfaces to inspect:

    backend/app/agent/gateway.py
    backend/app/main.py

request_replan / plan generation must bind produced ReplanProposal rows to the
AgentRun's RecoveryEpoch when invoked from a recovery Agent.

Do not infer it later only from mission ancestry.

If proposals are also created through ordinary non-Agent product APIs, keep
recovery_epoch_id nullable there.

## 8. Semantic deduplication

Do not deduplicate by proposal UUID.

Use a normalized executable plan identity.

Start from existing server-owned PlanVersion/Activity structure and exclude
pure storage identity.

A candidate fingerprint should include at least decision-relevant itinerary
shape:

- ordered executable activities;
- canonical place/service identity;
- schedule boundaries where materially relevant;
- commitment/protected-state semantics;
- cost facts where they affect authority.

Do not include:

- proposal UUID;
- generated explanation prose;
- model provider/model id;
- timestamps.

If two Agents discover the same future, the product should be able to say:

    same future, two discovery paths

not:

    two competing futures because two UUIDs exist.

Preserve both discovery provenance trails even if the candidate is deduplicated.

## 9. Approval / continuation binding

Files:

    backend/app/agent/approval.py
    backend/app/agent/continuation.py
    backend/app/agent/gateway.py

continuation.py already binds:

    AgentPendingAction -> authority_receipt_id

Extend the same exactness to recovery_epoch_id.

When capture_pending_action persists a suspended action, snapshot the run's
server-owned recovery_epoch_id.

On resume:

    pending.recovery_epoch_id
    approval.recovery_epoch_id
    current RecoveryEpoch
    authority receipt recovery_epoch_id

must agree before mutation can occur.

Do not silently update an old pending action to a new epoch.

A stale pending action is historical evidence, not a reusable command.

## 10. Final mutation boundary

File:

    backend/app/main.py

Critical anchors:

    collective_authority_preflight(...)
    collective_mutation_gate(...)
    _accept_replan_impl(...)
    _accept_replan_executing(...)
    journey_write_lock(...)

The final replan path already has the right shape:

- enter Journey write boundary;
- re-read state;
- recompute collective authority;
- require the same authority receipt id before mutation.

R32 should add one more independent check inside that same serialized boundary:

    bound recovery epoch == current open recovery epoch

and require it to still be current.

Do this before active_plan_version_id changes.

After a successful commit:

- close the winning RecoveryEpoch as COMMITTED;
- durably supersede/close competing attempts;
- do not delete losing runs/proposals/approvals.

The loser should remain inspectable.

## 11. Typed stale outcome

Avoid leaking R32 into generic exception handling.

Introduce a typed server result/code:

    RECOVERY_EPOCH_SUPERSEDED

Suggested facts:

    stale_recovery_epoch_id
    stale_generation
    current_recovery_epoch_id
    current_generation
    stale_recovery_reality_fingerprint
    current_recovery_reality_fingerprint

Runtime policy:

- not FAILED_EXTERNAL;
- not TOOL_ERROR;
- not accidental PARTIAL;
- may become a typed terminal SUPERSEDED outcome.

The model/provider did not fail merely because the world changed.

## 12. Tests to write first

Recommended new file:

    backend/tests/test_r32_recovery_epoch.py

Start with server deterministic invariants before touching the live harness.

First tranche:

1. open/join idempotency;
2. one OPEN epoch per Journey under concurrent creation;
3. relevant event-set change supersedes;
4. irrelevant observation does not supersede;
5. AgentRun binding cannot be caller-forged;
6. stale AgentRun cannot mint authority;
7. pending approval cannot cross epochs;
8. final mutation closes winner;
9. loser is typed SUPERSEDED;
10. exact same plan discovered twice deduplicates semantically.

Then extend existing:

    test_r30_collective_authority_receipt.py
    test_r28_durable_approval_continuation.py
    test_agent_runtime_state_epoch.py

Do not start by editing run_r30_live.py.

## 13. CI

Create a dedicated R32 workflow or rename the narrow workflow only if doing so
does not weaken R30/R31 coverage.

A good R32 deterministic gate should explicitly include:

    test_r32_recovery_epoch.py
    test_r31_epoch_integrity.py
    test_r30_collective_authority_receipt.py
    test_r29_disagreement_mediation.py
    test_r28_durable_approval_continuation.py
    runtime state/continuation/gateway tests

Do not trust a local-only R32 test report if the remote workflow does not run the
new test file.

## 14. Suggested implementation order

Commit A:
- RecoveryEpoch model/schema/migration;
- pure recovery reality projection;
- open/join/supersede deterministic tests.

Commit B:
- AgentRun + proposal binding;
- no-forgery / no-cross-epoch tests.

Commit C:
- receipt / approval / pending-action epoch binding;
- stale approval test.

Commit D:
- final mutation current-epoch validation;
- concurrent winner/loser test;
- typed SUPERSEDED result.

Commit E:
- semantic proposal dedupe / merged candidate surface.

Only then:
- R32 machine verifier;
- new live concurrent-shock strike.

This order lets each commit expose a real product invariant instead of building a
large harness before the product exists.

## 15. One warning from the current code

R31 intentionally made candidate-surface freshness independent from E and W.

Do not accidentally collapse R32 RecoveryEpoch into S either.

A recovery generation is orchestration causality.

E/W/S are mutation authority facts.

Keep both layers explicit.

That separation is the architectural point of R32.
