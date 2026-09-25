# Hermes R24 — concurrent identical request_replan

This scenario exercises the Hermes MCP boundary, not the model planner. Two
independent MCP client processes issue the exact same request_replan request
concurrently against one fresh disposable SQLite database, with the same
CITYNEXUS_AGENT_ID, Journey, trigger event, request id, and arguments.

The expected result is one idempotent proposal-generation outcome: both callers
receive the same full proposal contract in the same order, while only one
proposal and one candidate PlanVersion are created. Journey authority and the
event remain unchanged. The outer and inner idempotency records are recorded by
identity. No accept_replan, booking, payment, or commitment action is called.

The closure/provider state is a SYNTHETIC_HARNESS_FIXTURE; it is not LIVE or
provider-verified evidence. CityNexus and MCP traffic are loopback-only.

Run from a clean committed Hermes worktree:

    $env:CITYNEXUS_AGENT_ID = "hermes-test"
    python scripts/hermes_r24_concurrent_request_replan_probe.py --evidence-dir C:\Users\<user>\Downloads\hermes-r24-evidence --trials 3

Then build and validate the external package using the two R24 package scripts.
