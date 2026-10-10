# Revolution R67 — Open-World Live Moment Scout

## Product-first baton

Current branch: `gpt/revolution-r33-open-world-journey-adaptation`.

- R66 implementation: `6de6e47df8368b3df84f2c2078d57ad3f5bc0eae`.
- R66 added a member-private Moment Scout: one-time signed-member location, catalog-based nearest suggestions, explicit selection into R63 separation + R64 quest, then R65 fit/return.
- GPT's direct R66 review fixes on this branch before this taskbook:
  - `23148c162bab5f22d040cf5a3e2395ef1d98be32`: locality-ordered shortlist **before** the 500-row limit, not latest-updated-first.
  - `f8f6983ecb754ea0b6b3e0e5dcdca34b300f6b28`: focused dense-catalog regression.
  - `aac60cd751e0f3d05c2a7eadfcdabb97d0a1389c`: clear actionable UI when Journey Operator has not started, or membership/rendezvous is stale.
- These GPT fixes have not been verified by Codex's local tests yet. **Run the narrow R66 tests / typecheck once before R67**. Repair actual failures and move on.
- R66's checked GitHub artifact `reports/e2e-provenance/authoritative.json` records isolated `r66moment20261008i`, with AI disabled. It is run provenance, not live Overpass/physical-site evidence. No standalone R66 result document was found at the checked original SHA; do not manufacture one or turn this into an evidence campaign.

## The new traveler ability

R66 works when CityNexus already knows enough nearby Places. A real traveler in a less-covered area still hits `NO_GROUNDED_OPTIONS`.

R67 must offer a new explicit choice:

> **“Look for fresh places around me”**
>
> “This will share this one-time approximate search location with an external place-data provider. Results may be unavailable, outdated, unnamed, closed, or unroutable.”

After explicit opt-in, CityNexus may make **one bounded user-initiated provider discovery attempt** around the freshly authenticated member location. If real named OpenStreetMap venues are captured, the traveler can pick one and enter the existing R63/R64/R65 side quest, **even if that venue did not previously exist in the city's Place catalog**.

This is **an external-data capability**, not another framework, verifier, or generic Agent strike.

## Existing code to reuse

Before implementing, read these existing, working files:

- `backend/app/execution/moment_scout.py` (R66 local shortlist, geodesic ranking, signed member location, context, selection).
- `backend/app/integrations/discovery/real_city.py`:
  - `OverpassPOIProvider.search_with_evidence(query, latitude, longitude, radius_m, limit)`: actual OSM/Overpass nearby query with explicit answered / unavailable evidence and provider identity.
  - `DiscoveryCandidate`: provider key, stable OSM external identity, name, category, coordinates, tags, opening-hours evidence.
  - `materialize_candidates(...)`: existing provider-to-Place machinery; **carefully inspect its shared Journey-scoped evidence/Service/WebObservation side effects before reusing it**. Never send a private member's observation, search coordinates, interest or choice into group-readable records merely for convenience.
  - `normalize_opening_hours`, `_merge_existing_canonical_place_truth`, `_external_id`, provider coordinate/provenance handling.
- `backend/app/integrations/discovery/orchestration.py` if useful, but do not require a model/Agent or city-wide Nominatim geocode to answer a **known member-coordinate** nearby query.
- `backend/app/execution/member_side_quest.py` for owner-only quest and real-route authority.
- `backend/app/main.py` current `/moment-scout`, `/moment-scout/select`, and R63 planned separation binding.
- `frontend/src/features/execution/MomentScoutCard.tsx`; integrate here in the existing Journey Live screen.

Important: `capture_real_city_candidates(..., mode="live")` currently searches around a Journey-derived city/arrival anchor and writes Journey-scoped discovery evidence; it is **not** automatically safe as a drop-in for private member location. Reuse the safe provider and canonical identity layer; isolate the new private discovery product path.

## User interaction

