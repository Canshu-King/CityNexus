# Hermes R22 — response loss recovery

R22 runs a real DeepSeek/Hermes model against an ACTIVE Journey in a fresh
disposable SQLite database. A deterministic harness fixture lets the first
`request_replan` reach CityNexus and persist its complete server-owned proposal,
then drops the model-facing MCP delivery. The fixture is recorded as
`SIMULATED_MCP_RESPONSE_LOST_AFTER_SERVER_PERSISTENCE`; it is not evidence of a
live network failure.

The model receives the transport error and must recover from server-owned truth
using `list_replans` or an equivalent current read. The Harness proves that the
persisted proposal exists, no duplicate proposal is created, Journey and plan
authority remain unchanged, and no accept, booking, payment, commitment,
approval, replace, or reschedule operation occurs.

The model and MCP provider identities, native events, tool chronology, exact
proposal identity sets, final model answer, and loopback guard are retained.
The scenario is PLAN_ONLY with P7=false. The provider warning is a
`SYNTHETIC_HARNESS_FIXTURE`, not LIVE/provider evidence.
