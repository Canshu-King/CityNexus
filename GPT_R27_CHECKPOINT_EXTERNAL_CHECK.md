# GPT external check — R27 checkpoint -> collective live closure

Reviewed:
- uploaded REVOLUTION_R27_COLLECTIVE_JOURNEY_MEDIATOR_RESULT.md;
- remote codex/revolution-realtrip-recovery head;
- R27 taskbook branch;
- current fact acquisition/source-binding code;
- current WebResearchProvider surface;
- JourneyRoleCapability seed;
- R22 live Nara opportunity evidence;
- current official Nara sources outside the repository.

## Verdict

R27 is an implementation checkpoint, not closure.

The report is honest about the missing machine fact:
no fresh live run yet proves real collective mediation into Gateway + physical execution.

The member-aware surface and arithmetic may be substantial, but they are not remotely inspectable yet because the reported final code SHA is not on GitHub.

Do not start R28.

## P0 — source binding is broken again

The report names local final code:

09550ac461ea7e9a566a5ed0b0c9992aece57091

But GitHub cannot resolve this SHA and origin/codex/revolution-realtrip-recovery still points to:

e135c5cba3c4860f69767f784324a759da395805

Before any new product work:
1. verify local 09550ac... exists;
2. verify e135c5c... is an ancestor;
3. verify worktree has no accidental unrelated edits;
4. fast-forward push codex/revolution-realtrip-recovery;
5. fetch and verify remote HEAD.

Do not rebase or create a Git archaeology project unless fast-forward fails.

## The current blocker is misnamed

The report calls the live blocker:

R27_REAL_SHARED_COMPROMISE_NOT_CLOSED

and describes a provider-fact frontier because only Isuien had canonical opening + cost in the fresh Nara run.

External source inspection shows that the world facts do exist.

Examples:
- Nara Craft Museum / なら工藝館 has a Nara City official page with opening 10:00-18:00 and free admission.
- R22 in this same repository already closed a live path for overpass:node/2465643503, bound to that Nara City official page, with OFFICIAL_WEB_VERIFIED opening and VERIFIED_PROVIDER JPY 0.
- Yoshikien has source disagreement in current public material, so do NOT force it into a clean fact. A current tourism page says free while a current prefecture page labels it paid. Treat that as conflict or avoid it for the closure.

Therefore the accurate blocker is:

R27_FACT_ACQUISITION_COVERAGE_NOT_CLOSED

The product cannot currently rediscover/bind a clean official source on a fresh runtime even though the source exists.

## Why current Agent source acquisition stalls

Current code correctly refuses to trust a model-supplied URL.

When binding_origin=agent:
- source_class becomes AGENT_SOURCE_CANDIDATE;
- matched_provider_entity=false;
- approval=AGENT_SOURCE_CANDIDATE.

That means parsed official-page facts are NOT promoted merely because the model found a URL.

This boundary is correct.

The missing bridge is:

source discovery
-> server-owned identity corroboration
-> CORROBORATED_OFFICIAL_SOURCE
-> official parser
-> canonical promotion

Do not weaken the boundary by treating a search result as authority.

## Existing pieces to reuse

Already present:
- WebResearchProvider;
- POST /api/v1/journeys/{journey_id}/web-research;
- persisted WebObservation with NON_AUTHORITATIVE status;
- SearXNG source lead path when configured;
- acquire_place_facts;
- exact provider identity from Overpass/Nominatim;
- official-page parser for Japanese opening/cost;
- AGENT_SOURCE_CANDIDATE boundary;
- stored stronger bindings preserved over model candidates.

Do not build a generic browser framework.

## Preferred source-truth bridge

Add a bounded read-only Agent tool, e.g.:

research_place_sources

Input:
- journey_id
- place_id

Server derives query from exact Place + provider identity + city.

Provider order:
1. existing configured WebResearchProvider;
2. configured SearXNG;
3. if neither exists, return SOURCE_DISCOVERY_UNAVAILABLE.

Persist at most five WebObservation rows, NON_AUTHORITATIVE.

Then let acquire_place_facts optionally accept a server-persisted source_observation_id rather than trusting an arbitrary URL.

Before promotion, add deterministic corroboration:
- observation belongs to this Journey;
- URL is public-safe;
- fetched page matches exact provider Place identity;
- require normalized name match plus at least one independent strong anchor such as phone, postal/address token, exact provider website tag, or other server-verifiable identity field;
- government/local-government official domain may strengthen source class but must not replace identity matching;
- persist the evidence basis.

