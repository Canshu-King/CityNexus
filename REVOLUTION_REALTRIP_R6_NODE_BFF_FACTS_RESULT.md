# CityNexus Revolution Lab R6 — exact node BFF facts to selected plan

## Execution binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- starting commit: `07d5d550305e26d6681eed3664cd1269e48dcbbd`
- final experimental commit: `db9178a954766bab5cbf0f9aadfc512d862c196d`
- final `git status --porcelain`: empty after the source/test commit and before
  the product provider call
- disposable database:
  `C:\Users\仓鼠王\AppData\Local\Temp\citynexus-r77-authority-gate-r4-20260930.sqlite3`
- P7: false
- no authority/mainline merge, no real payment, no commerce mutation

The provider call, fact acquisition call, plan generation call, and plan
selection call were executed against the final clean source commit. Evidence
files record the HTTP responses; no raw credential is included.

## Exact scenario

- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- city: `CN-SUZHOU`
- window: `2026-10-04 09:00–19:00 Asia/Shanghai`
- exact Place: `real-place-bcd9c9f324751168d422a06b`
- display name: `网师园`
- exact provider identity: `overpass:node/5042033121`
- coordinates: `31.3003833, 120.6298435`
- exact Nominatim result: `ACQUIRED`, `matched_provider_entity=true`
- exact Nominatim/OSM website extratag:
  `http://jump.szjlxx.cn/?park=wsy`

The nearby same-name entity `overpass:way/44679452` remains a separate Place.
Its municipal-page facts were not copied to the node and did not establish the
node's identity or cost.

## Bounded experimental repair

The previous pipeline stopped at a login-shell HTML page and classified the
exact node as UNKNOWN even though the public ticket application exposed
structured facts through its BFF APIs. The experimental change in
`backend/app/fact_acquisition.py`:

1. accepts only the exact final host/path
   `wap.lotsmall.cn/vue/detail/ticket`;
2. parses the exact `id`, `productCode`, and `m_id` from the bound URL;
3. requires an exact provider identity binding with
   `matched_provider_entity=true`;
4. calls the public detail BFF and requires all three identifiers to echo
   exactly;
5. calls the date-bound ticket-grid BFF and accepts only an active, allowed,
   exact-merchant adult ticket with a numeric price;
6. retains the raw source URLs and provider product/ticket/model IDs in the
   fact receipt; and
7. leaves the result UNKNOWN if any identity or ticket check fails.

No canonical demo seed, same-name first-result rule, fuzzy identity, or mock
fact was introduced. Regression tests cover both the exact success path and an
identity mismatch fail-closed path.

## Provider evidence

The exact URL was followed in a real browser first. Its rendered page was a
login shell (`用户登录`), but the browser trace exposed these public APIs.

### Detail BFF

- HTTP: `200`
- endpoint:
  `https://wap.lotsmall.cn/bff/merchant/api/merchantParkInfo/merchantParkInfo?merchantParkInfoId=8187&wayType=1&merchantInfoId=1939`
- echoed `id`: `8187`
- echoed `productCode`: `park2021051111555676069`
- echoed `merchantInfoId`: `1939`
- opening: `07:30–17:30`
- raw order notice retained, including the seasonal November–February
  closing-time rule

### Ticket-grid BFF

- HTTP: `200`
- reference date: `2026-10-04`
- endpoint:
  `https://wap.lotsmall.cn/bff/merchant/api/merchantParkTicketGridNew?currPage=1&pageSize=50&playDate=2026-10-04&businessType=park&merchantParkInfoId=8187&merchantInfoId=1939`
- accepted exact adult ticket: `网师园旺季成人票`
- `parkTicketId`: `52526`
- `modelCode`: `MP2021060917054740913`
- price: `40 CNY` = `4000` minor units
- `saleStatus`: `T`
- `buyDateAllow`: `true`

The product fact receipt therefore contains:

```text
opening_hours.status = OFFICIAL_WEB_VERIFIED
opening_hours.open = 07:30
opening_hours.close = 17:30
cost_evidence.status = VERIFIED_PROVIDER
cost_evidence.amount_minor = 4000
cost_evidence.currency = CNY
provider_identity.merchant_park_info_id = 8187
provider_identity.merchant_info_id = 1939
provider_identity.product_code = park2021051111555676069
```

The persisted SQLite row also retains the exact source binding:

```text
provider_entity = overpass:node/5042033121
source_class = OFFICIAL_TICKETING
approval = PROVIDER_TAG_EXACT_URL
matched_provider_entity = true
secondary_provider = nominatim
```

## Before / after product behavior

Before this commit and BFF adapter:

```text
Nominatim identity              = ACQUIRED / exact match
official_web                   = NO_STRUCTURED_FACTS
opening_hours.status           = UNKNOWN
cost_evidence.status           = UNKNOWN
known_opening_count            = 0
known_cost_count               = 0
```

After the same exact Place was sent through the real endpoint:

```text
POST /api/v1/journeys/{journey_id}/facts/acquire  = HTTP 200
official_web                                    = ACQUIRED
opening_hours.status                            = OFFICIAL_WEB_VERIFIED
cost_evidence.status                            = VERIFIED_PROVIDER
known_opening_count                             = 1
known_cost_count                                = 1
```

The public `/api/v1/places?city_code=CN-SUZHOU&q=网师园` readback returned the
same exact node with the verified opening and provider cost. No compatibility
zero was interpreted as free.

## Real product planning and selection

The same Journey was then passed through the real planner:

```text
POST /api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/plans/generate
HTTP = 201
plan_id = d80bb9c1-4b68-5b1a-ad76-602b237cba22
version_no = 14
status = CANDIDATE
selectable = true
```

The emitted candidate has five real Place activities, with the exact node as
the fifth stop at `15:14–16:14`:

```text
1 Old Town       real-place-06361e97cfc5a371f68f7875
2 狮子林          real-place-054fa857eff7a99169399bdf
3 网师园          real-place-8bc850f117297987997c87cf
4 拙政园          real-place-ba7377353c422c39dfd752b7
5 网师园          real-place-bcd9c9f324751168d422a06b
```

The plan was not treated as success from the candidate response alone. The
real product selection endpoint was called:

```text
POST /api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/plans/d80bb9c1-4b68-5b1a-ad76-602b237cba22/select
HTTP = 200
Journey.status = PLANNED
Journey.active_plan_version_id = d80bb9c1-4b68-5b1a-ad76-602b237cba22
```

The final plan readback returned `status=SELECTED`, `selectable=true`, and
`is_current=true`. The final Journey Twin returned `projection_status=READY`.

### Actual used edges and eligibility receipts

These are read from the final selected plan's persisted mobility evidence; no
edge ID or receipt was synthesized:

```text
used_edge_ids = [
  ["real-place-06361e97cfc5a371f68f7875", "real-place-054fa857eff7a99169399bdf"],
  ["real-place-054fa857eff7a99169399bdf", "real-place-8bc850f117297987997c87cf"],
  ["real-place-8bc850f117297987997c87cf", "real-place-ba7377353c422c39dfd752b7"],
  ["real-place-ba7377353c422c39dfd752b7", "real-place-bcd9c9f324751168d422a06b"]
]
```

| Actual edge | persisted min | hard min | provider | quality | decision |
| --- | ---: | ---: | --- | --- | --- |
| Old Town → 狮子林 | 13 | 13 | `valhalla-http` | `LIVE_PROVIDER_CAPTURE` | `HARD_ELIGIBLE` |
| 狮子林 → 网师园 (way) | 38 | 38 | `valhalla-http` | `LIVE_PROVIDER_CAPTURE` | `HARD_ELIGIBLE` |
| 网师园 (way) → 拙政园 | 42 | 42 | `valhalla-http` | `LIVE_PROVIDER_CAPTURE` | `HARD_ELIGIBLE` |
| 拙政园 → 网师园 (node) | 41 | 41 | `valhalla-http` | `LIVE_PROVIDER_CAPTURE` | `HARD_ELIGIBLE` |

The final mobility snapshot was
`f5ec6205-aa14-4f80-b750-85b281dd00fe`, with 132 captured facts,
`route_provenance=LIVE_PROVIDER_CAPTURE`, and
`all_actual_edges_hard_eligible=true`.

## User-visible evidence

The live frontend was reloaded after selection at:

```text
http://127.0.0.1:4175/v8/hub
```

The refreshed page visibly showed five numbered stops, four provider-backed
route segments, and the second `网师园` stop at `15:14`. The exact node no
longer appeared in the pending list; unrelated places with UNKNOWN facts
remained visible as pending. The browser screenshot, fresh DOM snapshot, and
console/request records are included in the review package.

## DeepSeek / Hermes disclosure

The supported native DeepSeek web-research route was actually invoked for the
exact node, with an exact-identity query. Its machine result was:

```text
status = NO_RESULTS
authority = NON_AUTHORITATIVE
observations = []
```

Runtime status was `NATIVE_DEEPSEEK_TOOL_LOOP`,
`deepseek_configured=true`, `ai_state=CONFIGURED_UNVERIFIED`, and
`native_mcp_proven=false`. DeepSeek did not provide the BFF facts and did not
receive credit for the repair. The bounded code change and all product calls
were executed in this lab worktree.

Hermes was not fabricated: the recorded capability result is
`configured=false`, `reachable=false`, `ready=false`. No Hermes trace is
claimed for this round.

## Focused tests

```text
21 passed, 1 warning in 6.07s
```

The warning is the existing Starlette/httpx deprecation warning. The new tests
cover exact BFF promotion and exact product identity mismatch fail-closed
behavior. Output: `citynexus-r77-r6-node-bff-focused-tests-20260930.txt`.

## Product defects exposed

1. The exact provider page is a login shell while its public BFF APIs carry the
   usable structured facts. The old HTML-only acquisition path therefore
   under-reported a real provider-backed destination.
2. The historical provider-mesh capture still exposes the exact node as an
   older `UNKNOWN` discovery observation even after the canonical Place and
   selected plan are verified. That capture is not used as authority, but its
   stale wording is a projection clarity defect for the next round.
3. The detail BFF's generic `openTime/endTime` is currently paired with a raw
   seasonal notice. The selected date is inside the verified October window;
   date-specific interval projection should be made explicit before using the
   adapter for dates outside that window.

## Result

This round reached the legitimate success path for the exact provider entity:

```text
exact provider identity
→ source-bound public BFF facts
→ canonical Place facts
→ real planner candidate
→ actual LIVE mobility edges
→ all actual edges hard-eligible
→ real /select HTTP 200
→ selected current plan
→ user-visible five-stop journey
```

The result is a real selected product plan, not provider-only success, not a
mock plan, and not a report-only PASS.

## Next autonomous experiment

Refresh the provider-mesh/public pending projection from the canonical Place
facts for this exact entity, then make the BFF opening interval date-aware and
rerun the same Journey for an out-of-season date. Keep exact entity binding,
UNKNOWN semantics, and the no-fuzzy/no-first-result rule unchanged.
