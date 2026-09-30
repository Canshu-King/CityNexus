# Revolution Lab R6 — 网师园第二源事实采集

## Execution binding

- Branch: `codex/revolution-realtrip-recovery`
- Isolated worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Starting source commit: `c10d84c9abaa822b6d6f2cd2adcb4c533be8cc1d`
- Final experimental source commit: `c10d84c9abaa822b6d6f2cd2adcb4c533be8cc1d`
- This round changed no product source; the previous public-fact projection
  repair remains the exact experimental source.
- Mainline/authority merge: none
- `git status --porcelain` was empty before the provider call.

## Same destination and exact target

- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- City: `CN-SUZHOU`
- Product call: `POST /api/v1/journeys/{journey_id}/facts/acquire`
- Request: `{"place_ids":["real-place-bcd9c9f324751168d422a06b"]}`
- Exact provider entity: `overpass:node/5042033121`
- Display label: `网师园`

## Machine evidence

The product returned HTTP 200 and recorded a matching Nominatim entity:

```text
secondary_source.provider       = nominatim
secondary_source.status         = ACQUIRED
matched_provider_entity         = true
element_count                   = 1
```

Nominatim extratags contained only:

```text
website = http://jump.szjlxx.cn/?park=wsy
```

The bounded official-page attempt resolved to
`https://wap.lotsmall.cn/vue/detail/ticket?id=8187&productCode=park2021051111555676069&m_id=1939`
but returned `NO_STRUCTURED_FACTS`. The product therefore recorded:

```text
opening_hours.status            = UNKNOWN
cost_evidence.status            = UNKNOWN
cost_evidence.amount_minor      = null
cost_evidence.currency          = CNY
known_opening_count             = 0
known_cost_count                = 0
search_source.status            = UNCONFIGURED
```

The page itself was then captured for a parser-boundary check. It returned
HTTP 200 but was a 16,644-byte Vue application shell with an empty `<title>`,
no `application/ld+json`, and zero occurrences of the fact labels
`门票`, `票价`, `价格`, `开放`, `营业`, `opening`, `ticket`, or `price` in the
returned HTML. There was therefore no structured or visible fact to promote;
the raw page is included in the evidence package.

This is a real second-source match without a promotable opening or price fact.
No website text was relabeled as structured evidence, and the compatibility
`cost_minor=0` value was not treated as free.

## Product state after acquisition

The same public catalogue response exposes the updated row as:

```text
real-place-bcd9c9f324751168d422a06b
external_id       = overpass:node/5042033121
opening_status    = UNKNOWN
cost_status       = UNKNOWN
cost_amount_minor = null
```

The selected journey was untouched:

```text
active_plan_version_id = 09715a08-4e06-57b7-bebc-b9a5adf872a2
selected plan version  = 11
selected plan status   = SELECTED
Twin projection        = READY
```

Actual mobility evidence still contains exactly these three edges:

```text
real-place-06361e97cfc5a371f68f7875 -> real-place-054fa857eff7a99169399bdf  WALK 13
real-place-054fa857eff7a99169399bdf -> real-place-8bc850f117297987997c87cf  WALK 38
real-place-8bc850f117297987997c87cf -> real-place-ba7377353c422c39dfd752b7  WALK 42
```

All actual edges remain `LIVE_PROVIDER_CAPTURE`, non-degraded, and
`HARD_ELIGIBLE`. The newly inspected node was not synthesized into a route,
used-edge list, eligibility receipt, or selectable result.

## Agent and safety status

- DeepSeek evidence used from the preceding exact-node run:
  `cdc9b1e5-9afa-40b8-aff6-b726e61189c1`, three read-only calls. It is retained
  as machine evidence, not used to award a planner PASS.
- No new DeepSeek mutation or fact claim was made in this deterministic
  acquisition round.
- Hermes remains not configured/reachable; no Hermes execution is claimed.
- P7 remains `false`; no mainline merge; `MOCK != LIVE`.

## Focused gates

- Backend Revolution/agent/mobility/catalog suite: **52 passed, 1 warning**.
- Frontend `npm run typecheck`: **passed**.

## Exact conclusion

The second source confirms the same physical OSM entity but does not supply a
structured opening or cost fact. The current exact blocker for this duplicate
row is therefore **FACTS_NOT_STRUCTURED_AFTER_PROVIDER_MATCH**, not a planner,
mobility, or authority bypass opportunity. UNKNOWN remains the only honest
state.

## Evidence files

- `runtime/wangshi-node-facts-acquire.json`
- `runtime/wangshi-node-public-after.json`
- `runtime/wangshi-node-plans-after.json`
- `runtime/wangshi-node-twin-after.json`
- `runtime/wangshi-official-page.html`
- `runtime/wangshi-node-focused-tests.txt`
- `runtime/wangshi-node-frontend-typecheck.txt`
- `runtime/deepseek-lion-node-facts.json`
- `runtime/citynexus-r77-authority-gate-r4-20260930.sqlite3`
