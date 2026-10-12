# Revolution R32 — Autonomous Recovery Mesh Under Concurrent Shocks

## Starting point

Base this round on the green R31 authority head:

    0639d68b1efc5d08d7b12589a2f3a93cc001624f

R30 is already accepted as a real live autonomous recovery proof.
R31 has now separated E / W / S and closed renewed-consent surface freshness.

Do not reopen those rounds for ceremony.

## Revolution objective

Move CityNexus from:

    one shock -> one recovery Agent -> one valid authority -> one mutation

to:

    multiple decision-material shocks
    + multiple autonomous recovery attempts
    + changing candidate surfaces
    + possible human approval delay
    -> one current server reality
    -> one consumable authority
    -> one exactly-once winning mutation
    -> every stale loser fails closed with a typed reason

This is not a load test.

This is a product capability: an autonomous Journey must remain coherent while
the world changes faster than one Agent can finish reasoning.

## Product principle

Agents may race in strategy.

They may not race in truth.

The server owns:

- the current material reality;
- the current recovery epoch;
- candidate identity and deduplication;
- collective authority;
- approval binding;
- mutation serialization;
- supersession;
- terminal-state validity.

No Agent wins because it returned first.

No stale Agent loses with a generic TOOL_ERROR merely because reality moved.

## 1. Introduce a server-owned RecoveryEpoch

Add the smallest durable object or equivalent durable state needed to represent
one coherent recovery window for a Journey.

Suggested semantics:

    recovery_epoch_id
    journey_id
    active_plan_version_id_at_open
    material_world_epoch_at_open
    opened_at
    closed_at nullable
    close_reason nullable
    superseded_by_recovery_epoch_id nullable

A recovery epoch is server-owned.

An Agent never invents or chooses it.

Opening or joining an epoch must be idempotent for the same current recovery
reality.

A decision-material provider shock that changes W supersedes the previous open
recovery epoch.

A committed plan transition closes the winning epoch.

Do not create a new epoch merely because an Agent retries or a tool call repeats.

## 2. Bind autonomous recovery work to the epoch

Every post-shock recovery AgentRun must durably identify the recovery epoch it
is operating against.

Every recovery proposal / pending action / approval path that can lead to a
plan mutation must be traceable to:

    Journey
    -> RecoveryEpoch
    -> AgentRun / Mission
    -> Proposal
    -> CollectiveAuthorityReceipt
    -> ActionApproval / PendingAction
    -> final mutation audit

Do not make mission ancestry the sole carrier.

Do not let the model submit a recovery_epoch_id as trusted input.

## 3. Merge exploration, not authority

Two Agents may independently discover different grounded futures.

The server may merge those futures into the current candidate surface.

Required behavior:

- semantic-equivalent plans are deduplicated by server-owned normalized plan
  identity, not proposal UUID;
- distinct grounded futures may coexist;
- the current E/W/S authority machinery judges the merged surface;
- Agent votes, model confidence and arrival order do not create authority;
- no majority vote between Agents;
- no "first proposal wins" rule.

If the merged surface becomes a real human trade-off, existing collective
authority rules still apply.

If one future is genuinely current UNANIMOUS_DOMINANCE, the server may issue
the exact authority receipt normally.

## 4. Typed supersession instead of accidental PARTIAL

When an Agent started under recovery epoch R1 but the Journey has moved to R2,
its next authority-bearing operation must fail with a typed server result such
as:

    RECOVERY_EPOCH_SUPERSEDED

or an equally explicit code.

The durable result should include:

    stale_recovery_epoch_id
    current_recovery_epoch_id
    stale_material_world_epoch
    current_material_world_epoch
    proposal_id / pending_action_id when relevant

Do not call this TOOL_ERROR.

Do not mark the model itself as externally failed.

A stale Agent may inspect the current state and choose a new strategy, or may
terminate with a typed SUPERSEDED outcome.

## 5. Approval race safety

Prove this causal path:

    authority valid
    -> approval requested
    -> world changes before traveler approves
    -> old recovery epoch superseded
    -> traveler approval arrives
    -> old authority cannot mutate
    -> approval is not silently transferred to a new proposal
    -> new recovery path requires current authority

The old approval may remain historically queryable.

It must not become a reusable permission token.

Do not burn unrelated approvals merely because one stale mutation failed.

## 6. Multi-Agent commit race

Prove two recovery attempts can reach the mutation boundary close together.

The Journey write boundary must guarantee:

- at most one active-plan transition wins;
- the second transaction re-reads current Journey state;
- the second receipt is revalidated against current E/W/S and recovery epoch;
- a stale loser receives a typed supersession/conflict result;
- no duplicate accepted proposal;
- no double-consumed approval;
- no duplicate continuation side effect.

Do not solve this with a process-local mutex alone.

Existing database / transaction / Journey write semantics must remain the final
authority.

## 7. R31 provenance honesty closeout

While touching the authority path, make provenance labels mode-accurate.

