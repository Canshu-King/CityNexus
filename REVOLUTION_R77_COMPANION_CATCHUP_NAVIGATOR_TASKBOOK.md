# CityNexus Revolution R77 — New Companion, Real Catch-Up Navigation

## Source of truth and exact handoff
Implement on the SAME branch `gpt/revolution-r33-open-world-journey-adaptation`, starting from `9d0614823a9c6b62597ddeb03d401f12ac704699`. Do not merge `commander/control`, default branch, or run archival R58–R75 strike suites.

**Codex R76 result:** `REVOLUTION_R76_REAL_COMPANION_JOIN_CATCHUP_RESULT.md` @ `2365be2cd69956253698bf0269024f4466668cfe`; implementation `e8b6321e88fcfbe51545b73b2f9dbf9974d67852`. Codex reports backend 3 R75 re-consent + 7 R75 + 7 R76/member + 1 R73 = **18 passed**, one fresh signed nonmember -> own ACCEPT -> one COLLABORATOR -> current Journey browser closure; TS typecheck:all/build/compileall/diff check passed. No AgentRun/ProviderCall/GuardianRun, no live route or GPS. The no-route catch-up screen was honestly `UNKNOWN / ROUTE_UNAVAILABLE`. Test-issued HMAC travelers are not production login proof.

**GPT post-review code pushed, NOT locally tested:**
- `5de945d0996841245e36708197d1a7a98643a474`: `backend/app/execution/group_presence.py` projects the exact shared-plan **public Place** WGS84 destination (place ID, lat/lon, CRS) to a signed in-force member, never another member's origin. Unknown/invalid/non-WGS84 geometry stays NULL.
- `28c964c47582e816ba8a816858304ebcbee623e9`: types that bounded destination.
- `de85beac1d60a331592267ebb3977d2ef0f52e25`: `JourneyMembershipPanel` displays next plan meeting stop after page reload; with explicit consent opens public OSM pin by exact coordinates when grounded, otherwise labels ambiguous name search, never an ETA or live group location.
- `4cc83831f630a74d0eea05aea3fa7e7c628a4ddc`: backend regression for destination/public-place binding.
- `9d0614823a9c6b62597ddeb03d401f12ac704699`: focused Playwright reload assertion.
FIRST pull and run `pytest tests/test_r76_journey_membership_invitation.py -q` from the configured backend venv; `npm run typecheck:all`; the single `e2e/r76-companion-join-catchup.spec.ts` Playwright with its isolated config/runtime. Fix genuine regressions. Do not present these GPT commits as tested until Codex executes them.

## The Revolution user story
R76 finally lets C, a real independent signed traveler, accept an ACTIVE Journey invitation. But “How do I catch up?” only shows a *public map pin* and an honest UNKNOWN, not a usable member-owned route. R77 lets a newly joined companion decide for themself:

> “I just joined the trip. Where do I meet everyone? Show the exact shared stop, check whether I can reach it from *my* location, and let me tell the group I'm on my way without exposing my precise position. If routing is unavailable, keep the truthful public pin and a manual fallback.”

Deliver one **real Join -> consented one-time route -> grounded or UNKNOWN guidance -> opt-in coarse status -> shared rendezvous** slice in the normal Journey UI. This is a traveller feature, not another permissions/test round.

## Implement exactly one bounded product path

