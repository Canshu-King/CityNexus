# CityNexus Revolution Lab R7 — canonical fact projection and freshness

## Result

R7 completed on the same real Suzhou journey and exact OSM entity. A fresh
provider run updated the exact node's canonical facts and its freshness
timestamp; the existing selected product plan remained authoritative.

This round did not claim a new plan-generation success. It read back the
existing selected plan after acquisition.

## Execution binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- starting commit: `c8a59ffc077c55daffd5ee781d795226360da39d`
- source repair commit: `f0919caf4ef6da2ebf3227c1e6127cb8a5a2bced`
- freshness repair commit: `9b3acb13b8055fef4d979a58ad8debf4021afb44`
- product-call executed commit: `9b3acb13b8055fef4d979a58ad8debf4021afb44`
- product-call worktree status: `CLEAN`
- final experimental commit: recorded after this report is committed
- disposable database: `C:\Users\仓鼠王\AppData\Local\Temp\citynexus-r77-authority-gate-r4-20260930.sqlite3`
- P7: `false`
- no authority/mainline merge, no real payment, no persistent secret

The machine bindings are in `execution-binding-r7-timestamp-before.json` and
`execution-binding-r7-timestamp-after.json`. Every real product call checked
the clean worktree immediately before the request.

## Exact scenario

- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- city: `CN-SUZHOU`
- window: `2026-10-04 09:00–19:00 Asia/Shanghai`
- exact Place: `real-place-bcd9c9f324751168d422a06b`
- display name: `网师园`
- provider identity: `overpass:node/5042033121`
- coordinates: `31.3003833, 120.6298435`
- Nominatim: `ACQUIRED`, `matched_provider_entity=true`
- provider website tag: `http://jump.szjlxx.cn/?park=wsy`

The nearby `overpass:way/44679452` remains a different entity. Its facts were
not copied to this node.

## Bounded repairs

### Canonical facts cross the provider-mesh boundary

The R6 provider-mesh response exposed this exact node's historical discovery
capture as `opening_hours.status=UNKNOWN` and
`cost_evidence.status=UNKNOWN`, with no facts source or timestamp.

R7 now resolves a materialized candidate to its current canonical `Place` row.
It returns `facts_source=CANONICAL_PLACE`, canonical opening/cost evidence, and
a freshness timestamp. A candidate without a materialized canonical Place
remains explicitly `CAPTURED_CANDIDATE`; no stale capture is promoted.

### Lotsmall seasonal notice is date-aware

The exact public BFF notice is retained as two provider-backed intervals:

```text
2026-10-04: 07:30–17:30
2026-11-04: 07:30–17:00
```

This parser runs only after the exact Lotsmall product identity is bound to the
exact OSM/Nominatim entity. Unknown text is not converted to free or all-day.

### Fact freshness follows the provider observation

The acquisition path now sets `Place.updated_at` to the same observation
timestamp used by the acquisition receipt. Fresh content is therefore not
reported with the older row timestamp.

## Real provider evidence

```text
POST /api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/facts/acquire
payload = {"place_ids":["real-place-bcd9c9f324751168d422a06b"]}
HTTP = 200
receipt.status = ACQUIRED
Overpass = HTTP 200, one exact element
Nominatim = ACQUIRED, element_count = 1
matched_provider_entity = true
official_web = ACQUIRED
known_opening_count = 1
known_cost_count = 1
```

The resulting canonical facts are:

```text
opening_hours.status = OFFICIAL_WEB_VERIFIED
opening_hours.open = 07:30
opening_hours.close = 17:30
opening_hours.seasonal_periods = 2
cost_evidence.status = VERIFIED_PROVIDER
cost_evidence.amount_minor = 4000
cost_evidence.currency = CNY
```

The exact public BFF identity is retained in the raw receipt:

```text
merchantParkInfoId = 8187
merchantInfoId = 1939
productCode = park2021051111555676069
provider_ticket_id = 52526
provider_model_code = MP2021060917054740913
```

## Before / after machine evidence

The pre-R7 baseline is the captured R6 provider-mesh response, included as
`r6-provider-mesh-before-r7.json`. The clean R7 source first projected the
existing canonical row, then the exact-node acquisition refreshed it.

```text
R6 baseline:
  opening_hours.status = UNKNOWN
  cost_evidence.status = UNKNOWN

R7 after fresh acquisition:
  facts_source = CANONICAL_PLACE
  facts_updated_at = 2026-09-30T13:49:59.730551+08:00
  opening_hours.status = OFFICIAL_WEB_VERIFIED
  seasonal_periods = [07:30–17:30, 07:30–17:00]
  cost_evidence.status = VERIFIED_PROVIDER
  cost_evidence.amount_minor = 4000
```

The fresh receipt has the identical timestamp:

```text
retrieved_at = 2026-09-30T13:49:59.730551+08:00
facts_updated_at = 2026-09-30T13:49:59.730551+08:00
```

