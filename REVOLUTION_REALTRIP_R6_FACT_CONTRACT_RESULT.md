# Revolution Lab R6 — fact-acquisition contract sync

## Binding

- Branch: `codex/revolution-realtrip-recovery`
- Isolated worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Starting source commit: `4edf9d36b5048c1ac827721313b8a328136b8a1a`
- Final experimental source commit: `a833851437e337595d70aa4850b71d331d107272`
- Mainline/authority merge: none
- Clean source was verified before the replay product call.

## Defect

The live backend route already existed and was used successfully:

```text
POST /api/v1/journeys/{journey_id}/facts/acquire
```

But the route was absent from `contracts/openapi.yaml` and
`frontend/src/generated/api.ts`. The contract parity gate therefore reported
the real runtime route as an undocumented extra.

## Bounded repair

- Added the optional `place_ids` request shape and 200/502 response surface to
  the OpenAPI contract.
- Added the matching generated TypeScript path and operation.
- No runtime behavior, provider parser, planner, mobility, or authority rule
  changed.

## Focused gates

- Contract/identity subset: **36 passed, 2 warnings**.
- Frontend `npm run typecheck`: **passed**.

The prior single contract failure for the missing facts-acquisition route is
gone.

## Same-destination replay

- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- City: `CN-SUZHOU`
- Target: `real-place-bcd9c9f324751168d422a06b`
- Provider entity: `overpass:node/5042033121`

The clean-source product replay returned:

```text
facts acquire HTTP              200
Nominatim matched entity        true
opening status                  UNKNOWN
cost status                     UNKNOWN
cost amount_minor               null
selected plan                   09715a08-4e06-57b7-bebc-b9a5adf872a2 / SELECTED
active_plan_version_id          09715a08-4e06-57b7-bebc-b9a5adf872a2
Twin projection                 READY
```

The actual used edge IDs remained the same three real Valhalla edges from the
selected plan, all previously recorded as non-degraded and `HARD_ELIGIBLE`.
No route or selectable truth was synthesized.

## Agent and safety status

- DeepSeek machine evidence retained from the prior exact-node read-only run:
  `cdc9b1e5-9afa-40b8-aff6-b726e61189c1`.
- No new DeepSeek mutation or fact assertion was used to pass this gate.
- Hermes remains not configured/reachable; no Hermes execution is claimed.
- P7 remains `false`; `MOCK != LIVE`; UNKNOWN cost remains UNKNOWN.

## Evidence

- `runtime/contract-replay/00-summary.json`
- `runtime/contract-replay/01-facts-acquire.json`
- `runtime/contract-replay/02-public-places.json`
- `runtime/contract-replay/03-runtime-openapi.json`
- `runtime/contract-replay/04-plans.json`
- `runtime/contract-replay/05-twin.json`
- `runtime/facts-contract-sync-tests.txt`
- `runtime/facts-contract-sync-frontend-typecheck.txt`
- `runtime/wangshi-official-page.html`
