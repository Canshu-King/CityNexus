# Revolution R27 — Collective Live Closure Strike

## Objective

Close R27 without changing species again.

Do not start R28.

Machine fact required:

shared Journey
-> multiple real in-force members
-> separate preference truth
-> at least two real GROUNDED_FEASIBLE options
-> material cross-member conflict
-> real Agent tries bounded mediation
-> compromise if reality supports it, otherwise targeted member clarification
-> server-owned group resolution
-> Gateway authority
-> physical execution

## Phase 0 — publish the implementation

First bind the existing R27 code to GitHub.

Expected local final code:
09550ac461ea7e9a566a5ed0b0c9992aece57091

Expected remote base:
e135c5cba3c4860f69767f784324a759da395805

Verify ancestry and push fast-forward.

Only after remote binding continue.

## Phase 1 — inspect the real implementation after push

Before adding new code, inspect the remote diff and verify:
- member projection really filters MEMBER_IN_FORCE;
- member TravelerTwin contexts are separate;
- owner mission preferences are not copied;
- per-member fit matrix retains explicit vs learned provenance;
- classifier cannot average away an unacceptable member;
- INSUFFICIENT_WORLD_FACTS blocks mediation;
- role capabilities are loaded from JourneyRoleCapability.

If any of these exist only in tests, fix them before runtime.

## Phase 2 — close the fact-acquisition coverage gap

Preferred minimal capability:
research_place_sources(place_id)

Read-only.

It should reuse existing WebResearchProvider/SearXNG, persist NON_AUTHORITATIVE WebObservation rows, and return a bounded source list.

No raw search result becomes authority.

Extend acquire_place_facts with source_observation_id or equivalent server-owned reference.

Add deterministic source identity corroboration.

A successful binding receipt should look conceptually like:

provider_entity = exact Place.external_id
source_url = official source
approval = CORROBORATED_OFFICIAL_SOURCE
identity_basis = {
  matched_provider_entity: true,
  matched_name: ...,
  matched_secondary_anchor: phone/address/postcode/provider-url,
  web_observation_id: ...
}

Only then promote parsed opening/cost.

### Required negative controls

- same-name wrong-city page => reject;
- official-looking domain but identity mismatch => reject;
- model raw URL without corroboration => no promotion;
- conflicting official price/opening => CONFLICTING, not latest-wins;
- search snippet alone => NON_AUTHORITATIVE.

## Phase 3 — do not over-scope if web search is unavailable

If no configured WebResearchProvider and no SearXNG:

record:
SOURCE_DISCOVERY_UNAVAILABLE

Then use existing OPERATOR_VERIFIED live source binding for at most 2-3 candidates in the final R27 experiment.

The operator supplies source identity, NOT fact values.

The server must fetch/parse live page and still enforce canonical truth.

Do not spend hours installing a search stack.

## Phase 4 — Nara closure fixture

Stay in Nara first.

Use fresh disposable DB.

Live:
- Overpass
- Nominatim
- Valhalla
- official page fetch

No copied R22 Place facts.

Useful known lead for debugging only:
Nara Craft Museum
overpass:node/2465643503
official Nara City facility page.

Do not place its name, ID, URL, or "choose craft" in the Agent mission.

At minimum obtain two materially different real GROUNDED_FEASIBLE candidates.

One may be Isuien if current facts remain valid.
The second should be independently reacquired.

## Phase 5 — clean member semantics

At least two MEMBER_IN_FORCE travelers.

Each has:
- own JourneyMember;
- own explicit journey preference;
- own TravelerTwin soft context.

Create material conflict.

Example dimensions are allowed in setup:
- traveler A values garden/outdoor;
- traveler B values craft/culture.

Do not make one option hard-infeasible just to manufacture a social conflict.

## Phase 6 — preference voice vs mutation authority

Any in-force member may state ONLY their own preference.

This is not a Journey mutation.

Do not require JOURNEY_UPDATE just to say:
"I prefer craft."

But final Journey mutation must still use role capabilities.

Current seed means OWNER has JOURNEY_UPDATE and ADMIN/COLLABORATOR do not.

