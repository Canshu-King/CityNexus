# Hermes R20 — request_replan transport reliability

R20 verifies the agent-mcp transport boundary exposed by R19. The current
backend request_replan contract and proposal authority remain unchanged. Only
the server-owned HTTP client's request budget changes: `request_replan` gets
120 seconds because generation may persist proposals before a large response is
ready; other tools remain at 15 seconds.

The probe runs the existing disposable R4 direct planner and stdio MCP parity
scenario. It requires a real stdio MCP response, full
`hermes-replan-proposal-view.v1`, semantic parity, unchanged Journey authority,
one ACTIVE PlanVersion, exact V2 tool surface and loopback-only service
children. The raw R4 receipt remains untouched.

If the legacy probe's post-run SQLite evidence digest encounters an isolated
cleanup error after all core assertions pass, R20 records that exact blocker as
`PASS_WITH_EVIDENCE_CLEANUP_BLOCKER`; it is not silently converted to PASS.

Runtime is not model-backed: `NOT_USED`, `PLAN_ONLY`, `P7=false`. No acceptance,
booking, payment or commitment mutation is performed.
