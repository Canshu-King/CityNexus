# Revolution R31 — Epoch Integrity, Authority Provenance, and No More Hash Aliasing

## GPT review verdict

R30 is accepted as a real architectural advance, not an evidence-only win.

The pushed R30 evidence proves:

- external post-shock Agent execution remained mandatory;
- one configured model failed externally with MODEL_TIMEOUT and another configured external model completed recovery;
- stale E1/W1 authority failed closed;
- the old selected proposal did not become accepted;
- server-owned provider replay changed the consent-relevant material world;
- recovery legitimately used current UNANIMOUS_DOMINANCE rather than forcing a human round;
- inherited R28 approval/continuation returned PROVEN;
- the R30 machine verdict is 11 PROVEN / 0 NOT_PROVEN / 0 CONTRADICTED.

Do not repeat R30 just to increase sample count.

## The next knife

The current UNANIMOUS_DOMINANCE receipt path contains one semantic shortcut that should not become permanent product architecture.

In backend/app/collective_authority.py:

    decision_epoch = gate.current_decision_epoch or surface_fingerprint
    material_world_epoch = gate.current_material_world_epoch or surface_fingerprint

This means that when the gate does not expose real current epochs, the same candidate-surface hash can stand in for:

1. semantic decision identity;
2. material-world identity;
3. candidate-surface identity.

Those are not the same fact.

The current R30 strike is still valid because the authority chain is exact and the post-shock mutation was recomputed, but this aliasing weakens the long-term meaning of the receipt and makes future invalidation proofs less trustworthy.

## R31 objective

Make authority receipts carry genuinely distinct server-owned provenance for:

- decision epoch E;
- material-world epoch W;
- candidate surface fingerprint S.

No receipt may be issued by inventing a missing E or W from S.

The Agent owns strategy.

The server owns truth, epochs, authority, and mutation validity.

## Required product change

### 1. Remove fallback epoch aliasing

For UNANIMOUS_DOMINANCE, do not issue a receipt unless the server-owned gate can provide authoritative current E and W.

Do not use:

    E = S
    W = S

as a fallback.

If an authority mode genuinely has no prior human decision epoch, define a server-owned semantic decision epoch explicitly from the semantic decision state, with its own helper/name/schema. It may be derived deterministically, but it must not silently reuse the candidate-surface fingerprint field.

W must come from the same material-world epoch mechanism used by shock invalidation.

### 2. Make the gate expose exact provenance

The allowed collective mutation gate should return explicit fields:

    current_decision_epoch
    current_material_world_epoch
    candidate_surface_fingerprint

and enough provenance metadata to explain how each was computed.

The receipt issuer consumes those fields. It does not synthesize missing values.

### 3. Fail closed on missing epoch provenance

If a collective mutation is otherwise allowed but E or W is unavailable:

    COLLECTIVE_AUTHORITY_EPOCH_UNAVAILABLE

or another typed server-owned error.

Do not create an approval first.

Do not mint a receipt with substitute hashes.

### 4. Preserve idempotency

The same exact authority fact should still return the same durable receipt identity.

Changing W while leaving S identical must produce a different authority fact and make the old receipt unspendable.

Changing E while leaving W and S identical must also make the old receipt unspendable.

### 5. Strengthen R30/R31 verifier observability

For every final collective mutation, machine evidence should expose:

    receipt_id
    authority_mode
    decision_epoch
    material_world_epoch
    candidate_surface_fingerprint

and assert they are non-empty server-owned facts.

Do not require the three hashes to be different merely for cosmetic reasons. Require their provenance and semantics to be distinct.

## Mandatory deterministic tests

Add focused tests for all of these:

1. UNANIMOUS_DOMINANCE receipt issuance fails if current W is missing.
2. Receipt issuance fails if current E is missing unless an explicit server semantic-epoch builder produced it.
3. Same S + changed W makes the old receipt unspendable.
4. Same S + changed E makes the old receipt unspendable.
5. Same E/W/S returns the same receipt id.
6. Approval cannot be created before exact receipt authority exists.
7. A stale receipt remains queryable after invalidation.
8. A new receipt cannot borrow E or W from candidate_surface_fingerprint through fallback logic.
9. Existing R28/R29/R30 authority and exactly-once tests remain green.
10. The strategy-neutral runtime tests remain green; do not prescribe model tool order.

## Live work policy

Do not immediately run another expensive full external strike.

First land the epoch-integrity product change and deterministic regressions.

Only run a new external strike if deterministic behavior reveals a new architecture path that needs real-model validation. If the change is purely authority provenance and all existing live R30 evidence remains semantically valid, preserve that evidence rather than manufacturing a new run for ceremony.

## Delivery truth

Do not claim a new R31 PROVEN merely because tests are green.

R31 is an architecture hardening round unless a new live claim is actually required and executed.

Keep the truth boundary explicit:

- R30 provider shock = SERVER_OWNED_PROVIDER_REPLAY_FIXTURE
- post-shock Agent = configured external runtime
- physical travel = NOT PROVEN

## Revolution principle

R30 proved that autonomous strategy can recover without scripted choreography.

R31 must make the authority token worthy of that autonomy.

A system is not truly autonomous if its permission object cannot distinguish:

    what the people decided,
    what the world currently is,
    and what options are currently being evaluated.

Do not spend another round polishing the proof harness.

Fix the semantic authority core.
