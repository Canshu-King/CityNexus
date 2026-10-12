# CityNexus Revolution Lab — R6 provider-identity result

## Scope and binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- round starting source: `f992bb84d0d90f4154fbc20c6e4490d06358a831`
- final product source commit: `e84ba03da808072e1496c7a07c7abc6b77c92b8d`
- final report/package commit: recorded in the package's `sources/report-commit.txt`
- disposable database: `C:\Users\仓鼠王\AppData\Local\Temp\citynexus-r77-authority-gate-r4-20260930.sqlite3`
- no authority/mainline merge; `P7=false`

This round followed the cursor repair and investigated whether duplicate provider entities
could cross the real planner boundary. It also made provider identity visible as a first-class
field on the agent search surface. No alias, fuzzy match, merge, or canonical-data injection
was added.

## Same-destination evidence

Journey `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2` (`CN-SUZHOU`, 2026-10-04 09:00–19:00 Asia/Shanghai)
was retained. The catalog contains two distinct rows with the display name `网师园`:

| Place | Provider identity | Fact state |
|---|---|---|
| `real-place-8bc850f117297987997c87cf` | `overpass:way/44679452` | official municipal page id=45, `OFFICIAL_WEB_VERIFIED`, `VERIFIED_PROVIDER`, `OPERATOR_VERIFIED` |
| `real-place-bcd9c9f324751168d422a06b` | `overpass:node/5042033121` | opening `UNKNOWN`, cost `UNKNOWN`, no official binding; stored `cost_minor=0` remains a placeholder |

Before the repair, the real `search_city_services` response returned both rows but did not
expose `provider_key`/`external_id` at the top level. The response still contained the rows'
metadata, but that forced an agent or consumer to infer identity from nested fields.

## Bounded repair

The agent search result now includes:

```json
{"provider_key":"overpass","external_id":"overpass:way/44679452"}
```

for every returned Place. This is an identity projection only. It does not choose a row,
promote facts, or grant plan authority. The focused regression asserts that the exact provider
identity survives the search contract.

## Candidate-source diagnosis

1. Explicit product generation with the verified way and the unverified node returned HTTP 422:

```text
reason_code = PLACE_COST_UNVERIFIED
message = GENERIC_COMPOSE_INFEASIBLE:GENERIC_COMPOSE_UNKNOWN_COST:real-place-bcd9c9f324751168d422a06b
```

No selectable plan was created from the mixed identity input.

2. Automatic generation on the same catalog returned HTTP 201 with plan
`969333d0-293b-55cf-a83b-0d9f0f78b757`. Its four activities included the verified
`real-place-8bc850f117297987997c87cf` and did not include
`real-place-bcd9c9f324751168d422a06b`. The strict catalogue source therefore excludes the
unknown-cost node; it does not silently choose the first same-name row.

3. Re-selecting the existing real plan through the product returned HTTP 200. The readback
remained:

```text
active_plan_version_id = 09715a08-4e06-57b7-bebc-b9a5adf872a2
Journey.status = PLANNED
Twin.projection_status = READY
```

The selected plan still uses the verified OSM way, not the node.

## DeepSeek execution

The actual runtime was enabled in the disposable server process and completed a read-only
PLAN_ONLY loop:

- run: `9c436aa4-0f02-4932-a0f8-377a889d2f12`
- mission: `95766813-8709-4877-b8d5-a000882506bd`
- runtime: `NATIVE_DEEPSEEK_TOOL_LOOP`
- provider/model: `deepseek` / `deepseek-v4-flash`
- tool calls: 4 (`inspect_journey`, `inspect_twin`, `search_city_services`, `list_replans`)
- status: `COMPLETED`
- no replan, select, booking, payment, or evidence fabrication

DeepSeek independently compared both provider identities, identified the official facts as
bound only to `overpass:way/44679452`, and confirmed the selected plan was unchanged.

Hermes remains honestly unavailable: `configured=false`, `reachable=false`, `ready=false`.
No Hermes execution is claimed.

## Focused tests

```text
56 passed, 1 warning
```

Suites included the R77 recovery tests, agent runtime gate, current-plan projection,
mobility-evidence sources, catalog reason code, and agent alternatives. The warning is the
existing Starlette/httpx deprecation warning.

## Result and next experiment

The duplicate identity boundary is now machine-visible and fail-closed. The real planner did
not turn the unknown node into a selectable activity. The only product change in this round is
the first-class provider identity projection in the agent search response.

Next autonomous experiment: inspect the second observed duplicate service mapping (`狮子林`)
and compare its `CityService.place_id` bindings with the exact OSM Place identities, ensuring
service search and planner input cannot diverge even when both rows share a display label.

