# CityNexus Revolution Lab R8 — winter seasonal facts to authority

## Result

R8 used a backup of the R7 disposable database, changed only that backup's
journey window to winter, and ran the same real product path for the exact
`网师园` OSM node:

```text
winter journey copy
→ real Overpass + Nominatim + Lotsmall acquisition
→ canonical seasonal opening = 07:30–17:00
→ real planner candidate
→ real select endpoint
→ READY Twin with live mobility and hard eligibility
```

The original R7 journey was not changed by this experiment. The selected
winter result below is authoritative only inside the disposable database copy.

## Execution binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- starting commit: `a137f785ff66e7be1acfbcd0af7ea83022bbd25c`
- product-call executed commit: `a137f785ff66e7be1acfbcd0af7ea83022bbd25c`
- final experimental/report commit: recorded after this report is committed
- product-call worktree status: `CLEAN` before every call
- original database: unchanged R7 database
- winter database copy: `C:\Users\仓鼠王\AppData\Local\Temp\citynexus-r77-winter-probe-20260930.sqlite3`
- P7: `false`
- no mainline merge, no real payment, no commerce mutation

The exact before/after bindings are in `execution-binding-before.json` and
`execution-binding-after.json`. The source commit is recorded in every product
call envelope.

## Exact scenario

- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2` in the copy
- city: `CN-SUZHOU`
- winter window: `2026-11-04 09:00–19:00 Asia/Shanghai`
- exact Place: `real-place-bcd9c9f324751168d422a06b`
- provider identity: `overpass:node/5042033121`
- display name: `网师园`
- coordinates: `31.3003833, 120.6298435`
- Nominatim: `ACQUIRED`, `matched_provider_entity=true`

The nearby `overpass:way/44679452` was not substituted.

## Real provider acquisition

The exact product endpoint was called against the copy:

```text
POST /api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/facts/acquire
payload = {"place_ids":["real-place-bcd9c9f324751168d422a06b"]}
HTTP = 200
receipt.status = ACQUIRED
retrieved_at = 2026-09-30T14:12:33.754146+08:00
```

Machine receipt:

```text
Overpass = HTTP 200, one exact element
Nominatim = ACQUIRED, element_count = 1
official_web = ACQUIRED
known_opening_count = 1
known_cost_count = 1
```

The exact Lotsmall identity remained bound to the node. The ticket-grid source
returned an active provider ticket at `4000` minor CNY for this replay date;
the system did not infer free from zero or from missing data.

## Seasonal fact at the canonical and candidate boundaries

The provider-mesh readback after acquisition returned:

```text
facts_source = CANONICAL_PLACE
facts_updated_at = 2026-09-30T14:12:33.754146+08:00
opening_hours.status = OFFICIAL_WEB_VERIFIED
opening_hours.open = 07:30
opening_hours.close = 17:00
seasonal_periods = [07:30–17:30, 07:30–17:00]
cost_evidence.status = VERIFIED_PROVIDER
cost_evidence.amount_minor = 4000
```

The `facts_updated_at` equals the acquisition receipt timestamp. The whole raw
notice is retained and the selected interval is the winter one.

## Real planning, selection, and authority

The explicit five-place planner call was made on the disposable copy only:

```text
POST /api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/plans/generate
payload.place_ids = [five real Place IDs including the exact node]
HTTP = 201
plan_id = 893598ec-fa26-5b79-ac79-2e8371236f37
version_no = 17
status = CANDIDATE
selectable = true
is_current = false
```

The exact node's actual generated activity was:

```text
start_at = 2026-11-04T13:45:00+08:00
end_at = 2026-11-04T14:45:00+08:00
opening_hours.status = OFFICIAL_WEB_VERIFIED
opening_hours.close = 17:00
cost_status = KNOWN_PAID
estimated_cost.amount_minor = 4000
```

This proves the seasonal fact crossed the product planner boundary. It was not
just a provider receipt or a direct schema projection.

The real selection endpoint then ran against the copy:

```text
POST /api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/plans/893598ec-fa26-5b79-ac79-2e8371236f37/select
HTTP = 200
Journey.status = PLANNED
Journey.active_plan_version_id = 893598ec-fa26-5b79-ac79-2e8371236f37
Twin.projection_status = READY
```

This is an authoritative selection in the disposable winter envelope, not a
claim that the original October journey was replaced.

### Actual used edges and hard eligibility

Read from the post-selection Twin; no edge or receipt was synthesized:

```text
used_edge_ids = [
  ["real-place-ba7377353c422c39dfd752b7", "real-place-054fa857eff7a99169399bdf"],
  ["real-place-054fa857eff7a99169399bdf", "real-place-06361e97cfc5a371f68f7875"],
  ["real-place-06361e97cfc5a371f68f7875", "real-place-8bc850f117297987997c87cf"],
  ["real-place-8bc850f117297987997c87cf", "real-place-bcd9c9f324751168d422a06b"]
]
```

All four actual receipts were `HARD_ELIGIBLE` with provider
`valhalla-http`, `route_provenance=LIVE_PROVIDER_CAPTURE`, and
`all_actual_edges_hard_eligible=true`. The winter snapshot is
`10348726-354e-4102-bd3a-ce380858ecea` with 20 facts and `degraded=false`.

The last edge was reported as 0 minutes by Valhalla and remains recorded as a
live provider fact. R8 does not convert that observation into a synthetic or
mock route, and does not hide it.

## Original journey isolation

The original R7 database was not used for the winter mutation. The copy's
pre-selection readback still showed the original active plan ID
`d80bb9c1-4b68-5b1a-ad76-602b237cba22`; only after the explicit select on the
copy did the copy's active pointer become `893598ec-fa26-5b79-ac79-2e8371236f37`.

The original live UI evidence remains the R7 five-stop October journey. R8 does
not claim a UI screenshot for the isolated winter copy.

## DeepSeek / Hermes disclosure

R8 used the deterministic provider/planner path. No new DeepSeek Builder or
Hermes Critic action is claimed. The R7 runtime evidence remains honest:
DeepSeek configured but unverified; Hermes native gateway unavailable. No agent
prose is used as authority.

## Focused gates

The R7 focused regression file was rerun on this unchanged source commit:

```text
backend/tests/test_revolution_r77_recovery.py
22 passed, 1 warning
```

The warning is the existing Starlette/httpx deprecation warning.

## Evidence and replay

The R8 archive contains the raw and structured envelopes for journey date,
exact-node acquisition, provider mesh, planner candidate, selection, final
journey, and final Twin, plus the clean-source bindings, R7 UI evidence, R7
baseline, source lineage, and focused test output. No raw credential is
included.

Replay requires the disposable copy and source commit above. Run the backend on
port 8013 with that copy, then repeat the exact POST/GET sequence recorded in
the `winter-*.json` envelopes. Do not point the winter mutation at the original
database.

## Next autonomous experiment

Investigate the real Valhalla 0-minute edge between the two nearby garden
entities using the persisted coordinates and provider response, without
replacing it with a synthetic edge. If it is a genuine co-located transition,
make that provenance explicit; if it is a route-provider anomaly, preserve the
hard gate and produce an exact evidence-backed blocker or bounded repair.
