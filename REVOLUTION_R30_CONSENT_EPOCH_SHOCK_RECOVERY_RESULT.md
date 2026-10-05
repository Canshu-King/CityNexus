# Revolution R30 live strike result

## Status

`R30_LIVE_BLOCKED`: the live causal chain reached the fresh approval boundary, but the final continuation was refused by the existing collective mediation gate. No final proposal was accepted and no execution mutation was forced after that refusal.

The strike database is [r28-live-592728682e7eb64c.sqlite3](backend/r28-live-592728682e7eb64c.sqlite3). The machine evidence is [R30_MACHINE_VERDICT.json](output/revolution-r30-live-20261006/R30_MACHINE_VERDICT.json), with the compact [R30_LIVE_RECEIPT.json](output/revolution-r30-live-20261006/R30_LIVE_RECEIPT.json).

## Verified causal chain

1. The real Hermes Agent opened the first collective surface (`AgentRun ea95a890-6fa7-4c9e-b9f3-b79349de6b59`), and authenticated members made distinct choices.
2. The real external mediator (`AgentRun d419837b-7db8-4426-9bb0-bb57052b4f4b`) created a server-owned improved future and a renewed consent surface.
3. The old resolved consent durably stored:
   - E1: `4e17c402fc53bd01de2ff8e113d91a364adbf968e0e01f11b83146d22732bb07`
   - W1: `74e41924218fb32be8def8fd227fa0d45fa7eb727b141edb502747608e6f2600`
   - mediator mission: `f9fb2239-c3a8-4e33-b988-ceb5db163f34`
   - selected proposal: `86e29664-2e46-44ed-a524-931f120c03ac`
4. Normal provider-backed closure event `9b1199b0-0047-4bbc-bbe8-cfbe7529391a` arrived after E1/W1, targeted future Activity `8a9d4822-5f9e-4f3a-8342-7752ed682cc2`, and left the old proposal `PRESENTED`.
5. W changed to `dcee9be66c58279f36c60f411318a1974f14f5752a5b0783b0a11959a8a721ae` while the old selected plan remained `CANDIDATE`.
6. Replaying the old mutation reached the core and returned the exact refusal `COLLECTIVE_CONSENT_WORLD_EPOCH_STALE` (`AgentRun 0422ea22-b5f1-4216-be4f-f92f813950a6`).
7. A real recovery Agent (`AgentRun 1fdad295-a060-4286-a068-103013a7264b`) executed `request_replan` and `request_collective_decision`. Fresh authenticated responses resolved mission `d117022b-6b2f-447d-9c0b-0d6272a48556` with:
   - E2: `cda5e51f2722c3c0f7cd3f40d31e7f95a409baf6efd10b904bf9effe519873ef`
   - W2: `c67ad7583d6238fce2adcf44d8816eab3ca4c9a5f53f252f00d220787f702443`
   - selected proposal: `d9152f9e-e43f-42bd-93c2-6ab029178f6b`
   - two authenticated response audits.

## Narrow integration repair

- `backend/app/main.py` now carries a provider closure attached to a future candidate through impact validation while anchoring the actual replan operation to the current mutable Activity. The normal server proposal path then succeeds for the future-candidate shock.
- `backend/app/agent/gateway.py` now maps a semantic future candidate back to a server-validated base-plan mutation anchor before evaluating acceptance facts. The fresh approval facts consequently report `impact_target_server_validated=true`.

## Remaining live blocker

The single permitted fresh continuation rerun reached the normal approval boundary (`AgentRun 41376976-c155-4000-bd20-2258c6ce5dda`). Approval then returned:

```text
COLLECTIVE_MEDIATION_SELECTED_PLAN_REQUIRED: collective mediation must be resolved before mutation
```

`pending_resolved_mediation_selection()` still resolves to the older mediator mission `f9fb2239-c3a8-4e33-b988-ceb5db163f34`, while the fresh E2/W2 mission is `d117022b-6b2f-447d-9c0b-0d6272a48556`. This is recorded as a real server-side lineage blocker. The live run was not retried again, and no database row was rewritten to manufacture acceptance.

Therefore the final exactly-once acceptance and execution continuation are **not proven** in this strike; the verifier reports them as `BLOCKED`.

## Verification

```text
python -m compileall -q app
python -m pytest -q tests/test_r29_disagreement_mediation.py tests/test_r28_authenticated_member_principal.py tests/test_r28_durable_approval_continuation.py
39 passed, 4 warnings
```

The machine verifier reports 9 proven causal claims and 2 blocked final claims. `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` was kept in force.
