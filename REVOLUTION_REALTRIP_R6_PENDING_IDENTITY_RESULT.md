# CityNexus Revolution Lab R6 — pending provider identity

## Execution binding

- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Starting source commit: `6e3613b0481e2cdca020849a45e9aff35f0378e4`
- Final source commit: `7801bf0546db840e94be5b281ad7ff821df78049`
- The API and browser calls in this round were made from a clean worktree at
  the final source commit.
- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`

## Why this experiment

The previous round made provider facts visible in the pending set. The live
screen then showed a pending `网师园` with UNKNOWN facts while the selected
plan showed a verified `网师园`. The next question was whether that was a
bad projection join or two provider entities with the same display name.

The comparison was performed using the immutable pair
`provider_key + external_id`, never by label, suffix, distance, or first
result.

## Machine result

The same Journey's provider-mesh and public Places responses contain:

| Display name | Provider identity | Opening | Cost | Public place |
|---|---|---|---|---|
| 网师园 | `overpass + overpass:way/44679452` | `NORMALIZED_VALID` in capture; `OFFICIAL_WEB_VERIFIED` in public projection | `KNOWN` in capture; `VERIFIED_PROVIDER` in public projection | `real-place-8bc850f117297987997c87cf` |
| 网师园 | `overpass + overpass:node/5042033121` | `UNKNOWN` | `UNKNOWN` | `real-place-bcd9c9f324751168d422a06b` |

The coordinates are about 5.82 m apart, but that is supporting context only;
it is not used as an identity rule. The external IDs are different OSM
entities, so the deterministic decision is:

```text
SEPARATE_PROVIDER_ENTITIES_BY_EXTERNAL_ID
```

The official facts must not be copied from the way to the node.

Raw responses and the derived comparison are in `runtime/`:

- `provider-mesh.json`
- `places.json`
- `identity-comparison.json`
- `execution-binding.json`

## Bounded product change

The pending-set technical details now carry `external_id` alongside
`provider_key`. This gives the operator a traceable identity without changing
the normal traveller-facing sentence or upgrading any fact. The final live
technical detail rendered:

```text
cap:rpc-fb515b241bbf6f1224e7b9ed · DISCOVERED · overpass · overpass:node/5042033121 · real-place-bcd9c9f324751168d422a06b · attraction
```

The separator is intentional; it does not manufacture a new composite ID.

## User-visible result after the final source commit

The real `/v8/hub` page rendered:

```text
pending_rows = 18
opening facts rendered as UNKNOWN = 18
cost facts rendered as UNKNOWN = 18
malformed `overpass:overpass:` label = false
```

The ordinary rows still say:

```text
营业: 营业时间未知 · 费用: 暂无价格（未知）
```

Browser evidence is in `evidence/`:

- `browser-pending-identity.png`
- `browser-ui-summary.txt`

## Verification

- `npm run typecheck`: PASS.
- `npm run build`: PASS; only the existing Vite large-chunk warning was emitted.
- Clean-source browser run: PASS; the identity line contains the exact OSM
  node ID and no duplicated provider prefix.
- No database write, plan mutation, selection, payment, or mobility change
  was performed.

## Agent/runtime disclosure

The runtime endpoint still reported `NATIVE_DEEPSEEK_TOOL_LOOP` with
`deepseek_configured=true` and `ai_state=CONFIGURED_UNVERIFIED`. This round
does not claim a new DeepSeek action. Hermes remained unavailable:
`hermes_compat_configured=false`, `hermes_native_gateway.ready=false`.

## Truth boundary

- Same name is not identity.
- UNKNOWN cost is not free.
- MOCK is not LIVE.
- The node remains unresolved and is not eligible for fact promotion merely
  because a nearby way has official facts.
- `P7=false`; no authority/mainline merge occurred.

## Next autonomous experiment

Use the node's exact provider identity in the fact-acquisition path and run a
bounded second-source lookup for `overpass:node/5042033121`. If no source-linked
opening/cost facts are returned, keep both values UNKNOWN and record the
negative receipt. If a source resolves to the node itself, promote only that
node's evidence; never inherit the way's facts.
