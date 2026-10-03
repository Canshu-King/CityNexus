# Revolution R25 — Strategic Horizon Steward

## Result

R25 is an implemented but not closure-grade checkpoint.

The product now exposes a bounded remaining-trip horizon and a server-governed typed `TAKE_NOW` / `DEFER` surface. It does not yet claim the required live Agent W1-defer → W2-revalidate → execute → Journey COMPLETED result.

The missing closure is intentional: the available live Agent call through the configured WB2api GLM endpoint did not return an AgentRun within 90 seconds, and the exercised active Nara Journey exposed only one remaining horizon window. No model prose, mock mobility, or synthetic second window was counted.

## Source binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- starting/base SHA: `dc93b91db9878690465349c4c2f76888870b6f49`
- final experimental SHA: `2a4b53a3daf958de939abec0beeb5bc453d27d3e`
- substantive commits: `26b5139b`, `2a4b53a3`
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- configured runtime: `HERMES_COMPAT_ENDPOINT`, model `cn:glm-5.3-flash`
- native Hermes/MCP runtime: not proven/configured; no claim made

## Implemented behavior

1. `learn_from_journey` now consumes source OutcomeEvent IDs idempotently. Reflecting a Journey again does not refresh `created_at`, `expires_at`, strength, or evidence count. Cleared and expired rows retain their source IDs, so replay cannot resurrect them.
2. Independent Journeys reinforce bounded evidence with a capped noisy-OR per Journey. Opposing signals retain provenance and reduce effective soft strength. Learned data remains `LEARNED_SOFT` and cannot become authority, budget, capability, opening, mobility, or commitment truth.
3. Preference fit reports current mission, persisted explicit preference, and learned-soft contributions separately. The effective soft ranking precedence is `CURRENT_EXPLICIT_MISSION > EXPLICIT_PERSISTED_PREFERENCE > LEARNED_SOFT > NEUTRAL`.
4. `JourneyTwin.context.remaining_opportunity_horizon` is bounded to two windows and exposes window boundary, next commitment, optional budget, canonical opening/cost, category/tags, preference fit, resource use, and mobility evidence state.
5. Future route evidence is labelled `FROZEN_PLAN_EVIDENCE` when it comes from the active PlanVersion and `STALE / REVALIDATION_REQUIRED` when missing. The projection explicitly records `future_live_traffic=false`; inspection does not mutate the active plan or reserve a future activity.
6. `conclude_recovery` accepts a typed `horizon_decision`. `DEFER` is only valid with `NO_ACTION`; Gateway rechecks two grounded, individually feasible windows, higher later preference, and scarce combined budget. A model cannot make a proposal and then claim a strategic defer by prose alone.

## Machine evidence

Live HTTP Twin read on active Nara Journey `b926e1f1-e705-4f03-a69f-1585a502faa8`:

- Journey status: `ACTIVE`
- active PlanVersion: `27b9b274-5176-5633-b3bb-37e7526c8c89`
- horizon max: `2`
- observed windows: `1` (therefore insufficient for the R25 DEFER contract)
- candidate: `real-place-22cf72809897ff4c7f312fcf`, category `garden`
- opening: provider-normalized `09:00–16:30`, Monday/Wednesday–Sunday
- cost: `KNOWN`, `1200 JPY`, source `overpass`
- mobility: `FROZEN_PLAN_EVIDENCE`, provider `valhalla-http`
- route pair: `real-place-1ffd66e7224682f5558f1579` → `real-place-22cf72809897ff4c7f312fcf`
- optional budget remaining: `13000` minor units
- `future_live_traffic`: `false`
- status: `GROUNDED`

The raw Twin capture was written during execution as `r25-twin-existing.json`; it is a local disposable runtime artifact and is not used to replace the committed machine contract.

Configured runtime status before the Agent attempt:

- `runtime_identity=HERMES_COMPAT_ENDPOINT`
- `hermes_compat_configured=true`
- `ai_state=CONFIGURED_UNVERIFIED`
- `native_mcp_proven=false`

The strategy-neutral Agent command asked the model to inspect the active Journey/Twin/horizon and choose whether to preserve scarce budget. The HTTP call was stopped after more than 90 seconds without a response or persisted AgentRun. This is recorded as an integration timeout, not as NO_ACTION, DEFER, or success.

## Tests

- R25 strategic horizon tests: `2 passed`
- final R20–R23 lineage run: `35 passed`
- combined focused run including R24 memory tests: `40 passed`
- Python compile check: passed
- warnings: one existing Starlette/httpx deprecation warning

## Honest remaining blocker

The implementation needs one clean, live execution fixture—not a golden answer—with an ACTIVE provider-backed Nara Journey containing two materially distinct, grounded future windows. The current sampled active Journey has only one. The configured GLM endpoint also needs to return within the bounded runtime budget.

Until both are true, R25 cannot honestly claim:

`W1 feasible → Agent DEFER → W2 current → live revalidation → Gateway → activity execution → Journey COMPLETED`.

## Next bounded experiment

Create one fresh active Nara Journey from the existing real provider catalog, retain two independent future windows with live/frozen mobility provenance, then rerun the same strategy-neutral Agent surface with a bounded request timeout. Capture the model's typed decision, server DEFER validation, W2 revalidation, Gateway approval, and the normal execution state machine. If the model endpoint times out again, stop that attempt and preserve the exact configured-provider timeout as the blocker; do not substitute deterministic fallback prose for Agent autonomy.
