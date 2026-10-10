# Revolution Lab R6 — public place-fact projection

## Execution binding

- Branch: `codex/revolution-realtrip-recovery`
- Isolated worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Starting product commit: `a998e6c03bc7781c62070d8705daf1624c742715`
- Repair commit: `8a23d2e150d279855677b91ecff95368a897284c`
- Final experimental commit: `4f119150c458ddcc254c866ee51ecafc8d990729`
- Mainline/authority merge: none
- Product calls were made only after `git status --porcelain` was empty; the final
  clean source was `4f119150`.

## Scenario and exact destination

The same live catalog scenario was retained; no destination or seeded answer was
changed:

- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- City: `CN-SUZHOU`
- Query: `狮子林`
- Selected plan: `09715a08-4e06-57b7-bebc-b9a5adf872a2`, version 11
- Disposable DB: `C:\Users\仓鼠王\AppData\Local\Temp\citynexus-r77-authority-gate-r4-20260930.sqlite3`

The exact live rows are deliberately kept separate by provider identity:

| Place | Provider entity | Opening fact | Cost fact |
|---|---|---|---|
| 狮子林 | `overpass:way/44679451` | `OFFICIAL_WEB_VERIFIED` | `VERIFIED_PROVIDER`, 4000 CNY minor |
| 狮子林 | `overpass:node/4246892594` | `NORMALIZED_VALID`, 07:30–17:30 | `UNKNOWN`, amount `null` |

## Defect and bounded repair

Before this round, `GET /api/v1/places?city_code=CN-SUZHOU&q=狮子林`
returned HTTP 200 but only the basic place fields. The agent search on the same
rows carried opening and cost evidence, so the public product projection was
silently dropping facts and did not expose `external_id` for duplicate labels.

The repair is limited to the shared public catalogue projection:

- `PlaceSchema` now requires `external_id`, `opening_hours`, and `cost_evidence`.
- `place_schema()` passes the stored evidence through.
- Missing cost evidence becomes explicit `{"status":"UNKNOWN","amount_minor":null}`.
- The compatibility `cost_minor=0` field is never used as price truth.
- OpenAPI, generated TypeScript, and the `PlaceRecord` client type were updated.
- No planner, selection, mobility, or authority rule was weakened.

## Machine result after repair

Final clean-source product calls all returned HTTP 200. The public response now
contains both exact provider identities and fact payloads:

```text
way/44679451       opening=OFFICIAL_WEB_VERIFIED  cost=VERIFIED_PROVIDER/4000
node/4246892594    opening=NORMALIZED_VALID       cost=UNKNOWN/null
```

The live OpenAPI response marks all three new fields as required. The same
selected plan remained selected; Twin remained `projection_status=READY`.

The selected plan's actual mobility evidence remains:

```text
real-place-06361e97cfc5a371f68f7875 -> real-place-054fa857eff7a99169399bdf  WALK 13 min
real-place-054fa857eff7a99169399bdf -> real-place-8bc850f117297987997c87cf  WALK 38 min
real-place-8bc850f117297987997c87cf -> real-place-ba7377353c422c39dfd752b7  WALK 42 min
```

All three edges are `LIVE_PROVIDER_CAPTURE`, non-degraded, and
`HARD_ELIGIBLE`. The unknown node was not substituted into the selected plan.
No `used_edge_ids`, eligibility receipt, or selectable state was synthesized.

## Agent traces

- DeepSeek native runtime was configured and used in the preceding exact-node
  acquisition round: run `cdc9b1e5-9afa-40b8-aff6-b726e61189c1`, mission
  `239c8da8-b21e-4c64-b7c6-522c5bf26883`, three read-only calls. Its machine
  evidence established the node's exact Nominatim opening fact and unresolved
  cost. This round's projection repair was deterministic code applied to that
  evidence; no agent prose awarded PASS.
- Hermes was not configured/reachable in this environment. No Hermes execution
  is claimed for this round.

## Focused gates

- Backend Revolution/agent/mobility/catalog suite: **52 passed, 1 warning**.
- Frontend `npm run typecheck`: **passed**.
- Contract/identity subset with temporary PyYAML/pytest runtime: **35 passed,
  1 pre-existing failure**. The failure is exact route parity for
  `/api/v1/journeys/{journey_id}/facts/acquire`, which already exists in the
  runtime but is absent from `contracts/openapi.yaml`; the current diff does not
  touch that route.

## Evidence files

- `runtime/public-facts-final/00-summary.json`
- `runtime/public-facts-final/01-public-places-lion.json`
- `runtime/public-facts-final/03-agent-search-lion.json`
- `runtime/public-facts-final/04-selected-plans.json`
- `runtime/public-facts-final/05-selected-twin.json`
- `runtime/public-facts-final/06-agent-runtime-status.json`
- `runtime/public-facts-final/07-openapi.json`
- `runtime/public-facts-before.json`
- `runtime/deepseek-lion-node-facts.json`
- `runtime/r77-public-facts-focused-tests.txt`
- `runtime/r77-public-facts-contract-tests.txt`

## Next autonomous experiment

Use the now-truthful public facts in the actual UI detail path: verify that the
user-facing stop detail renders `NORMALIZED_VALID` and `UNKNOWN` distinctly for
the node, while the verified way renders official opening and paid evidence.
Do not turn either value into a planner/selectable decision until the authority
layer has the corresponding facts.

P7 remains `false`. `MOCK != LIVE`.