1. User first gets the existing local R66 shortlist. For `NO_GROUNDED_OPTIONS`, show **“Search live nearby”**. An explicit refresh option may also be offered when local results are thin, stale or fixture-only.
2. Explain external-location transfer at the moment of action, distinct from the browser's geolocation permission. A user who declines still has full local R66/R64/manual travel capability.
3. On confirmation, acquire one fresh foreground location observation through the existing callback, then call the new signed-member endpoint with `observation_id`, interest, radius/budget. Do **not** accept naked lat/lon, traveler_id or Journey plan from request body.
4. Server asks a bounded real provider for nearby **named** OSM POIs and returns at most three relevant choices with real OSM identity, category, straight-line distance, provider provenance, capture time and availability confidence.
5. Show separate states: `LIVE_RESULTS`, `LIVE_ZERO_RESULTS`, `PROVIDER_UNAVAILABLE`, `PROVIDER_DISABLED`, `LOCATION_UNAVAILABLE`. Provider outages must not be advertised as “there is nothing interesting nearby.”
6. A result is a **place lead**. Never equate OSM tags or distance with open-now, cost, navigability, physical arrival or guaranteed return fit. If an opening-hours evaluator cannot establish time and timezone confidently, show UNKNOWN.
7. The traveler explicitly taps **Choose** and confirms returning to the current exact active-plan rendezvous. Only then is the chosen public POI materialized into the catalog (if not already present) and converted to a member-private R64 side quest via the current R63/R64 authority path. Existing R65 preview and return are immediately accessible.
8. Their partner only sees coarse member status and the shared rendezvous. No private shortlist, selected venue relationship, observation ID, raw coordinates, interest or private route geometry goes to non-owner views.

## Privacy-by-construction design

The location/interest is private even though a selected public OSM Place can be a reusable shared catalog fact.

- Never write the private search query/coordinates/provider response to generic `ProviderCall`, globally readable `RealPlaceCandidate` or `RouteAcquisitionOperation` views that other Journey members can read.
- `materialize_candidates` presently has substantial Journey-level side effects. For R67 either create a narrowly scoped *public Place only* canonical-upsert helper for the explicitly selected result, or demonstrate the reusable helper does not leak a private association. Do **not** materialize all returned suggestions or a member-specific search anchor.
- Prefer a short-lived **member-bound server receipt** for the captured candidate set. Bind to journey_id, member_id, traveler_id, location_observation_id, active PlanVersion, rendezvous target, interest and TTL. Store only what selection needs, in a private table or properly authenticated private store. Never put the full candidate list into `operator` or group projections.
- All select/read actions must revalidate signed in-force member, current active plan, rendezvous, candidate provider identity, TTL and current R64 state. An expired/stale receipt is a recoverable `SCOUT_EXPIRED` UI state.
- If choosing a venue would need a new split, the user must explicitly consent to that split exactly as in R66. If operator preconditions fail, show an actionable start-Operator instruction. No Agent call merely to decide whether a cafe exists.
- A provider should receive only the minimum one-time coordinates necessary. Product UI must disclose the external transfer. No background location, idle network requests, silent retries or cross-member query pooling.
- Ensure that provider/exception logs and persisted audit receipts contain only safe provenance/count/status, not private exact lat/lon or candidate-choice relationship. If normal provider error text includes private request data, sanitize logging.
- Use canonical OSM type/id identity to deduplicate a selected Place. Do not fabricate an entity, use bare name matching, or trust a client-supplied external identity to mint a Place.
- Respect stored WGS84 coordinates and source coordinate declarations. Do not silently merge different cities or alter existing known canonical opening/cost evidence.

## Real external discovery boundary

Use existing `OverpassPOIProvider.search_with_evidence` for actual provider work rather than generating examples. Keep one user action bounded:

- 800–2000 m locality radius by default (bounded below project policy); explicit query category mapping to existing provider vocabulary.
- 1–3 interest/category queries at most (ideally **one** per action), provider result limit small (e.g. 12 raw, top 3 displayed).
- Public Overpass mirrors are flaky; one provider invocation may follow the existing fixed bounded mirror policy. Record actual endpoints and failures, but do not rerun the entire strike to manufacture a LIVE_RESULTS conclusion.
- Honor existing `settings.real_city_enabled`, timeout and public-network proxy policy. No force-on when disabled.
- Accept zero only if provider actually answered with zero. If all mirrors failed, surface PROVIDER_UNAVAILABLE and keep local/manual search intact.
- Do not label `OPENSTREETMAP_REPLAY`, demo/fixture, synthetic or captured replay as new live discovery.
- Prefer returning valid named OSM objects with explicit OSM identity and legal usable source credit/link. Unnamed POIs must not become “OSM cafe” product suggestions.
- Results can remain unavailable in the isolated offline test. The new **real provider boundary** must be implemented, and run at most one bounded fresh attempt if configuration/network allows; faithfully report the result, not invent success.

