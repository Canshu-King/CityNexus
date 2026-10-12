# Revolution R66 — Moment Scout: Real Nearby Micro-Adventures

## Why this is a Revolution strike

R63 allowed intentional group separation. R64 gave a member a private side-quest execution lane. R65 added private routing, a source-qualified fit preview, and an explicit return-to-group action.

**The missing magic is discovery.** Today the traveler still has to supply a specific destination. R66 should make CityNexus useful when the user says:

> "I've got 30 minutes before we meet. What's worth doing around me?"

The product should offer a small set of *real, nearby, individually actionable* options, plainly distinguish discovery from route guarantees, and take the user's chosen option straight into the existing R63 → R64 → R65 journey. This is a user-facing Moment Scout, **not another verifier, status dashboard, agent/solver stack, or report round**.

## Starting baton and review corrections

- Branch: `gpt/revolution-r33-open-world-journey-adaptation`.
- R65 original implementation: `72b88fe1253c81cb7074b678c6b432c24e35d725`.
- GPT post-review changes are already on the same branch, through `3e5337d6af4502a624f8c7d55d9d49b6e74008ad` at drafting time.
- R65 review fixes:
  1. A fit preview/private route is displayed only for the exact quest identity, destination, rendezvous, execution state, and selected dwell time; delayed stale responses cannot resurrect old guidance.
  2. One-time guidance expires after 30 seconds on the client without location/provider polling.
  3. R65 no longer recommends an impossible leave-by time when a detour is already unworkable or cannot meet the protected return buffer.
  4. Directly related focused backend and Playwright assertions were added.
- **Run narrow affected tests before implementing R66**, and repair actual failures. These GPT edits have not yet been locally exercised.
- The R65 branch had an isolated E2E provenance record `r65detour20261008h`, but no `REVOLUTION_R65_TIMEBOXED_PRIVATE_DETOUR_REJOIN_NAVIGATOR_RESULT.md` was found at the original implementation HEAD. Do not invent external success or spend a strike doing paperwork. A short truthful R65 result in the eventual R66 handoff is enough.

## End-to-end product promise

Inside the real Journey Live screen, an active in-force traveler sees a contextual action:

**"Find a quick adventure nearby" / "附近有什么可以顺路玩？"**

A reasonable experience:

1. User chooses a rough personal time budget: 15 / 30 / 45 minutes and an optional interest (coffee/food, culture, nature, anything).
2. The user taps Scout. Ask for **one foreground location sample with consent** via the existing `onRefreshLocation` flow, never automatic background tracking.
3. The server resolves the active Journey, signed member, current shared meeting point/time and a small shortlist of known real Place records near the member, excluding the active shared plan's stops and the current rendezvous.
4. Show up to 3 grounded choices with name, category, **straight-line distance** (explicitly not walking ETA), provider/data provenance, opening-hours status if and only if the evidence legitimately supports it, and next shared rendezvous.
5. Clearly label whether each option's return fit is `UNVERIFIED` vs `GROUNDED`; do not call an option "fits" or "safe" using a distance heuristic.
6. On user selection, require a confirmation: "Go to this private stop, then rejoin at <exact shared rendezvous>." Only after confirmation, use the existing R63 planned separation and R64 exact-known-place private quest. Then hand the user into the existing R65 preview/navigation/return card.
7. Other group members see the same coarse R63/R64/R65 privacy-safe progress **but no selected private Place, exact coordinates, personalized interest, route geometry, private scout candidates, or private scoring**.
8. If no suitable known Places are present, show `NO_GROUNDED_OPTIONS` with a useful next action (choose/type a private destination or continue the shared Journey), not three invented venues.
9. The shared PlanVersion, shared execution cursor, protected commitments, recovery/approval states are unchanged simply because a member explored or selected a private stop.

This should work as a **real API + UI flow**, not a statically generated list of attractive cards.

## Product strategy / boundaries

### Real nearby discovery

Use existing `Place` rows as the grounded candidate universe first:

- `Place` has `id, city_code, name, category, latitude, longitude, provider_key, external_id, opening_hours_json, tags_json, metadata_json, updated_at, coordinate_system, source_coordinate_system`.
- Only exact current-Journey-city Place rows with valid WGS-84 coordinates may be suggested as actionable canonical Place choices.
- Exclude places already present in the single active shared plan (and current rendezvous); exclude structural/demo anchors that are not a tourist destination.
- Use geodesic/Haversine straight-line distance solely for shortlist discovery and ranking. Never present it as a travel-time estimate, walkable path, arrival guarantee, or place opening fact.
- Restrict the shortlist to a reasonable locality and cap candidates; do not return the entire city catalog or score thousands of POIs per request.
- Personal interest ranking may use user-selected category and already-authorized confirmed traveler preferences when present. Do not fabricate personalized tastes.
- Carry source/provenance: demo/fixture records must be labeled as demo/fixture, not "live nearby"; stale/unknown opening hours remain `UNKNOWN`.
- No generic model guess can mint a canonical Place identity. Existing place providers/catalog hydration may be reused *if present and honestly governed*, but **live external search is not required for this bounded strike**.

### Time budget

A user-selected 15/30/45-minute budget is a **preference**, not permission to alter protected commitments.

