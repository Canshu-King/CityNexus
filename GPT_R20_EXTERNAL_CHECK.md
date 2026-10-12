# GPT external check — R20 -> R21

Inspected:
- uploaded `REVOLUTION_R20_AUTONOMOUS_BRANCH_ARBITRATION_RESULT.md`
- full R20 delivery ZIP raw machine receipts
- remote code/report commits:
  - `8cb2a10ceb09bcb458649897765f06c72502cdc9`
  - `8a6ac5470a1fe4ff5596517b0b4b4e03a07855db`
- current remote experiment branch `codex/revolution-realtrip-recovery`

## R20 verdict

R20 is a genuine Revolution step.

The accepted machine trace proves:
- fresh ACTIVE Journey state;
- two fresh server-owned mobility standby branches;
- real configured GLM runtime;
- model tool calls `inspect_journey -> inspect_twin -> activate_standby`;
- correct standby plan ID was not supplied in mission user text;
- deterministic trigger matcher rejected a semantically wrong WEATHER branch;
- Gateway required confirmation before mutation;
- approved standby activation atomically replaced the active plan;
- siblings were retired;
- revised Journey completed with live Valhalla used-edge evidence.

This is materially beyond R19.

## Important qualification 1 — strategy choice is still compiler-biased

The R20 system prompt correctly tells the model to choose among:
- `activate_standby`;
- `request_replan`;
- `NO_ACTION`.

However the mission payload also includes a deterministic ordered mission plan. Current `build_mission_plan()` inserts:

```text
inspect_journey
inspect_twin
arbitrate_standby -> activate_standby
...
request_replan
```

for ordinary autonomous missions.

That mission plan is embedded in the system prompt via `mission_payload(mission)`.

Therefore R20 cleanly proves:
- the model chose WHICH matching standby to activate;

but it does not yet cleanly prove:
- the model independently chose standby activation over fresh replan or no-action without a deterministic action-order prior.

R21 should remove that strategy bias without removing the authority envelope.

## Important qualification 2 — the two primary branches were not materially different futures

The R20 primary portfolio contained:
- `route_plus_20`;
- `route_plus_30`.

Both were:
- 4 activities;
- total cost 170000 JPY minor;
- same affected activity IDs;
- same affected Place IDs;
- same allowed event/provenance classes.

The underlying counterfactual receipts also show both P80/P95 branches dropping the same future slot with the same 60-minute schedule drift.

So the model selected between two risk-scenario labels that likely materialized into the same or nearly the same executable itinerary.

That is useful arbitration plumbing, but not yet strong evidence that the Agent can compare genuinely different futures.

R21 must require at least two materially distinct executable outcomes.

Examples:
- KEEP + retime;
- DROP optional stop;
- REPLACE with grounded indoor/nearby Place;
- fresh replan creating a new candidate.

Do not count two scenario labels over the same materialized itinerary as two futures.

## Important qualification 3 — user/event text still scaffolds the strategy

The final mission user text says, in substance:

"inspect Journey/Twin/standby portfolio, then choose a compatible standby, or request_replan, or NO_ACTION."

This is transparent and does not leak the correct plan ID, but it still tells the model the exact recovery strategy menu.

R21 should use a more natural disruption mission and let the system/tool surface expose capabilities.

The final proof should not contain:
- the correct plan ID;
- the correct action;
- an explicit ordered recovery recipe.

## Important qualification 4 — runtime observability is internally inconsistent

The accepted AgentRun used:
- provider `hermes`;
- model `cn:glm-5.3-flash`;
- HERMES_COMPAT_ENDPOINT;
- persisted real tool steps.

But the mission/runtime payload still reports `ai_state=DISABLED_BY_OPS` in the same accepted trace.

That is observability drift, not an autonomy failure.

Fix it inline if practical:
- runtime availability/status should distinguish native MCP disabled from Hermes-compatible runtime active;
- do not let UI/ops report "AI disabled" while a real model is executing.

Do not make this a separate project.

## Important qualification 5 — interrupted runs leave orphaned RUNNING rows

The R20 report notes earlier compatibility attempts left orphaned RUNNING mission/run rows after server restart.

That does not invalidate the success trace.

R21 should add a bounded startup/run reconciliation:
- stale RUNNING rows older than a configured threshold -> INTERRUPTED/ABORTED with reason;
- do not silently keep zombie runs.

Again: small reliability repair only.

## Revolution frontier

Do not make R21 "more branch arbitration".

The next leap is Autonomous Future Synthesis:

> remove deterministic strategy-order hints, give the model materially different futures, and require it to decide whether an existing future is good enough. If not, it must autonomously create a new grounded future through request_replan / fact acquisition / mobility capture, while deterministic truth and Gateway remain authoritative.

The key new machine fact is not "Agent can pick a branch".

It is:

> Agent knows when the futures it has are insufficient, and can create a better one without the wrapper telling it which strategy to use.
