# Revolution R27 — Collective Journey Mediator

## The leap

R26 learned when one human must answer.

R27 learns that one Journey can belong to several humans whose preferences and authority differ.

Target behavior:

shared ACTIVE Journey
→ multiple in-force JourneyMembers
→ each member has separate TravelerTwin and explicit journey intent
→ real grounded options differ in value across members
→ server builds member-aware decision context
→ Agent searches for a mutually better option before escalating conflict
→ if a bounded grounded compromise exists, Agent proposes it and normal Gateway authority applies
→ if no acceptable compromise exists, clarification is targeted only to decision-relevant authorized members
→ expired, withdrawn, or unauthorized people cannot decide
→ group resolution changes actual execution

## Hard invariants

- one member's TravelerTwin must never be copied into another member;
- learned evidence remains soft and traveler-scoped;
- current explicit member intent beats that member's learned soft preference;
- membership state and role capability are server facts;
- withdrawn/lapsed members do not participate in current authority;
- role rights come from JourneyRoleCapability, not prompt assumptions;
- model never invents member authority;
- provider facts remain provider facts;
- group preference never changes hard feasibility, cost, mobility, commitments, or booking authority;
- no opaque averaging that hides a severe loser;
- no majority-vote shortcut.

## Phase 0 — R26 hygiene

Fix the three inline blockers in GPT_R26_EXTERNAL_CHECK, then move on.

## Phase A — member-aware Journey read model

Expose compact shared-journey context in inspect_journey / inspect_twin.

For every MEMBER_IN_FORCE:
- member_id
- traveler_id
- role
- capabilities read from JourneyRoleCapability
- explicit journey-scoped preferences
- compact TravelerTwin learned-soft preferences/conflicts
- decision relevance for the current action

Do not dump private historical prose.

## Phase B — per-member candidate value

For each grounded candidate, expose a bounded member-fit matrix.

Persist per member:
- explicit contribution
- learned-soft contribution
- effective fit
- provenance/conflict state

Use existing verified preference scoring separately for each traveler.

Do not collapse immediately to one group score.

## Phase C — deterministic mediation classes

Classify before asking anyone:

UNANIMOUS_DOMINANCE:
one grounded option is not materially worse for any decision-relevant member and better for at least one.

COMPROMISE_AVAILABLE:
no current option dominates, but a third grounded option reduces material conflict and passes bounded fairness.

HUMAN_TRADEOFF_REQUIRED:
authorized member preferences materially conflict and no acceptable grounded compromise exists.

AUTHORITY_CONFLICT:
preference is clear but the member who wants the mutation lacks the required role capability.

INSUFFICIENT_WORLD_FACTS:
provider truth is missing. Acquire facts; do not ask humans.

Server owns the classification.

## Phase D — bounded fairness rule

Keep it transparent.

Preferred first rule:
- hard constraints remain absolute;
- explicit strong negative is a material penalty;
- learned soft has smaller bounded weight;
- compare highest minimum member fit first;
- compare lowest maximum regret second;
- mean fit is only a later tiebreak;
- explicit current intent beats learned soft.

A candidate cannot be called compromise if any required member falls below the declared unacceptable threshold.

## Phase E — autonomous compromise search

When the initial set conflicts:
- Agent may search real city through existing search_city_services;
- max three new candidates;
- canonical facts only for a bounded shortlist;
- normal real mobility truth;
- no whole-city crawl.

The mission must not name a compromise Place.

Success means the Agent discovers a provider-backed candidate not already in the active plan and server proves it improves the group conflict.

## Phase F — targeted multi-member clarification

If HUMAN_TRADEOFF_REQUIRED:
- identify exactly which in-force members are decision-relevant;
- identify which have the capability needed to bind the journey-level choice;
- persist one shared decision epoch;
- expose the question only to those required members.

Do not ask people whose answer cannot change the result.
Do not let one member answer for another unless explicit role policy permits it.

## Phase G — member-scoped answers

Every answer is bound to exact JourneyMember and Traveler.

Default scope:
THIS_JOURNEY_MEMBER_DECISION.

An answer may update only that member's journey-scoped explicit preference.

It must not rewrite another member, create cross-Journey memory without explicit remember choice, or widen Agent authority.

## Phase H — transparent group resolution

Minimal policy:
1. hard facts and constraints dominate;
2. each member's explicit intent dominates that member's learned soft;
3. seek unanimous dominance;
4. seek bounded compromise;
5. if trade-off remains, require decision-right holders derived from role capability / journey policy;
6. missing required responses => WAITING_FOR_MEMBERS;
7. no silent model tie-break.

If a journey-level group policy field is needed, add the smallest explicit representation. Do not hide policy in prompt prose.

## Phase I — real collective proof

Create a fresh provider-backed shared Journey with at least two real Traveler rows and two in-force JourneyMember rows.

Give them materially different but plausible preference contexts.

Preferred C path:
- member A materially favors garden;
- member B materially favors museum/craft;
- two obvious real options conflict;
- real Agent searches and discovers a third real grounded candidate;
- server proves lower max-regret / acceptable minimum fit;
- role authority permits action;
- Gateway governs;
- compromise activity actually executes;
- Journey completes.

Then run a no-compromise control:
- bounded search finds no acceptable compromise;
- only relevant authorized members are asked;
- their answers resolve the shared decision;
- execution follows the resolution.

If provider reality offers no honest compromise, targeted resolution may be the main C path. Do not synthesize a fake Place.

## Phase J — governance controls

Mandatory:
- withdrawn member preference stops participating;
- expired member cannot answer;
- member lacking required capability cannot bind mutation;
- OWNER / ADMIN / COLLABORATOR behavior is read from capability table;
- role change changes authority without rewriting preference truth.

## Phase K — privacy

Agent sees only the minimum preference summary needed for mediation.
No full TravelerTwin history.
No unrelated private memory.
No cross-member leakage.

## Success levels

REVOLUTION_A:
multi-member read model keeps preferences and authority separate.

REVOLUTION_B:
server classifies unanimous, compromise, tradeoff, authority-conflict, and world-fact cases from grounded options.

REVOLUTION_C:
real Agent either discovers and executes a grounded compromise or targets the correct authorized members and executes the resolved shared choice.

REVOLUTION_D:
role/expiry/withdrawal controls prove that changing membership authority changes who may decide without rewriting anyone's preference truth.

Target C/D.

## Anti-ORD

One capability branch.
No R27.1.
No generic voting system.
No group-chat framework.
No recommender rewrite.
No embeddings/personality vector.
No majority-vote shortcut.
No city-specific production code.
No report-only checkpoint carousel.

## Final report

REVOLUTION_R27_COLLECTIVE_JOURNEY_MEDIATOR_RESULT.md

Include base/final SHA, R26 hygiene, Journey/member IDs, roles/capabilities, per-member preference summaries, grounded candidate matrix, mediation classification, compromise/fairness receipt, real Agent trace, targeted clarification if used, authority resolution, Gateway result, actual execution, governance controls, and focused R20-R27 regression delta.

## Success sentence

CityNexus stopped treating a shared trip as if one TravelerTwin spoke for everyone. It understood who was actually in the Journey, kept each person's preferences and authority separate, found a grounded compromise when one existed, asked only the people whose judgment could change the shared decision when no compromise existed, and turned the collectively governed result into real execution.
