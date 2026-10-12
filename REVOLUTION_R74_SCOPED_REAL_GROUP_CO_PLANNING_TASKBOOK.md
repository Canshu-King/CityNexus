# Revolution R74 — Real Companion Co-Planning, Not Test-Only Owners

## Exact starting baton and evidence boundary
Stay on `gpt/revolution-r33-open-world-journey-adaptation`, beginning at `e00db435fdb95b86b0e32698222c977a87b3aae1`.

- Codex R73 implementation: `47918f514c4b93398e9f33e9f3b34c7ab63d7845`. Report HEAD `1221cc3fa2c04f7823f7be6531a73effd5efe65e` (`REVOLUTION_R73_PROMOTE_DISCOVERY_TO_SHARED_JOURNEY_RESULT.md`). Its isolated Playwright **1 passed**, backend R72/R73 **5 passed**; the v1->v2 active PlanVersion transition and C4 preservation occurred with an explicitly labelled `R73-TEST-REPLAY-EXPLICIT-FIXTURE` route and all three test members changed to `OWNER` by test-only setup. No external ProviderCall or AgentRun and no real GPS.
- GPT R73 follow-up edits **pushed, NOT locally run**:
  - `0bfdd6ecd98099a446e2fc6967aebb694a7c631b`: server-scoped read-only proposal trade-off, and `viewer_can_propose` bound to the existing `JOURNEY_UPDATE` capability.
  - `97741cff535647cf06872918d92ffc1455035ae3`: API typings.
  - `c34fc139f3cc37766255f350698dbea44c3d1757`: Journey UI now presents real server-derived candidate diffs (stops, route time, schedule, budget minor units, C4 preservation, route provider/fact quality), and accurately blocks unsupported role CTA.
  - `e00db435fdb95b86b0e32698222c977a87b3aae1`: two focused regression assertions (proposal trade-off provenance, real read-only collaborator).
- FIRST run focused R73 backend (`pytest backend/tests/test_r64_member_side_quest.py -k r73 -q`) and frontend `npm run typecheck`, fix actual failures; no R58–R72 historical strike loop. If diff quality is not EXPLICIT_FROZEN_FIXTURE in the TEST_REPLAY case, inspect the serialized `verified_evidence.mobility.snapshot.facts` and correct the projection/test, never forge provenance.

## The real product blocker
R73 **works in an all-OWNER TEST_REPLAY cohort**, but an ordinary Journey has A=OWNER, B/C=COLLABORATOR. Real R73 create/respond paths and the existing `answer_collective_clarification` require `JOURNEY_UPDATE`; R73 also fails closed when any required current member cannot authorize. The test helper's OWNER-role patch does NOT solve normal traveler onboarding. Do **not** grant JOURNEY_UPDATE to all COLLABORATOR roles, impersonate their choices, or simply remove capability checks.

There is also an immediately relevant membership integrity issue in pre-existing code:
- `backend/app/main.py` `_add_journey_member` / `POST /api/v1/journeys/{journey_id}/members` (~7373–7428) accepts a client-supplied `invited_by` and `role` with **no route-level traveler principal or MEMBER_MANAGE authorization**.
- `POST /api/v1/journeys/{journey_id}/members/{member_id}/withdraw` (~7465–7495) likewise has no signed management authority check.
- The two HTTP middlewares at ~863/881 cover error receipts and write budget, NOT identity. A dangerous self-appointed membership/role must not become spendable R73 authority. Close the actual write boundary before presenting R74 as secure.
- Audit the related member preference update and member-read privacy boundaries as needed; don't create an isolated R73 policy while the underlying Journey member set is writable by an unsigned caller.

## Revolution user story
In the normal product, A discovers a public Place and tells B and C:
> "Want to add this to OUR itinerary? I can invite you to co-plan this one stop without giving you unlimited power over bookings or every future plan."
B/C explicitly accept **one scoped planning permission** and subsequently make their own proposal-specific consent decisions. When all *required* current members vote for the exact grounded candidate, A uses the existing authoritative apply path; the shared Journey acquires one real stop. If anyone declines, lacks authority, or route proof is UNKNOWN, the current plan remains.

R74 must turn R73's role-shim-only success into a plausible, secured multi-member user journey, while preserving existing capability policy.

## One vertical slice — do in this order

### 1. Close membership impersonation (prerequisite, narrowly)
In strict signed mode (`settings.traveler_auth_secret` configured):
- A membership CREATE, WITHDRAW, and any role-changing endpoint MUST authenticate an in-force Journey member with the server-defined `MEMBER_MANAGE` capability. `invited_by` from a request body is metadata to validate or ignore, NEVER authority. No anonymous add/remove, no self-mint of OWNER or ADMIN, no ability to manage another Journey with a foreign signed token. Preserve durable audit and database uniqueness/idempotency.
- Invited traveler B must independently accept elevated/scoped authority with B's own signed identity; creating an invitation does not itself spend B's choice. If supporting ordinary COLLABORATOR membership creation, be explicit about joining vs being assigned.
- Keep explicitly isolated, labelled demo fixture setup operational without shipping an anonymous production override. Update only the directly affected R73 two-/three-member setup and relevant tests to sign their membership writes (or seed solely through test-only bootstrap).
- If an unsigned legacy endpoint must remain for a local-only compatibility harness, hard fail in strict deployed mode and document the exact isolation. Never let a publicly callable route mint current OWNER membership.

