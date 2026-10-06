# ORD main-exec-path, cell 4 — the reported-disruption Event now crosses the main path

Same building. This cell cuts on the tip `e9b231b876c777bc592923bc41d8c397a577e691` (which already carries
cells 1–3, landed), on branch `review/cff87c64-main-exec-path-r2`. Cells 1–3 left one thing open and named it
for the commander: the two natural-language routes wrote the domain `Event` *beside* the gateway rather than
*through* it, so that one agent-initiated write never got the allowlist, the tool audit, or the policy. This
cell closes it.

## What changed

The disruption is now a typed tool, `report_disruption`, and both natural-language routes dispatch it instead
of building the row themselves.

- `backend/app/agent/contracts.py` — `AgentAction.REPORT_DISRUPTION`.
- `backend/app/agent/tool_catalog.py` — a `ToolDescriptor` in `TYPED_TOOLS` (V2), `mutates_domain_truth=True`,
  no money, no C4. Receipt: `catalog_shape_r2.txt` — the pinned **V1 six are unchanged**, V2 is now twelve and
  `report_disruption` is in V2 only. Putting it in `TOOLS` would have changed the pinned V1 catalog; the gate
  `test_agt10_19_catalog_contains_only_v1_allowlist` caught exactly that on the first attempt, and it is the
  reason the descriptor lives with the typed tools.
- `backend/app/agent/delegation_policy.py` — `REPORT_DISRUPTION` classified beside `REQUEST_REPLAN`
  (ALLOW_AUTO, `PROPOSAL_ONLY` / `DOMAIN_TRUTH_NOT_ACTIVATED`). This is the traveller stating a fact the server
  then derives; it moves no money and touches no protected commitment, so the default ADVISORY envelope admits
  it — which is exactly how these two routes already behaved before they were tools (the focused tests enforce
  that: a disruption report creates an Event under the default policy).
- `backend/app/agent/gateway.py` — the `report_disruption` handler: validates journey + `event_type` + `reason`,
  evaluates the policy, derives `provider_key`/`source` from a fixed two-entry map (so a caller cannot write an
  arbitrary provenance key, and the two surfaces keep their own stored keys), and calls the landed
  `_capture_reported_disruption` with the caller's `semantic`/`simulation_only` so each stored row is byte-for-byte
  what that surface wrote before.
- `backend/app/schemas.py` — `AgentToolCall` gains `event_type`, `source`, `semantic`, `simulation_only`.
- `backend/app/main.py` — `run_agent_command` and `_capture_copilot_disruption` each dispatch `report_disruption`
  through `AgentToolGateway(session).dispatch(...)` instead of calling `_capture_reported_disruption` directly.

## Why it now crosses the boundary

Every tool dispatch writes an `agent_tool_requested` audit row (`gateway.py` dispatch) before the handler runs.
So a reported disruption now leaves a tool-audit trail it never had, and it is evaluated against the traveller's
delegation policy. That is the concrete difference between "the write happened" and "the write happened on the
main path".

## Behaviour-unchanged proof (whole backend suite, same tip, both sides)

| run | passed | failed | skipped | xfailed |
|---|---|---|---|---|
| clean tip e9b231b8 | 1718 | 11 | 16 | 1 |
| this branch | 1720 | 10 | 16 | 1 |

The branch's failure set is a subset of the tip's: every red on the branch is also red on the clean tip
(comment-anchor drift ×3, anywhere g5/g9b/g14a/g14c/g8a/g10, g3_xproc_http). Zero new failures. The suite is
two tests *more* green because of the one added arm. `catalog_hydration` is red on the clean tip and green here —
it is load-flaky under the full run (it passes in isolation on both sides), not a fix I claim.

The added arm, `test_v15_copilot.py::test_v15_disruption_report_crosses_the_main_path_as_a_tool_call`, reads the
`agent_tool_requested` audit row and asserts it names `report_disruption`. It was run against the pre-change
product code on this same tip and **failed** there (the row does not exist), then passed with the change — so it
is a real discriminator, not a tautology.

## The one thing the commander still decides

Adding a twelfth V2 tool is a (small, additive) contract change: the MCP surface and the catalog both grow by
one. I chose the conservative policy class (ALLOW_AUTO, proposal-only, no money / no C4) and the conservative
placement (V2 only, V1 pinned six untouched) precisely so the change is minimal and reviewable. The change is on
a branch and lands only on the commander's word; nothing here moves the tip.