# Revolution R68 — Real-World Navigation Handoff (Walk There, Rejoin Everyone)

## Product purpose

R63 lets a group member deliberately leave for a while. R64 provides a member-owned private stop. R65 adds private route evidence, rough route sketch, detour timing and explicit return-to-group. R66 finds existing nearby Places. R67 can request real OpenStreetMap POIs with explicit consent and materialize only the confirmed one.

**The user-facing hole:** after accepting a private place, the product often presents a tiny route sketch or an honest `UNKNOWN`. That is not a usable navigation experience on a phone. The traveler still has to copy the name, switch to a map app, search again, and risk choosing the wrong place.

R68 must close the real-world action loop:

> "Show me a real nearby place → I choose it → open trustworthy walking directions to that exact place → when done, get walking directions back to our exact shared rendezvous."

This is a **new capability** bridging the Journey execution system to actual walking navigation. Do not spend the strike on another verifier, evidence bundle, or abstract framework.

## Starting baton

Same branch: `gpt/revolution-r33-open-world-journey-adaptation`.

- R67 product implementation: `e6ff4a8c56ff9ebf025382d8cceedc5aa421f169`.
- GPT R67 post-review edits already pushed in the same branch:
  1. exclude active shared-plan stops and the exact group rendezvous from new live suggestions;
  2. revalidate member, planned split, location and shared plan **after** external Overpass latency;
  3. reject live POI selection after the rendezvous time passes;
  4. clear old live results when budget/interest/Journey changes;
  5. offer opt-in fresh OSM discovery even when the local catalog has a few entries, with explicit consent;
  6. narrow regressions for shared stops, expired meeting and opt-in visibility.
- These GPT edits need one local focused test pass, then immediately proceed to R68. Do not rerun historical R58–R67 strike campaigns.
- The checked R67 `reports/e2e-provenance/authoritative.json` has runId `r67live20261008a`, AI disabled. R67's external-search Playwright used an explicitly controlled local Overpass fixture; this does **not** prove real public-provider results. No independent R67 result document was found at the checked original implementation SHA. Report the boundary truthfully.
- The real provider is opt-in deployment configuration. `backend/app/core/config.py` defaults `CITYNEXUS_REAL_CITY_ENABLED=false` and `CITYNEXUS_REAL_CITY_MODE=replay`. R68 must not silently flip those settings or claim live discovery active everywhere.

## Existing implementation to reuse

Read the actual code before implementation:

- `frontend/src/features/execution/MemberSideQuestCard.tsx`: R64 lifecycle, R65 private route preview and head-back card; currently displays only `routeSketch()` as a small SVG for a route.
- `frontend/src/features/execution/LiveRecovery.tsx`: Journey Live, member-bound location callback, `routeAfterPrivateStop()`, group-rendezvous guidance.
- `frontend/src/features/execution/MomentScoutCard.tsx`: R66/67 destination selection, member-private state.
- `backend/app/execution/member_side_quest.py`: R64 current split binding, member ownership, private destination exact Place, rendezvous Place id held on durable `MemberSideQuest`.
- `backend/app/main.py`: signed Journey member principal resolution, side-quest API, existing `group-presence/route` for real provider return feasibility.
- `frontend/src/api/citynexus.ts`: `MemberSideQuestProjection` includes private destination `place_id`, and rendezvous `activity_id` but the current owner projection does not include the rendezvous Place coordinates.
- `Place` model: canonical latitude/longitude stored WGS84 with coordinate system and provider identity.

## R68 product experience

### A. Direct navigation to the user's selected private place

When a signed in-force member has a current, exact-known R64 side quest in READY or EN_ROUTE:

- Present **"Open walking directions" / "打开步行导航"** directly in Journey Live.
- Resolve the exact destination server-side from the member's current quest; never accept a destination coordinate or traveler/member id from the browser request body.
- Prefer a narrow owner-authorized `GET /api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/navigation-targets`, returning current member-private, plan-bound exact destination and exact shared rendezvous targets. A small owner-only projected extension is acceptable if it has equal server-side authority.
- Include name, exact Place id, WGS84 coordinates and data provenance of each target; never include the member's own origin coordinates in the response/link by default.
- Give a clear **external maps handoff**: clicking opens a platform-appropriate external walking navigation URL for the exact destination; don't merely draw a route thumbnail.
- The external map provider determines live directions using its own app/location permissions. CityNexus's R65 route/ETA may be unavailable or stale; the handoff should *still work*. Do not claim the external app's travel ETA is backed by CityNexus's provider receipts.
- If Place coords missing/invalid/unsupported CRS, disable the handoff with a truthful message and retain ordinary side-quest/manual execution.
- Show an explicit privacy explanation **before first external launch**: selected destination coordinates/name will be shared with the chosen maps provider; no member origin coordinates are sent by CityNexus.

### B. Direct navigation back to the exact shared rendezvous

After `COMPLETED` or `CANCELLED` for the current R64 side quest, and while the bound R63 split is still current:

- Show **"Navigate to everyone" / "导航回共同会合点"** with the exact authoritative active-plan rendezvous, never a guessed group centroid.
- Reuse the same member-authorized target resolution. If the shared plan/rendezvous changed, don't navigate to the stale target; ask for refresh/re-grounding.
- Reuse the existing explicit `head-back` action for recording a `RETURN_STARTED_REPORTED` if user elects to report returning. Merely opening external Maps does not create a forged returning/rejoined status. If combining return reporting and map handoff, make each effect explicit and ensure the server receipt is saved or a recoverable error is shown.
- Keep the R63/R57 Guardian risk logic exclusively on trusted member-current-location + qualifying provider route facts. An external maps click cannot prove physical arrival, return, or ETA.