Receipts must distinguish:
- member_preference_authority
- journey_mutation_authority

Do not let OWNER answer for ADMIN/COLLABORATOR.

## Phase 7 — Agent mediation

Mission should be neutral:

"Use the shared trip well. Respect each current member's separate stated preferences and role boundaries. Prefer a real grounded option that avoids a material loser. If current options conflict, search only a small number of real alternatives before asking people. Do not invent world facts or social authority."

Do not include:
- candidate names/IDs;
- correct compromise;
- search terms that encode the answer;
- target classification.

Real Agent should:
1. inspect shared Journey;
2. inspect member-aware Twin;
3. observe the conflict;
4. bounded search/acquire facts if useful;
5. let server recompute mediation.

## Phase 8A — compromise closure if reality supports it

If a third real candidate becomes GROUNDED_FEASIBLE and fairness receipt shows:
- acceptable minimum member fit;
- lower max regret than the conflicting extremes;
- no hard-constraint loss;

then classify COMPROMISE_AVAILABLE.

Agent may propose it through the existing replan/opportunity surface.

Normal Gateway applies.

Execute it physically.

Journey should progress normally.

## Phase 8B — truthful no-compromise closure

If bounded search finds no acceptable real compromise:
do NOT fabricate one.

Classifier:
HUMAN_TRADEOFF_REQUIRED

Persist shared decision:
- decision_epoch;
- exact grounded options;
- required_member_ids;
- member response state;
- role/capability snapshot;
- policy id/version.

Policy:
MATERIAL_TRADEOFF_REQUIRES_ALL_RELEVANT_MEMBER_RESPONSES

Each relevant member answers for self.

Missing answer:
WAITING_FOR_MEMBERS

If responses align:
GROUP_PREFERENCE_RESOLVED

Then owner/JOURNEY_UPDATE authority or normal approval authorizes the mutation.

If responses conflict:
remain unresolved or ask the smallest next decision-specific question.
No majority vote.
No owner preference overwrite.

## Phase 9 — execute reality

The resolved collective choice must change the actual Journey.

Use normal:
- Gateway;
- PlanVersion/replan;
- live mobility;
- HTTP execution state machine.

Final evidence:
- selected option;
- per-member fit receipt;
- member responses or compromise receipt;
- authority receipt;
- actual used route edges;
- activity execution;
- Journey status.

## Phase 10 — governance controls

Mandatory:

1. Withdraw member B:
   - B disappears from active mediation;
   - B historical preference remains audit data;
   - classifier recomputes.

2. Expire member B:
   - B cannot submit a new preference response.

3. Role change:
   - preference truth unchanged;
   - mutation authority changes according to JourneyRoleCapability;
   - pending shared decision goes stale if authority basis changed.

4. Cross-member spoof:
   - member A cannot submit B's response.

5. World-fact gap:
   - INSUFFICIENT_WORLD_FACTS routes to acquisition;
   - no human question asks "is this place open?" or "how much is it?"

## Phase 11 — tests

Before live run:
- source corroboration tests;
- member preference-vs-mutation authority tests;
- shared decision state tests;
- R27 focused tests.

After live closure:
run R20-R27 focused lineage once.

No broad suite after each patch.

## Final report

Update the existing:
REVOLUTION_R27_COLLECTIVE_JOURNEY_MEDIATOR_RESULT.md

Do not create R27.1.

Append:
Collective Live Closure Addendum

Include:
- remote-bound final SHA;
- source-discovery availability;
- official source binding receipts;
- exact grounded candidate set;
- member matrix;
- real Agent trace;
- compromise search result;
- shared clarification/responses if needed;
- role/Gateway authority;
- final physical execution;
- governance controls;
- focused regression delta.

## Closure sentence

CityNexus did not merely put several TravelerTwins in one JSON response. It kept each traveler's preference truth separate, found the real world facts needed to compare shared options, searched for a mutually acceptable alternative before interrupting people, and when a human trade-off remained it collected only each member's own decision-relevant preference, kept mutation authority separate from preference voice, and turned the governed collective result into real execution.
