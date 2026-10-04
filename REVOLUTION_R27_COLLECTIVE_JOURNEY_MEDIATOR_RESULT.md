# Revolution R27 — Collective Journey Mediator

## Checkpoint

- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Base SHA: `e135c5cba3c4860f69767f784324a759da395805`
- Final experimental code SHA: `09550ac461ea7e9a566a5ed0b0c9992aece57091`
- Taskbook: `origin/gpt/revolution-r27-collective-journey-mediator-20261004`
- Mission blob SHA: `922a263453c504d801648dcec87ed179345b891d`
- Agent chain: WB2api / Hermes-compatible, `cn:glm-5.3-flash` -> `cn:deepseek-v4.1-flash`
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- P7 remains false; no authority/mainline merge was made.

## Implemented product change

The shared Journey surface is now member-aware rather than owner-Twin-aware:

- Journey creation creates an explicit OWNER `JourneyMember`.
- `inspect_journey` and `inspect_twin` return only `MEMBER_IN_FORCE` members.
- Each member carries its own `member_id`, `traveler_id`, role, server-derived `JourneyRoleCapability` values, journey-scoped explicit preferences, and compact learned-soft/conflict context.
- Owner mission preferences are not copied to collaborators.
- Withdrawn or lapsed members disappear from the in-force mediation projection while their membership row remains auditable.
- Candidate evaluation returns per-member explicit and learned contributions, minimum fit, maximum regret, mean fit, and unacceptable member IDs.
- Deterministic classification is `UNANIMOUS_DOMINANCE`, `COMPROMISE_AVAILABLE`, `HUMAN_TRADEOFF_REQUIRED`, `AUTHORITY_CONFLICT`, or `INSUFFICIENT_WORLD_FACTS`.
- The classifier does not average away a severe loser and does not treat UNKNOWN/revalidation-required facts as feasible.
- R26 skip hygiene is preserved: physical routing state is respected, EN_ROUTE fails closed, new adjacency requires a live provider capture, and clarified strategic skips are marked `CLARIFIED_HORIZON_CHOICE` with `preference_learning_eligible=false`.

## Runtime evidence

### Member isolation and configured Agent runtime

Disposable runtime DB: `backend\r27-runtime-20261004.sqlite3`.

Fresh demo shared Journey inspection produced two independent in-force members:

- Owner traveler: `11111111-1111-4111-8111-111111111111`; role `OWNER`; capabilities included `JOURNEY_UPDATE` and `MEMBER_MANAGE`.
- Collaborator traveler: `97750eb1-d523-4a2f-b9d8-44d57967df0f`; role `COLLABORATOR`; capabilities were server-derived and did not include owner-only mutation authority.

The collaborator's journey-scoped `craft` preference appeared only under that collaborator. After withdrawal, the collective projection contained only the owner. A real `cn:glm-5.3-flash` run inspected the shared Journey and Twin through:

`inspect_journey -> inspect_twin -> list_replans -> conclude_recovery`

The run was persisted by the Hermes-compatible runtime. It correctly found no current member conflict in that control Journey and selected a typed `NO_ACTION`. This is an Agent/context proof, not the R27 product closure claim: that control was a draft demo Journey and used no live shared-plan execution.

### Fresh live Nara shared Journey

- Journey: `378ea8dc-7121-4e80-b321-b0ebc426b6a9`
- Owner: `57730d77-68a9-44fe-b4f3-b6c0c2bb2686`
- Second member: `c04d92e4-1356-43dc-8ef5-acddb0aea3ae`, role `ADMIN`
- Discovery: live Overpass; no seeded golden itinerary was added.
- Secondary identity: live Nominatim lookup matched exact Overpass entities.
- Mobility policy: live Valhalla required for any executable candidate; no mock mobility was used.

The bounded acquisition run produced the following machine facts:

| Place | Provider identity | Opening | Cost | Result |
|---|---|---|---|---|
| `real-place-22cf72809897ff4c7f312fcf` / 依水園 | `overpass:way/97082272` | `NORMALIZED_VALID` | `KNOWN`, 1200 JPY | usable fact candidate |
| `real-place-e5c0ef1d8ffb8a8bd6fac3ee` / 吉城園 | `overpass:way/97082273`; Nominatim exact match | `NORMALIZED_VALID` | `UNKNOWN` | not authority-eligible |
| `real-place-343ee994da6a2014af11b3ed` / 東洋民俗博物館 | `overpass:node/1423069493`; Nominatim exact match | `UNKNOWN` | `UNKNOWN` | not authority-eligible |

