# GPT R21 checkpoint — Context Boundary Live Run

Basis: uploaded `r21-context-boundary-live.json` and user checkpoint screenshot.

## What this checkpoint genuinely proves

This is a useful R21 intermediate result, not product closure.

The live configured AgentRun proves:
- provider/model: `hermes / cn:glm-5.3-flash`;
- status: COMPLETED;
- mission handoff did NOT expose `trigger_event_id`;
- model tool sequence: `inspect_journey -> inspect_twin -> list_replans`;
- the model discovered event context through server-owned Twin state rather than mission answer leakage;
- `list_replans` returned proposals scoped to a server-selected event;
- 57 isolated regressions passed;
- the checkpoint explicitly refuses a product-success claim because mobility was mock and the event was simulated.

This is exactly the right honesty boundary.

## Publication blocker

The screenshot names local commit `0946a6fb`.

At GPT review time, GitHub remote `codex/revolution-realtrip-recovery` still points to `8a6ac5470a1fe4ff5596517b0b4b4e03a07855db`.

Therefore GPT cannot independently inspect the R21 source diff yet.

Before further product work:
1. push the local R21 commit(s) to `origin/codex/revolution-realtrip-recovery`;
2. verify the remote head;
3. keep working on that same code branch;
4. do not reset to the taskbook carrier.

No audit detour is required.

## What this checkpoint does NOT prove

It does NOT prove Autonomous Future Synthesis.

The accepted tool trace stops at:

`inspect_journey -> inspect_twin -> list_replans`

No machine mutation or explicit no-action outcome occurred.

It also used:
- `database_scope=disposable_demo_db`;
- `mock_mobility_is_not_live=true`;
- `server_selected_latest_event.provenance=SIMULATED`;
- `product_success_claim=false`.

So the result proves context isolation and model self-inspection only.

## New semantic concern: latest event is not necessarily relevant event

The receipt says:
- model trigger ID visible: null;
- server selected latest event: CLOSURE;
- list_replans was scoped to that event.

This is safe only when there is exactly one relevant actionable event.

For a real multi-signal Journey, "latest" may not be the dominant or relevant event.

R21 final behavior should be:
- zero actionable events -> no event-scoped action;
- exactly one actionable event -> server default is acceptable;
- multiple actionable events -> require explicit model event selection from Twin, OR expose a deterministic server priority decision with reason codes;
- never silently treat newest timestamp as semantic priority.

A good server response when the model omits event ID under ambiguity is:
`EVENT_SELECTION_REQUIRED` plus a compact list of actionable event IDs/types/severity/scope.

The model then chooses an event without the mission prompt leaking it.

## Strategy-neutral completion remains the core R21 goal

Do not confuse "model discovered the event" with "model chose the recovery strategy".

R21 still needs:
- no ordered mutation step in the mission plan;
- materially different executable futures;
- a natural user mission;
- model-selected activate vs request_replan vs no-action;
- fresh future synthesis when the portfolio is insufficient;
- normal truth/mobility/Gateway authority.

## NO_ACTION should be machine-visible

If R21 wants a real three-way strategy surface:
- activate existing branch;
- synthesize fresh future;
- no action;

then NO_ACTION should ideally have a server-visible outcome, not only free-form prose.

Use the smallest mechanism:
- a structured mission outcome / conclusion receipt;
- or a tiny bounded no-action completion action.

Do NOT create a new orchestration framework.

The important property is that a completed AgentRun can distinguish:
- resolved by mutation;
- pending approval;
- deliberately no action;
- unresolved / model stopped early.

This prevents `list_replans -> final prose -> COMPLETED` from being mistaken for a resolved mission.

## Final R21 product proof requirements

The main closure run must use:
- estimate authority OFF;
- real/live mobility provider, not mock;
- truthful USER_REPORTED or PROVIDER_VERIFIED event/constraint, not SIMULATED;
- real configured GLM/DeepSeek runtime;
- no trigger ID or correct recovery action in mission text;
- at least two materially different grounded futures OR one grounded standby plus a fresh synthesized proposal;
- existing portfolio deliberately insufficient for the main event;
- model independently chooses `request_replan`;
- new future is canonical-fact + live-mobility grounded;
- Gateway/approval remains authoritative;
- revised Journey executes to COMPLETED.

Add one control run where the same strategy-neutral surface correctly produces no mutation when the event is irrelevant/low severity.