### 2. Explicit, scoped co-planning enablement
Prefer a small `SharedStopCoPlanningGrant` or equivalent durable scoped receipt. At minimum bind:
`Journey`, the exact R70 invitation/public Place, base PlanVersion/cursor, grantee in-force JourneyMember/traveler, granting signed manager, grant purpose `R73_SHARED_STOP_ONLY`, expiration, member acceptance, and later exact promotion/decision epoch when available. Server validates at every affected write.

- A current authorized manager explicitly offers scoped co-planning to B/C. Each member independently accepts. A declined/not-yet-accepted B/C is not counted as consent, and the proposal remains unavailable until required participants have eligible authority. Include uninvolved current C.
- DO NOT add global `JOURNEY_UPDATE` to `COLLABORATOR` or quietly upgrade everyone to ADMIN/OWNER. Co-planning grants may be effective only for the bound R73 collective response and its specific spend receipt; non-R73 replans, plan select, booking/payment, generic Agent tools, MEMBER_MANAGE and future proposals remain forbidden. Treat scoped authority as an explicit, single-operation extension in existing collective authority calculation, NOT an independent voting engine.
- Required member identities and capability/approval scope must be bound into existing decision epochs, receipt validation, world epoch and apply-time rechecks. Changing membership, roles, grant, plan, candidate or world evidence invalidates previous signatures/consent; never auto-replay another member's answer.
- Preserve R73's existing legitimate OWNER/ADMIN JOURNEY_UPDATE path. A still needs normal authority to CREATE/APPLY. B/C only receive narrow ability to answer this promotion, unless they separately hold real update authority.
- If the existing authority gate genuinely cannot accept one scoped grant without broader policy change, fail closed and report the specific blocking interface, rather than lowering governance or making B/C permanent owners.

### 3. Actual traveler UI
Within the existing R73 proposal card:
- A sees which of B/C still need a scoped invite/acceptance.
- B/C see a readable `Accept co-planning for this one shared stop` choice (or decline) and then the full **candidate trade-off** plus independent yes/no approval.
- Before assent display added Place, route time, time/cost delta with provenance class, protected commitments and affected rendezvous. Never treat a fixture, `UNKNOWN`, or old provider capture as live.
- When all required members consent and the existing collective receipt is valid, A applies one successor PlanVersion via the actual `_accept_replan_impl` chain; do not directly set `journey.active_plan_version_id`.
- Keep B's existing personal trip and R72 consent progress separate. No implicit physical-arrival, no R62/R69 closure, no new money/booking action, no covert location.

## Focused acceptance test (ONE bounded closure)
Use fresh SQLite with normal A=OWNER, B=COLLABORATOR, C=COLLABORATOR — **no test-only upgrading B/C to OWNER**.
1. Negative first: unsigned or foreign-member add, self-granted OWNER, fake invited_by, unsigned withdraw -> 401/403 and no membership mutation; role rules intact.
2. Real signed management grant + B/C own signed opt-in; C not in R70/R72 micro-group but required for R73 collective. Without C opt-in/approval, A+B can NOT apply.
3. A creates R73 proposal bound to exact previously disclosed public Place; show full candidate diff/receipt. Use explicitly labelled captured replay fixtures to control route feasibility if needed; distinguish `TEST_REPLAY` from `LIVE_PROVIDER`.
4. B and C independently approve after seeing same exact candidate; A explicitly applies. Assert exactly one active successor PlanVersion, one inserted Place, preserved C3/C4, zero unintended AgentRuns, Guardian/booking/payment side effects. Signed identities, true persisted decision receipts.
5. Try using B's scoped grant for generic `/plans/select`, generic `/replans/accept`, unrelated proposal, other Journey, post-apply replay or member removal. All denied. Expiration/revocation and parallel double-accept are safe.
6. One focused signed multi-context Playwright through the actual Journey UI, targeted backend tests, TypeScript/build, compileall, diff check. Correct old R73 post-review test failures first; do NOT rerun historical R58–R72 campaigns.

## Stop/go and honest handoff
Primary deliverable is a normal multi-person Journey where **existing collaborators can participate in one real collective shared-stop decision without impersonation or unrestricted plan powers**. This is a Revolution capability, not a role-table green check.

A live-provider trial is OPTIONAL only if a configured real provider is available with bounded consent; do not spend hours manufacturing a live success. If it returns NO_GROUNDED_ROUTE, keep it BLOCKED and state that separately from the controlled authorized-code test.

Write `REVOLUTION_R74_SCOPED_REAL_GROUP_CO_PLANNING_RESULT.md` with implementation SHA, tests, precise scope and grant expiry, normal-roles browser outcome, permission-negative results, replay/live provenance, and push to SAME Revolution branch. No merge with `commander/control`, no default-branch updates.

**Revolution principle: empower real travelers to shape their trip together, without confusing identity, consent, data origin, and actual authority.**
