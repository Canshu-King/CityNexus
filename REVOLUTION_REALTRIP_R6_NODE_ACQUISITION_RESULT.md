# CityNexus Revolution Lab R6 — exact node fact acquisition

## Execution binding

- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Starting commit: `f09379fc460752b0980c1aafc08c097c6cf752a6`
- Final experimental commit: `f09379fc460752b0980c1aafc08c097c6cf752a6`
- No source change was required by this negative-result experiment.
- Database: disposable `citynexus-r77-authority-gate-r4-20260930.sqlite3`

## Exact target

- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- Place: `real-place-bcd9c9f324751168d422a06b`
- Provider identity: `overpass + overpass:node/5042033121`
- Display name: `网师园`

The request was made through the existing product endpoint:

```text
POST /api/v1/journeys/{journey_id}/facts/acquire
{"place_ids":["real-place-bcd9c9f324751168d422a06b"]}
```

## Machine result

The acquisition returned HTTP 200 and one exact Overpass element. Nominatim
returned `ACQUIRED` with `matched_provider_entity=true`, so the identity is
confirmed. Its only extratags contribution was a website URL:

```text
http://jump.szjlxx.cn/?park=wsy
```

The source-linked result was:

- `opening_hours.status = UNKNOWN`
- `cost_evidence.status = UNKNOWN`
- `known_opening_count = 0`
- `known_cost_count = 0`

The bound official page was attempted and returned:

```text
status = NO_STRUCTURED_FACTS
acquired = 0
```

The search source was not configured, so it was not counted as a failed fact
or a source-backed answer:

```text
provider = searxng
status = UNCONFIGURED
attempted = false
```

Raw receipts are in `runtime/`:

- `execution-binding.json`
- `before-places.json`
- `acquisition-response.json`
- `after-places.json`
- `after-provider-mesh.json`
- `after-twin.json`
- `result-summary.json`

## Before/after truth

After acquisition, the exact node still reported UNKNOWN opening and UNKNOWN
cost with `amount_minor = null`. The selected plan remained
`09715a08-4e06-57b7-bebc-b9a5adf872a2`, and the Twin remained `READY`.
No facts were copied from the nearby but different
`overpass:way/44679452` entity.

The clean-source user-visible reread reported:

```text
pending_rows = 18
unknown_opening_rows = 18
unknown_cost_rows = 18
identity = overpass · overpass:node/5042033121
```

The page screenshot and DOM summary are in `evidence/`.

## Exact blocker

The current blocker is source availability for this exact provider entity:

```text
Nominatim identity: available
Opening-hours evidence: absent
Cost evidence: absent
Official page: attempted, no structured facts
Search source: not configured
```

This is not a planner, mobility, or UI projection blocker. The UI now carries
the negative result honestly. No plan was generated or selected as part of
this experiment.

## Verification

- Product acquisition: HTTP 200, one exact element, zero known opening/cost
  facts.
- Product after-state: node still UNKNOWN; plan selection unchanged.
- Browser reread: PASS; UNKNOWN remains visible and the node ID is traceable.
- `P7=false`, `MOCK != LIVE`, `UNKNOWN != free`.
- No raw credentials, real-user mutation, payment, booking, or mainline merge.

## Agent/runtime disclosure

No new DeepSeek or Hermes run was needed for this deterministic fact-source
experiment. The runtime remains `NATIVE_DEEPSEEK_TOOL_LOOP` with configured but
unverified DeepSeek and unavailable Hermes; no agent prose is used as truth.

## Next bounded experiment

Enable or provide a real search-source adapter inside the isolated lab, then
query only the exact node identity. If it yields no structured opening/cost
facts, preserve this blocker. Any evidence must bind to
`overpass:node/5042033121`; a result for the way or a same-name first result is
not admissible.