Server must derive the next rendezvous from the current active PlanVersion and any R63 current split. When there's too little actual time or the return time is unknown, say so. If the user chooses a candidate, run the existing **R65 member-private fit preview** as the authoritative route-derived evaluation, subject to its live-provider and provenance policy. You may reuse a bounded preview for the chosen candidate; do not trigger expensive 3×N live route captures merely to populate a pretty shortlist.

- No "can fit" labels from Haversine distance, static walk-speed multipliers or model confidence.
- If R65 has no qualifying provider route, show "route time unverified; check before you go" while still allowing explicit manual choice (subject to R63/R64 preconditions).
- If exact rendezvous unavailable or too late, do not quietly create a split; show a truthful explanation and let the user continue current plan.

### Private and governed selection

No R63 intent or R64 quest may be created by **search alone**. Selection requires an explicit confirm action from the authenticated in-force member.

Prefer reusing `_run_planned_separation_command` / R63 active-plan server resolution and the R64 `create_or_replace_member_side_quest` product path rather than introducing a parallel intent state machine. R63 has existing operator-start preconditions; surface them naturally and safely rather than bypass them. If a combined atomic action is practical, bind member/plan/rendezvous/place server-side and use one transaction; if not, make partial success visibly recoverable without silently leaving an orphan split.

When an R63 split already exists, reuse its active rendezvous and create/select a new R64 private quest according to its state transition policy; don't silently overwrite an in-progress quest.

### Privacy and authority

- All scout queries and selection actions require authenticated in-force Journey membership.
- Bind the one-time location observation to this exact member/traveler/Journey and reject stale, future, poor-accuracy, foreign, removed-member, wrong-city or malformed observations.
- Private discovery results only go to the requesting member. Never put candidate lists or private selection into shared `operator.group_presence`, shared plan/proposals, generic route-operation status, group events, or globally readable audits.
- Other members can observe only preexisting coarse `PLANNED`, `ACTIVE_SELF_REPORTED`, `FINISHED_RETURN_UNCONFIRMED`, `RETURN_STARTED_REPORTED` group status.
- An optional nearby coordinate is user-owned location evidence and never becomes device-level physical-presence proof simply by appearing in the shortlist.
- Do not initiate external Agent calls for suggestions solely to create an "autonomous" label. *Real, actionable suggestions using grounded places* are the product proof.

## Implementation suggestions (not architectural mandates)

- Thin member-bound endpoint such as `POST /api/v1/journeys/{journey_id}/moment-scout` with `location_observation_id`, `budget_minutes`, `interest` as validated schema. Existing signed principal resolution, location freshness/accuracy, and group presence routines can be reused.
- Return `scout_state`, `rendezvous`, requested budget, `observed_at`, evidence boundary, and up to three `{place_id, name, category, straight_line_distance_m, place_provenance, opening_state, fit_authority}` candidate items. This output must be owner-only.
- A short-lived scout-context token/fingerprint may help guard against race between discovery and acceptance. At **selection** re-resolve membership, exact Place, active PlanVersion, rendezvous and active R64 quest status; never trust a stale candidate ID or client-selected plan.
- Put new UI in the existing Journey Live flow near the private side-trip card, or in a compact built-in "Moment Scout" element, not a new demo page or separate route planner.
- Cap query/response/provider work; no background provider loops, repeated exploratory fetches or continuous location tracking.
- Make result copy in Chinese/English. The user should see why an option is attractive and what is still unknown, without reading internal status enums.

## Focused verification only

A small set of targeted backend tests and a two-authenticated-browser Playwright journey are sufficient. Must cover:

1. Real one-time location + real known Places -> up to 3 correctly ranked local choices, not static text.
2. Consent declined/no location -> no fabricated "near me".
3. Owner/member auth, foreign observation and removed-member requests are denied.
4. Shared-plan Places / synthetic structural anchors excluded; unknown opening hours not presented as open.
5. Straight-line distance not misrepresented as route time; source labels retained, including synthetic/demo.
6. One scout read changes no Journey state, no R63/R64 write, no Agent/Guardian operation.
7. Explicit selection creates/reuses **member-owned R63 split + R64 private quest** by the existing governed path, or reports a recoverable precondition failure.
8. Stale PlanVersion/rendezvous/member/candidate selection rejected; no retroactive retarget.
9. Non-owner projection/response contains no private option/destination/coordinates.
10. Selected option leads directly into actual R65 private navigation and return UI; no second active plan or shared cursor.
11. Live route absent => `UNKNOWN` fit, not guaranteed arrival.
12. R65 narrow tests including GPT's post-review preview/leave-by corrections pass.

For E2E: use fresh isolated SQLite; 2 actual authenticated contexts; owner requests scout with foreground location, chooses a real known Place, explicitly confirms and enters the R64/R65 card; partner sees only coarse status. Mocking external provider response is acceptable if labeled, **not** mocking the core R66 action API and R63/R64 mutations.

Run focused tests, frontend TypeScript/build, Python compileall, diff-check. One bounded fresh product flow. Report what happened and what did not (no external Agent/provider/physical visit if none). Stop there; no campaign repeats.

## Definition of done

R66 succeeds when CityNexus helps a traveler who **hasn't picked a destination** discover a grounded, appealing nearby personal stop, understand the shared rendezvous and uncertainty, explicitly choose it, and seamlessly begin the existing private Journey execution and return path.

This is the product outcome, not number of tests, commits, evidence files, or mutations.
