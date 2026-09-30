# CityNexus Revolution Lab — R6 service-identity result

## Scope and binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- starting and final product source: `fc401ee004c1aeb02813900aa9e22409041824a6`
- this diagnostic round made no source change
- disposable database only; no authority/mainline merge; `P7=false`

This round followed the provider-identity repair and checked whether the service layer could
point at a different same-name provider entity than the planner. The target remained the same
real Suzhou Journey `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`.

## Catalog and service mapping

The catalog contains 47 `CityService` rows. Duplicate display names include `狮子林` and
`网师园`. For `狮子林`, the service mapping is explicit and does not collapse the entities:

| CityService | place_id | provider identity | facts |
|---|---|---|---|
| `service-054fa857eff7a99169399bdf` | `real-place-054fa857eff7a99169399bdf` | `overpass:way/44679451` | official opening, `VERIFIED_PROVIDER` cost |
| `service-3295a86383d1f7216648cb00` | `real-place-3295a86383d1f7216648cb00` | `overpass:node/4246892594` | normalized opening, cost `UNKNOWN` |

The first-class identity fields added in the preceding round were present in the real agent
search response. Both services and both Places were returned, with their own `place_id` and
`external_id`.

## Real product boundary test

The explicit product request used exactly the two `狮子林` Place IDs and returned:

```text
HTTP 422
reason_code = PLACE_COST_UNVERIFIED
message = GENERIC_COMPOSE_INFEASIBLE:GENERIC_COMPOSE_UNKNOWN_COST:real-place-3295a86383d1f7216648cb00
```

The unknown-cost node did not become a selectable activity. No plan selection or authority
mutation was performed. The current plan remained:

```text
Journey.status = PLANNED
Journey.active_plan_version_id = 09715a08-4e06-57b7-bebc-b9a5adf872a2
Twin.active_plan_version_id = 09715a08-4e06-57b7-bebc-b9a5adf872a2
Twin.projection_status = READY
```

The selected plan's next activity is the verified `real-place-054fa857eff7a99169399bdf`,
not the node.

## DeepSeek operator evidence

The first unrestricted read-only attempt was real but did not reach a valid terminal inspection:

- run: `48aebb23-c1fb-4190-aa39-5b6a5d66ff8d`
- status: `COMPLETED` with the runtime's repetition-stop outcome
- first four tools completed, then repeated `inspect_journey`/`inspect_twin` calls were stopped as
  `STOP_REPETITION`
- it is retained as a runtime behavior observation, not claimed as a clean PASS

A narrower retry was then executed:

- run: `8d85ef5c-b154-46d1-b2df-67493d53ffb0`
- runtime: `NATIVE_DEEPSEEK_TOOL_LOOP`
- status: `COMPLETED`
- exactly 3 calls, once each: `inspect_journey`, `inspect_twin`, `search_city_services(q=狮子林)`
- no replan, select, booking, payment, or mutation

DeepSeek confirmed the exact way carries official opening/cost truth and the node's zero storage
value is not free; it also confirmed the current plan stayed unchanged.

Hermes remains honestly unavailable (`configured=false`, `reachable=false`, `ready=false`).

## Focused tests

```text
56 passed, 1 warning
```

The warning is the existing Starlette/httpx deprecation warning. The test output is included in
the round package.

## Result and next experiment

The service-to-place mapping is explicit, identity-preserving, and fail-closed at the cost
authority gate. No new product defect was exposed in this boundary, so no speculative alias or
deduplication repair was made.

Next autonomous experiment: use the same two-node pattern to inspect whether any provider-backed
opening/cost acquisition can legitimately enrich the exact `overpass:node/4246892594` entity
without borrowing facts from `way/44679451`; otherwise keep it UNKNOWN and leave the authority
gate closed.