Today both algorithmic UNANIMOUS_DOMINANCE and authenticated human consent can
be rendered with the same generic semantic-epoch provenance label even though
their server computations are not identical.

Do not claim a provenance schema or builder that did not actually produce the
value.

Expose enough durable metadata to distinguish at least:

    ALGORITHMIC_UNANIMOUS_SEMANTIC_EPOCH
    AUTHENTICATED_MEMBER_COLLECTIVE_DECISION_EPOCH
    MATERIAL_WORLD_EPOCH
    CANDIDATE_SURFACE_FINGERPRINT

This is observability, not a new authority source.

Do not invalidate historical R30 truth claims merely to rename metadata.

## 8. Deterministic tests before live work

At minimum prove:

1. Same Journey/current W joins the same open RecoveryEpoch idempotently.
2. Decision-material W change supersedes the old RecoveryEpoch.
3. Irrelevant observation churn does not create a new RecoveryEpoch.
4. AgentRun cannot forge or switch its epoch binding.
5. Equivalent proposals from two Agents deduplicate semantically.
6. Distinct grounded proposals remain distinct candidates.
7. Arrival order does not determine collective authority.
8. Old-epoch proposal cannot mint a current receipt.
9. Old-epoch receipt cannot create a new approval.
10. Approval created before supersession cannot mutate after supersession.
11. Failed stale mutation does not burn unrelated approval state.
12. Two concurrent final mutations yield at most one active-plan transition.
13. Losing mutation is durably typed as superseded/stale, not generic PARTIAL.
14. Same-state read replay semantics from R30 remain strategy-neutral.
15. Existing R28 exactly-once continuation remains green.
16. Existing R29 disagreement mediation remains green.
17. Existing R30 shock-recovery invariants remain green.
18. Existing R31 E/W/S tests remain green, including current-S validation.
19. No system/user prompt prescribes the correct tool sequence.
20. No deterministic fallback impersonates an external Agent.

## 9. New live strike — only after deterministic convergence

A new live strike is justified for R32 because this is a new runtime behavior.

Use configured external Agents without prescribing their tool sequence.

Suggested causal strike:

Phase A:
- establish a real current Journey and collective authority baseline through
  normal product surfaces.

Phase B:
- ingest decision-material shock A through the server-owned provider replay
  boundary;
- open RecoveryEpoch R1;
- start external recovery Agent A.

Phase C:
- before A can commit, ingest independent decision-material shock B;
- prove W changes and R1 is superseded by R2;
- start external recovery Agent B against R2.

Phase D:
- allow A and B to continue strategy-neutrally;
- A must not be allowed to spend R1 authority against R2;
- B may succeed, or the merged current surface may legitimately require
  renewed human authority / resolve UNANIMOUS_DOMINANCE / end UNRESOLVED.

Phase E:
- if a legal current recovery path exists, prove exactly one final plan
  transition and one current authority chain;
- if the correct outcome is UNRESOLVED, preserve it honestly rather than
  manufacturing success.

Do not engineer model prompts so that one Agent is scripted to lose.

## 10. Machine verdict

The R32 verifier should judge causal server facts, not an expected Agent script.

Suggested verdict dimensions:

    recovery_epoch_server_owned
    shock_a_opens_r1
    shock_b_supersedes_r1_with_r2
    stale_agent_cannot_spend_old_authority
    concurrent_agents_strategy_independent
    candidate_surface_server_merged
    current_authority_only
    approval_supersession_safe
    exactly_one_plan_transition
    losing_attempt_typed_not_partial
    inherited_r28_exactly_once
    truth_boundary_honest

Do not accept a checkpoint-authored verdict bit without durable evidence.

## 11. Truth boundary

Unless the experiment actually changes these facts, preserve:

- provider shocks may be SERVER_OWNED_PROVIDER_REPLAY_FIXTURE;
- external Agents must be configured real external runtimes for the live strike;
- physical travel remains NOT PROVEN.

Do not call replay data a live public-network incident.

## 12. What not to do

Do not:

- run five copies of the same R30/R31 strike;
- prescribe tool order;
- pick a winning Agent by arrival time;
- use model confidence as authority;
- copy authority receipt ids between recovery epochs;
- silently retarget an approval;
- turn stale-world supersession into TOOL_ERROR;
- mark stale Agent output as FAILED_EXTERNAL when the provider/model worked;
- weaken E/W/S validation to make concurrency pass;
- use process-local locking as the only race guarantee;
- forge Event/E/W/S rows;
- create a deterministic Agent fallback;
- claim physical-world proof that was not obtained.

## Revolution principle

R30 taught CityNexus to recover autonomously.

R31 taught its authority token to mean what it says.

R32 must teach the system to survive a world that changes again while it is
still thinking.

The target is not "two Agents can run."

The target is:

    many strategies
    one current reality
    one valid authority
    one exactly-once mutation

That is the autonomous recovery mesh.
