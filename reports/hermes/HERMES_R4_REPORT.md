# Hermes R4 request_replan contract

## Result

`HERMES_R4_REQUEST_REPLAN_CONTRACT = PASS` on the isolated validation branch.

The real CityNexus product planner route and the real stdio MCP V2 route were
run from two fresh SQLite databases cloned from one seeded prestate. Both
produced non-empty replan candidates. The MCP boundary now exposes a validated
`hermes-replan-proposal-view.v1` projection containing the proposal identity,
plan identity, lifecycle status, hard constraints, protected commitment result,
utility score, candidate family, activity diff, cost/travel/time deltas,
reason codes, and feasibility envelope.

## Executed evidence

The focused run was:

```text
python scripts/hermes_r4_contract_probe.py \
  --output-dir D:/moodle/_hermes_r4_probe_20260923_1905
```

The run returned `PASS` with nine passing assertions:

- same logical seed snapshot before the two lanes;
- real direct planner candidate exists;
- real stdio MCP candidate exists;
- non-empty candidate diff, proposed plan ID, and utility score;
- candidate semantic parity;
- versioned complete MCP proposal contract;
- active Journey and sole ACTIVE plan unchanged after proposal generation;
- exactly the V2 allowlist of 11 discovered MCP tools;
- every service child was under the loopback-only socket guard.

`H11_REAL_MODEL = NOT_RUN` and `P7 = false` remain in force.

## Isolation

The probe used fresh disposable SQLite files, `CITYNEXUS_AI_ENABLED=false`,
deterministic solver mode, disabled impact provider, mock city/mobility
fixtures, a synthetic agent token, and an isolated loopback port per backend
process. Production credential names were absent from child environments and
the network audit recorded four guarded child processes with zero blocked or
non-loopback connections.

## Code change

`backend/app/agent/gateway.py` now returns the complete persisted proposal
payload instead of a four-field summary. `agent-mcp/citynexus_mcp/schemas.py`
defines and validates the stable Hermes proposal view. The MCP adapter emits
the versioned projection and rejects incomplete candidate evidence. The probe
and focused tests are under `scripts/` and `agent-mcp/tests/`.

## Focused tests

```text
agent-mcp/tests/test_mcp_boundary.py
agent-mcp/tests/test_hermes_validation_principal.py
agent-mcp/tests/test_replan_proposal_view.py
=> 13 passed

backend/tests/test_agent_principal_boundary.py
=> 2 passed
```

The remaining R3 findings are unchanged: model-mediated prompt injection and
the Hermes 0.21.3 runtime were not run; R4 does not claim either.