## Selection behavior and partial success

Reuse R66's explicit-select→R63→R64 flow; do not create a parallel plan/Operator.

- Discovery is read-only as to shared Journey, plans, intents and quests.
- Candidate upsert is allowed only after signed owner confirmation; persist **public POI information only** in `Place`, no private origin/interest.
- Binding failure or R63 plan/rendezvous drift must **not** strand the Journey in an orphaned half-created state without a clear user recovery path. Prefer an atomic product transaction or a durable, explicit recoverable receipt; do not overwrite an in-progress quest.
- Idempotent double-confirmation must not mint duplicate public Places, splits or private quests.
- After selection, the side quest should be immediately usable with the *normal* R65 real provider/UNKNOWN semantics. Never lower provenance or skip the owner-bound execution state machine.
- The single active PlanVersion, protected commitments and shared cursor remain exactly unchanged by scouting or private selection.

## Focused implementation/test expectations

Product readiness is a real Journey Live experience with 2 authenticated members.

Focused backend cases:
1. Signed member makes an explicit one-shot real-provider query on a fresh own observation; foreign/stale/removed/low-accuracy observation rejected.
2. No consent action ⇒ no external request; disabled provider ⇒ PROVIDER_DISABLED; timed out provider ⇒ PROVIDER_UNAVAILABLE (not empty).
3. Real named OSM candidate may appear with identity/provenance, accurate straight-line distance and UNKNOWN route/fit if no route provider.
4. Provider result with only unnamed/invalid/unroutable objects yields honest LIVE_ZERO_RESULTS/NO_ACTIONABLE_POIS, no invented names.
5. Browsing/failed discovery writes no shared Journey mutation and no private provider data into public read models.
6. Member-private receipt cannot be consumed by another member or after plan/split/rendezvous/member/TTL change.
7. Confirming one real OSM result upserts **only that public Place** exactly once, then creates/reuses R63/R64 private execution. No candidate-list materialization and no cross-member selected-place association.
8. Group member receives only coarse status, not exact side stop/provider capture/coordinates.
9. Existing R65 `UNKNOWN` without real mobility is unchanged; no Guardian event from mere discovery/selection.
10. R66 nearest-first cap and actionable Operator error patches pass.

Frontend Playwright:
- Two actual authenticated contexts, one foreground consent path.
- Local R66 no-options or explicit freshness case ⇒ show opt-in external search; no automatic request.
- Controlled test-only provider substitution for positive named POI and outage cases, clearly labeled as simulation.
- Real `/moment-scout/live` API and selection writes; one confirmed candidate enters the R64/R65 card, collaborator sees only coarse status.
- Do not mock the core R67 write path or authentication.
- A fresh isolated SQLite DB once, focused TypeScript/build/compileall/diff check.
- If externally configured, one **bounded real** live provider attempt, record LIVE_RESULTS/LIVE_ZERO_RESULTS/PROVIDER_UNAVAILABLE/PROVIDER_DISABLED faithfully. No repeated attempts just for green proof.

## Definition of done

A member who has not named a destination, and whose local catalog is thin, can **explicitly request real nearby place data**, see honestly source-qualified options or truthful unavailability, select one, and immediately act on it within the one shared Journey — without publishing their private location or side quest to their companions.

**That is Revolution.** The goal is a new public-world capability the traveler can use, not additional audit/verifier scaffolding.

## Outside scope

- No R58–R66 historical strike replay.
- No second active plan, mock place seeding to claim broad city coverage, fake provider success, or endless verifier passes.
- No app-wide provider rewrite, large Agent orchestration or new planner.
- No permission to send private location to external providers without explicit user action.
- No pretending public-OSM availability means opening hours, physical presence, confirmed accessibility or viable return.
