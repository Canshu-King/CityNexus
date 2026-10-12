# Revolution R27 — Truth Mesh + Governed Collective Execution Strike

## Mission

Finish R27 as a real product capability.

Do not make the next run a provider retry exercise.

Required species change:

multiple people
-> separate preference truth
-> truthful world facts
-> collective mediation
-> collective server gate
-> normal mutation authority
-> real physical execution

## Phase 0 — correct the experimental fixture

Create a fresh disposable DB.

Before any provider call, create:
- one OWNER member
- one ADMIN or COLLABORATOR member

Write BOTH preferences through the product member-preference endpoint.

Example only:
- OWNER: garden/outdoor
- second member: craft/culture

Read them back through inspect_journey.

Hard precondition:
- both member IDs appear;
- both journey_scoped_explicit_preferences are non-empty;
- neither contains the other member's preference.

If this fails, abort the live run.

Do not rely on prose.

## Phase 1 — make provider identity acquisition independent

Refactor acquire_place_facts so exact identity providers are attempted independently.

The current OSM ref is already exact:
node / way / relation + numeric ID.

For each exact ref, capture identity evidence from bounded providers:

### Overpass
Useful for tags and enrichment.
Failure must be recorded, not automatically fatal.

### Nominatim lookup
Exact osm_type + osm_id match is valid entity identity evidence.
It does NOT by itself establish ticket/opening facts.

### Optional Photon
Only use if it provides an exact stable OSM identity already supported by current code.

Required rule:

If Overpass is unavailable but Nominatim independently returns the exact requested OSM type/id, official-source acquisition may continue.

Do NOT fabricate missing OSM tags.

Receipt example:

identity_mesh = {
  exact_ref: "node/2465643503",
  overpass: {status: "UNAVAILABLE", attempts: [...]},
  nominatim: {status: "EXACT_IDENTITY_MATCH"},
  identity_authority: "EXACT_OSM_ID_VIA_NOMINATIM"
}

If neither provider confirms the exact identity:
fail closed.

## Phase 2 — official source truth on degraded identity path

On exact Nominatim identity + trusted source binding:

- OPERATOR_VERIFIED is allowed as existing product behavior;
- CORROBORATED_OFFICIAL_SOURCE is allowed when WebObservation identity proof passes;
- raw Agent URL remains non-authoritative.

Fetch the official source live.
Parse opening/cost with existing official parser.

Opening/cost authority comes from official source, NOT from provider outage.

This permits:
Nominatim exact identity
+
Nara City official page
to produce canonical facts even while Overpass is down.

No UNKNOWN->FREE.

## Phase 3 — fix source-binding precedence

Fix both:
1. stored strong binding must outrank agent_observation candidate;
2. source_url must be derived AFTER final binding selection.

Test:
- stored OPERATOR_VERIFIED URL A
- Agent observation suggests URL B
- acquisition must fetch/use A unless server independently corroborates and intentionally upgrades according to explicit precedence.

Never let receipt binding and fetched URL disagree.

## Phase 4 — source bridge integration test

Add actual integration coverage:

server-owned WebObservation
-> acquire_place_facts(source_observation_id)
-> live/mocked HTTP page fixture in test
-> corroboration
-> canonical promotion

Negative:
- observation from another Journey
- wrong OSM identity
- wrong postcode/address
- raw URL
- page redirect to unsafe/private target
- stronger stored binding cannot be downgraded

Do not test only helper functions.

## Phase 5 — score the decision delta, not the whole trip

For every candidate plan, determine the collective preference subject by comparing it with current active plan / parent.

Preferred:
- added Place
- replaced optional Place
- materially changed optional experience

Persist:
- fit_subject_place_ids
- fit_subject_tags
- fit_subject_basis

Do not score shared base activities as if they were the candidate choice.

If the only difference is garden vs craft, the matrix must reflect garden vs craft even if both plans share hotel, park, station, or C4 commitments.

Add regression where a shared background garden tag does not make the craft alternative look garden-friendly.

## Phase 6 — introduce collective mutation gate

Create one deterministic helper, conceptually:

collective_mutation_gate(
  session,
  journey,
  candidate_plan_ids,
  target_plan_id,
  mission_id
)

At mutation time it must recompute:
- MEMBER_IN_FORCE set;
- member preference contexts;
- role capabilities;
- candidate hard status;
- fit matrix;
- mediation classification.

Rules:

### INSUFFICIENT_WORLD_FACTS
deny mutation:
COLLECTIVE_WORLD_FACTS_INCOMPLETE

### AUTHORITY_CONFLICT
deny:
COLLECTIVE_MUTATION_AUTHORITY_CONFLICT

### UNANIMOUS_DOMINANCE
only the server-derived dominant candidate may proceed.

### COMPROMISE_AVAILABLE
only the server-derived selected/acceptable compromise candidate may proceed.

### HUMAN_TRADEOFF_REQUIRED
deny unless a current resolved collective decision explicitly selects this candidate.

Integrate this gate into at least:
- accept_replan
- activate_standby if that path can mutate a shared Journey in the experiment

Do not rely on the model to obey fairness prose.

## Phase 7 — first-class shared decision state

Reuse JourneyMission.clarification_json if it remains clean enough.
Do not build a voting platform.

Required state:

