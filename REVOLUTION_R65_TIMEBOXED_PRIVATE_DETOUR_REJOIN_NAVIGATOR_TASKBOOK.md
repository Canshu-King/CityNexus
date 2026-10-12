# Revolution R65 — Timeboxed Private Detour + Rejoin Navigator

## Starting baton

- Branch: `gpt/revolution-r33-open-world-journey-adaptation`
- R64 implementation: `dfd37ec1bf6fb2eb9f8fb8702ca54d13fc47e4af`
- GPT's narrow R64 truth-language fix: through `cada27d35830d27a1ebfb772548dcf5673d33ad8`
- R64 result: `REVOLUTION_R64_MEMBER_SIDE_QUEST_EXECUTION_RESULT.md`
- R64 source: `backend/app/execution/member_side_quest.py`, `frontend/src/features/execution/MemberSideQuestCard.tsx`
- Existing return route: `POST /api/v1/journeys/{journey_id}/group-presence/route`
- Existing member location: `POST /api/v1/journeys/{journey_id}/location`
- Existing route engine: `backend/app/route_session_operations.py`, `app.execution.route_session_contract.RouteRequest`

R64 is functionally accepted at the authenticated API/domain/UI boundary, not as physical-world validation. Five post-review commits corrected a product claim: READY is not physically AWAY, and COMPLETED is not automatically RETURNING. The post-review changes are not yet locally tested. **Run their narrow regression tests first**, fix any breakage and continue directly to this product strike. Do not restart the R58–R64 verification campaign.

## Revolution promise

A traveler is on an active shared Journey with a planned R63 separation and has chosen a private R64 side stop.

Instead of just showing READY → ARRIVED → COMPLETED, CityNexus should now answer:

> “Can I fit this personal stop before our 11:00 meeting? If I go, when should I leave? When I'm done, take me back to the group.”

Implement a private, timeboxed detour preview and a one-tap **return-to-the-group** action in the *existing Journey Live product*. This is a practical navigator, not a new plan/version/agent/verification subsystem.

The user should gain two real abilities:
1. Before/while executing their private stop: understand whether it still fits the current shared rendezvous, using source-qualified travel truth.
2. After finishing/canceling: actively initiate a member-owned return and request a route to the shared rendezvous, not merely read “please return.”

## Explicit source review observations

### Already available and to be reused

- R64 member-side-quest CRUD/transition and owner-only projection.
- R63 member-bound planned separation and exact current PlanVersion rendezvous.
- Existing R57/R63 `group-presence/route` takes a fresh member-bound LocationObservation, derives the shared rendezvous server-side and preserves return-risk/Guardian provenance.
- `LiveRecovery.guideToGroup()` already calls `onRefreshLocation()` and the existing return route endpoint. **Extract/reuse this callback** rather than building a second shared-rendezvous engine.
- `rendezvous_commitment_risk()` already understands protected C3/C4 commitments and server-derived safety buffer.
- R64 non-owner status was corrected to `PLANNED`, `ACTIVE_SELF_REPORTED`, `FINISHED_RETURN_UNCONFIRMED`.

### Privacy hazard to resolve by construction

The generic `GET /api/v1/journeys/{journey_id}/routes/operations/{operation_id}` currently reads a RouteAcquisitionOperation without resolving a member principal. A private outbound route stored in a generic Journey-scoped operation might expose the owner's private `target_key`, place identity, origin, or route geometry through that endpoint or other Journey mobility/read projections.

**Never send a private side-destination route through a globally readable operation/read model unless every public/read path is first correctly filtered or the private operation is securely segregated.** This is a real privacy boundary, not a request for more evidence. Inspect generic route-operation reads, `MobilityFact` projections, logs, audit, and API responses before reusing storage for private route targets. Use a member-authorized private route result/operation if required; reuse the provider and route-truth engine, not shared visibility.

## Product surface: owner only

Integrate directly in `MemberSideQuestCard`, localized Chinese/English.

### A. “Will this detour fit?”

For an exact-known private Place on the active R64 quest, let the member request an on-demand feasibility preview with a small chosen dwell time (e.g., 10/20/30 minutes). No background polling or fabricated countdown.

