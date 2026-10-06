# ORD main-exec-path, cell 3 — the frontend runs on the main path too

Same building, same tip (`2e2ddbaf72eed9565fd8b18ea9b8216061269f57`), same branch
(`review/cff87c64-main-exec-path-r1`). Cell 3 changes no product bytes. It closes the sweep's last surface:
the frontend, because the building says **whole tree** and the main path's first hop is an HTTP route the
frontend also calls. Evidence: `cell3_sweep_r1.txt` (each line names file:line).

## What the frontend does

- `frontend/src/api/citynexus.ts:1104,1117` — `callAgentTool` POSTs `/api/v1/agent/tools/{tool}`. That is the
  main path's HTTP surface, the same one the MCP adapter uses. Correct by construction: the browser does not
  reach past the gateway.
- `frontend/src/api/citynexus.ts:915,926` — the `/agent/commands` and `/copilot/messages` routes are the two
  natural-language entries cell 1 converged on the shared `_capture_reported_disruption` statement. The
  frontend calls the same two surfaces; it does not add a third execution path.
- `frontend/src/features/agent/CopilotDock.tsx:55,58` — `accept_replan`, `create_booking` etc. appear as display
  strings for the tool list. They are labels the dock renders, not invocations.
- `frontend/src/app/V8Experience.tsx:1336` — `auto_accept_replan: true` looks like an execution bypass at a
  glance. It is not: it is a `PUT /travelers/{id}/agent-policy` that sets the traveller's autonomy envelope.
  The gateway enforces that envelope at dispatch (DelegationPolicy), so writing the policy is the user
  choosing how much autonomy to grant, not a second path executing an action.

## Net, across the whole tree

Every surface that can execute an agent action — MCP adapter, agent runtime, guardian, the two HTTP tool
routes, and the frontend's `callAgentTool` — funnels through `AgentToolGateway.dispatch` behind the pinned
catalog. The two natural-language entries now share one statement for the domain row they write. The single
agent-initiated domain write that does not cross the gateway is the reported-disruption `Event`, and closing
it needs a `report_disruption` tool in the pinned eleven-tool catalog — a contract change, named for the
commander in cell 1 and cell 2, not done here.

So "the main execution path is the one statement" is now a claim with receipts on both sides of the wire,
and the judgment criterion the building set (sweep every entry, converge what should converge, prove
behaviour unchanged by running it) is discharged within this lane's authority. Behaviour proof for the one
convergence is the whole-backend-suite before/after in `cell1_note.md`: 9 pre-existing failures on both
sides, none new.