### A. Own-location, plan-bound route check (priority)
1. Add `Check my route to our next stop` in `frontend/src/features/execution/JourneyMembershipPanel.tsx` for a signed in-force member, including after page reload. Reuse `V8Experience.tsx`'s `captureForegroundLocation` callback (already writes authenticated `POST /journeys/{id}/location`) and `cityNexusApi.routeToGroupRendezvous` (`POST /journeys/{id}/group-presence/route`) wherever compatible. DO NOT fabricate an R63/R64 side quest to make a newcomer eligible. `group_presence.can_guide` is already based on active Journey, 2+ members and a real rendezvous Place.
2. Before requesting geolocation show a clear, separate consent statement: this makes a **Journey-bound foreground location observation**; its coarse group-presence effect may be seen by companions; your exact origin may be transmitted to the explicitly configured routing provider; there may be a protected-commitment/Guardian consequence if existing deliberate route-risk logic says so; no passive polling/hidden background location; the shared plan is not silently updated. Refusing must keep public pin/name fallback fully usable. Do not imply the observation is “only used once” if persisted.
3. Validate returned `location_observation_id` belongs to C's authenticated in-force member and is fresh/accurate enough, Journey and active PlanVersion/cursor still current, next shared exact public rendezvous destination is unchanged. Reuse existing group route API's actual authority/evidence and R55–R65 protected commitment checks. If a completed operation is `MOCK`/`FIXTURE`, stale, unknown CRS, or unauthorized replay, do NOT show a confident green ETA. Display `ROUTE_UNAVAILABLE/UNKNOWN` and use public exact pin. If grounded CAPTURED_REPLAY, explicitly label *captured historic route, not current traffic*; live provider can be labelled live only when receipt actually proves it.
4. If a route is evidenced, display source, freshness, walking duration and next protected commitment risk/slack **only when grounded**. Clearly distinguish “destination is a shared planned Place” vs “the group is physically at this point”—none of the member observation/self-report APIs prove physical co-location.
5. Recheck active PlanVersion, current shared execution cursor and rendezvous Place when the member asks for a route and when rendering a saved result. Invalidated routes must not linger after a collective R73/R75 replan or Journey progress. Clicking “open exact Place pin” must similarly refresh/bind the current destination before release to OSM, or visibly refuse stale preview and ask for reconfirmation. Do not open an outdated meeting point because a tab has been open for an hour.