### C. Mobile and offline behavior

- One clear default walking-navigation option for mobile PWA plus one reliable alternative for source/position viewing. Consider Google Maps universal directions URL (`https://www.google.com/maps/dir/?api=1&destination=...&travelmode=walking`) for WGS84 exact destination and OSM place/map view as an independent fallback. Apple Maps may be offered when appropriate.
- Build links through a small reviewed URL builder that validates finite -90..90/-180..180 coords and encodes the place label; never concatenate untrusted provider URLs, embedded query strings or freeform HTML.
- Do not pass member's last foreground location into the external link by default. The external map decides whether/how to access origin location.
- Do not silently feed raw WGS84 into a regional maps URI that expects another coordinate system (e.g. GCJ-02) without a correct conversion. A neutral map alternative is better than a wrong pin.
- Make it obvious that the external map provider may have different availability, routes and traffic truth. Browser fallback should still reveal the exact pin when external navigation app is not installed.
- Never automatically launch Maps on creating/selecting a stop, receiving a location, mounting a component, or refreshing an API. User must tap.
- Don't request new background location or browser permissions solely to construct the destination URL. If native directions are unavailable, preserve the exact Place name and current private stop state.

## Authority, privacy, and race boundaries

- Side quest target coordinates are **member-private relationship data** even though the canonical Place itself may be a public catalog entry. A collaborator may browse the public catalog but must not get a quest→Place binding from the new endpoint/projection.
- Bind principal server-side on every exact-navigation-target read; reject foreign member, removed/expired member, nonexistent quest, stale split, stale PlanVersion or terminal rendezvous. No special admin backdoor.
- Prefer returning `404` for a foreign quest and `409` for an owner with stale state.
- Check the exact current quest/split/rendezvous at launch/target-read time. A cached target must be invalidated when active plan, private destination, side-quest state, rendezvous or membership changes.
- Do not leak member location, exact private destination or route geometry to `operator.group_presence`, shared Journey Activity, ProviderCall or shared PlanVersion.
- An external link is a distinct privacy boundary: make explicit which destination facts go to the third party, when, and only as a direct user action.
- Never turn an external-navigation click into a physical presence verification, a side-quest completion or a collective plan mutation.

## Engineering scope

- Build the feature *inside* existing `MemberSideQuestCard`, with a small server owner-only target resolver when needed. No new generic navigation engine, map framework, private route-operation table, autonomous Agent run or separate page.
- Use public, documented external directions URL patterns that accept WGS84. Check their current specifications and avoid any unstated geo-data conversion. If route URL specifics are uncertain, use verified OSM map pins rather than a knowingly incorrect directions link.
- A route duration coming from external Maps must **not** be silently imported as `LIVE_PROVIDER_CAPTURE` or Guardian evidence.
- Keep the card understandable for casual travelers: use Chinese and English labels, concise error/retry states and clear buttons instead of raw JSON or internal enums.

## Focused acceptance only

Backend tests:
1. Signed owner resolves exactly their R64 private target and authoritative current-plan rendezvous Place; both WGS84.
2. Another member cannot retrieve the owner's current private destination through the new read endpoint, even with a guessed quest id.
3. Removed/expired owner, R63 split ended, Journey plan changed and rendezvous terminal => no stale navigation target.
4. Navigation-target read has no side effect on shared PlanVersion, Activity, proposals, Guardian or AgentRun.
5. An unresolved descriptive-only private place cannot be promoted to an exact pin.

Frontend tests / one authentic dual-member Playwright:
1. R66 or R67 chosen Place → R64 side quest READY → visible direct walking Maps action, no manual re-entry of the destination.
2. Real destinations are encoded as exact lat/lon and name in the owner-only handoff URL, no member origin included. The E2E may intercept popup/navigation rather than contacting external Maps.
3. Explicit privacy message/confirm precedes external navigation; cancellation triggers no external visit.
4. Outbound navigation remains usable when R65 route capture is `UNKNOWN`.
5. After COMPLETE, exact shared rendezvous navigation is available even without Valhalla; no false `RETURN_STARTED_REPORTED` or physical reunion claim just for opening Maps.
6. If user explicitly reports `HEAD_BACK`, existing receipt/return-risk path is unchanged.
7. Collaborator never sees the owner's side-quest navigation action, private destination or maps URL via group projection.
8. Switching quest/plan or ending split invalidates previously displayed actionable external target.
9. Native/walk link and fallback pin URLs are correctly encoded with no coordinate-system confusion.

Run focused backend + one two-context Playwright, TypeScript/build, compileall, diff-check. Use one fresh isolated SQLite database and a bounded product API/UX flow. No external map invocation is required for E2E; test the generated links and click handling. No fake live route/provider/physical trip claims.

## Success

A real traveler using CityNexus on a phone can discover a place, explicitly choose a private stop, **tap once to launch actionable external walking directions to that exact destination**, finish the stop, and **tap to navigate back to the exact shared rendezvous**, while every group/privacy/authority boundary remains intact.

That is a leap from *knowing* to *doing* and makes the R63–R67 work more useful to humans.

## Not this strike

- No R58–R67 history replay, massive evidence pack or new verifier.
- No second shared active plan, private stop promoted to shared Activity or fake physical reunion.
- No hidden external navigation call, silent user-coordinate sharing, or global logging of private link.
- No broad rewrite of GIS, map providers, Place table, routing, Hermes, Guardian or collective mediation.
- No demand for a live provider success just to close one developer strike.
