# Revolution R94 — Pick a public city area, then go explore

## Review and implementation boundary

- R94 taskbook reviewed from GPT remote commit `7a41d1dc305d6bfeadb0dcede2ff84e3aec6eb98` (`REVOLUTION_R94_PICK_PUBLIC_CITY_AREA_AND_GO_TASKBOOK.md`).
- R93 was accepted through the GPT review loop; no R58–R93 historical campaigns were rerun and no live Overpass request was made.
- Implementation commit is `33c3851532` on `codex/revolution-r63-planned-parallel-journey`.

## User-visible changes

- Added a deliberate “Choose public area on map” onboarding control. The picker is not mounted and cannot fetch OpenStreetMap tiles until the separate tile-provider disclosure is checked.
- A single map tap produces a rounded WGS84 `MANUAL_PUBLIC_CENTER` candidate. The strict offline fallback accepts only an exact `https://www.openstreetmap.org/` map link with a valid `#map=zoom/latitude/longitude` or one `mlat/mlon` pair; it performs no URL fetch or geocoding.
- Map-tile consent, foreground GPS permission, public discovery provider consent, and external walking-map release remain separate controls. The selected public center is labelled as neither presence, route origin, city relation, arrival, nor a live route claim.
- Existing bootstrap → private shortlist → destination-only walking handoff → R92 resume flow remains intact. The external map receives only the chosen destination and walking mode; no origin, receipt, or private journey identifier is released.

## Stale-response and privacy boundary

- Discovery, candidate selection, shortlist mutation, resume, and map-release continuations are fenced by the signed bearer generation, journey id, source mode, and discovery generation.
- Foreground GPS callbacks carry their own request generation and are ignored after a bearer, journey, source, or manual-center change. A delayed discovery response is ignored after the selected center changes.
- The browser proof uses two signed travelers on one isolated Journey. Owner A's delayed shortlist save is committed by the real backend, but collaborator B sees an empty private board; switching back restores only A's saved item.

## Fresh controlled evidence

- Authoritative run: `r94-20261010-09`, Python 3.13, frontend `:4212`, backend `:8212`, isolated SQLite `backend/_r94-20261010-09.db`, AI disabled.
- The Overpass provider is a local controlled boundary on `127.0.0.1:8211`; tile and Google directions requests are browser-boundary fixtures. This proves consent and release boundaries without claiming live provider availability.
- The browser asserts zero tile requests before tile consent, tile requests after consent, a Shanghai public tap, stale GPS suppression, one controlled discovery receipt, A/B shortlist isolation, `route ETA UNKNOWN`, destination-only walking release, no `Place`/`PlanVersion` claim, and resume after reload.
- No live Overpass, physical GPS, opening-hours verification, route feasibility, ETA, arrival, booking, payment, or formal PlanVersion claim is made by this controlled path.

## Focused proof

| Check | Result |
| --- | --- |
| authoritative `npm run test:e2e -- --project=chromium e2e/r94-pick-public-city-area-and-go.spec.ts` (`r94-20261010-09`) | 2 passed (real seed + R94 browser scenario) |
| `npm run typecheck:all` | passed |
| `npm run build` | passed; existing Vite chunk-size warning only |
| `python -m compileall -q backend/app` | passed |
| `python -m compileall -q backend` | blocked by pre-existing `backend/run_r39_live.py:305` syntax error; no R94 backend file changed |
| `git diff --check` | passed |

R94 is **CONTROLLED_PRODUCT_PATH_PROVEN** for explicit public-area selection, consent-separated provider boundaries, stale-response fencing, private signed-member isolation, destination-only walking handoff, and resume. Real provider availability, mobile OS GPS prompts, current opening, route feasibility, physical travel, and arrival remain **UNVERIFIED**.