### B. Optional, explicit “I'm coming” coordination (small durable action)
6. Once C has accepted R76, allow a member-owned **opt-in coarse heading-to-rendezvous self-report** for the current exact active-plan rendezvous. This must be a deliberate action independent of route acquisition, with server-bound JourneyMember/traveler, PlanVersion/cursor/target, reported timestamp, unique currently-active member signal/idempotency and withdrawal for future projections. Reuse suitable R62/R69/group-presence domain primitives if compatible; avoid writing a second group-wide execution cursor.
7. A/B may see “C reports heading to the next shared stop” (and, if opted in, only grounded coarse ETA band/provenance—not C's precise coordinates, observation ID, route geometry or origin). **Do not automatically infer “on my way” from route request, map click or R76 acceptance**, and do not infer “arrived”. Reuse R69 handshake only at its original shared rendezvous and only with its required explicit member execution reports. If a new status model would expand this strike too far, deliver A in full with a clear UI next step and record B as separate BLOCKED follow-up; do not dilute A or claim completed coordination.

### C. Capability/evidence gates and human safety
8. Never trigger background AgentRun, GuardianPulse, provider route or location sampling from projection, a newly accepted invitation or app polling. If deliberate routing invokes the existing member-risk/Guardian path, the UI must explain *what actually happened* with exact server status rather than claiming 0 when nonzero. No plan mutation without separate protected commitment governance.
9. R76 onboarding still depends on an existing signed traveler ID and trusted local test signer. Do not re-label it production identity or build a fake “anyone can sign in as any traveler” shortcut. If adding an accessible share/invite affordance, keep identity verification independent of a possession-only URL and do not expose bearer tokens in URLs.
10. Avoid all full-device navigation “arrived” claims. A browser geolocation observation is advisory evidence, not device attestation. Show real user action and exact provenance.

## Concrete code seams verified by GPT
- `backend/app/execution/group_presence.py`: `rendezvous_target` picks the active-plan next eligible stop, preferring a C3/C4 commitment; a target is NOT the group's live GPS position. `group_presence_projection` returns `can_guide` for active 2+ member Journey, and `viewer_route` provenance.
- `frontend/src/api/citynexus.ts`: `routeToGroupRendezvous(journeyId, locationObservationId)` -> `/group-presence/route`; `GroupRendezvousRouteResult` exposes `status`, `target`, `route.provider/provenance/duration_min`, `authority`, `shared_commitment_risk`, `guardian_triggered`, `plan_unchanged`.
- `frontend/src/app/V8Experience.tsx` around original line 1343: `captureForegroundLocation` calls the browser geolocation once, posts exact observation with signed identity, refreshes Journey. Pass it down to the membership panel rather than clone a separate location implementation.
- `frontend/src/features/execution/LiveRecovery.tsx` around original 800–836 already calls `routeToGroupRendezvous` from explicit foreground location and handles unknown. Reuse its error/authority handling; do not accidentally start a competing Guardian loop or share route geometry.
- `backend/app/integrations/mobility/runtime.py` / `backend/app/execution/group_presence.py::_route_eta`: distinguish LIVE_PROVIDER_CAPTURE vs CAPTURED_REPLAY vs MOCK/FIXTURE and stale results. Check route operation's target bindings.
- `frontend/src/features/execution/JourneyMembershipPanel.tsx`: after GPT follow-up the exact pin and user-facing catch-up card persist after reload. The map button still needs a *fresh plan target revalidation* (it currently uses a cached projection until component reload).
- `backend/app/execution/member_place_group_share.py`: R75 full-group consent remains audience- and plan-bound. R77 must not retroactively widen an unrelated private Place share when C joins. R76 invalidates prior R73/R74 collective authority on join.

## Bounded fresh closure / no old treadmill
Fresh isolated signed A=OWNER, B=COLLABORATOR, C=initial nonmember; A invites C, C accepts through normal UI. Then C uses the existing Journey catch-up card:
- Before consent: no location recorded, no provider/Agent action, public planned pin available.
- C declines one-time location -> original Journey and exact pin still work, no disclosure.
- C consents once -> **C-bound observation** only -> route operation to server's current exact shared destination. In one controlled CAPTURED_REPLAY/frozen route fixture prove the route/result/provenance UI path, but label it REPLAY. In another case with no eligible route, show UNKNOWN and no fabricated minutes. If a real external mobility provider is configured, permit at most one deliberate bounded live trial; otherwise do not force provider success.
- With A/B separate sessions, verify no precise C coordinates/observation IDs leak. A's screen never reports C physically arrived merely because route succeeded.
- Change PlanVersion/cursor/target while UI open -> old pin and ETA invalidated, user must reconfirm. Test no stale route reuse, no C4 downgrade, no unauthorized route from signed stranger, no old R75 consent inheritance.
- If completing opt-in heading status B: test reload/revoke/member deletion/changed rendezvous and independent authorization. Exactly once durable receipt, no spoofed arrival.
- One new 2–3 signed browser-context Playwright; targeted backend tests, `npm run typecheck:all`, build, compileall, diff check. Only direct R76 regression; **no archival R58–R75 campaigns**.

## Definition of done, honest delivery
C joins a living Journey and has a **persistent, member-owned, useful meet-up path**: exact public destination + explicit one-time personal route request + either grounded/provenance-labelled guidance or honest UNKNOWN; optional narrow opt-in status if delivered. All member privacy and shared plan authority remain intact. Real live-provider/real GPS presence must not be claimed without actual evidence.

Write `REVOLUTION_R77_COMPANION_CATCHUP_NAVIGATOR_RESULT.md` with exact implementation/result SHA, commands/exit codes, pre/post PlanVersion, route/Guardian/Agent/provider counts, evidence classes, privacy negatives, and any BLOCKED capability. Push to SAME branch. The main effort must be new visible code, not verifier cycles.

**Revolution is the freedom to enter the trip midway and still find your people, without surrendering agency over your location or inventing reality.**