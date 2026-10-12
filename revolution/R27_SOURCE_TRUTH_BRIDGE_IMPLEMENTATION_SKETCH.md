# R27 source-truth bridge — concrete implementation sketch

This file exists to reduce rediscovery. Keep the patch narrow.

## 0. First action is still remote binding

Do not implement against an unpushed private history.

Verify and fast-forward push local:
09550ac461ea7e9a566a5ed0b0c9992aece57091

onto:
origin/codex/revolution-realtrip-recovery

Then continue on the experiment branch.

## 1. Add one bounded Agent action

In backend/app/agent/contracts.py:

add:
RESEARCH_PLACE_SOURCES = "RESEARCH_PLACE_SOURCES"

In backend/app/agent/tool_catalog.py:

add tool:
research_place_sources

Semantics:
- mutates_domain_truth = false
- changes_money = false
- changes_c4 = false

It may persist NON_AUTHORITATIVE evidence rows, but it must not mutate canonical Place truth.

Allow it in normal autonomous/PLAN_ONLY research envelopes. Do not make it approval-required.

## 2. Extend AgentToolCall minimally

In backend/app/schemas.py add:

source_observation_id: UUID | None = None

Keep existing:
place_id
source_url
source_class

Raw source_url remains compatibility input but must never gain authority merely because the model supplied it.

## 3. research_place_sources gateway method

Implement in AgentToolGateway.

Input:
- journey_id
- place_id

Server checks:
- Journey exists
- Place exists
- Place.city_code == Journey.city_code

Server builds the query. The model does NOT supply the search query.

Use exact server facts:
- Place.name
- city_code / traveler-facing city label if available
- Place.external_id only as an internal disambiguation term where useful

Suggested query intent:
"<place name>" <city> official opening hours admission fee

Provider order:
A. configured DeepSeek/WebResearchProvider if ai key + web search are enabled
B. configured SearXNG
C. otherwise return:
SOURCE_DISCOVERY_UNAVAILABLE

Maximum five observations.

Persist each result as existing WebObservation:
- journey_id
- query
- url
- domain
- title
- provider/model
- evidence_fingerprint
- content_excerpt
- authority_status = NON_AUTHORITATIVE

Do not add a new table.

Return only bounded fields:
id, url, domain, title, captured_at, provider, authority_status.

## 4. Do not import app.main private helpers into Gateway

Avoid making gateway depend on main._deepseek_client.

Preferred:
add a small provider factory/helper beside WebResearchProvider, or a small source-research service module using settings + DeepSeekResponsesClient.

Reuse the same config fields:
- ai_api_key
- ai_model
- deepseek_api_url
- deepseek_reasoning_effort
- deepseek_web_search_enabled
- searxng_url

No browser framework.

## 5. acquire_place_facts accepts server-owned observation identity

When source_observation_id is present:

Gateway loads WebObservation and verifies:
- observation exists
- observation.journey_id == current Journey.id
- authority_status is NON_AUTHORITATIVE / acceptable evidence state
- URL is present
- place_id is still same-city

Do NOT mark it operator verified.

Pass an explicit origin such as:
agent_observation

into fact acquisition.

Do not reuse the current non-agent branch, because that branch means OPERATOR_VERIFIED.

## 6. Add deterministic source-to-place corroboration

The correct location is fact_acquisition.py after fresh Overpass + Nominatim have returned the exact provider entity and before official facts are promoted.

Suggested pure-ish helper:

corroborate_official_source(
    client,
    *,
    place,
    observation,
    overpass_tags,
    nominatim_row,
    retrieved_at,
) -> dict

Return a receipt, never a boolean only.

Possible statuses:
CORROBORATED_OFFICIAL_SOURCE
IDENTITY_MISMATCH
INSUFFICIENT_IDENTITY_EVIDENCE
SOURCE_FETCH_FAILED
SOURCE_CONFLICT

### Identity evidence

Use server-derived provider identity plus page content.

Collect names from:
- Place.name
- Overpass name / name:ja / name:en / official_name
- Nominatim namedetails

Collect independent anchors from:
- phone / contact:phone
- addr:postcode
- addr:city
- addr:street + housenumber
- Nominatim display_name / address fields
- exact website/contact:website/url provider tag

