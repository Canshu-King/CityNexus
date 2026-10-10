# Revolution R15 — Truth-Seeking Autonomous Operator

## Result

R15 reached a real selectable and completed journey with estimate authority off.
The decisive product repair was allowing an exact OSM entity discovered by Nominatim or Photon to be re-queried through the Overpass/Nominatim enrichment path. No name matching or synthetic fact was added.

- branch: `codex/revolution-realtrip-recovery`
- clean source before product calls: `c9e3a2aa254e25ccdbac1818ef443bdfe1956f64`
- code checkpoint: `fc6a6d61` (`allow exact OSM provider ids to reach truth acquisition`)
- final report commit: recorded by the containing commit
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- runtime: `cn:glm-5.3-flash` through local WB2api compatibility endpoint
- P7: false; no mainline/authority merge

## R15 startup contract

- taskbook blob: `766e9bff59574f2bcb37be9fdbef8613cff454da`
- task: `Revolution R15 — Truth-Seeking Autonomous Operator`
- source approval boundary confirmed: an Agent-provided `source_url` is only `AGENT_SOURCE_CANDIDATE`; it cannot mint `OPERATOR_VERIFIED`.
- c9 preflight: real `inspect_journey` + `inspect_twin` completed with `cn:glm-5.3-flash`. The initial 1200-token context exhausted; the bounded same-model retry was raised to 4800 and completed. No raw credential was persisted.

## Real product run

### First strategy and pivot

The fresh Xiamen run `9768fe01-bb07-4b4e-a7ed-de868e874d34` used live discovery and found eight real OSM-backed viewpoint Places. No provider website tags or canonical opening/cost facts were available. With estimate authority off, the generated plan remained `PROVISIONAL_UNRESOLVED_FACTS` and `selectable=false`.

The operator then tried a different city/category strategy rather than repeatedly asserting the same blocker. Hangzhou was selected for a fresh museum-oriented acquisition attempt.

### Hangzhou truth acquisition

Journey: `068220ed-ca69-48fc-b32d-131873b42715` (`CN-HANGZHOU`).

Persisted AgentRun: `751154dd-05ba-487d-80df-44eb9d60190e` using `cn:glm-5.3-flash`.

Live discovery returned seven museum Places. The Agent inspected Journey and Twin, searched once, selected the best source-bearing candidate, and attempted acquisition. Before the repair, the exact row `nominatim:relation/8281187` incorrectly returned `NO_PROVIDER_ENTITIES` because the enrichment boundary accepted only `overpass:` IDs.

The bounded repair changed `_element_ref` to accept only explicit provider namespaces (`overpass`, `nominatim`, `photon`) with an exact OSM type/id. It does not perform name, substring, edit-distance, or first-result matching.

After restart, the same place was reacquired through the real product gateway:

- Place: `real-place-f96479630d9416746831e90f`
- provider entity: `nominatim:relation/8281187`
- Overpass: HTTP 200, one exact element
- Nominatim lookup: `ACQUIRED`, one matching entity, `extratags=1`
- opening: `Mo 12:00-17:00; Tu-Su 09:00-17:00`, normalized valid
- cost: `KNOWN`, `amount_minor=0`, `fee=no`, source Overpass/Nominatim
- website binding: `PROVIDER_TAG_EXACT_URL`, `matched_provider_entity=true`
- official page fetch: attempted but unavailable; it did not block because the provider-backed OSM facts were already sufficient

The second exact Nominatim entity, China Tea Museum Shuangfeng, also supplied canonical opening/cost facts. No estimates were used.

### Candidate, selection, mobility

The real `generate_plans` call produced:

- PlanVersion: `24b72baa-c182-50b5-9071-fffa17bf20b2`
- `status=CANDIDATE`
- `selectable=true`
- unresolved facts: `[]`
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- mobility: `valhalla-http`, `LIVE_PROVIDER_CAPTURE`
- snapshot: `e76f99cb-c24d-4f17-81de-0425b373937e`
- edge: Silk Museum → Tea Museum, 62 minutes, hard eligible

The real select call changed Journey to `PLANNED` with active plan `24b72baa...`; the real start call changed it to `ACTIVE`. JourneyTwin exposed the actual `used_edge_ids` and eligibility receipt:

```json
{
  "used_edge_ids": [["real-place-f96479630d9416746831e90f", "real-place-a493eff36ea37ca736d797d3"]],
  "provider": "valhalla-http",
  "fact_quality": "LIVE_PROVIDER_CAPTURE",
  "hard_eligible": true,
  "decision": "HARD_ELIGIBLE"
}
```

### Disruption, authority approval, completion

The real current activity was reported closed. Event:

- event: `78938f29-f879-41cf-af6c-21e55a1d6c32`
- type: `CLOSURE`
- affected activity: Silk Museum
- target resolution: `CURRENT_POSITION`

Deterministic recovery captured a fresh Valhalla incident snapshot `16b03df6-c67f-4a7a-8a55-211922a3cd4f` and generated proposal `dd466bda-c2d3-4f91-94b4-cf9b1897d6dc`:

- family: `F1_OPTIONAL_REMOVAL`
- removed: Silk Museum
- kept: Tea Museum
- travel delta: `-62` minutes
- hard constraints: passed
- provider evidence: live Valhalla, not synthetic

The explicit authority accept call changed the proposed PlanVersion `29d2b66e-9711-4ffb-9e92-1850b4a7be09` to the active plan. The revised activity then executed `depart → arrive → begin → complete`. Final Journey status is `COMPLETED`; active plan is the revised PlanVersion; the closure event and old/new plan lineage remain persisted.

## Source authority regression

`backend/tests/test_r15_source_authority.py` proves:

1. an arbitrary Agent URL remains `AGENT_SOURCE_CANDIDATE` and cannot promote canonical facts;
2. an exact fresh provider website tag can produce `PROVIDER_TAG_EXACT_URL` only after exact entity corroboration;
3. `overpass:`, `nominatim:`, and `photon:` OSM identities all map to the same exact `(type,id)` enrichment reference.

## Focused tests

```text
29 passed, 1 warning in 9.88s
uv run pytest tests/test_r15_source_authority.py tests/test_agent_mission_runtime.py -q
```

The warning is the existing Starlette/httpx deprecation warning. `git diff --check` passed.

## Remaining limitation

This run proves truth acquisition, estimate-off selectable planning, live mobility, authority selection, a closure pivot, grounded deterministic replan, and completion. The closure event itself was operator-reported and the recovery proposal was generated by the deterministic authority service; the AgentRun that preceded acquisition is persisted and machine-visible, but the native Agent did not autonomously call `request_replan` after the closure. That is the next capability increment, not a reason to relabel this run as synthetic success.

The official web fetch for the Silk Museum URL was unavailable, but canonical opening/cost were independently present in the exact Overpass/Nominatim entity and were promoted without using the unavailable page.

