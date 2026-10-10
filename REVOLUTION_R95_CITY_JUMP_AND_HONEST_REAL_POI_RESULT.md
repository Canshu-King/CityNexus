# CityNexus Revolution R95 result

## Delivery

R95 adds an explicit `Find my city` action to the first public-area picker. The city result is a camera hint only: the traveler sees the provider, evidence grade and centroid uncertainty, then must load tiles under a separate disclosure and tap the public discovery area. A configured city provider is opt-in, has one selected provider, an identifying operator User-Agent requirement, a durable database-backed one-request-per-second application gate and a cross-user cache. Missing operator configuration leaves city search disabled and preserves the validated OpenStreetMap link/manual WGS84 fallback.

The Overpass result grade is now derived from the endpoint that actually answered. Loopback and explicit controlled endpoints are `TEST_PROVIDER`; recognized public Overpass mirrors are `LIVE_PROVIDER`; unknown or unavailable answers remain `UNVERIFIED`. The grade is persisted and propagated through candidate, shortlist, preview, selected Place metadata and API responses. Old rows without evidence are not upgraded.

## Evidence

| Check | Result |
| --- | --- |
| R95 backend provenance/cache slice | `1 passed` — consent gate, controlled city result, cache hit without a second geocoder call, TEST_PROVIDER grade through discovery/shortlist/preview/selected Place |
| R95 Chromium acceptance | `2 passed` in authoritative run `r95-20261010-05` — real-seed setup plus `r95-city-jump-and-honest-real-poi.spec.ts` at mobile viewport |
| Controlled city provider calls | 1 explicit request, 0 automatic requests on mount/typing |
| Controlled Overpass calls | 1 bounded request |
| Public external geocoder/Overpass calls | 0 |
| Tile consent | separate; no tile request before disclosure |
| A/B privacy | owner saved item visible only to owner; collaborator saw `Saved 0 of 3` |
| Walking handoff | destination-only Google walking URL; no `origin`, receipt or private center |
| TypeScript | `npm run typecheck:all` passed |
| Frontend build | `npm run build` passed |
| Python compile | `python313 -m compileall -q backend/app` passed |
| Diff check | `git diff --check` passed |

The browser run used a fresh isolated SQLite database, signed owner and collaborator tokens, a local city-search fixture on `127.0.0.1:8213`, and a local Overpass fixture on `127.0.0.1:8214`. These prove the controlled product path and privacy boundaries; they do not prove a physical visit, GPS presence, opening status, price, route ETA, or public-service availability.

## Source and policy boundary

The implementation keeps the external geocoder behind explicit operator configuration and an explicit traveler action. The public OSM service rules used for the gate are [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/) and [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/). No autocomplete or request-on-typing behavior was added.

## Git baton

- GPT reviewer base safely integrated: `33f0fc02837340927dca77b07c66f63b9e39f7e0`.
- Codex R95 implementation and this result are committed on `codex/revolution-r63-planned-parallel-journey` and pushed to `origin` below.
- No R58–R94 historical campaign was rerun.

## Unverified claims and next action

Real mobile GPS, physical arrival, live public geocoder availability, live public Overpass availability, opening hours, prices and route ETA remain unverified. The next reviewer action is to inspect this R95 commit and decide whether to merge it into `gpt/revolution-r33-open-world-journey-adaptation`.
