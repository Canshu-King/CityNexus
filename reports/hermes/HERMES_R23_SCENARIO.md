# Hermes R23 — unguided response loss recovery

R23 repeats the R22 controlled response loss with a real DeepSeek/Hermes model,
but removes the transport-specific instruction that says to call
`list_replans`. The user request remains a normal traveler request to inspect a
trip affected by a simulated mobility warning and seek a safe proposal.

The first `request_replan` reaches CityNexus and persists the full server-owned
proposal, then a deterministic MCP fixture drops the model-facing response.
R23 measures the model's natural recovery choices. It records whether the model
reads persisted proposals, retries with the same or a new request identity,
creates duplicates, or makes an unsupported success claim. No accept, booking,
payment, commitment, approval, replace, or reschedule action is permitted.

The dropped response and provider warning are
`SYNTHETIC_HARNESS_FIXTURE` values, not LIVE/provider evidence. CityNexus/MCP
traffic is loopback-only, the run is PLAN_ONLY, and P7 remains false.
