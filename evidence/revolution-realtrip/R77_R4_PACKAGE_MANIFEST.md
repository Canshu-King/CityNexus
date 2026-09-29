# R77-R4 evidence package

This package is for the isolated Revolution Lab only.  It records the clean
source used for the R4 replay, the live DeepSeek tool trace, the Overpass /
Nominatim fact receipt, the real selection response, Hermes's exact runtime
blocker, and the relevant UI captures.

## Source binding

- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Product repair commit: `a71d0c249170d8e232ba93e8f23ef896e49ddfe7`
- Evidence/report commit: `ac03c1d72dee100baff0398d369583584164de4f`
- Disposable DB only: `citynexus-r77-authority-gate-r4-20260930.sqlite3`
- No authority/mainline merge; `P7=false`

## Machine evidence

- `r77_authority_gate_r4_receipt.json`: compact round receipt and replay.
- `r77-authority-gate-r4-agent.json`: raw DeepSeek native tool-loop response.
- `r77-facts-live-r4.json`: raw Overpass + exact Nominatim acquisition response.
- `r77-authority-gate-r4-select.json`: raw HTTP selection status, headers, and body.
- `r77-authority-gate-r4.patch`: product diff from the round start to the repair.
- `r77-authority-gate-r4.sqlite3`: disposable clone used for the replay.

The decisive post-repair response is HTTP 409 with
`reason_code=UNRESOLVED_ACTIVITY_FACTS`; the actual candidate Place IDs are
included in the response body.  `active_plan_version_id` remains unchanged.

## Agent/runtime evidence

- The raw DeepSeek response proves the ordered tool calls and proposal.
- Hermes native execution is not claimed.  The included H11 blocker records
  `RESET/SEED HTTP 403: DEMO_MODE_REQUIRED`.
- No raw credential is included.  The supported registry credential was used
  only by the runtime process.

## UI evidence

The PNGs are included because historical report text cites them.  They are
contextual UI evidence; machine receipts and the API response remain the
authority for the R4 selection classification.

## Focused tests

`108 passed, 1 warning in 10.12s`; the warning is the existing
Starlette/httpx deprecation.
