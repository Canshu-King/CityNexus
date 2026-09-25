# Hermes R25 — concurrent signature conflict

Before the concurrency arm, the Harness performs one serial proposal-only
request_replan to materialize the existing traveler policy row. This keeps
first-use policy provisioning outside the measured race.

This scenario then sends two concurrent request_replan calls with the same Agent,
Journey, trigger event, and request_id, while changing candidate_count between
1 and 2. The idempotency contract requires one request to win and the other to
receive a deterministic 409 because one request identity cannot represent two
canonical argument signatures.

The winning call must return the full Hermes Proposal contract. The losing call
must not generate any Proposal or PlanVersion. The winning response may include
the already-persisted proposals for the trigger event; every response identity
must be persisted, and the response identities not present in the pre-race
baseline must exactly match the newly persisted Proposal and PlanVersion
identities. Journey authority and Event identity remain unchanged, and exactly
one outer and one inner idempotency row must be created. The scenario never
calls accept_replan.

The provider/event state is a SYNTHETIC_HARNESS_FIXTURE, not LIVE evidence.
CityNexus and MCP traffic are loopback-only. The run is PLAN_ONLY and P7=false.
