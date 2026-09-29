# R77 Hermes truth-projection repair

## Source binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:/moodle/CityNexus-Revolution-RealTrip-Recovery`
- starting commit: `4ee14229f80691cf8e5ea913375c0caf83ac02ee`
- prior clean product code: `8c05fb4373efc866fbcc30e49e6177be4e07721a`
- mobility projection repair commit: `001882a34e479b6c111937aeee0608ca92745559`
- used-edge projection repair / final experimental code commit: `f7cc3d45888035a9abbb9b88397c70b149251333`
- clean before product calls: yes (`git status --porcelain` empty)
- authority/mainline merge: none

## Scenario

The same disposable R77 Journey was used throughout:

- destination: `苏州市`
- city: `CN-SUZHOU`
- journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- selected plan: `fbb534a5-b307-5597-a5e7-65a91a4c163c`
- real provider-backed places: `real-place-8bc850f117297987997c87cf` and `real-place-ba7377353c422c39dfd752b7`
- disposable database: `backend/r77_selectable_probe.db`

The selected PlanVersion held a Valhalla snapshot with 72 facts. The plan's actual consecutive activity edge is:

```json
{
  "used_edge_ids": [[
    "real-place-8bc850f117297987997c87cf",
    "real-place-ba7377353c422c39dfd752b7"
  ]],
  "minutes": 42,
  "provider": "valhalla-http",
  "route_provenance": "LIVE_PROVIDER_CAPTURE",
  "fact_quality": "LIVE_PROVIDER_CAPTURE",
  "degraded": false
}
```

## Defect and repair

Before `001882a3`, `_twin_snapshot()` initialized `context.mobility` as `mock-mobility / deterministic-offline` whenever there was no active C4 commitment, even when the selected PlanVersion carried frozen provider evidence. The Plans API and the agent inspection therefore disagreed.

The repair exposes a compact summary of the selected plan's persisted evidence:

- `provider` / `source_provider`
- `snapshot_id`
- `fact_count`
- `fact_quality`
- `route_provenance`
- evidence-backed `used_edge_ids` and `used_edges`

Precedence is preserved: an active C4 commitment's persisted replan snapshot/fact still overrides the context used for that commitment window. The selected-plan summary is used when that override is absent. Missing or incomplete evidence continues to use the existing honest mock fallback; no fact is synthesized.

## DeepSeek Builder execution

The WorkBuddy OpenAI-compatible endpoint was called in process memory with no credential persisted or printed:

- model calls: `cn:deepseek-v4-pro`, then `cn:deepseek-v4.1-flash`
- role: Builder proposal for the bounded `_twin_snapshot()` repair
- result: runtime calls executed; provider returned reasoning/truncated final content, not an authoritative patch or PASS
- contribution: independently pointed to selected-plan frozen evidence as the fallback precedence before mock, while the actual patch was made from the source trace and deterministic tests

This was a WorkBuddy-compatible DeepSeek model call, not native CityNexus DeepSeek Responses runtime.

## Hermes Operator execution

Runtime status on the clean experimental service:

```json
{
  "runtime_identity": "HERMES_COMPAT_ENDPOINT",
  "native_mcp_proven": false,
  "deepseek_configured": false,
  "hermes_compat_configured": true,
  "ai_state": "CONFIGURED_UNVERIFIED"
}
```

The final bounded operator run:

- mission: `6a894604-c171-441c-9cc4-e72e394ca14b`
- AgentRun: `ed5938a0-c8d1-4e7b-af5e-6778e72f5271`
- provider: `hermes`
- model: `cn:deepseek-v4.1-flash`
- runtime: `HERMES_COMPAT_ENDPOINT`
- status: `COMPLETED`
- tools, in order: `inspect_journey`, `inspect_twin`, `list_replans`
- all three: `COMPLETED / ALLOW_AUTO`
- mutation: none

Machine-returned operator lines:

```text
AUTHORITY=PLAN_ONLY; read-only, all three calls ALLOW_AUTO
MOBILITY=provider=valhalla-http, snapshot=52541f63-1d56-49c7-b371-73984268e0c5, fact_quality=LIVE_PROVIDER_CAPTURE, degraded=false
USED_EDGE_IDS=[["real-place-8bc850f117297987997c87cf","real-place-ba7377353c422c39dfd752b7"]] -> 42 min (provider valhalla-http, LIVE_PROVIDER_CAPTURE)
GAPS=No replan proposals exist and journey has no confirmed capabilities or commitments.
```

## Product readback after the run

- `GET /api/v1/journeys/{journey_id}`: HTTP 200; status `PLANNED`; active pointer is the selected plan
- `GET /api/v1/journeys/{journey_id}/plans`: HTTP 200; plan `SELECTED`, `selectable=true`, `is_current=true`, `stale=false`, total cost `12000 CNY`
- `GET /api/v1/journeys/{journey_id}/twin`: HTTP 200; projection `READY`; mobility and used-edge fields agree with the selected plan evidence
- Journey remained `PLANNED`; no agent mutation occurred

## Focused gates

```text
py -3.13 -m pytest -q \
  tests/test_revolution_r77_recovery.py \
  tests/test_qoder_beijing_catalogue.py \
  tests/test_qoder_catalog_reason_code.py \
  tests/test_qoder_generic_compose_reason_codes.py \
  tests/test_qoder_mobility_evidence_sources.py \
  tests/test_provider_runtime_gate.py \
  tests/test_agent_runtime_gate.py \
  tests/test_agent_authority_v2_actions.py \
  tests/test_gpt_adversarial_provider_hardening.py

71 passed, 1 warning
```

The warning is the existing Starlette/httpx deprecation warning.

## Frontend gates

The isolated frontend had no installed dependencies initially. `npm install --no-package-lock` populated only the ignored local `node_modules`; it did not change `package.json` or `package-lock.json`.

```text
npm run typecheck  -> passed
npm run build      -> passed
```

Vite emitted only its existing chunk-size advisory; the production bundle was generated successfully.

## Truth boundaries

- `P7=false`
- `MOCK != LIVE`
- `UNKNOWN cost != known free`
- no synthetic mobility was relabeled as live
- no provider-only result was treated as product authority
- no authority/mainline merge
- no raw API credential in the tree or receipt