For the museum acquisition, the receipt was:

- Overpass answered HTTP 200.
- Nominatim secondary source was `ACQUIRED` and `matched_provider_entity=true`.
- Official web source was `NO_SOURCE_URL`.
- Search source was `UNCONFIGURED`.
- `known_opening_count=0`, `known_cost_count=0`.

No UNKNOWN cost was converted to free, and no synthetic opening or mobility evidence was promoted.

## Exact current blocker

`R27_REAL_SHARED_COMPROMISE_NOT_CLOSED`

The current fresh Nara catalog has only one place with both canonical opening and canonical cost. Other real provider entities can be identified and corroborated, but their opening and/or cost facts remain UNKNOWN. Therefore the deterministic gate cannot produce the required pair of materially different, individually `GROUNDED_FEASIBLE` candidates. Without that pair:

- no honest per-member conflict/compromise decision exists;
- no compromise Place can be selected by the Agent;
- no Gateway activation or shared Journey execution is claimed;
- no member clarification is issued merely to hide a world-fact gap.

This is a provider-fact frontier, not a majority-vote or owner-Twin defect.

## Focused verification

Executed with Python 3.13:

```text
63 passed, 1 warning
```

Covered:

- R20 standby trigger authority
- R21 autonomous future synthesis
- R22 opportunity capture
- R23 adaptive TravelerTwin
- R24 adaptive memory
- R25 strategic horizon
- R26 decision-critical clarification
- R27 collective mediation arithmetic
- R27 member surface isolation
- R27 skip hygiene and live post-skip routing boundary

Also passed:

- `compileall -q app`
- `git diff --check`

## Next bounded experiment

Keep the same member-aware mediation branch. Use the Agent's bounded search/source path to acquire a second real Nara candidate with canonical opening and cost, or pivot once to another fresh city if the provider frontier remains unavailable. Only after two individually `GROUNDED_FEASIBLE` candidates exist should the real Agent be allowed to arbitrate compromise and enter the normal Gateway/execution path.

## Collective Live Closure Addendum — 2026-10-05

### Source binding and publication

- Closure taskbook: `origin/gpt/revolution-r27-collective-closure-20261004`.
- Source-truth implementation sketch blob: `dfd09cb6788ad6632a9d70b322f4a1db5378b1d2`.
- Local implementation was published before this runtime attempt. Local HEAD and
  `origin/codex/revolution-realtrip-recovery` both resolve to
  `d7f63fbdaeb25a18efdf32e466f163a59c579306`.
- The working tree remained free of tracked product edits after the commit; old R20–R26
  receipts and disposable databases remain untracked and were not included in the commit.

The bounded source-truth bridge is now in the product:

- `RESEARCH_PLACE_SOURCES` exposes only `research_place_sources(place_id)`; the server builds
  the query from the exact Place and Journey city.
- Results are persisted as `WebObservation` with `authority_status=NON_AUTHORITATIVE`.
- `acquire_place_facts` accepts the server-owned observation reference, fetches the page itself,
  and can promote only after exact normalized venue identity plus an independent provider-known
  anchor. Raw Agent URLs remain `AGENT_SOURCE_CANDIDATE`; snippets never become facts.
- Same-name/wrong-city, missing-anchor, and raw-URL negative controls are covered.

### Fresh same-Journey runtime readout

The earlier zero-byte database was discarded from consideration. A new disposable database was
created and product-created with the same shared Journey shape:

- DB: `backend\\r27-live-closure-20261004.sqlite3`
- Journey: `3a059855-1634-49b6-b4ce-8f3549d90998`
- two fresh Travelers and two `MEMBER_IN_FORCE` rows were created; the second member is `ADMIN`.
- owner preference and second-member preference were written through the member-scoped product
  route; no owner preference was copied to the other member.
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.

The same Journey was sent through the product's live discovery path with `Nara Craft Museum`.
Nominatim captured the city anchor, but the category query did not obtain a catalog response:

