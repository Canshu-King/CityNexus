# ORD main-exec-path, cell 1 — the reported-disruption Event row now has one statement

Building (ORDERS, read at the top of this lane's slot): make "the main execution path" a single project-wide
statement — when another module wants to execute something it must call the main path, not grow its own.
Measure it myself: sweep the whole tree for execution entries, judge each for whether it should converge,
and after converging run it once to prove behaviour is unchanged.

Tip read for this cell: `2e2ddbaf72eed9565fd8b18ea9b8216061269f57` (mirror branch), fetched and work-cut.
Branch: `review/cff87c64-main-exec-path-r1` (cut from the tip; only `backend/app/main.py` and this folder differ).

## What the main path is, in this codebase's own words

`contracts/AGENT_RUNTIME_ARCHITECTURE.md` names it:

```
-> agent-mcp safe adapter
-> /api/v1/agent/tools/{tool}
-> AgentToolGateway
-> persisted DelegationPolicy
-> server-derived proposal/Event/Journey/C4 facts
-> existing deterministic accept-time gate
-> PlanVersion/Activity/Commitment domain truth
```

The gateway (`backend/app/agent/gateway.py:357 dispatch`) is that path: an allowlist check, an audit row,
then a per-tool handler. Two HTTP routes feed it (`main.py` call_agent_tool x2). The contract's rule that
matters for this building: domain truth is written *behind* the gateway's policy/gate boundary.

## The sweep (whole tree), and the per-entry judgment

Instrument: `review_exec_inventory_r1.py` (in the branch root; read-only). It walks `backend/app/**.py`,
finds every `session.add/add_all/merge(` of a domain-truth model (PlanVersion/Activity/Commitment/Event/
JourneyMission), names the enclosing function, and buckets each site:

- VIA_MAIN_PATH — the enclosing function routes through AgentToolGateway.dispatch.
- AGENT_WRITE_NO_GATEWAY — agent/copilot context but no gateway call on the function body.
- PRODUCT_WRITE — a user-driven domain mutation (trip edits, bookings, weather, commerce). These are the
  domain truth the main path is *allowed* to call; they are not execution entries in this sense.

Counts before -> after: AGENT_WRITE_NO_GATEWAY 3 -> 2, VIA_MAIN_PATH 0, PRODUCT_WRITE 19 (unchanged).
`inventory_before_r1.txt` / `inventory_after_r1.txt` are the two tables.

Per the building, here is every AGENT_WRITE_NO_GATEWAY site judged:

1. `main.py` `_capture_copilot_disruption` — **converged in this cell.** It built the reported-disruption
   `Event` itself. (The `run_agent_command` Event block was the third pre-convergence site and is folded in
   with it; the sweep attributed one of them to the shared function afterwards.)
2. `agent/guardian.py:175` `_recovery_mission` and `agent/mission.py:537` `create_mission` — **left as-is,
   with reason**: both are called from the agent's own command/guardian flow (main.py create_mission x3,
   guardian.py _recovery_mission x1). They write `JourneyMission`, which is the mission bookkeeping of the
   main path, not a separate execution of a domain action. Converging them into the gateway would change
   what the path does, not remove a duplicate. Noted here so the judgment is on the record, not silent.

The 19 PRODUCT_WRITE sites are the user-driven domain the main path calls into; the building does not ask
to route a traveller's own trip edit through the agent gateway, and doing so would be a behavioural change.

## What converged, and why behaviour is unchanged

The two entry points each built the same domain row — a reported disruption becoming an `Event` — with the
same fields but a different payload shape, provider key and audit footprint:

- `/api/v1/journeys/{id}/agent/commands` -> `run_agent_command`: `provider_key="user-command"`,
  `source="agent_command"`, payload semantic = the whole envelope, `occurred_at = target.occurred_at or now`,
  no per-event audit (it audits the mission next).
- `/api/v1/journeys/{id}/copilot/messages` -> `copilot_message` -> `_capture_copilot_disruption`:
  `provider_key="user-copilot"`, `source="copilot"`, payload adds `simulation_only: False` and an expanded
  semantic, `occurred_at = target.occurred_at`, records `copilot.disruption.captured` and commits.

Both now call `_capture_reported_disruption(session, journey, ...)`, which takes the per-caller specifics
(description, provider_key, source, semantic payload, occurred_at fallback, audit action, commit,
payload_extra) and reproduces each caller's exact row, audit and receipt from them. The unresolved-target
early-return is the shared one; `run_agent_command` re-wraps it into its own response shape (it always did).
One file changed: `backend/app/main.py` (four hunks: add the shared function; the two callers call it).

Behaviour-unchanged proof (run once, whole backend suite, both sides):

| run | passed | failed | skipped | xfailed | error |
|---|---|---|---|---|---|
| clean tip | 1719 | 9 | 16 | 1 | 0 |
| this branch | 1719 | 9 | 16 | 1 | 0 |

The 9 failures are the same test ids on both sides (anywhere_gates g5, anywhere_lock_duration g9b,
anywhere_matrix_truth g14a+g14c, anywhere_provider_independence g8a, anywhere_provider_truth g10,
qoder_g3_xproc_http g3, ord0479 H07, ord0495 G07) — every one pre-existing on the tip, none introduced
here. The two focused behaviour suites (test_v15_copilot, test_agent_mission_runtime = the two entry points,
9 tests) pass on both sides. `test_g3` is load-flaky under multi-file runs but passes in isolation and in
its own file on this branch — recorded here so it is not mistaken for a regression. One hermes transport
probe (test_v18_hermes_r20_transport_reliability_probe) is excluded from both runs: it imports `mcp`, which
is not installed in this venv, and errors at collection on the clean tip too — pre-existing environment
gap, unrelated.

## What this cell does NOT claim

- It does not add a gateway tool. The strongest convergence — routing the disruption capture through
  `AgentToolGateway.dispatch` (so it would get the allowlist / DelegationPolicy / tool-audit) — means
  adding a tool to a pinned catalog (V1 six / V2 eleven). That is a contract change I will not make
  unilaterally; it is the natural next cell and needs the commander's call.
- It does not touch the 19 product-write sites or the mission bookkeeping (reasons above).
- It moves no authority: the tip is untouched; this is a candidate branch only.