# ORD main-exec-path, cell 2 — the main path has exactly one statement; here is every consumer that proves it

Same building, same tip read (`2e2ddbaf72eed9565fd8b18ea9b8216061269f57`), same branch
(`review/cff87c64-main-exec-path-r1`). This cell changes no product bytes. It is the verification the
building asks for: after cell 1's convergence, enumerate every consumer of the main execution path and show
each one funnels through the gateway, so "the main path is the single tool-execution statement" is a claim
with receipts rather than a reading of one file. Evidence: `cell2_sweep_r1.txt` (each line names file:line).

## The consumers, one by one

- The MCP adapter (`agent-mcp/citynexus_mcp/client.py`) — `call()` POSTs to
  `/api/v1/agent/tools/{tool_name}`. It is the contract's first hop and it goes through the HTTP surface, not
  around it. Correct by construction.
- The agent runtime (`backend/app/agent/runtime.py:471`) — dispatches via
  `AgentToolGateway(session).dispatch(tool_name, payload)`. The runtime's tool trace runs through the gateway.
- The guardian (`backend/app/agent/guardian.py:399,406,418,458`) — builds one `AgentToolGateway` and dispatches
  `inspect_twin`, `request_replan`, `accept_replan` through it. The guardian's autonomous actions go through the
  main path.
- The two HTTP tool routes (`backend/app/main.py` `call_agent_tool`, feeding `AgentToolGateway(session).dispatch`)
  — the gateway's front door.

So every consumer of an agent tool — adapter, runtime, guardian, HTTP routes — goes through the gateway. The
gateway's allowlist (`backend/app/agent/gateway.py` dispatch first line) and the pinned catalog
(`backend/app/agent/tool_catalog.py:63`) are the one gate.

## What cell 1 changed the picture by

Before cell 1 the two reported-disruption builders wrote the domain `Event` outside the gateway. After cell 1
they share one statement (`_capture_reported_disruption`), which is still called from the two natural-language
routes (not through dispatch). That is the one place an agent-initiated domain write does not cross the
gateway's policy boundary — and closing it means a `report_disruption` tool in the pinned catalog
(`report_disruption present today: False`, `cell2_sweep_r1.txt`). That is a contract change (V2 is a pinned
eleven-tool surface), so it is named for the commander and not done unilaterally.

## What this cell does NOT claim

- No product bytes changed in cell 2; the tree difference vs the tip is still just cell 1's `main.py` plus the
  two evidence folders.
- `mission_plan.py` mentions "AgentToolGateway" only in a docstring string (its model-facing authority text); it
  constructs no gateway and executes nothing — it is not a consumer.
- It does not assert the gateway is bug-free, only that the path is single. Behaviour proof for cell 1's
  convergence is the whole-backend-suite before/after in `cell1_note.md` (9 pre-existing failures, none new).