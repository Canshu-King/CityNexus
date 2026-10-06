# Revolution R30 — Next Product Knife: Autonomous Convergence Control Plane

## Decision

Do NOT run a third copy of the same R30 live strike.

The two strategy-neutral live runs already produced the useful signal:

1. A configured external Agent may legitimately discover a current
   UNANIMOUS_DOMINANCE proposal and move to approval without entering the
   harness's expected trade-off path.
2. A mediator may make real progress and then repeat an equivalent tool request;
   the current runtime turns that same-state repetition into TOOL_ERROR/PARTIAL.
3. The inherited R28 proof still relies too heavily on mission ancestry to carry
   collective authority across later recovery missions/runs.

These are product architecture problems, not evidence-volume problems.

The next work is the Autonomous Convergence Control Plane.

---

# 1. Keep missions strategy-neutral

Non-negotiable:

- do not put a correct tool sequence in the system prompt;
- do not add "first call A, then B, then C";
- do not force the model to manufacture disagreement;
- do not force mediation when the current grounded state is unanimously dominant;
- do not add deterministic fallback that impersonates the configured external Agent.

The model chooses strategy.

The server owns:
- truth;
- authority;
- idempotency;
- terminal-state validity;
- no-progress detection.

A strategy-neutral mission is allowed to reach any server-valid terminal path.

---

# 2. Stop using mission ancestry as the sole authority carrier

## Product problem

Today the R28 verifier often discovers collective authority by walking:

    final AgentRun
      -> mission
      -> parent_mission_id
      -> COLLECTIVE_TRADEOFF clarification

That is useful causal context, but it is too fragile to be the sole proof of
authority.

A later recovery Agent can be perfectly valid while living on a new mission
branch. Missing parent lineage must still fail when no other authority proof
exists, but the product needs an explicit durable authority object.

## Introduce CollectiveAuthorityReceipt

Add a server-owned durable receipt representing the authority that may be spent
on one collective mutation.

Suggested fields:

    id
    journey_id
    proposal_id
    plan_version_id

    authority_mode
      AUTHENTICATED_MEMBER_CONSENT
      UNANIMOUS_DOMINANCE

    decision_epoch
    material_world_epoch
    candidate_surface_fingerprint

    source_mission_id nullable
    source_agent_run_id nullable

    required_member_ids_json
    response_audit_ids_json
    principal_actor_ids_json

    classification
    issued_at
    invalidated_at nullable
    invalidation_code nullable

The receipt is issued only by server-owned authority code after the current
decision surface has been validated.

The model never invents a receipt and never supplies its fields.

## AUTHENTICATED_MEMBER_CONSENT issuance

Issue only when all of these are true:

- collective round is RESOLVED;
- exact selected proposal is server-owned and grounded;
- every required member has a persisted response;
- every required member response has AUTHENTICATED_TRAVELER audit proof;
- the persisted decision/world epochs match the current decision surface;
- any R30 independent-member-convergence requirement is satisfied.

## UNANIMOUS_DOMINANCE issuance

Issue only when current server recomputation proves:

    classification == UNANIMOUS_DOMINANCE

for the exact proposal/plan/current world.

No human response rows are fabricated.

## Consumption

The pending action / approval / final replan.accepted audit must bind the
authority receipt id.

At final mutation:

    load receipt
    -> target must match
    -> receipt must not be invalidated
    -> recompute current E/W / authority conditions
    -> only then execute

A world shock invalidates or makes the old receipt unspendable. Historical
evidence remains immutable.

## Verifier rule

Do NOT weaken R28.

A final run without reachable collective parent still fails UNLESS it carries a
valid server-issued authority receipt that independently proves the same
authority facts.

Therefore:

    missing parent + no authority receipt
        => still fail

    missing parent + invalid/stale/wrong-target receipt
        => fail

    new recovery mission + valid strict receipt
        => authority is proven without pretending the mission trees are identical

This replaces an accidental topology requirement with an explicit product
authority contract.

---

# 3. Same-state semantic replay instead of false TOOL_ERROR

## Current bug class

The runtime currently keys repeated calls by:

    tool_name + normalized arguments + state_epoch

and, when the key repeats, persists:

    STOP_REPETITION
    TOOL_ERROR

That turns an equivalent repeated observation into a false execution failure and
can push an otherwise-progressing autonomous mission to PARTIAL.

## New rule

For server-read / inspection tools only:

    inspect_journey
    inspect_twin
    list_replans

when the exact call repeats in the same state_epoch:

- do not execute the tool again;
- do not mark TOOL_ERROR;
- replay the previous server-owned result;
- persist a normal step with:

      decision = REPLAY_SAME_STATE
      status = COMPLETED
      replayed_from_sequence_no = <original>

- feed the replayed result back to the model with neutral metadata:

      state_changed = false
      same_state_replay = true

The product is saying only:

    "You already know this fact and the world has not changed."

It is NOT saying which tool or strategy comes next.

Do not apply this blindly to external search or mutations.

For mutation duplicates, preserve existing idempotency / approval semantics.
Never re-execute a mutation merely because the model repeated itself.

## Stall protection

A replay is not infinite-loop permission.