```json
{
  "mode": "live-unavailable",
  "provider_status": {
    "nominatim": "CAPTURED",
    "photon": "NOT_CALLED",
    "overpass": "UNAVAILABLE",
    "failure_stage": "category_search",
    "fallback_reason": "PROVIDER_TIMEOUT",
    "wrong_city_replay_blocked": true,
    "attempts": [
      {"endpoint": "https://overpass-api.de/api/interpreter", "http_status": 504},
      {"endpoint": "https://overpass.kumi.systems/api/interpreter", "error": "ReadTimeout"},
      {"endpoint": "https://overpass.private.coffee/api/interpreter", "error": "ReadTimeout"},
      {"endpoint": "https://overpass.openstreetmap.fr/api/interpreter", "error": "ReadTimeout"}
    ]
  },
  "candidates": []
}
```

The bounded `research_place_sources` Agent read-tool was also exercised on the fresh Journey.
There was no configured WebResearchProvider or SearXNG endpoint, so it returned the honest
machine result below and persisted no authoritative observation:

```json
{
  "status": "SOURCE_DISCOVERY_UNAVAILABLE",
  "authority": "NON_AUTHORITATIVE",
  "observations": [],
  "query": "\\\"吉城園\\\" NARA official opening hours admission fee overpass way/97082273"
}
```

As a bounded fallback probe, live Nominatim independently resolved two exact OSM entities on
that same fresh Journey (`node/2465643503` and `way/97082272`). They were materialized as live
Nominatim candidates with opening facts still `UNKNOWN`; the existing fact-acquisition boundary
correctly did not treat Nominatim-only identities as Overpass fact entities. The attempted
operator-bound official fetch therefore did not promote opening/cost. No R22 persisted facts,
manual opening values, free-price inference, mock mobility, or synthetic compromise was used.

### Exact current blocker

The blocker has changed from “Nara has no second real candidate” to:

`R27_LIVE_FACT_ACQUISITION_COVERAGE_BLOCKED_BY_OVERPASS_PROVIDER_TIMEOUT`

This is precise and machine-derived:

1. live Nominatim is available and can resolve real OSM identities;
2. all four bounded Overpass mirrors failed during the category acquisition stage;
3. the current canonical fact acquisition function requires an Overpass entity reference and
   performs its own Overpass + Nominatim observation before official fact promotion;
4. therefore the fresh Journey has zero product-canonical, fully grounded candidates from this
   run, so a two-candidate collective conflict cannot honestly be constructed;
5. consequently no collective Agent mediation, Gateway mutation, or physical execution is
   claimed in this checkpoint.

This is not evidence that Nara lacks a second real candidate. It is a live provider coverage
frontier. The source bridge is implemented and bounded fallback is exhausted for this run; the
next in-scope action is to rerun the same fresh Journey when Overpass category acquisition is
available, then acquire facts through server corroboration before starting the real collective
mediation.

### Focused verification after source bridge

```text
67 passed, 1 warning
python -m compileall -q app: PASS
git diff --check: PASS
```

The 67 tests include the complete R20–R27 focused lineage, R27 member isolation/fairness/skip
hygiene, and the new source-truth bridge controls. This remains an implementation + exact
blocker checkpoint, not a collective live closure claim.

## Truth Mesh + Governed Execution Addendum — 2026-10-05

### Source binding

- Current branch: `codex/revolution-realtrip-recovery`.
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`.
- Prior local/remote starting SHA: `a8f8cc342dcdd56c61acb8cce5f834588d21b2c2`.
- Substantive implementation SHA before the final select-gate follow-up: `e18c68e1fe8d4187d230b58301494b6c380dcc53`; the final SHA is recorded by Git with this addendum.
- R27 final-strike taskbook blobs: `a47afcd79a0fb6da7e0557b68d6c783b95b6cbd1`, `0f658ba5f97be4797393d46db153224b2badd838`, `6e23b3218f1563a397459bffd4eb486da3847bab`, `4fb9dbf5c1a2b2f68c1bc1350a0bc83798c22370`.
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`; no authority/mainline merge was made.

### Fresh live runtime facts

Disposable DB: `backend\\r27-live-20261005-d.sqlite3`.

