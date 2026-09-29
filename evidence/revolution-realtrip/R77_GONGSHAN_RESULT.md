# R77 Gongshan real-trip recovery receipt

This is a machine-grounded receipt for the clean-source execution after commit
`300a6abbe24a66ac731f98c0d2f4705c3169dc76`.

## Source binding

- Starting commit: `4ee14229f80691cf8e5ea913375c0caf83ac02ee`
- Experimental code commit: `300a6abbe24a66ac731f98c0d2f4705c3169dc76`
- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Worktree state before product calls: clean (`git status --porcelain` empty)
- Runtime DB: `backend/r77_final_live.db` (disposable lab DB)

## Same destination execution

`贡山独龙族怒族自治县` / `OSM:R:2729765`

1. Live Overpass `park`: HTTP 200; three mirrors timed out/504, then
   `overpass.openstreetmap.fr` returned one element.
2. Live Overpass `attraction`: HTTP 200; the same mirror returned one element,
   classified as `viewpoint`.
3. Exact provider Places persisted:
   - `real-place-b80da739cba29adc7cb6a006` → `overpass:way/1417996052` (`park`)
   - `real-place-c365c44a508d5cd3c4fc5484` → `overpass:node/13030932589` (`viewpoint`)
4. Fact acquisition: HTTP 200, `ACQUIRED`; Nominatim `/lookup` matched both
   provider entities exactly. It added no opening-hours or cost authority.
5. Real planner: HTTP 201, PlanVersion
   `dd171df4-a987-565b-bbd4-3904926eb11e`, status `CANDIDATE`.
6. Live Valhalla: both captured matrix directions were available (52 and 53
   minutes); the candidate's actual used edge is park → viewpoint, 52 minutes,
   with `LIVE_PROVIDER_CAPTURE` provenance and real route geometry.
7. Selection: HTTP 409, `UNRESOLVED_ACTIVITY_FACTS`; no active-plan pointer was
   created.

The candidate is therefore a real, user-visible draft, not a selectable plan.
`cost_minor=0` remains compatibility storage only; both activity projections say
`cost_status=UNKNOWN` and `price_known=false`.

## Exact current blocker

Both actual visit Places have empty authoritative opening and cost observations.
Nominatim supplied exact entity identity plus unrelated extratags, but no opening
or cost fact. There is no official source URL and the optional SearXNG source is
not configured. The deterministic authority gate stops selection at
`UNRESOLVED_ACTIVITY_FACTS`.

The receipt records `used_edge_ids` only for the activity order actually used by
this candidate. The reverse matrix edge is not counted as used. No hard
eligibility receipt is invented because the product did not emit one before the
fact-authority stop.

## Agent runtime

- DeepSeek: `NOT_CONFIGURED`; no live execution claimed.
- Hermes native: `configured=false`, `ready=false`; no live execution claimed.

## Verification

Focused gates: `48 passed, 1 warning`.

The warning is the existing Starlette/httpx deprecation warning. The new recovery
tests cover one-client fact acquisition, latest UNKNOWN observation semantics,
official-source SSRF boundaries, query-keyed discovery cache, and real-catalogue
provisional visibility versus selection authority.

Full machine values are in [r77_gongshan_live_receipt.json](./r77_gongshan_live_receipt.json).

## Replay

From the isolated worktree, with no persistent secret:

```powershell
$env:CITYNEXUS_REAL_CITY_ENABLED = "true"
$env:CITYNEXUS_LIVE_VALHALLA_URL = "https://valhalla1.openstreetmap.de"
$env:CITYNEXUS_DATABASE_URL = "sqlite:///./r77_final_live.db"
py -3.13 -m pytest -q backend/tests/test_revolution_r77_recovery.py
```

The live API sequence is: create traveler and Journey for
`OSM:R:2729765`; set the disposable arrival context to
`27.7443567,98.6672235`; call live discovery for `park` and `attraction`; call
`POST /api/v1/journeys/{journey_id}/facts/acquire`; call
`POST /api/v1/journeys/{journey_id}/plans/generate`; then call the returned
plan's `/select` endpoint and expect `409 UNRESOLVED_ACTIVITY_FACTS`.
