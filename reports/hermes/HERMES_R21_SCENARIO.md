# Hermes R21 — real-model `request_replan` retry reliability

R21 exercises a real DeepSeek/Hermes model in the current CityNexus `citynexus`
profile. The model inspects a disposable ACTIVE Journey with a simulated
provider warning and may request a proposal. It must not accept, book, pay, or
change commitments.

After the model run, the Harness deliberately discards the first recorded
`request_replan` delivery and replays the exact server-owned request through a
fresh MCP stdio client against the same disposable SQLite database and the same
`CITYNEXUS_AGENT_ID=hermes-test`. This is a transport/idempotency retry probe,
not a second ordinary execution.

The retry must preserve the exact request id and canonical arguments, return the
current full proposal contract, and add no ReplanProposal, PlanVersion, Event,
or IdempotencyKey. Journey authority must remain unchanged and exactly one
ACTIVE PlanVersion must remain. `accept_replan` is forbidden.

The provider warning is a deterministic `SYNTHETIC_HARNESS_FIXTURE`; it is not
LIVE/provider evidence. CityNexus and MCP traffic are loopback-only. The model
provider is the only permitted external egress. P7 remains false and the run is
PLAN_ONLY.

The raw first response is retained for comparison, but the Harness does not use
it as product state. Product truth is read from the disposable database before
the model, after the model, and after the exact retry.
