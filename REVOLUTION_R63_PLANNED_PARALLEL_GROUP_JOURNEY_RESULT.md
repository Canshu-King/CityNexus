# Revolution R63 — Planned Parallel Group Journey

## Product result

CityNexus now recognizes an authenticated member's explicit temporary split as a member-scoped `PLANNED_SEPARATION` JourneyIntent. It binds that intent to a server-resolved future stop on the one active shared PlanVersion, projects the rendezvous and return state to the group, and does not treat separation alone as a disruption. Ending the intent or allowing it to expire does not claim that members physically reunited.

The existing route-to-rendezvous path is reused. For an active planned separation, only trusted member location plus an exact `LIVE_PROVIDER_CAPTURE` can hand a material return risk into the existing group-recovery incident/Guardian boundary. A captured replay may inform context but does not trigger this planned-split escalation. No second plan pointer, solver, or recovery state machine was added.

## Implementation and R62 closeout

- R63 implementation commit: `d99eed400108e7de4794911e6e85a47ec16844c4`.
- R62 closeout result document blob: `03c91fa62c273a8119a52c23d2550382980db69b` (`REVOLUTION_R62_GROUP_RECOVERY_FOLLOW_THROUGH_RESULT.md`).
- R62 post-review fixes were validated together with directly affected R57/R60/R62 seams; this is not a rerun of the R57–R62 campaign.

## Bounded fresh API experiment

The experiment used a fresh, isolated disposable SQLite database (`backend/_r63api20261008.db`), the normal product journey/plan/start APIs, and signed test principals. It did not reuse persisted facts from another database.

- Journey: `22222222-2222-4222-8222-222222222222`, `ACTIVE`, with two in-force members (owner and collaborator).
- Owner's intent: `acbaa10b-4120-432c-ad15-73644ec93cd3`, created by traveler `11111111-1111-4111-8111-111111111111` and member `47f4bcd4-d9cb-52a8-a586-b47d11af1e30`.
- Collaborator's separate intent: `14ad98e7-f6cf-4e48-8979-0f924f349f57`, created by traveler `66647ec7-92b5-49a9-9190-906db3c11d55` and member `c33a6018-d14e-4e67-aef3-ced9014f3e72`.
- Both rendezvous at active-plan Activity `abe4e842-249e-516f-ac43-b41695083792`, bound to active PlanVersion `55523d40-cafe-5bd2-b30a-de057ec7a839`.
- The owner and collaborator can create only their own intent; unauthenticated and body-spoofed requests are rejected by regression coverage.
- Active PlanVersion before/after: `55523d40-cafe-5bd2-b30a-de057ec7a839` (unchanged); PlanVersion count: 1; replan proposals: 0; approvals/events/recovery mutation: 0 on the no-route safe path.
- No route was available in this bounded API experiment, so return status remained `RETURN_UNKNOWN`; no ETA or physical reunion was invented.
- The named side activity was not promoted to a canonical side destination.

The route-risk tests use controlled test-only route-operation receipts, including a negative control where `CAPTURED_REPLAY` is insufficient and a positive control where the exact live-provenance boundary admits the existing handoff. Those receipts and the monkeypatched Guardian call are regression fixtures, not a live Valhalla or live Guardian run.

## Validation

- Focused backend set (`test_r63_planned_separation.py`, `test_r57_group_presence_operator.py`, `test_r60_collective_recovery_apply.py`, `test_r62_group_recovery_followthrough.py`): **41 passed**, 4 existing deprecation warnings.
- Dedicated fresh-database API experiment: **1 passed**.
- Two-context Playwright run: **2 passed** including the real-product-API seed setup and owner/admin UI test; isolated ports `43921/43922`, fresh `_r63ui20261008b.db`, external AI disabled. The R63 UI read-model transitions were mocked; this is not a live provider or Agent run.
- Frontend TypeScript: passed.
- Vite production build: passed; Vite emitted its existing large-chunk advisory.
- Python `compileall`: passed.
- `git diff --check`: passed.

`CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` throughout. No external Agent/model call, live route-provider call, real device attestation, or physical-world execution is claimed. The signed principals in tests are test/operator-issued credentials, not proof of a complete public login/identity-provider integration.

## Boundary

R63's user-visible product step is real at the local API/domain/UI boundary: one member can deliberately leave temporarily while the shared Journey remains authoritative, and the product can distinguish unknown, advisory, and eligible return risk without fabricating an ETA. This strike does not claim that an actual traveler separated in the physical world or that a live Valhalla route was captured. Safe unknown plus zero mutation is the observed bounded outcome; test-only risk fixtures prove the guarded handoff seam.
