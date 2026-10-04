# GPT deep external check — R27 closure checkpoint

Reviewed:
- uploaded REVOLUTION_R27_COLLECTIVE_JOURNEY_MEDIATOR_RESULT.md;
- uploaded CityNexus-Revolution-R27-Collective-Closure-20261005.zip;
- runtime DB r27-live-closure-20261004.sqlite3 from that ZIP;
- remote head a8f8cc342dcdd56c61acb8cce5f834588d21b2c2;
- member projection and collective mediation code;
- source-truth bridge;
- fact acquisition/provider ordering;
- generate_plans collective scoring;
- accept_replan / activate_standby mutation gates.

## Verdict

Do not start R28.

R27 remains open for product reasons, not for report polish and not merely because one Overpass retry failed.

The current implementation contains useful primitives, but collective governance has not yet become mutation authority.

## Machine contradiction 1 — runtime fixture did not contain two explicit member preferences

The uploaded SQLite runtime is authoritative over report prose.

Journey:
3a059855-1634-49b6-b4ce-8f3549d90998

The two in-force JourneyMember rows are:
- OWNER 99c9f386-7a77-4595-b586-f53e6853bb51
- ADMIN f676aed9-ec63-4d8b-8bc9-be3ae63ebd87

Machine state:
- OWNER preferences_json = {}
- ADMIN preferences_json = craft + culture
- Preference table = 0 rows
- both TravelerTwinSnapshot.explicit_preferences_json = []
- JourneyMission rows = 0
- AgentRun rows = 0
- PlanVersion rows = 0
- Activity rows = 0

Therefore the report sentence that owner and second-member preferences were both written is not supported by the delivered runtime DB.

The closure fixture must fail immediately unless BOTH intended member-scoped preference receipts read back successfully.

## Machine contradiction 2 — this is not only an Overpass identity issue

Current _element_ref already accepts exact OSM identity stored under:
- overpass
- nominatim
- photon

Example:
nominatim:node/2465643503
is a valid exact OSM ref.

The actual choke point is orchestration:

acquire_place_facts()
-> _acquire_overpass_payload()
-> if every Overpass mirror fails, exception escapes
-> Nominatim exact lookup and official source fetch never get a chance

So the current system is not yet a truth mesh; it is an Overpass-first chain with Nominatim as a secondary path reached only after Overpass succeeds.

Do not wait for Overpass to recover as the primary fix.

## Source bridge correctness bug

The new agent_observation source bridge has two correctness problems.

### Strong binding preservation

The code preserves an existing stronger binding only when:

binding_origin == "agent"

but not when:

binding_origin == "agent_observation"

Therefore a WebObservation path can ignore a stored OPERATOR_VERIFIED / PROVIDER_TAG_EXACT_URL / CORROBORATED_OFFICIAL_SOURCE binding.

Fix:
binding_origin in {"agent", "agent_observation"}

A weaker candidate must never downgrade stronger canonical source identity.

### source_url must follow the final binding

source_url is currently computed before stored-binding precedence is resolved.

After final source_binding is selected, source_url must be recomputed from that binding.

Never fetch URL A while the receipt claims authoritative binding B.

Add direct regression.

## Source bridge tests are still too shallow

Current tests cover pure helper behavior:
- raw Agent URL stays AGENT_SOURCE_CANDIDATE
- exact provider website tag corroborates
- same-name without anchor rejects
- wrong-city same-name rejects

They do NOT yet prove the end-to-end path:

WebObservation
-> exact Journey ownership
-> page fetch
-> identity corroboration
-> CORROBORATED_OFFICIAL_SOURCE
-> official parser
-> canonical Place opening/cost promotion

Add one integration test and negative controls around the actual gateway/acquisition path.

## Collective mediation is currently advisory, not authoritative

generate_plans returns:
- collective_member_fits
- collective_fairness
- collective_mediation

But accept_replan() does not recompute or enforce any collective mediation state before mutation.

activate_standby() also has no collective gate.

Therefore an Agent could theoretically see a severe-loser receipt and still activate/accept that plan if the existing single-traveler policy allows it.

This is not collective governance.

R27 closure requires a server-side collective mutation gate.

## Multi-member clarification is not implemented

The codebase currently contains R26 single-user clarification state.

The uploaded R27 code does not contain:
- WAITING_FOR_MEMBERS
- GROUP_PREFERENCE_RESOLVED
- required_member_ids
- shared response state
- collective decision epoch

Therefore HUMAN_TRADEOFF_REQUIRED currently has no complete runtime resolution path.

Do not claim targeted collective clarification until such state exists.

## Candidate fit can be polluted by shared background activities

generate_plans currently collects tags from every Place in each full candidate plan.

If every alternative shares a background garden/culture/place, both candidates can inherit that tag and appear to fit a member even when the decision-specific changed activity does not.

Collective preference fit must be based on the decision subject / plan delta, not indiscriminately on all shared activities.

Persist:
- fit_subject_place_ids
- fit_subject_basis = PLAN_DIFF or OPPORTUNITY_CANDIDATE

Use only materially changed optional candidate experience tags for group mediation.

Hard feasibility still applies to the whole plan.

## Authority conflict implementation note

AUTHORITY_CONFLICT does exist at the active_journey_members_with_capabilities wrapper:
if grounded mediation exists but no in-force member has JOURNEY_UPDATE, the projection becomes AUTHORITY_CONFLICT.

That part is real.

However it still is not enforced at accept_replan/activate_standby.

## Caller identity limitation

The current JourneyMember preference endpoint is member-addressed but not caller-authenticated.

The repository itself already notes that naming a traveler/member in a path is not proof of who is asking.

Therefore R27 must not claim transport-level anti-spoof governance yet.

For this round:
- target REVOLUTION_C as the mandatory close;
- keep D as a stretch only if an existing trusted caller-principal seam is found and reused;
- do not invent an unauthenticated X-Traveler-ID header and call it security.

A server test can prove response/member data separation, but not real user authentication.

## Revolution target

R27 is closed only when:

1. provider truth no longer has an unnecessary single-provider choke;
2. two in-force members really carry distinct machine-visible preference truth;
3. two or more real candidates are fully grounded;
4. the real Agent observes the conflict and attempts mediation;
5. the server collective gate constrains which plan can be mutated;
6. if a real compromise exists, it is selected/executed under the collective gate;
7. if no compromise exists, shared decision state resolves the trade-off before mutation;
8. Gateway remains the final mutation authority;
9. physical execution proves the collective result.

No R28 until this exists.