kind = COLLECTIVE_TRADEOFF
policy = MATERIAL_TRADEOFF_REQUIRES_ALL_RELEVANT_MEMBER_RESPONSES
decision_epoch
active_plan_version_id
candidate_plan_ids
required_member_ids
responses_by_member
status
selected_candidate_id

Possible statuses:
- WAITING_FOR_MEMBERS
- RESOLVED
- STALE

Server creates this only when mediation == HUMAN_TRADEOFF_REQUIRED.

The Agent must not choose required_member_ids.

They come from decision_relevant_member_ids intersect MEMBER_IN_FORCE.

## Phase 8 — member-scoped responses

Each response updates only that member's response.

Validate:
- member belongs to Journey;
- MEMBER_IN_FORCE now;
- member is required for this decision;
- candidate option is server-derived;
- decision epoch still matches active plan + membership + role + candidate set;
- one member response cannot overwrite another row/key.

Do not claim caller authentication beyond what the repository actually has.

In the report distinguish:
- member-data scoping proven
- transport principal authentication not proven, if still absent

Missing required response:
WAITING_FOR_MEMBERS

All required members align:
RESOLVED
selected_candidate_id = aligned option

Conflicting responses:
remain unresolved.
No majority vote.
No OWNER preference overwrite.

Normal OWNER/JOURNEY_UPDATE or existing approval later authorizes mutation.

Preference voice is not mutation authority.

## Phase 9 — collective gate must bind the resolved decision

accept_replan must verify:

- target candidate is exactly selected_candidate_id;
- decision epoch is fresh;
- all required members still in force;
- role/capability basis has not changed;
- world facts still grounded;
- mobility still valid.

If member withdrawn / expired / role changed:
STALE_COLLECTIVE_DECISION
and recompute.

## Phase 10 — real shared live closure

Stay in Nara unless provider reality forces one bounded pivot.

Fresh DB only.

Useful experiment lead, not mission input:
- Nara Craft Museum exact OSM node/2465643503
- Isuien exact OSM way/97082272

Do not copy R22 facts.
Re-fetch identity and official facts live.

If WebResearch/SearXNG unavailable:
OPERATOR_VERIFIED source identity is acceptable for the experiment.
The operator supplies URL identity only, never opening/cost values.

### Build an ACTIVE Journey

Do not stop at DRAFT.

Need:
- active PlanVersion
- current activity
- actual opportunity/replan context
- live mobility

### Real Agent

Neutral mission.

The Agent must see:
- two real members;
- their separate preferences;
- grounded candidate plans;
- collective mediation receipt.

It must NOT receive:
- the desired candidate ID;
- a hardcoded compromise;
- a scripted tool order.

Allow bounded candidate/source search.

## Phase 11A — compromise path

If real third candidate satisfies the fairness gate:
- COMPROMISE_AVAILABLE;
- Agent chooses/proposes it;
- collective mutation gate confirms it;
- normal Gateway/approval;
- execute;
- Journey progresses/completes.

## Phase 11B — trade-off path

If no honest compromise exists:
- HUMAN_TRADEOFF_REQUIRED;
- open shared decision;
- collect required member responses;
- if they align, RESOLVED;
- collective mutation gate admits only selected plan;
- normal Gateway authority;
- execute.

Do not synthesize agreement.

## Phase 12 — physical proof

Final receipt must show:
- exact members and preferences;
- exact candidate facts;
- fit subject/delta;
- per-member fit;
- mediation state;
- Agent trace;
- shared decision if used;
- collective gate receipt;
- normal authorization receipt;
- actual mobility edges;
- actual activity execution;
- final Journey state.

## Mandatory controls

1. One member withdrawn:
   recompute mediation without them.

2. One member lapsed:
   cannot participate in new decision state.

3. Role capability change:
   preference truth remains unchanged;
   mutation authority changes;
   pending collective decision becomes stale if authority basis changes.

4. Severe-loser plan:
   accept_replan must reject it even if Agent calls accept.

5. Model tries non-selected candidate after compromise classification:
   reject.

6. Human-tradeoff unresolved:
   reject mutation.

7. World fact becomes stale/unknown:
   reject before collective mutation.

8. Overpass down, Nominatim exact identity + trusted official source available:
   fact acquisition can still close truth.

9. Overpass and Nominatim both unavailable:
   fail closed.

## Tests

Add focused tests for:
- independent identity mesh;
- source binding precedence;
- end-to-end source observation promotion;
- decision-delta preference scoring;
- collective mutation gate;
- shared decision state;
- stale membership/role decision;
- severe-loser rejection.

Then run R20-R27 focused lineage ONCE.

No repeated audit carousel.

## Success levels

R27-A:
member-aware read model.

R27-B:
grounded collective mediation.

R27-C:
server collective gate changes which real shared Journey mutation can execute, and the governed result physically executes.

R27-D:
only if a real caller-principal seam already exists or is reused cleanly; do not fake transport authentication.

Mandatory target: C.
Stretch: D.

## Anti-ORD

No R27.1.
No R28.
No new generic browser.
No generic voting system.
No group chat.
No recommender rewrite.
No manual fact values.
No waiting indefinitely for Overpass.
No synthetic compromise.
No report-only success.

## Closure sentence

CityNexus no longer merely explains what different travelers might prefer. It can keep their preference truth separate, build world truth from more than one provider without weakening authority, prevent an Agent from mutating a shared trip against the server's collective mediation result, and turn the collectively governed choice into real physical execution.
