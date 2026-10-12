# Revolution R71 — Can We Actually Make It?

## Delivery

- R70 baseline: `5b8491e979b6ebb0626fea99d311b04d67c9b410`.
- GPT taskbook handoff: `f8fae0c30aa52184ab9ff5e98456a712050405ce`.
- R71 implementation: `3fe401eff807283f12007c016752a2b28fd4bc59`.
- Branch: `codex/revolution-r63-planned-parallel-journey`, to be pushed to `origin/gpt/revolution-r33-open-world-journey-adaptation`.

## What changed

The addressed invitee can request a signed feasibility preview for one R70 Place invitation. The request requires a fresh location observation owned by that recipient and explicit route-check consent. It evaluates the frozen public Place against the active PlanVersion rendezvous and existing protected-commitment checks. It returns `CAN_MAKE_IT`, `AT_RISK`, `UNKNOWN`, or `BLOCKED`; missing or stale evidence stays `UNKNOWN`.

The preview token binds the invitation, authenticated recipient, plan/rendezvous context, recipient observation version, route evidence, and a short expiry. It excludes coordinates and route geometry. Acceptance rechecks the binding and current context. Unknown and at-risk outcomes require an explicit acknowledgement; protected conflicts fail closed. Conditional database updates protect response, decline, and acceptance recovery against duplicate writes. Preview and acceptance do not mutate the shared PlanVersion or replace a recipient's existing side quest.

The recipient UI asks separately before one foreground location capture and route check. It keeps map-pin consent separate, shows evidence provenance/freshness and grounded minutes only, and offers decline or an explicit unverified acceptance when no usable route evidence exists.

## Verification

All commands below exited `0` unless noted.

| Check | Command / setup | Result |
| --- | --- | --- |
| R70/R71 backend | From `backend`: `.\.venv\Scripts\python.exe -m pytest tests/test_r64_member_side_quest.py -k 'r70 or r71' -q` | `18 passed, 21 deselected` |
| Python compile | From repository root: `backend\.venv\Scripts\python.exe -m compileall -q backend\app\execution\member_place_invitation.py backend\app\main.py backend\app\schemas.py backend\tests\test_r64_member_side_quest.py` | Passed |
| Focused Ruff | From repository root: `backend\.venv\Scripts\python.exe -m ruff check backend\app\execution\member_place_invitation.py` | Passed |
| Frontend typecheck | From `frontend`: `npm run typecheck` | Passed |
| Production build | From `frontend`: `npm run build` | Passed; Vite reported the existing large-chunk warning |
| Fresh isolated browser run | `npm run test:e2e -- --grep 'R71 checks invitation feasibility'`, authoritative run `r71relay-20261009e`, frontend `43901`, backend `43902`, fresh SQLite database, `reuseExistingServer=false`, AI disabled | `2 passed (29.1s)` |
| Diff whitespace | `git diff --check` | Passed |

The backend cases cover feasible, at-risk, protected-blocked, missing-origin, stale-route, stale-rendezvous, invalid/expired token, withdrawal, recipient scoping, and acceptance lease/recovery. Deterministic route fixtures are labelled as test fixtures; they do not stand in for live provider evidence.

## Provider and Agent evidence

The browser contexts had no geolocation permission. B's explicit check therefore returned `UNKNOWN` with no ETA, and the R71 preview did not call an external mobility provider. No LIVE_PROVIDER_CAPTURE was produced in this run, and the result makes no physical-arrival claim. AI was disabled. The E2E seed did call the existing `/agent/commands` endpoint to set up A's planned split; that command took the deterministic in-process planned-separation path and did not create an AgentRun or invoke an external Agent.

The authoritative harness record for this final browser run is `reports/e2e-provenance/authoritative.json`.