Track same-state no-progress turns. After a small bounded number of repeated
same-state observations, emit a typed neutral control result such as:

    MISSION_NO_PROGRESS

with facts:

    state_epoch
    repeated_observation_count
    terminal_contract_satisfied = false

The message may say:

    "No new server state has been produced. Choose another allowed strategy or
     conclude the mission with a valid typed outcome."

It must NOT name a required next tool.

---

# 4. Strategy-neutral terminal supervisor

Remove any runtime/user nudge whose purpose is to encode the expected tool
sequence.

Replace it with a generic server terminal contract.

When the model returns prose/no tool call:

    evaluate persisted server state

If a legal terminal state exists:
- complete/suspend normally.

If not:
- do not mark the mission completed from prose;
- return one neutral machine message describing the unmet terminal condition;
- allow the model another turn.

Examples of legal server-owned terminal states:

    MUTATION_EXECUTED
    APPROVAL_PENDING
    WAITING_FOR_MEMBERS
    WAITING_FOR_USER
    NO_ACTION
    UNRESOLVED

The supervisor may state what is missing at the contract level, for example:

    "No typed terminal recovery outcome exists yet."

It must not say:

    "Call request_collective_decision next."

This is the difference between product control and prompt choreography.

---

# 5. Restructure the R30 causal strike

The external Agent should not be responsible for manufacturing the human
authority precondition that R30 wants to invalidate.

## Phase A — establish a real human authority anchor

Use the normal CityNexus collective-decision product surface:

- grounded candidate decision surface;
- distinct authenticated relevant members;
- independent responses;
- server-issued AUTHENTICATED_MEMBER_CONSENT receipt;
- E1/W1 bound to that receipt.

This phase is a human-authority product flow, not an LLM strategy test.

Do not tell an Agent to create a particular disagreement.

## Phase B — shock

Inject the normal server-owned provider replay shock.

Prove:

    E1 semantic decision identity remains relevant
    W1 changes to W2
    old authority receipt cannot be spent
    old proposal is not accepted
    denial is durable
    failed action does not burn unrelated approval state

## Phase C — autonomous recovery

Now start the configured external recovery Agent with a strategy-neutral
mission.

Any server-valid strategy is acceptable.

Path U:

    Agent finds current UNANIMOUS_DOMINANCE
    -> server issues fresh unanimous authority receipt
    -> no fresh human round
    -> approval/continuation/mutation

Path H:

    current decision remains a real human trade-off
    -> Agent may create/improve/research however it chooses
    -> server eventually opens a fresh collective decision
    -> authenticated members establish E2/W2
    -> server issues fresh human authority receipt
    -> approval/continuation/mutation

Path N:

    Agent cannot safely resolve current state
    -> typed UNRESOLVED is a valid mission outcome
    -> R30 is not PROVEN, but this is not a runtime PARTIAL caused by a false
       duplicate-tool error

The machine verifier judges authority and final state, not one expected tool
sequence.

---

# 6. Deterministic tests before any new live strike

Do not run another full external strike until the following product tests are
green.

## Authority receipt

1. Valid authenticated collective response set issues one strict receipt.
2. Current unanimous dominance issues one strict receipt without fake human responses.
3. Wrong proposal cannot spend a receipt.
4. Wrong Journey cannot spend a receipt.
5. Changed W makes old receipt unspendable.
6. Historical invalid receipt remains queryable.
7. Failed mutation does not consume approval/receipt incorrectly.
8. A new recovery mission can spend a valid receipt even without collective
   parent_mission_id.
9. Missing parent AND missing receipt still fails the inherited R28 verifier.
10. A forged/mismatched receipt fails the verifier.

## Runtime convergence

11. Same inspect_journey in one state epoch replays prior server result and is
    not TOOL_ERROR.
12. Replay does not increment domain state epoch.
13. A new state epoch permits a fresh real inspection.
14. Repeated mutation is never blindly re-executed.
15. Bounded same-state replay produces typed NO_PROGRESS rather than accidental
    PARTIAL.
16. A mediator can recover from one repeated observation and still reach a
    valid server terminal state.
17. No test prompt contains a prescribed correct tool order.

Only after these are green should Codex run a NEW causal strike. That new strike
is not "third try of the same harness"; it exercises a different product
architecture.

---

# 7. What not to do

Do not:

- add another evidence-only pass;
- run the same current strike again before product changes;
- hard-code a tool sequence in a prompt;
- force the Agent to choose mediation;
- reject a legitimate UNANIMOUS_DOMINANCE strategy just because a harness
  expected disagreement;
- change PARTIAL to COMPLETED cosmetically;
- make STOP_REPETITION disappear without durable replay/no-progress semantics;
- weaken R28 to accept missing lineage with no replacement authority proof;
- copy collective mission ids into unrelated missions merely to satisfy a
  verifier;
- forge human responses;
- add deterministic fallback in place of the external Agent.

---

# Revolution principle

The Agent should own strategy, but it must not own truth or authority.

Mission topology is implementation history, not permission.

Repeated observation is not failure.

A valid autonomous system needs a server-owned control plane that can answer:

    What changed?
    What authority exists?
    Is that authority still valid?
    Has the mission actually reached a legal terminal state?

without dictating:

    Which tool must the model call next?

That is the next Revolution knife.