Normalize:
- Unicode NFKC
- casefold
- whitespace/punctuation
- telephone digits

### Minimum promotion rule

Strong path 1:
source URL exactly equals a provider website/contact:website/url tag
+ exact provider entity was freshly returned
=> existing PROVIDER_TAG_EXACT_URL behavior.

Strong path 2:
official source observation
+ normalized exact/sufficiently strong venue-name match
+ at least one independent identity anchor match
=> CORROBORATED_OFFICIAL_SOURCE.

A government/local-government domain may strengthen source classification but NEVER replaces the identity anchors.

Do not accept:
- same display name only
- official-looking domain only
- search snippet only
- model claim "this is official"

Persist identity_basis, for example:
{
  matched_provider_entity: true,
  provider_entity: place.external_id,
  basis: "official_page_name_plus_phone",
  matched_name: "...",
  matched_anchors: ["phone"],
  web_observation_id: "..."
}

## 7. Only then promote official facts

If corroboration succeeds, create the source binding:

provider_entity = place.external_id
source_url = observation.url
source_class = OFFICIAL_WEB or MUNICIPAL_AUTHORITY as server-derived
approval = CORROBORATED_OFFICIAL_SOURCE
identity_basis.matched_provider_entity = true

Then use existing:
_official_web_facts

Promotion rules stay unchanged:
- opening must parse into OFFICIAL_WEB_VERIFIED
- cost must parse into VERIFIED_PROVIDER
- no UNKNOWN -> FREE

If corroboration fails:
- the page may remain an observation
- canonical Place opening/cost do not change because of it.

## 8. Conflict handling

If multiple corroborated official sources disagree materially:

do not "latest wins".

Persist a bounded conflict receipt.

Canonical result:
- conflicting field is not authority-eligible
- mediation sees INSUFFICIENT_WORLD_FACTS or explicit CONFLICTING

For R27 closure, avoid a conflicted candidate rather than solving source arbitration as a new project.

## 9. Nara debug lead, never mission instruction

The repository's own R22 machine receipt already proves a clean real entity:

overpass:node/2465643503

Nara Craft Museum / なら工藝館

previously bound to the Nara City official facility page and parsed as:
- opening 10:00-18:00
- JPY 0

Use this only to debug source acquisition.

Fresh R27 runtime must:
- discover/provider-load the Place again
- refetch the page
- parse it again
- recapture live mobility

Do not copy R22 fact rows.

Do not put this entity/name/URL into the Agent mission.

## 10. Operator fallback

If research_place_sources returns SOURCE_DISCOVERY_UNAVAILABLE because neither web provider nor SearXNG is configured:

stop source-tool implementation work there.

For the final R27 experiment, use existing OPERATOR_VERIFIED binding for at most 2-3 candidates.

Operator may assert:
"this URL is the exact official source for this exact provider entity"

Operator may NOT provide:
- opening hours value
- admission price value
- mobility value

Server must live fetch + parse.

Report clearly:
source_discovery_mode = OPERATOR_VERIFIED_FALLBACK

Do not call that autonomous source discovery.

## 11. Focused source tests

Add narrow tests:

1. research_place_sources persists <=5 NON_AUTHORITATIVE observations.
2. wrong Journey observation id rejected.
3. same-name wrong-city official page rejected.
4. official domain + name but no independent identity anchor rejected.
5. exact provider website tag remains eligible.
6. name + phone corroboration creates CORROBORATED_OFFICIAL_SOURCE.
7. name + postcode/address corroboration creates CORROBORATED_OFFICIAL_SOURCE.
8. raw Agent source_url alone remains AGENT_SOURCE_CANDIDATE.
9. search snippet cannot promote facts.
10. parsed free admission from a corroborated Japanese official page becomes VERIFIED_PROVIDER JPY 0.
11. conflicting corroborated sources do not latest-win.
12. unknown remains unknown.

## 12. Collective closure after facts exist

Do NOT stop again when two GROUNDED_FEASIBLE candidates exist.

Immediately continue the same run into:
- per-member fit matrix
- real Agent mediation
- bounded compromise search
- or HUMAN_TRADEOFF_REQUIRED
- per-member response
- group resolution
- normal Journey mutation authority
- Gateway
- live physical execution

R27 closure is collective behavior, not source research.