- Journey: `6b3f8094-7123-49a1-8774-88a279f1a8aa`.
- OWNER member: `505ca82f-2009-467b-ab9b-c1ea2334a36a`, preference `interest/garden`.
- ADMIN member: `14eec2cf-fd5b-4a81-a1c6-d72e234b6610`, preference `interest/museum`.
- Both rows are `MEMBER_IN_FORCE`; the preferences are distinct and were written through the member-scoped API. No owner preference was copied to the ADMIN.
- Live discovery created the Nara catalogue in this disposable run. The relevant provider entities were `overpass:way/97082272` (Isuien Garden) and `overpass:node/2465643503` (Nara Craft Museum).
- Truth Mesh acquisition ran live Overpass and live Nominatim exact lookup. The Craft Museum official page was fetched and parsed as `OFFICIAL_WEB_VERIFIED` / `VERIFIED_PROVIDER`; Isuien was provider-backed with canonical Nominatim/Overpass opening and cost tags (`1200 JPY`).
- Two independent plans were generated with `require_fully_grounded=true`; both received live Valhalla mobility. The garden-plus-museum plan used `real-place-22cf72809897ff4c7f312fcf -> real-place-b47a20314c81d5a81381d4a4`, `22` minutes, `LIVE_PROVIDER_CAPTURE`, `HARD_ELIGIBLE`.

The corrected collective projection uses only the plan delta and canonical category/tags. Machine receipt for the selected plan:

```json
{
  "classification": "UNANIMOUS_DOMINANCE",
  "selected_plan": "293a4de2-ed4e-5a78-8da2-5bd2b5d33f59",
  "owner_effective_fit": 1.0,
  "admin_effective_fit": 1.0,
  "rejected_alternative_owner_fit": 0.0,
  "rejected_alternative_admin_fit": 1.0,
  "alternative_rejection": "COLLECTIVE_CANDIDATE_NOT_DOMINANT"
}
```

The server gate was exercised on the normal selection path. The selected plan returned HTTP 200; selecting the museum-only alternative returned HTTP 409 `COLLECTIVE_CANDIDATE_NOT_DOMINANT`. This proves that fairness is enforced at the mutation boundary rather than trusted from Agent prose.

### Governed physical execution

The allowed plan was selected and executed through the ordinary product state machine:

```text
Isuien Garden: depart -> arrive -> begin -> complete
Nara Craft Museum: depart -> arrive -> begin -> complete
Journey: COMPLETED
active_plan_version_id: 293a4de2-ed4e-5a78-8da2-5bd2b5d33f59
```

The final Journey was read back as `COMPLETED`; the active plan carried the live Valhalla snapshot and the actual edge remained hard eligible. This is a deterministic collective-governance execution proof, not an Agent-autonomy claim.

### Real Agent runtime result and exact blocker

The existing WB2api configuration was loaded only into the disposable process environment. A short preflight against `http://127.0.0.1:7863/v1/chat/completions` returned a real `tool_calls` response from `cn:glm-5.3-flash`.

A real Hermes-compatible `AgentRun` was then persisted for the same shared Journey. It executed:

```text
inspect_journey -> inspect_twin -> conclude_recovery(NO_ACTION)
```

The model saw two separate `MEMBER_IN_FORCE` projections and the separate `garden` / `museum` preferences. The run was a completed NO_ACTION control against an already completed Journey; it did not mutate and is not counted as collective closure.

The principal R27 closure blocker therefore remains exact and unchanged in kind:

```text
R27_AGENT_COLLECTIVE_LIVE_MEDIATION_NOT_CLOSED
```

The configured model runtime is now proven callable, but this round did not run the model on an ACTIVE shared Journey whose candidate conflict required a model-selected compromise or member clarification. No fabricated Agent success is claimed. The transport-level caller-principal seam is also still not proven; member data scoping is proven, while authenticated traveler identity is not.

### Focused verification after Truth Mesh and gate changes

```text
30 passed, 1 warning
python -m compileall -q app: PASS
git diff --check: PASS
```

The focused run covered Truth Mesh independent Overpass/Nominatim behavior, source observation corroboration, plan-delta fairness, normal plan selection, member projection, R26 routing hygiene, and the R20–R27 endpoint lineage. One unrelated legacy baseline assertion still expects the pre-R27 tool catalog and is not part of this change.

This is the final R27 implementation/runtime checkpoint: the product now has multi-source identity convergence and a server-enforced collective mutation boundary; the remaining closure work is a real configured Agent mediation run on an ACTIVE shared Journey, not another report-only or provider-retry round.
