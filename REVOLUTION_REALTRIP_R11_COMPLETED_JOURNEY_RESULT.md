# CityNexus Revolution Lab R11 — complete the same real journey

## Result

R11 resumed the exact disposable winter journey used by R8–R10 and took its
fifth and final activity through the real execution state machine:

```text
ACTIVE at stop 5
→ real depart
→ real arrive
→ real begin
→ real complete
→ Journey COMPLETED
→ current_activity_id = null
→ all five activities COMPLETED
```

This is a product execution result, not a planner-only or provider-only
result. The selected plan, its frozen mobility evidence, the Twin, and the
user-visible live/map surfaces were read after the final transition.

## Execution binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- R11 executed source commit: `365ed4203038740d6b2407e45dcf024188432f65`
- final experimental/source commit: `365ed4203038740d6b2407e45dcf024188432f65`
- this round made no product-source change; the commit above is the R10
  report commit and was clean before every R11 product call
- disposable database:
  `C:\Users\仓鼠王\AppData\Local\Temp\citynexus-r77-winter-probe-20260930.sqlite3`
- backend: `http://127.0.0.1:8013`
- `git status --porcelain`: empty before every recorded transition call
- P7: `false`
- original authority database: unchanged
- no mainline merge, payment, commerce action, or persistent secret

## Exact scenario

- journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- city: `CN-SUZHOU`
- window: `2026-11-04 09:00–19:00 Asia/Shanghai`
- selected plan: `893598ec-fa26-5b79-ac79-2e8371236f37`
- final activity: `f95f61f8-4bc1-54cd-8389-c64dbc210dd6`
- final activity: `网师园`, provider-backed place
  `real-place-bcd9c9f324751168d422a06b`

## Machine product evidence

The four final state-machine calls all returned HTTP 200:

```text
POST /api/v1/journeys/{journey_id}/activities/{activity_id}/depart   200
POST /api/v1/journeys/{journey_id}/activities/{activity_id}/arrive   200
POST /api/v1/journeys/{journey_id}/activities/{activity_id}/begin    200
POST /api/v1/journeys/{journey_id}/activities/{activity_id}/complete 200
```

The final `/experience` response says:

```json
{
  "journey.status": "COMPLETED",
  "active_plan.status": "ACTIVE",
  "active_plan.current_activity_id": null,
  "activity_count": 5,
  "completed_count": 5,
  "active_plan_version_id": "893598ec-fa26-5b79-ac79-2e8371236f37"
}
```

The final `/twin` response says `projection_status=READY`,
`journey_status=COMPLETED`, `current_activity_id=null`, and no upcoming
commitments. Its feasibility envelope remains `robust=true`; no provider was
degraded.

Evidence files:

- `r11-evidence/02-depart-f95f61f8.json`
- `r11-evidence/03-arrive-f95f61f8.json`
- `r11-evidence/04-begin-f95f61f8.json`
- `r11-evidence/05-complete-f95f61f8.json`
- `r11-evidence/06-experience-after-complete.json`
- `r11-evidence/08-twin-final.json`
- `r11-evidence/09-authority-final-summary.json`

## Actual route truth

The selected plan still carries exactly four actual `used_edge_ids`:

```text
real-place-ba7377353c422c39dfd752b7
  -> real-place-054fa857eff7a99169399bdf
real-place-054fa857eff7a99169399bdf
  -> real-place-06361e97cfc5a371f68f7875
real-place-06361e97cfc5a371f68f7875
  -> real-place-8bc850f117297987997c87cf
real-place-8bc850f117297987997c87cf
  -> real-place-bcd9c9f324751168d422a06b
```

Every actual edge has a persisted hard-eligibility receipt with:

```text
provider          = valhalla-http
route_provenance  = LIVE_PROVIDER_CAPTURE
fact_quality      = LIVE_PROVIDER_CAPTURE
degraded          = false
decision          = HARD_ELIGIBLE
```

The fourth edge is the captured zero-minute co-located transition. Its
geometry is two identical provider coordinates and it remains explicitly
marked `co_located=true`; it is not relabeled as a positive-duration route or
as cost evidence. `UNKNOWN` cost remains unknown.

## User-visible evidence

After completion, the real frontend was opened against the 8013-backed
preview:

- `r11-evidence/ui-completed-map.png`
- `r11-evidence/ui-completed-map-snapshot.yml`
- `r11-evidence/ui-completed-realtime.png`
- `r11-evidence/ui-completed-realtime-snapshot.yml`

The map page visibly reports:

```text
路线包含 1 段同一网络点转换 · 0 分钟 · 实时供应商证据
```

It also reports four provider-supported legs and WGS84. The real-time page
visibly reports:

```text
现在没有待进行的步骤
```

The UI still exposes an unrelated detected closure as a recovery proposal;
R11 did not accept, book, or mutate that proposal. This preserves the
authority boundary while confirming the completed journey state.

## Chain of work delivered in this 12-hour package

- R7: recovered the real Revolution Lab lineage and real Suzhou product path.
- R8: selected a real provider-backed plan; Twin became READY; all actual
  mobility edges were hard eligible.
- R9: proved the exact Valhalla co-located edge with raw provider evidence.
- R10: made the co-located provider truth explicit in the backend projection
  and visible in the map UI.
- R11: completed the fifth activity and verified completed-state consistency
  across API, Twin, map, and live surfaces.

The complete earlier evidence chain is included under `prior-r10/`, which
contains the R10 package and its embedded R9/R8/R7 evidence.

## Tests and agent status

R11 is a deterministic runtime completion rerun; it adds no source change and
therefore no new focused-test run. The carried-forward focused gates remain:

- backend recovery suite: `23 passed, 1 warning`
- frontend `npm run typecheck`: passed
- frontend `npm run build`: passed with the existing Vite chunk-size warning
- Playwright R10 map gate: passed
- R11 Playwright: completed map and real-time pages reached through the
  HTTP-backed winter journey

No new DeepSeek or Hermes execution is claimed in R11. No agent narration is
used as authority; the machine receipts above are authoritative.

## Replay procedure

1. Use commit `365ed4203038740d6b2407e45dcf024188432f65` in the isolated
   worktree and verify an empty `git status --porcelain`.
2. Start the backend on port 8013 against the disposable winter SQLite copy.
3. GET the journey experience and confirm activity 5 is the server cursor.
4. POST `depart`, `arrive`, `begin`, and `complete` for activity
   `f95f61f8-4bc1-54cd-8389-c64dbc210dd6`.
5. GET `/experience` and `/twin`; confirm `COMPLETED`, `READY`, null cursor,
   five completed activities, four actual edges, and four hard-eligible
   receipts.
6. Open `/v8/{journey_id}`, then 地图 and 实时行程. Confirm the co-located
   evidence sentence and the no-pending-step sentence.

## Next autonomous experiment

Move from completed-journey truth to the next R77 product frontier: inspect
and repair the completed-state presentation of detected recovery proposals so
the UI distinguishes “journey completed” from “unaccepted advisory change”,
without accepting or mutating any proposal and without weakening MOCK != LIVE,
P7, or unknown-cost semantics.
