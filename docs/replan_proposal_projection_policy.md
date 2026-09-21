# CityNexus Canonical Replan Proposal Projection Policy

Status: arbiter contract note for the product-vs-agent ReplanProposal projection gap and H10b semantic parity.

## 1. Ownership decision

The current shape gap between the product ReplanProposal surface and the Agent/MCP surface is a
**product capability defect**, not a Hermes test defect.

It should be implemented by the product/backend lane (C) as a dedicated P1 order.

Do not merge this work into:

- ORD-0167, which owns pending destination identity semantics; or
- ORD-0172, which owns R14 causal-attribution acceptance mapping.

Those orders may depend on the result, but they are not the implementation owner.

Recommended order name:

    ORD-0175 — Canonical Replan Proposal Projection

Hermes remains the consumer/verifier. Hermes must not own the product projection implementation.

## 2. Problem statement

The same persisted ReplanProposal currently has materially different observable shapes:

- product surface: richer proposal representation;
- Agent/MCP surface: reduced representation.

A reduced Agent/MCP projection that omits semantic planning facts prevents a legitimate
product-direct-vs-Hermes semantic comparison.

This is not fixed by comparing:

    HTTP Agent Gateway request_replan
    vs
    MCP request_replan

because both paths pass through the same Agent Gateway and therefore only prove adapter/transport
parity.

That narrower test remains H10a.

H10b requires independent product-direct and Hermes entry paths with comparable semantic output.

## 3. Preferred architecture

Create one **server-owned safe canonical proposal projector**.

Conceptually:

    persisted ReplanProposal + authoritative related facts
        -> project_replan_proposal_safe(...)
        -> CanonicalReplanProposalProjection

Both product and Agent/MCP surfaces consume this projector where a safe proposal view is needed.

The projector is read-only. It must not:

- authorize acceptance;
- mutate proposal state;
- create a new proposal;
- infer missing planning truth;
- trust model-generated provenance;
- change trusted principal resolution.

The purpose is to expose the same safe semantic truth, not to widen mutation authority.

## 4. Projection content

Do not mechanically copy every database column.

The canonical projection must include all fields needed to explain and compare proposal semantics,
subject to security/privacy policy.

At minimum, where available:

- proposal identity;
- journey identity;
- proposal status;
- trigger/event identity or typed trigger summary;
- base plan version identity;
- proposed plan version identity;
- safe normalized diff/change summary;
- utility/scoring summary used by product decision surfaces;
- hard-feasibility verdict;
- stable reason codes;
- locked/protected commitment preservation result;
- cost/time/schedule deltas used by authorization or product explanation;
- evidence/provenance summary sufficient to trace authoritative planning facts;
- projection/schema version.

Exact names may follow existing repository conventions.

If any richer product field is intentionally withheld from Agent/MCP for safety, document the
reason and provide an equivalent safe semantic digest/summary so H10b can still compare the
underlying truth without leaking unsafe internals.

## 5. Provenance requirements

The safe projection must distinguish:

- persisted proposal facts;
- server-computed derived facts;
- provider-backed evidence;
- model/AI-only interpretation;
- unavailable/unknown fields.

It must not flatten AI-only or inferred values into authoritative product truth.

Where the product already has authoritative provenance for diff, feasibility, mobility, temporal,
cost, or commitment preservation, Agent/MCP must receive the safe projection of that provenance
rather than reconstructing it independently.

## 6. Surface parity requirement

For the same persisted proposal and the same caller visibility policy:

    product projection semantic fields
    ==
    Agent/MCP projection semantic fields

after removing fields intentionally classified as surface-specific metadata.

Surface-specific metadata may include:

- transport request id;
- trace id;
- rendering-only labels;
- adapter name;
- timestamps generated solely by the response envelope.

Semantic fields may not silently disappear on one surface.

## 7. H10 independence rule

H10b must preserve independent entry paths.

Allowed shape:

    Product direct replan path
        -> deterministic product/replan core
        -> persisted proposal
        -> canonical safe projector

    Hermes MCP path
        -> MCP adapter
        -> Agent Gateway / allowed orchestration
        -> deterministic product/replan core
        -> persisted proposal
        -> canonical safe projector

The two paths may intentionally converge on the same deterministic domain core and the same
canonical projector.

They must NOT be made equivalent by replacing the product-direct side with another call through
the Agent Gateway.

The parity claim is invalid if both sides share the very adapter/gateway layer whose behavior is
supposed to be compared.

## 8. H10b execution shape

Use cloned isolated databases from the same pre-state.

Run:

1. product-direct replan path on clone A;
2. Hermes/MCP replan path on clone B;
3. use semantically equivalent trigger/input;
4. allow proposal ids, request ids, trace ids, and response-only timestamps to differ;
5. compare canonical semantic projection or canonical truth digest.

Required parity dimensions:

- feasibility/hard verdict;
- stable reason codes;
- commitment preservation;
- proposed change semantics;
- relevant cost/time/schedule deltas;
- evidence/provenance class;
- eligibility/selection semantics where present.

If deterministic proposal ids differ, compare normalized semantic digest rather than raw ids.

## 9. Acceptance gates for ORD-0175

At minimum:

1. Product and Agent/MCP surfaces use one server-owned safe canonical projector.
2. The projector is read-only and does not widen mutation authority.
3. Same persisted proposal -> semantic projection parity across product and Agent/MCP.
4. Product-rich fields required for H10b are no longer silently absent on Agent/MCP, unless an
   explicit safety rule with equivalent safe digest exists.
5. Provenance classes remain distinguishable; AI-only does not become authoritative.
6. Trusted principal remains server-owned; projection fields cannot override actor identity.
7. H10a remains PASS as adapter parity.
8. H10b is rerun from independent product-direct and Hermes paths on cloned identical pre-state.
9. Mutation: route the product-direct comparator through Agent Gateway; H10b independence gate
   must go RED.
10. Mutation: drop one required semantic field from Agent/MCP projection; projection parity gate
    must go RED.
11. Mutation: replace authoritative provenance with model/self-reported provenance; provenance
    gate must go RED.
12. No new Agent mutation tools are added merely to expose richer read projection.

## 10. Relationship to current work

- ORD-0162 / ORD-0173: Hermes validation consumes this capability; it does not own the fix.
- H10a: remains adapter/transport parity and can stay PASS independently.
- H10b: remains NOT_PROVEN / BLOCKED_BY_PROJECTION until ORD-0175 is accepted and H10b is rerun.
- ORD-0167: unrelated pending destination identity work.
- ORD-0172 / R14: may consume the same structured truth discipline but do not own proposal
  projection implementation.

## 11. Freeze sentence

**One proposal may have many transport envelopes, but it must have one safe semantic projection.**