If corroborated:
- approval=CORROBORATED_OFFICIAL_SOURCE
- matched_provider_entity=true
- bind to exact Place.external_id
- only then allow _official_web_facts to promote opening/cost.

If official sources disagree:
- persist conflict;
- no canonical promotion;
- no UNKNOWN->FREE;
- no "latest page wins" shortcut.

## Bounded fallback for R27 closure

Do not let absence of a configured web-search service derail collective mediation.

If both WebResearchProvider and SearXNG are genuinely unavailable in the experimental runtime:
- record SOURCE_DISCOVERY_UNAVAILABLE;
- use the existing OPERATOR_VERIFIED source-binding path in experiment setup for a bounded number of live provider entities;
- re-fetch the official pages live;
- do not seed canonical fact values directly;
- do not give candidate IDs/names to the Agent mission;
- do not count this fallback as autonomous source discovery.

This is acceptable because R27's core capability is collective mediation, not a new web-search product.

## Clean Nara candidate lead

Prefer the already-proven real Nara Craft Museum entity rather than forcing Yoshikien:

provider entity:
overpass:node/2465643503

official source:
https://www.city.nara.lg.jp/site/shisetsu/60140.html

This is a DEBUG/EXPERIMENT LEAD, not mission input and not production hardcoding.

R22 already proved the same entity can become:
- OFFICIAL_WEB_VERIFIED 10:00-18:00;
- VERIFIED_PROVIDER JPY 0;
- live Valhalla executable.

The R27 fresh runtime must reacquire it from live sources; do not copy R22 persisted facts.

## Governance correction — preference voice != mutation authority

The current server seed is:

OWNER:
- JOURNEY_READ
- JOURNEY_UPDATE
- PLACE_EDIT
- MEMBER_MANAGE
- SHARE_GRANT_MANAGE

ADMIN:
- JOURNEY_READ
- PLACE_EDIT
- MEMBER_MANAGE

COLLABORATOR:
- JOURNEY_READ
- PLACE_EDIT

Therefore only OWNER currently has JOURNEY_UPDATE.

Do not interpret this as:
"only OWNER may have a preference."

Correct separation:
- any MEMBER_IN_FORCE may state their own member-scoped preference;
- no member may state another member's preference;
- those preferences participate in group fairness/mediation;
- mutation/approval authority still comes from JourneyRoleCapability + Gateway;
- ADMIN/COLLABORATOR preference can matter even when they cannot bind a Journey mutation;
- an OWNER cannot rewrite another member's preference truth merely because OWNER has JOURNEY_UPDATE.

This distinction must be visible in receipts.

## R27 closure target

Do not require a magical third compromise if provider reality does not supply one.

The preferred path is:
1. two or more real grounded options produce material member conflict;
2. real Agent performs bounded search for up to three compromise candidates;
3. if one passes fairness gate, propose/execute it;
4. otherwise classifier returns HUMAN_TRADEOFF_REQUIRED;
5. collect only decision-relevant member preference responses;
6. keep member preference authority separate from Journey mutation authority;
7. resolve using explicit shared-decision policy;
8. Gateway/approval owns mutation;
9. physical execution differs according to collective resolution.

Either real compromise OR truthful targeted human resolution can close C.

## No-compromise policy

Do not silently let OWNER break preference ties.

Use an explicit server-owned shared-decision policy.

Small first policy:
MATERIAL_TRADEOFF_REQUIRES_ALL_RELEVANT_MEMBER_RESPONSES

Meaning:
- every relevant in-force member may answer only for self;
- missing required response => WAITING_FOR_MEMBERS;
- disagreement is not silently majority-voted or owner-tiebroken;
- if all responses align, the shared preference resolution is machine-valid;
- final mutation still requires normal role/Gateway authority.

A separate owner approval may authorize mutation without changing anyone's preference answer.

## Success correction

R27 is not closed by:
- member-aware JSON;
- fairness tests;
- a single-member NO_ACTION control;
- provider blocker report.

R27 closes when:
multiple in-force members
-> separate preference contexts
-> real grounded conflict
-> real Agent mediation/search
-> compromise OR targeted member resolution
-> normal authority
-> changed physical execution.