The server derives:
- the exact private destination from R64, never from an untrusted client Place id during route preview;
- the current shared rendezvous from the bound R63 intent and one active PlanVersion;
- travel legs, if captureable: member's *fresh, consented* current location → side Place, and side Place → shared rendezvous;
- shared rendezvous time and any protected commitment buffer from the authoritative server plan.

Return a member-private structured projection, roughly:

- `state`: `FITS_WITH_BUFFER`, `TIGHT_RETURN`, `DOES_NOT_FIT`, or `UNKNOWN`;
- `dwell_minutes`;
- `outbound_eta_minutes` and `return_eta_minutes`, nullable;
- `recommended_leave_by`, nullable;
- `rendezvous_scheduled_at`;
- `safety_buffer_minutes`, nullable;
- `provenance` for both legs (separately);
- `origin_basis`: actual authenticated fresh one-time location for outbound vs **hypothetical** side Place for inbound;
- `authority`: advisory unless existing stronger truth explicitly warrants more;
- `plan_unchanged: true`.

Only present a definite “fits” or timeboxed leave-by if both legs have qualifying current real-provider route captures, fresh enough for the forecast, an exact known private Place, an exact rendezvous and usable rendezvous time/buffer. Otherwise give an actionable, honest UNKNOWN (“We can't confirm this stop fits; the group itinerary is unchanged. You can return to the shared meeting point instead.”).

For protected C3/C4, use actual commitment schedule and safety buffer. For a non-protected planned rendezvous, explicitly label any time estimate as advisory; do not invent a protected promise.

The side Place → rendezvous leg is a hypothetical future route from a known Place, **not proof the member is physically there**; never feed it to Guardian as if it were member-current-location evidence.

### B. “Take me to my private stop”

Provide a one-time, consented outbound route action if the quest is `READY` or `EN_ROUTE` and has an exact known Place.

- Bind the acting member from signed principal.
- Require a fresh, precise-enough observation from that exact member, as done in the R57 route path.
- Resolve private destination on the server from R64 quest, not request body.
- Return a private route status/ETA/source/geometry only if supported by real provider truth.
- Keep output in owner-only UI and private API; no shared active Activity, private target leak, group state mutation or Guardian trigger.
- If route is unavailable, display `UNKNOWN/UNAVAILABLE`; R64 manual execution must remain usable.

### C. “Head back to everyone”

After R64 quest `COMPLETED` or `CANCELLED`, give a prominent return action on the same card.

On click:
1. Persist one idempotent authenticated member-owned `RETURN_STARTED_REPORTED` (or equivalent) receipt tied to the exact R63 split and latest R64 side quest. This is a voluntary member report, not verified departure or co-location.
2. Request one fresh location *with foreground permission*. When available, call the existing R57/R63 `group-presence/route` rather than duplicating route risk/Guardian logic.
3. Show shared rendezvous title/place/time and route ETA, provenance and actionable return status. When location/route unavailable, retain the return-start report and show truthful UNKNOWN with a visible shared rendezvous; do not strand the user.
4. Keep `active_plan_version_id` unchanged. Do not end R63 separation automatically.
5. Co-member may now see “Alice reported heading back,” **not** “Alice is physically on the way,” and no private destination or exact coordinate.

If another private quest is created later for the same split, an old `RETURN_STARTED_REPORTED` receipt must not make the new quest appear “returning.” Derive the coarse current status from the latest active split/quest.

R62's authenticated member-specific rejoin execution, where applicable, remains the authority for recovery-followthrough closure. Merely starting a return route or completing a side quest never closes a recovery incident or proves reunion.

## Hard invariants

- Exactly one authoritative active shared PlanVersion. No new shared Journey, shared Activity or shared cursor.
- Side destination, private route geometry, notes and exact coordinates remain owner-only by default. Treat generic Journey-scoped route/read/audit surfaces as a potential privacy leak.
- Server authenticates the member on every new mutation/read. No user/member id supplied in request body is spendable authority.
- R63 plan binding, membership in-force and current quest state checked on every action. If split changes, reject/stale-safe; never re-target a cached private route/forecast to a new active PlanVersion.
- A returned ETAs/leave-by must carry source/age/mode. No synthetic, mock, fixture, captured replay, stale or missing evidence silently promoted to live.
- No background geolocation, ongoing surveillance, automatic side-quest creation, automatic permission prompt at page load or duplicate provider retries for “green” results.
- Keep the R57/R63 Guardian handoff exactly as it is for **trusted current member location + exact live return route**. Neither personal detour preview nor foreground advisory route may trigger it.
- On uncertain feasibility, keep the user's R64 side quest manually executable, but do not claim it can safely fit.
- Do not falsely label `PLANNED` as departed, `COMPLETED` as returning, or `RETURN_STARTED_REPORTED` as physical presence proof.

## Engineering guidance / constrained ambition

Try to reuse the existing route operation/provenance machinery, **but solve private-route visibility first**. Prefer a thin member-private wrapper or a privacy-safe isolated private route read model over adding a second route solver or letting generic `routes/operations` reveal personal destinations.

Do not change old shared route behavior globally just to get a private route through tests. If full outbound routing cannot be made private in this strike without a major unsafe refactor, prioritize the safe timeboxed return navigator and explain the bounded limitation; never ship a privacy-unsafe short-cut.

Do not start a Hermes/DeepSeek Agent for routine route preview, return action, or evidence. This is useful deterministic product execution with optional provider routing. Keep AI out of the critical path.

## Focused validation

Run the GPT R64 post-review narrow affected tests first: `backend/tests/test_r64_member_side_quest.py` and `frontend/e2e/r64-member-side-quest.spec.ts`, plus typecheck.

Then focused R65 cases:

1. Owner sees precise private stop/rendezvous; collaborator never receives private target/geometry, including generic route read endpoints.
2. One fresh signed-member location is bound to outbound route; spoofed member/observation rejected.
3. Exact Place and current plan binding required for preview/navigation.
4. Two qualifying fresh real-provider leg receipts (test-only captures) produce source-labeled feasibility/leave-by.
5. Replay, mock/synthetic, stale route, missing Place, no time or provider outage produce UNKNOWN, not a fabricated “fits”.
6. Calculating a hypothetical side Place return leg alone never raises Guardian.
7. Owner `HEAD_BACK` is idempotent and persists a report even if geolocation denied.
8. Co-member sees only `RETURN_STARTED_REPORTED`/safe coarse text, no destination.
9. `HEAD_BACK` with fresh foreground location reuses R63 return-route path and does not independently trigger Guardian.
10. Side-quest complete/cancel alone does **not** mark returning or rejoined.
11. R63 cancellation/supersession, PlanVersion drift, member removal invalidate sensitive route/return actions.
12. Multiple successive private stops do not reuse previous stop's current return receipt/feasibility.
13. No shared Activity/PlanVersion/approval/proposal changes on normal private navigation.
14. Existing R62 rejoin and R63 trusted return-risk handoff still work with one directly relevant regression each.

Two real authenticated browser contexts. Prefer real R65 writes and real R64 lifecycle APIs; controlled test-only mobility facts may stand in for external route availability. No whole-feature mock UI. Verify blocked private read responses, not merely absence of leaked names in rendered page.

One bounded fresh isolated-DB product flow:
R63 split → R64 exact private stop → R65 preview → START/ARRIVE/COMPLETE → explicit HEAD BACK → route or truthful UNKNOWN → co-member privacy projection. Document normal provider/Agent limitations without rerunning to manufacture mutations.

Use focused backend, focused E2E, `compileall`, frontend typecheck/build and `git diff --check`.

## Success definition

R65 is successful when a real authenticated member can ask “does my detour still fit?” with qualified route provenance, then explicitly set out for the shared rendezvous through the normal product, while the partner sees useful but private-safe return progress. A safe UNKNOWN is acceptable if providers are unavailable, **but the real member-bound action, privacy protection and full Journey Live UX must work**.

Report implementation SHA, remote HEAD, focused tests, what the actual bounded flow did, what was mocked in tests, and what was **not** physically or externally verified.

## Not the task

- No R58–R64 historical replay campaign.
- No generic verifier, evidence engine or endless CI loop.
- No second shared plan/Agent/recovery stack.
- No “returning” by inference from a completed side quest.
- No exposing private Place via generic Journey route infrastructure.
- No disabling identity to simplify browser tests.
- No route estimates from unknown evidence.
- No chasing mutation counts.
