# Hermes R5 — cross-version request-replan idempotency compatibility

Scenario: `hermes-r5-request-replan-idempotency-upgrade`

R5 adapts a cached legacy four-field proposal summary in memory using only the
persisted `ReplanProposal` row referenced by its ID. The retry keeps the same
request ID and canonical signature. It checks journey and trigger ownership,
preserves cached status and constraint outcomes, ordering, and fails closed on
malformed or unresolved cached state with
`AGENT_IDEMPOTENCY_RESPONSE_SCHEMA_UNAVAILABLE`.

The stdio client preserves this server-owned HTTP `detail` so the deterministic
compatibility code remains visible to the MCP caller.

The compatibility branch does not create proposals, plans, events, or an outer
idempotency record; it does not regenerate or accept a proposal. A current
full-fidelity response passes through unchanged. The complete measured run,
source and parent IDs, identity snapshots, focused test output, and independent
archive validation are recorded in the external-review package generated for
this source commit.

Safety truth: proposal-only; model `NOT_USED` / `NOT_RUN`; mobility fixture is
mock/synthetic; `P7=false`. No production credential, live/preview/user DB, or
authority/mainline merge is used.
