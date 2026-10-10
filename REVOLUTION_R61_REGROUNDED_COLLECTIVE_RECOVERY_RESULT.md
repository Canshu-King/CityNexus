# Revolution R61 — Re-grounded Collective Recovery Result

## Result

**Bounded R61 domain/API closure: PASS. Live provider/Agent product closure: NOT CLAIMED.**

When a previously agreed group recovery becomes unexecutable, CityNexus now preserves the old decision as history, invalidates its spend authority and proposal, and starts or reuses one PLAN_ONLY re-ground mission for the current incident and RecoveryEpoch. The Journey remains unchanged. A new shared decision can be opened only from current grounded feasible proposals classified as `HUMAN_TRADEOFF_REQUIRED`; old responses are not carried into it.

The stale-consent path is also closed when the RecoveryEpoch has already been superseded and there are not enough current grounded options: it starts the bounded re-ground instead of presenting a hollow re-vote. Repeated apply attempts reuse the same incident/epoch mission. Malformed server-owned epoch-generation data fails closed with 409 rather than surfacing as a 500.

## Evidence boundary

This was one bounded, local test/domain closure against the existing R60 API/domain fixture, as permitted when provider-grounded setup is unavailable. The test stubs Hermes readiness as unavailable (`provider=fixture`, `model=fixture`); CityNexus persists the R61 mission as `FAILED_EXTERNAL` / `RECOVERY_REGROUND_EXTERNAL_AGENT_BLOCKED`, preserves the Journey's active PlanVersion, and does not create fake proposals or mutate the Journey.

No real external Agent/model call, fresh provider-backed Journey, live place/route acquisition, or physical-world execution was performed in this run. The browser test uses mocked read-model responses to verify the two-member presentation; backend state transitions are exercised by API/domain tests. This report therefore does not claim provider-live or live Agent closure.

No fresh product experiment was created, so there are no reusable Journey, incident, RecoveryEpoch, proposal, clarification, receipt, or re-ground mission identifiers to report. The fixture IDs are generated per test and are not presented as a product-run receipt.

## Implementation

- Implementation commit: `05a45d917156f574327b3c92d3f22d517918eb4a`
- Branch: `gpt/revolution-r33-open-world-journey-adaptation`
- Changes cover the R61 bounded re-ground continuation, current-epoch proposal scoping, server-owned typed completion, operator projection, traveller-facing copy, and two-member UI rendering.
- On current-option shortage, stale authority cannot be spent and no empty collective room is created. A current-room path remains distinct from a re-ground path when current grounded options already exist but renewed authority is required.
- No WB2api/provider behavior or R60 mutation/spend authority was changed.

## Validation

| Check | Result |
| --- | --- |
| R61-focused backend tests: `tests/test_r60_collective_recovery_apply.py -k r61` | 7 passed, 6 deselected |
| Focused collective lineage: R60 apply, R59 group recovery plan, R29 disagreement mediation, R30 collective authority receipt, and collective operator tests | 80 passed |
| Python compile check (`compileall` for app and focused test module) | Passed |
| Frontend TypeScript typecheck | Passed |
| Frontend production build | Passed; existing large-chunk advisory remains |
| Focused two-context Playwright spec (`r60-group-recovery-apply.spec.ts`) | 3 passed, including 1 R61 read-only/regrounded-room case |
| `git diff --check` | Passed |

The focused backend suite emitted four existing deprecation warnings (Starlette/httpx test client and FastAPI `on_event` lifecycle API); no test failures.

## Remaining boundary

R61's server behavior and traveller-facing transition are covered locally, but the taskbook's provider-grounded product experiment was not available in this run. The next meaningful closure is a single fresh provider-backed Journey and real configured Agent run if the environment supports them—not another historical R58–R60 campaign or a claim inferred from these fixtures.
