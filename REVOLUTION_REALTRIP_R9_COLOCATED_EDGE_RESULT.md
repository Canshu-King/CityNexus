# CityNexus Revolution Lab R9 — live co-located edge diagnosis

## Result

R9 investigated the winter plan's 0-minute final mobility edge. Both direct,
live Valhalla directions returned the same snapped coordinate, zero route time,
and zero route length for two distinct provider-backed Place records only about
5.87 m apart. This is a provider-produced co-location result, not synthetic
mobility and not a locally manufactured duration.

The correct treatment is to preserve the provider's 0-minute result and its
live provenance. R9 did not apply a minimum-duration fudge, replace the edge,
or change product code. No new Mission A blocker was found.

## Execution binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- source commit used for both direct provider calls: `dd1754f7e6344f8ff1844aef6433cbcb4485c456`
- worktree status before and after calls: `CLEAN`
- direct provider calls: HTTPS POST to `https://valhalla1.openstreetmap.de/route`
- costing: `pedestrian`; units: `kilometers`
- P7: `false`
- no mainline merge; no real-user database was modified
- no DeepSeek or Hermes action was executed in R9

The before/after source bindings and complete request/response bodies are
included as machine evidence in this package.

## Exact edge

The same edge was present in the R8 winter Twin's actual `used_edge_ids`:

```text
real-place-8bc850f117297987997c87cf
  -> real-place-bcd9c9f324751168d422a06b
```

The records are:

| Endpoint | Provider identity | Coordinates |
|---|---|---|
| origin `real-place-8bc850f117297987997c87cf` | `overpass:way/44679452` | `31.3004105, 120.6297906` |
| destination `real-place-bcd9c9f324751168d422a06b` | `overpass:node/5042033121` | `31.3003833, 120.6298435` |

Great-circle distance from the submitted coordinates is `5.865931961868027 m`.
The R8 actual Twin receipt classified the edge `HARD_ELIGIBLE`, with
`provider=valhalla-http`, `route_provenance=LIVE_PROVIDER_CAPTURE`, and
`travel_time_minutes=0`. All four actual R8 used edges had hard eligibility;
the Twin was `READY` and not degraded. The R8 disposable winter database copy
was the only database changed by the select operation.

## Direct provider evidence

Both requests used those exact coordinates, one origin and one destination,
and pedestrian costing. Both returned HTTP 200:

| Direction | HTTP | time | length | snapped point | route shape |
|---|---:|---:|---:|---|---|
| way → node | 200 | 0.0 s | 0.0 km | `31.300802, 120.630125` | `ekmuz@{utaeF??` |
| node → way | 200 | 0.0 s | 0.0 km | `31.300802, 120.630125` | `ekmuz@{utaeF??` |

Each response contains one leg. The maneuver text describes walking north on a
walkway for “less than 10 meters”; Valhalla snaps both endpoints to the same
network point, so its route summary is zero. This supports a provider-side
snap/co-location explanation. The raw responses are preserved verbatim; the
table is a concise extraction, not a substitute for them.

## Truth classification

- R8 route candidate and selection: real product records in the disposable
  winter-copy database, with the actual route edges and eligibility receipts.
- R8 zero-minute edge: `HARD_ELIGIBLE` and live Valhalla evidence, not mock.
- R9 direct replay: independently reproduced the same zero/zero snapped result
  in both directions from the recorded coordinates.
- Selectable/active: true only for the winter plan in the disposable copy;
  this does not claim a real-user or production selection.
- P7 remains false.
- `MOCK != LIVE`; no mock evidence was relabeled.

## Focused tests and changes

R9 made no product-source changes, so no tests were required for a code diff.
The latest focused R7 recovery suite remains `22 passed, 1 warning` (the
existing Starlette/httpx deprecation warning), recorded in the R8 evidence.
R7's frontend typecheck and production build also passed. R9 added this report
only; the exact report commit is recorded in the package manifest.

## Evidence files

- `r9-evidence/execution-binding-before.json`
- `r9-evidence/execution-binding-after.json`
- `r9-evidence/forward-way-to-node.raw.json`
- `r9-evidence/reverse-node-to-way.raw.json`
- parsed response summaries for both directions
- `r8-evidence/` — complete R8 winter experiment and actual product receipts
- `r7-evidence/` — R7 canonical projection experiment, including the cited UI
  screenshot and browser evidence

## Replay

1. Check out the recorded R9 source commit in the isolated Revolution Lab
   worktree and confirm `git status --porcelain` is empty.
2. POST the coordinates and pedestrian costing from each raw evidence request
   to `https://valhalla1.openstreetmap.de/route`.
3. Compare the complete response bodies, snapped coordinates, summaries, and
   route shapes with the included raw responses.
4. To reproduce the product-side edge, replay the R8 winter scenario only
   against its disposable SQLite copy, not the original user database. R8's
   requests, responses, and copy bindings are included under `r8-evidence/`.

## Next experiment

Inspect the user-visible winter route rendering for how it communicates a live
0-minute co-located transition. If it is confusing, make the smallest truthful
presentation change using the existing live provenance and coordinates; do
not invent minutes or weaken hard eligibility. Keep Mission A on the same
provider-backed Suzhou destination and preserve the disposable-database
boundary.
