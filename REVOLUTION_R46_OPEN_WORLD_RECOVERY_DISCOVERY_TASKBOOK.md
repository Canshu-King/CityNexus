# REVOLUTION R46 — Open-World Recovery Discovery

## Product-direction gate

This task is governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

The required product answer is:

> **CityNexus newly learns to expand the solution space when the current trip has too few good recovery options: it can actively search the real city for new provider-backed places, verify enough facts to make them usable, route them into the Journey, and replan with those new possibilities instead of only rearranging what was already known.**

If implementation becomes “make R45 produce two candidates” or “run another verifier”, stop and correct course.

## Starting truth

R45 is complete at `c9ca50e95e147d1fa193b3ee61fb37a67024a24a`.

Its honest fresh shared-Journey result was:

`COLLECTIVE_OPERATOR_NO_COMPROMISE`

because the server-derived replan surface contained only one grounded feasible candidate.

R45 correctly refused to:
- fabricate a second option;
- majority-vote;
- hand-write a compromise;
- issue fake collective authority;
- mutate the plan.

Do not rerun R33-R45 historical closures.

## Existing capabilities to connect — do not reimplement

The repository already has:
- real-city discovery via Nominatim / Photon / Overpass;
- materialized provider-backed `Place` rows;
- `search_city_services`;
- `research_place_sources`;
- `acquire_place_facts`;
- exact route capture / Route Session;
- replan generation over city Places;
- Guardian / World Context / Operator Brain;
- R45 collective Operator and mediation.

The missing capability is orchestration:

**the Agent does not yet intentionally expand the city candidate surface when the current recovery space is insufficient.**

Today `search_city_services` auto-discovers only when the city has no services and no Places at all.

That is too passive.

## 1. Recovery-surface sufficiency

Create a server-owned read model that answers:

> “Does this recovery currently have enough grounded alternatives to make a meaningful decision?”

Do not use raw proposal count alone.

Count distinct **grounded semantic futures**.

At minimum distinguish:
- zero grounded feasible alternatives;
- one grounded feasible alternative;
- two or more materially distinct grounded feasible alternatives.

Suggested states:

- `NO_GROUNDED_OPTION`
- `SINGLE_GROUNDED_OPTION`
- `SUFFICIENT_GROUNDED_OPTIONS`
- `DISCOVERY_IN_PROGRESS`
- `DISCOVERY_EXHAUSTED`
- `DISCOVERY_DEGRADED`

For collective mediation, “meaningfully distinct” should preserve the existing candidate-surface identity logic rather than counting duplicate PlanVersions.

## 2. External Agent decides what to search for

Do not hard-code:

if closure -> search museums

The external Hermes/DeepSeek Agent should reason from:
- incident;
- affected activity/category;
- Journey/Twin preferences;
- protected commitments;
- timing window;
- collective member preferences if applicable;
- current route position;
- budget.

Then it may request bounded open-world recovery discovery.

The server owns:
- search radius;
- provider limits;
- materialization;
- identity;
- provenance;
- fact authority;
- dedupe;
- feasibility.

The model owns:
- what kind of alternative would help;
- which discovered candidates are worth grounding further.

## 3. Explicit discovery tool/path

The current `search_city_services` behavior is insufficient because it only calls live discovery when the catalog is empty.

Add an explicit Agent capability such as:

`DISCOVER_RECOVERY_OPTIONS`

or a semantically equivalent explicit expansion flag/path.

Preferred semantics:

Input:
- journey_id
- trigger_event_id
- q/category intent
- bounded radius/limit hints
- mission_id

Server behavior:
1. validate Journey + recovery epoch;
2. derive search anchor from Journey context;
3. call existing `capture_real_city_candidates(..., mode="live")` when live providers are configured;
4. materialize exact provider-backed Places;
5. exclude Places already active/terminally invalid for the current recovery;
6. return provider/provenance + exact Place ids;
7. never create a ReplanProposal itself.

Do not allow the model to supply arbitrary coordinates or external IDs as truth.

## 4. Discovery is not enough — ground candidates

A newly discovered Place is only identity + whatever provider facts came with discovery.

For a candidate to enter an authoritative recovery proposal, it must satisfy the same truth boundaries already used by replanning.

The Agent may use existing tools:
- `acquire_place_facts`
- `research_place_sources`
- exact route capture

to ground:
- opening compatibility;
- cost when required;
- route feasibility;
- provider identity;
- schedule fit.

Estimated Agent facts may help reasoning, but with `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` they must not become authoritative recovery evidence.

## 5. Bounded discovery budget

Do not turn one disruption into an open-ended crawler.

For one recovery epoch, persist/derive a bounded discovery budget.

Suggested v1:
- at most 2 semantic discovery queries;
- at most 8 candidates per query;
- at most 3 candidates promoted to deeper fact acquisition;
- at most one route matrix/capture stage for the promoted candidate set.

Exact numbers may be adjusted, but the limit must be durable and visible in advanced Operator state.

Repeated Guardian pulses must not restart the budget.

## 6. Search only when it can change the decision

Discovery is justified when:
- no grounded feasible recovery exists; or
- only one grounded semantic option exists and the current mission/collective context needs a meaningful choice; or
- mediation reports no progress because the candidate surface is too narrow.

Do not automatically search merely because:
- there are fewer than N proposals;
- the user opens the Operator UI;
- a GET endpoint is called;
- the previous search returned a candidate the model simply dislikes without a grounded reason.

## 7. Recovery lineage and idempotency

