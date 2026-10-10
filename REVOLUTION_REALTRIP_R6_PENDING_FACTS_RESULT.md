# CityNexus Revolution Lab R6 — pending-set fact visibility

## Execution binding

- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Starting commit: `a02f19e17c8c145aff8e80b60ae545dd587d68ac`
- Final source commit: `6e3613b0481e2cdca020849a45e9aff35f0378e4`
- Product calls after the source change were made from a clean worktree at
  `6e3613b0481e2cdca020849a45e9aff35f0378e4`.
- Database: `C:\Users\仓鼠王\AppData\Local\Temp\citynexus-r77-authority-gate-r4-20260930.sqlite3`

## Scenario

The same real Suzhou Journey was used throughout:

- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`
- City: `CN-SUZHOU`
- Window: `2026-10-04 09:00–19:00 Asia/Shanghai`
- Current plan: `09715a08-4e06-57b7-bebc-b9a5adf872a2`, version 11

The product was started from the clean source commit with the disposable
database and then opened at `/v8/hub` with this Journey ID in the product's
own local storage.

## Bounded change

The provider-mesh endpoint already returned `opening_hours` and
`cost_evidence`, but the pending-set read discarded both objects and the
traveller screen only rendered name, cause, and category. This round carries
the existing facts through the existing read path:

```text
GET /journeys/{journey_id}/provider-mesh
  -> readCapturedPlaces()
  -> PendingCandidate.opening_hours / cost_evidence
  -> derivePendingSet()
  -> PendingSetPanel
  -> visible pending-row-facts sentence
```

No candidate was added, no provider fact was synthesized, and no identity join
by display name was introduced.

## Machine evidence

Clean post-commit runtime files are in `runtime/` in the review archive:

- `execution-binding.json` — clean-tree commit, branch, worktree, and capture time.
- `provider-mesh.json` — exact provider candidates returned for this Journey.
- `places.json` — public Place projection for the city.
- `twin.json` — authoritative plan/Twin state.
- `runtime-summary.json` — derived counts from those exact responses.
- `agent-runtime-status.json` — runtime configuration state.

The clean provider-mesh response contained 20 candidates. One candidate had
non-UNKNOWN opening and cost evidence; the other 19 remained unknown. The
public city projection contained three official OSM-bound garden rows. The
selected Twin remained `READY`, with the existing plan and no synthetic route
flags.

## User-visible result

Playwright was run against the clean commit at:

```text
http://127.0.0.1:4175/v8/hub
```

The actual rendered pending-set reading was:

```text
pending_rows = 18
unknown_opening_rows = 18
unknown_cost_rows = 18
```

Every pending row visibly used the wording:

```text
营业: 营业时间未知 · 费用: 暂无价格（未知）
```

The visible screen included `网师园` as a pending provider candidate, but it
did not borrow the official facts of the separately bound selected Place row.
That distinction is intentional: same display label is not identity.

Included browser evidence:

- `evidence/browser-pending-facts.png`
- `evidence/browser-ui-summary.txt`

## Truth result

This is a UI truth-projection improvement, not Mission A closure. The result
is honest:

- `UNKNOWN` opening remains `UNKNOWN`.
- `UNKNOWN` cost remains `UNKNOWN`; zero or missing amount is not rendered as
  free.
- `MOCK != LIVE` remains intact.
- Existing provider-backed official selected Place facts are not copied onto
  a different pending candidate.
- `P7=false`.

## Focused verification

- `npm run typecheck`: PASS.
- `npm run build`: PASS; Vite emitted only the existing large-chunk warning.
- Clean-source browser run: PASS; 18 pending rows rendered, and all 18
  exposed explicit unknown opening/cost text.
- Prior backend focused suite on the immediately preceding backend contract
  checkpoint: `52 passed, 1 warning`; no backend source changed in this round.

## Agent/runtime disclosure

The clean runtime endpoint reported:

- `runtime_identity=NATIVE_DEEPSEEK_TOOL_LOOP`
- `deepseek_configured=true`
- `ai_state=CONFIGURED_UNVERIFIED`
- `hermes_compat_configured=false`
- `hermes_native_gateway.ready=false`

No new Hermes execution is claimed for this UI round. No new DeepSeek action
is claimed beyond the machine-visible runtime status above. Earlier native
DeepSeek evidence remains historical evidence and is not used as authority
for this UI result.

## Replay

1. Check out commit `6e3613b0481e2cdca020849a45e9aff35f0378e4` in the isolated
   worktree and keep `git status --porcelain` empty before starting services.
2. Start the backend on port `8012` against the disposable SQLite database
   named above.
3. Build the frontend and serve the built `dist` on port `4175` with
   `CITYNEXUS_BACKEND_PORT=8012`.
4. Open `/v8/hub`, set `citynexus.v8.journey_id` to the Journey ID above and
   `citynexus.locale` to `zh-CN`.
5. Scroll to `data-testid=pending-set` and read the rendered
   `data-testid=pending-row-facts` sentences. The machine reading must report
   18 rows, 18 unknown opening rows, and 18 unknown cost rows.

## Next bounded experiment

Trace the one provider-mesh candidate that has known facts and the pending
`网师园` candidate by immutable `provider_key + external_id`. Determine whether
the stale known candidate and the current official Place projection are two
observations of one provider entity or separate entities. If they are one
entity, repair the observation-to-public projection boundary by identity, not
by label; if they are distinct, preserve both truth states.
