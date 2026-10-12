# CityNexus Revolution Lab — R77/R5 real-trip checkpoint

## Result

`REAL_SELECTABLE_CLOSED` / `AUTHORITATIVE_SELECTION_CONFIRMED`

This round used the clean isolated lab worktree and the same persisted Suzhou
Journey.  The result is a real product selection, not a provider-only match,
not a mock route, and not an agent-written PASS.

## Source binding

- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Starting commit: `5a02f29b870198e3d53696945023d216ea4034fb`
- Product implementation commit: `151135fe18ea92ff85f93f5d37d124ea0523b463`
- Clean-source check before product calls: `git status --porcelain` was empty.
- P7: `false`
- The authoritative/mainline tree was not merged.

## Exact scenario

- Destination: Suzhou, China (`CN-SUZHOU`)
- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- Journey window: `2026-10-04T09:00:00+08:00` to `2026-10-04T19:00:00+08:00`
- Candidate PlanVersion: `c77fabf8-1aa7-559f-9dfd-232b96462318`
- Mobility snapshot: `891cdf3d-12e8-4697-a2a5-184cb2618485`

The R77 kit recovery work deliberately kept the real Suzhou scenario rather
than seeding a demo answer.  Earlier Gongshan blockers remain historical
evidence; they were not rewritten into this result.

## Provider and fact evidence

The final bounded acquisition was executed at `2026-09-30T07:53:17.468425+08:00`.

- Overpass: `https://overpass-api.de/api/interpreter`, `ACQUIRED`
- Nominatim lookup: `https://nominatim.openstreetmap.org/lookup`, `ACQUIRED`, 2 elements
- Official web: 2 attempted / 2 acquired
- `known_opening_count=2`, `known_cost_count=2`
- `overpass:way/44679451` (`狮子林`) was bound to municipal page `id=46`; Nominatim matched the exact provider entity and coordinates.
- `overpass:node/8714647418` (`Old Town` / `平江历史街区`) was bound to municipal page `id=34`; Nominatim matched the exact provider entity and coordinates.
- Lion Grove: official seasonal opening, `07:30–17:30` for the journey date, `VERIFIED_PROVIDER`, `4000 CNY`.
- Pingjiang Old Town: official `全天开放`, represented as `00:00–24:00`, `VERIFIED_PROVIDER`, explicitly free (`0 CNY`). This is not UNKNOWN-as-free.

The captured HTML and compact machine receipt are in `sources/` and
`runtime/r5_fact_acquisition.json`.

## Real plan and authority transition

The real generate call returned HTTP `201`.  The plan contained four actual
provider-backed place rows:

1. Old Town — `real-place-06361e97cfc5a371f68f7875`
2. 狮子林 — `real-place-054fa857eff7a99169399bdf`
3. 网师园 — `real-place-8bc850f117297987997c87cf`
4. 拙政园 — `real-place-ba7377353c422c39dfd752b7`

Total planned cost was `16000 CNY`.  The generated candidate carried
`selectable=true` only after deterministic fact and mobility gates were
present.  The real selection call then returned HTTP `200`; an idempotent
readback confirmed:

```text
Journey.status                 = PLANNED
Journey.active_plan_version_id = c77fabf8-1aa7-559f-9dfd-232b96462318
Plan.status                    = SELECTED
Plan.is_current                = true
Plan.selectable                = true
```

No booking, payment, or irreversible commerce was performed.

## Actual mobility edges and eligibility

The selected plan's own persisted evidence reports `110` provider facts, with
the following actual used edges (no IDs were synthesized):

```text
real-place-06361e97cfc5a371f68f7875 -> real-place-054fa857eff7a99169399bdf  WALK 13 min
real-place-054fa857eff7a99169399bdf -> real-place-8bc850f117297987997c87cf  WALK 38 min
real-place-8bc850f117297987997c87cf  -> real-place-ba7377353c422c39dfd752b7  WALK 42 min
```

Every actual edge has:

```text
provider          = valhalla-http
route_provenance  = LIVE_PROVIDER_CAPTURE
fact_quality      = LIVE_PROVIDER_CAPTURE
degraded          = false
```

The product's own `GET /api/v1/demo/scene` coverage says `3` total mobility
legs and `3` hard-eligible legs.  The package also contains per-edge receipts
from the product's `MobilitySnapshot.hard_minutes` decision on the persisted
selected-plan evidence; all three return their persisted minutes and
`HARD_ELIGIBLE`.

## User-visible product evidence

- `GET /api/v1/journeys/{journey_id}/experience`: HTTP `200`; selected plan,
  activities, exact `used_edge_ids`, live route provenance, and route legs are
  visible.
- `GET /api/v1/journeys/{journey_id}/twin`: HTTP `200`; `projection_status=READY`,
  cursor `VALID`, current Old Town and next 狮子林, next leg `WALK/13 min`.
- `GET /api/v1/demo/scene`: HTTP `200`; `evidence_state=FROZEN_WITHOUT_TTL`,
  evidence reference consistent, `mobility_legs_hard_eligible=3`.

These are the actual product projections included under `runtime/`; no mock
screen is cited as LIVE.

## DeepSeek and Hermes execution

DeepSeek was executed through the CityNexus native tool loop:

- Run: `262f360e-ec5e-4993-a8ab-d17bbe909f4d`
- Runtime: `NATIVE_DEEPSEEK_TOOL_LOOP`
- Model: `deepseek-v4-flash`
- Completed tools: `inspect_journey`, `inspect_twin`, `list_replans`, and two
  `search_city_services` calls.
- Final machine state: `FAILED_EXTERNAL`, `ai_state=PROVIDER_REFUSED`,
  `failure_reason=DeepSeek Agent completion failed`.

This is recorded as a real agent attempt and failure.  It did not award the
product selection and is not reported as a PASS.

Hermes was not fabricated.  The runtime status was machine-read as
`configured=false`, `ready=false`, `reachable=false`; therefore there is no
Hermes trace to claim in this round.

## Focused tests

```text
47 passed, 1 warning
tests/test_revolution_r77_recovery.py
tests/test_qoder_catalog_reason_code.py
tests/test_qoder_mobility_evidence_sources.py
tests/test_agent_runtime_gate.py
```

The exact `test_qoder_catalog_reason_code.py` source is included in the
package, together with the R77 recovery test and the modified fact acquisition
source.

## Product defects / next experiment

1. The DeepSeek native loop reaches the CityNexus gateway but the upstream
   provider refuses the final completion.  Next bounded experiment: diagnose
   the provider request/response contract without weakening deterministic
   authority or persisting credentials.
2. When a `PRESENTED` replan exists, the recovery-oriented
   `/route-evidence` surface reads that proposal's frozen snapshot; the
   active-plan truth is correctly exposed by `experience`, `twin`, and
   `demo/scene`, but this surface needs a focused consumer-contract test so a
   normal Journey screen cannot confuse a proposal route with the selected
   route.

Replay from the package:

1. Use the stated branch/worktree and clean commit.
2. Start the disposable server with the R77 live-provider environment and the
   disposable SQLite path recorded outside the repository.
3. Acquire facts for the two exact place IDs.
4. Generate the plan, select the returned PlanVersion, and read back
   `experience`, `twin`, and `demo/scene`.
5. Re-run the per-edge receipt probe against the persisted PlanVersion
   mobility evidence; do not replace any edge ID or evidence value.

