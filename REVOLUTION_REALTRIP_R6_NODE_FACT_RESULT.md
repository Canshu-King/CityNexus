# CityNexus Revolution Lab — R6 exact-node fact result

## Scope and binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- starting/final product source: `1444061cd3161381cc9abd2d7118d1b779c37a12`
- no source change in this diagnostic round
- disposable database only; no authority/mainline merge; `P7=false`

This round tested whether the unverified `狮子林` OSM node could receive facts from its own
provider identity without borrowing anything from the official OSM way.

## Exact provider acquisition

The real product endpoint was called with only:

```text
place_id = real-place-3295a86383d1f7216648cb00
provider_entity = overpass:node/4246892594
```

Machine receipt:

- HTTP 200
- acquisition status `ACQUIRED`
- Overpass element count `1`
- Nominatim secondary source `ACQUIRED`, exact provider match true
- `known_opening_count = 1`
- `known_cost_count = 0`
- official web `NO_SOURCE_URL`, not attempted
- searxng `UNCONFIGURED`, not attempted

The node's own facts after the call are:

```text
opening_hours.status = NORMALIZED_VALID
opening_hours = Mo-Su 07:30-17:30
cost_evidence.status = UNKNOWN
cost_evidence.amount_minor = null
price_known = false
cost_minor = 0   # compatibility placeholder, not “free”
```

No fact from `overpass:way/44679451` was copied to the node.

## Authority replay

After acquisition, the real explicit mixed-place generation was rerun with the verified way
and the exact node. It still returned:

```text
HTTP 422
reason_code = PLACE_COST_UNVERIFIED
message = GENERIC_COMPOSE_INFEASIBLE:GENERIC_COMPOSE_UNKNOWN_COST:real-place-3295a86383d1f7216648cb00
```

The current product plan remained unchanged:

```text
Journey.status = PLANNED
Journey.active_plan_version_id = 09715a08-4e06-57b7-bebc-b9a5adf872a2
Twin.projection_status = READY
Twin.active_plan_version_id = 09715a08-4e06-57b7-bebc-b9a5adf872a2
```

The selected plan still uses `real-place-054fa857eff7a99169399bdf` / `way/44679451` for
狮子林. Its frozen mobility evidence remains Valhalla-backed, non-degraded, and 3/3
hard-eligible on the actual used edges.

## DeepSeek operator evidence

The native DeepSeek PLAN_ONLY loop was rerun after the acquisition:

- run: `cdc9b1e5-9afa-40b8-aff6-b726e61189c1`
- mission: `239c8da8-b21e-4c64-b7c6-522c5bf26883`
- runtime: `NATIVE_DEEPSEEK_TOOL_LOOP`
- status: `COMPLETED`
- exactly three read-only calls, once each: `inspect_journey`, `inspect_twin`,
  `search_city_services(q=狮子林)`
- no replan, select, booking, payment, or other mutation

DeepSeek independently confirmed that opening truth can be retained for the exact node while
cost truth stays UNKNOWN and the node remains outside selectable planning.

Hermes remains honestly unavailable (`configured=false`, `reachable=false`, `ready=false`).

## Result and next experiment

The exact node has gained a legitimate provider-backed opening observation, but not a cost
fact. The authority gate correctly remains closed. No repair is justified by this evidence.

Next autonomous experiment: leave the node in the catalog as a visible, non-selectable row and
trace the user-facing API projection to ensure `NORMALIZED_VALID` opening plus `UNKNOWN` cost is
shown consistently without rendering the compatibility zero as free.