Open-world discovery must remain inside the same:
- Event;
- RecoveryEpoch;
- GuardianRun / Operator recovery;
- standing/recovery mission lineage.

Do not create a new incident just because new Places were found.

Discovery query identity should be durable for one recovery epoch:
- normalized intent/category;
- Journey;
- recovery epoch;
- bounded anchor/radius policy.

Equivalent repeated queries should reuse materialized/cached results where possible.

## 8. Replan with discovered Places

After discovery + grounding, the Agent should call the existing `request_replan` path.

Do not create proposals inside discovery.

For closure/weather:
- newly materialized same-city Places should naturally enter the existing closure replacement ranking when authoritative enough.

If the planner requires explicit `place_ids` to bound a specific product mode, pass only server-materialized Place ids selected by the Agent.

The final proposal remains server-generated.

## 9. Collective Operator integration

This is where R46 becomes larger than “R45 fix”.

For a shared Journey:
- if initial recovery surface has one option;
- Operator should say it is **looking for more alternatives**, not immediately force a fake collective decision;
- external Agent expands the surface;
- newly grounded semantic alternatives may then create a real collective trade-off;
- R45 takes over from there.

User copy:

> “I only found one workable recovery, so I’m looking nearby for better alternatives before asking the group.”

If discovery finds no new grounded option:

> “I looked for alternatives, but I still only have one grounded recovery.”

That may lead to:
- NEEDS_ATTENTION;
- single-option recommendation;
- or a later product policy decision.

Do not manufacture a trade-off.

## 10. Single-traveller Operator integration

R46 must also help solo journeys.

Example:

> “The museum is closed. I checked the current plan and couldn’t find a good replacement, so I searched nearby and found two open alternatives.”

This should feed the normal R43 approval/autonomy path.

Do not make R46 collective-only.

## 11. Operator states / timeline

Extend Operator product copy with discovery moments:

- “I’m looking for more recovery options nearby.”
- “Found 6 real places.”
- “Checking 2 promising alternatives.”
- “Found 2 grounded recovery options.”
- “I couldn’t find another grounded option.”

Do not expose:
- Overpass raw payload;
- Nominatim query internals;
- candidate hashes.

Advanced details may expose provider/provenance.

## 12. Provider degradation

If open-world providers fail:
- do not erase existing recovery options;
- do not downgrade existing provider-backed Places;
- Operator shows `DISCOVERY_DEGRADED`;
- R44 Brain remains separate — provider discovery failure is not model-brain failure.

Do not call deterministic fixture data LIVE.

Replay/fixture is allowed in focused lab experiments if explicitly labelled.

## 13. World Context continuity

If the material world changes during discovery:
- revalidate RecoveryEpoch before proposal generation;
- stale discovery results may remain cached Places, but they must not authorize a stale recovery;
- the Agent must use the current recovery reality.

## 14. Focused tests

Only tests that prove this product capability.

At minimum:

1. one grounded option -> discovery eligible.
2. two materially distinct grounded options -> no automatic discovery.
3. duplicate semantic proposals do not suppress needed discovery.
4. explicit discovery works even when city catalog is non-empty.
5. discovery materializes provider-backed Place ids.
6. caller/model cannot inject arbitrary coordinates as Place truth.
7. discovery budget persists across repeated pulses.
8. equivalent query does not repeatedly hammer provider.
9. Agent may acquire facts for promoted candidates.
10. estimate-only facts remain non-authoritative with lab estimate authority false.
11. discovered grounded Place enters normal replan surface.
12. no direct proposal/mutation occurs inside discovery.
13. provider failure preserves existing candidate surface.
14. shared Journey can move from single option -> multiple grounded options -> R45 WAITING_FOR_MEMBERS.
15. no new option -> honest DISCOVERY_EXHAUSTED/NEEDS_ATTENTION.
16. R44 brain outage during discovery preserves recovery lineage.
17. TypeScript + focused Operator discovery Playwright.

Do not rerun R34-R45 historical proof campaigns.

## 15. One bounded R46 product experiment

Use one fresh Journey.

Prefer a disruption whose initial known-city recovery surface is intentionally narrow but honest.

Sequence:

1. Operator ON.
2. one material LAB_FIXTURE or real provider incident through normal World Context.
3. external Agent runs.
4. initial replan surface is inspected.
5. if surface is insufficient, Agent invokes one bounded open-world discovery flow.
6. real/live public provider may be used once if configured; otherwise use clearly labelled captured replay/lab provider.
7. Agent promotes a small number of discovered Places for fact acquisition.
8. server grounds what it can.
9. Agent calls normal request_replan again under the same recovery epoch.
10. stop after the first terminal product outcome.

For a shared Journey, if multiple grounded options emerge, it is acceptable and desirable for R45 collective flow to begin.

Valid outcomes:
- `OPEN_WORLD_RECOVERY_EXPANDED`
- `OPEN_WORLD_RECOVERY_COLLECTIVE_CHOICE_READY`
- `OPEN_WORLD_RECOVERY_EXHAUSTED`
- `OPEN_WORLD_RECOVERY_PROVIDER_DEGRADED`
- `OPEN_WORLD_RECOVERY_BRAIN_BLOCKED`

Do not rerun discovery to force two options.

## Stop condition

Stop after one bounded recovery-surface expansion experiment.

The user-visible capability must be obvious:

> **“When the things already in my itinerary aren’t enough to recover the trip, CityNexus can go out into the real city, find new provider-backed possibilities, verify the promising ones, and bring them back into the plan instead of giving up or inventing an answer.”**