## Existing real plan and authority readback

```text
plan_id = d80bb9c1-4b68-5b1a-ad76-602b237cba22
plan.status = SELECTED
plan.selectable = true
plan.is_current = true
journey.status = PLANNED
journey.active_plan_version_id = d80bb9c1-4b68-5b1a-ad76-602b237cba22
twin.projection_status = READY
```

The existing plan contains five real Place activities and the exact node as the
fifth stop at `15:14–16:14`. It was not synthesized or reselected in R7.

### Actual mobility truth

Read from the real final Twin; no edge IDs or receipts were invented:

```text
used_edge_ids = [
  ["real-place-06361e97cfc5a371f68f7875", "real-place-054fa857eff7a99169399bdf"],
  ["real-place-054fa857eff7a99169399bdf", "real-place-8bc850f117297987997c87cf"],
  ["real-place-8bc850f117297987997c87cf", "real-place-ba7377353c422c39dfd752b7"],
  ["real-place-ba7377353c422c39dfd752b7", "real-place-bcd9c9f324751168d422a06b"]
]
```

All four actual receipts are `HARD_ELIGIBLE`, with
`route_provenance=LIVE_PROVIDER_CAPTURE`, provider `valhalla-http`, and
`all_actual_edges_hard_eligible=true`. The mobility snapshot remains
`f5ec6205-aa14-4f80-b750-85b281dd00fe` with 132 facts.

## User-visible evidence

The live UI was reloaded at `http://127.0.0.1:4175/v8/hub`. The fresh DOM
snapshot contains:

```text
已选行程
09:00 Old Town · 10:13 狮子林 · 11:51 网师园 · 13:33 拙政园 · 15:14 网师园
4 段路程
供应商支持的路线 · WGS84
```

The exact node is not in the pending list; unrelated places still show
`营业时间未知` and `费用：暂无价格（未知）`. The browser reported zero
console errors and all observed API requests returned HTTP 200. Viewport and
full-page screenshots are included.

## DeepSeek / Hermes disclosure

The current runtime status was read on the clean R7 source:

```text
runtime_identity = NATIVE_DEEPSEEK_TOOL_LOOP
native_binary_detected = true
deepseek_configured = true
ai_state = CONFIGURED_UNVERIFIED
native_mcp_proven = false
hermes_compat_configured = false
hermes_native_gateway.ready = false
```

The R7 bounded repairs were deterministic code changes; no new DeepSeek
Builder action or Hermes critique is claimed for this round. The previous R6
package contains the actual DeepSeek identity research result (`NO_RESULTS`,
`NON_AUTHORITATIVE`) and honest Hermes unavailable status. This report does not
turn runtime configuration into fabricated agent execution.

## Focused gates

```text
backend/tests/test_revolution_r77_recovery.py
22 passed, 1 warning
```

The warning is the existing Starlette/httpx deprecation warning. Frontend
typecheck and production build passed before the R7 source commits; the
unchanged build-size warning is non-blocking.

## Product defects exposed and repaired

1. Provider mesh could show a stale discovery capture even after canonical
   facts were acquired. The projection now distinguishes canonical facts from
   captured candidate facts.
2. Seasonal provider notices were reduced to a single generic closing time.
   The exact Lotsmall notice is now retained as date-bound intervals.
3. Fact content was refreshed without refreshing `Place.updated_at`; the
   acquisition timestamp now updates the canonical row timestamp.

## Evidence files and replay

The R7 package includes raw and structured evidence for provider-mesh before and
after, exact-node acquisition, places readback, plan, Twin, journey, runtime
status, clean-source bindings, browser screenshot/DOM/console/request records,
focused tests, the R6 baseline, and exact BFF responses. No raw credential is
included.

Replay on the disposable database:

```powershell
cd D:\moodle\CityNexus-Revolution-RealTrip-Recovery\backend
$env:CITYNEXUS_DATABASE_URL='sqlite:///C:/Users/仓鼠王/AppData/Local/Temp/citynexus-r77-authority-gate-r4-20260930.sqlite3'
uv run uvicorn app.main:app --host 127.0.0.1 --port 8012

POST http://127.0.0.1:8012/api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/facts/acquire
{"place_ids":["real-place-bcd9c9f324751168d422a06b"]}

GET http://127.0.0.1:8012/api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/provider-mesh
GET http://127.0.0.1:8012/api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/twin
```

The exact source binding must be
`9b3acb13b8055fef4d979a58ad8debf4021afb44` before product calls. Do not use
the mainline or Harness tree.

## Next autonomous experiment

Use a disposable copy of this same journey with a winter start date to verify
that the selected seasonal interval (`17:00` close) is carried through the
planner's candidate facts without changing the current selected journey. If it
passes, extend the same date-aware fact projection to the remaining
provider-bound garden rows; keep unrelated UNKNOWN rows UNKNOWN.


