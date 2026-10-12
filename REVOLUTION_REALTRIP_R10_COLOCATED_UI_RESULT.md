# CityNexus Revolution Lab R10 — co-located route truth reaches the UI

## Result

R10 took the already selected real winter plan through the actual execution
state machine and then exposed its final live co-located route edge in the
product map context.

```text
selected winter plan
→ real /start
→ real depart/arrive/begin/complete transitions for the first four stops
→ ACTIVE journey at stop five
→ /experience returns the actual zero-minute edge
→ map visibly says “同一网络点 · 0 分钟 · 实时供应商证据”
```

The numeric truth remains `duration_min=0`. No minimum duration, synthetic
route, or authority bypass was introduced.

## Execution binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- R10 starting commit: `f16c261a671740331ec1bebb552904f96fbc22c8`
- first repair commit: `10c383d5789c740b6c116c1ec6fb4945c983a09a`
- final experimental commit: `520e9b447e2a8dd2badfba79f2d04efb92bbc439`
- product execution calls at starting source: `f16c261a...`
- final `/experience` call and UI source binding: `520e9b44...`
- `git status --porcelain`: empty before every recorded product call and at
  final package time
- P7: `false`
- original R7 database: unchanged
- R10 database: disposable copy only
- no mainline merge, real payment, commerce action, or persistent secret

## Exact scenario

- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- city: `CN-SUZHOU`
- disposable database:
  `C:\Users\仓鼠王\AppData\Local\Temp\citynexus-r77-winter-probe-20260930.sqlite3`
- plan: `893598ec-fa26-5b79-ac79-2e8371236f37`
- winter window: `2026-11-04 09:00–19:00 Asia/Shanghai`
- active journey state after the real transitions: `ACTIVE`
- current activity after the fourth completion: sequence 5, `网师园`

The fourth-to-fifth transition is:

```text
real-place-8bc850f117297987997c87cf
  -> real-place-bcd9c9f324751168d422a06b
```

It is the exact edge previously captured from the two provider-backed places:
the nearby `overpass:way/44679452` and exact `overpass:node/5042033121`.

## Real execution evidence

At the clean R10 starting source, the product accepted:

- `POST /api/v1/journeys/{journey_id}/start`
- four real activity transition groups, each consisting of `depart`,
  `arrive`, `begin`, and `complete`
- final `GET /api/v1/journeys/{journey_id}/experience`

The final state was `ACTIVE`, with the fifth activity as the server-owned
cursor. The last projected leg was returned as:

```json
{
  "duration_min": 0,
  "co_located": true,
  "provider_key": "valhalla-http",
  "provenance": "LIVE_PROVIDER_CAPTURE",
  "geometry": {
    "type": "LineString",
    "coordinates": [[120.630126, 31.300803], [120.630126, 31.300803]]
  }
}
```

The complete HTTP call records are under `r10-evidence/01-start.json` through
`r10-evidence/17-complete-*.json` and the final response is preserved as
`r10-evidence/experience-after-r10-final.json`.

## Bounded repair

`10c383d5` adds one server-side derived field to the selected-plan projection:
`co_located=true` only when the captured provider geometry has at least two
points, every captured point is the same point, and the provider duration is
exactly zero. It does not change the duration or eligibility decision.

`520e9b44` adds the user-visible map summary. The summary reads only the
authoritative active-plan legs and says:

```text
路线包含 1 段同一网络点转换 · 0 分钟 · 实时供应商证据
```

The exact screenshot and Playwright snapshot are included:

- `r10-evidence/ui-map-co-located.png`
- `r10-evidence/ui-map-snapshot.yml`

## Authority and safety truth

- R8 already proved this selected plan crossed the real select endpoint and
  produced a `READY` Twin in the disposable winter copy.
- R8's four actual `used_edge_ids` all had `HARD_ELIGIBLE` receipts; R10 did
  not synthesize or replace them.
- R10's final response still carries all four actual edge IDs, including the
  zero-minute edge, with `LIVE_PROVIDER_CAPTURE` and `valhalla-http`.
- `MOCK != LIVE` remains intact.
- unknown cost remains unknown; the zero-minute route is not a cost claim.
- no canonical demo seed was added.

## Tests

- focused backend recovery suite: `23 passed, 1 warning`
- frontend `npm run typecheck`: passed
- frontend `npm run build`: passed, with the existing Vite chunk-size warning
- Playwright runtime: map page reached HTTP-backed winter journey and exposed
  the new `data-testid="map-co-located-evidence"` text

The warning is the existing Starlette/httpx deprecation warning; it does not
affect the R10 assertion.

## DeepSeek / Hermes

No new DeepSeek or Hermes execution was claimed in R10. The work was a
deterministic product-truth repair and a real UI rerun. Existing runtime
status remains documented in earlier round evidence; no agent prose was used
as authority.

## Replay procedure

1. Check out `520e9b447e2a8dd2badfba79f2d04efb92bbc439` in the isolated worktree
   and verify an empty `git status --porcelain`.
2. Start the backend against the disposable winter SQLite copy on port 8013.
3. GET the journey experience and confirm the final leg has
   `duration_min=0`, `co_located=true`, `provider_key=valhalla-http`, and
   `provenance=LIVE_PROVIDER_CAPTURE`.
4. Open `/v8/{journey_id}` through the frontend proxy and select 地图.
5. Confirm the map contains the visible co-location sentence and the route
   still reports four provider-supported legs.

## Next autonomous experiment

Continue the same provider-backed journey into the final activity while
preserving the server execution state, then verify the activity detail and
live surfaces remain consistent with the map's co-location statement. Do not
turn the zero-minute provider result into a positive duration.
