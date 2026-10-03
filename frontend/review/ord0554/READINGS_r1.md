# ORD-0554 · `/v8/live` English-arm caps census · lane a68b0631

Base commit: `ccfd11c034e94c871af168b0429417debe2dae52` (authoritative line at the time these
readings were taken; every `path:line` below was re-read from that commit, not carried over).

## Judgement

The order decides each painted all-caps word by one test: *can the word be grepped as an upstream
vocabulary name in `backend/app/`?* That test matches letters, not sources. Two of the named words
do have same-named server literals:

- `NEXT` -- `backend/app/operations/v9.py:96` (`EDGE_ALLOWED_ACTIONS`) and `backend/app/schemas.py:432`
  (`action: Literal[...]`)
- `LIVE` -- `backend/app/integrations/china/amap.py:51` (`provenance="LIVE"`) and one comment in
  `backend/app/replanning/provider_snapshots.py:65`

and five do not (`NAVIGATE`, `RISK`, `CLOCK`, `CURRENT`, `OFFLINE`: 0 quoted literals in `backend/app/`).

The source test says something different. Every caps word painted on this screen comes out of the
shipped English dictionary, requested by name through `t("<key>")`, and its Chinese counterpart is
translated rather than repeated:

| painted word | dictionary key | en entry | zh entry | painted by |
| --- | --- | --- | --- | --- |
| NEXT | `live.nextLeg` / `live.nextSelect` / `live.leaveBy` | `src/i18n/LocaleContext.tsx:291` / `:292` / `:297` | `:1380` / `:1381` / `:1386` | `src/app/V8Experience.tsx:3653`, `:3667`, `:3773` |
| LEAVE | `live.leaveBy` | `src/i18n/LocaleContext.tsx:297` | `:1386` | `src/app/V8Experience.tsx:3773` |
| NAVIGATE | `live.navigate` | `src/i18n/LocaleContext.tsx:304` | `:1393` | `src/app/V8Experience.tsx:3802` |
| RISK | `live.risk` | `src/i18n/LocaleContext.tsx:305` | `:1394` | `src/app/V8Experience.tsx:3806` |
| ROUTE | `live.routeEvidence` | `src/i18n/LocaleContext.tsx:310` | `:1399` | `src/app/V8Experience.tsx:3822` |
| STATUS | `exec.liveStatus` | `src/i18n/LocaleContext.tsx:574` | `:1649` | `src/features/execution/V10LiveExecutionPanel.tsx:51` |
| LIVE | `exec.liveStatus` / `exec.liveJourneyPrefix` | `src/i18n/LocaleContext.tsx:574` / `:620` | `:1649` / `:1695` | `src/features/execution/V10LiveExecutionPanel.tsx:51` |
| CLOCK | `exec.clock` | `src/i18n/LocaleContext.tsx:577` | `:1652` | `src/features/execution/V10LiveExecutionPanel.tsx:61` |
| CURRENT | `exec.currentStep` | `src/i18n/LocaleContext.tsx:579` | `:1654` | `src/features/execution/V10LiveExecutionPanel.tsx:74` |
| STEP | `exec.currentStep` | `src/i18n/LocaleContext.tsx:579` | `:1654` | `src/features/execution/V10LiveExecutionPanel.tsx:74` |
| OFFLINE | `exec.offline` | `src/i18n/LocaleContext.tsx:583` | `:1658` | `src/features/execution/V10LiveExecutionPanel.tsx:82` |
| EVIDENCE | `live.evidence` / `live.routeEvidence` | `src/i18n/LocaleContext.tsx:308` / `:310` | `:1397` / `:1399` | `src/app/V8Experience.tsx:3818`, `:3822` |
| NOW | `live.now` / `exec.now` | `src/i18n/LocaleContext.tsx:273` / `:595` | `:1370` / `:1670` | `src/app/V8Experience.tsx:3629` |
| ETA | `live.eta` | `src/i18n/LocaleContext.tsx:300` | `:1389` | `src/app/V8Experience.tsx:3793` |
| LOW | `live.routeCurrent` | `src/i18n/LocaleContext.tsx:307` | `:1396` | `src/app/V8Experience.tsx:3812` |
| WGS84 | -- (not a label) | -- | -- | the map caption's coordinate-system read-back, a data value |

So `NEXT` and `LIVE` are **local style words that happen to share letters with a server enum**, not
server enums painted through. The screen's own transport never reaches a label slot: the A3 arm put
one distinct sentinel into each of 12 enum-shaped fields of the real `/experience` answer and none
of them painted (5 further fields -- `activities[].cost_status`, `disruptions[].type/severity/status`,
`supply.state` -- are absent from this journey's answer and are recorded NOT_PROBED rather than
counted as clean).

Product bytes changed by this hand: none. The words the order asked to keep are kept, and the
guard that keeps them is new.

## Arms

`frontend/e2e/qoder-a68b0631-ord0554-live-caps-r1.spec.ts`, run on the production build chain
(`playwright.prod-gate.config.ts`: `npm run build` + `vite preview` + the lane's own backend on a
throwaway `data/_guard_<epoch>.db`, fresh `CITYNEXUS_E2E_RUN_ID` per attempt):

- A1 `[en]` -- census of 16 painted caps words, each attributed to a dictionary key with its request
  site; positive control is the four panel words (`LIVE`, `CLOCK`, `CURRENT`, `OFFLINE`) having to
  paint, so an empty screen cannot pass. Green.
- A2 `[zh-CN]` -- same screen, one language: no label word of the live modules paints, and the four
  Chinese labels the arm reads out of the zh dictionary itself do. Green.
- A3 -- sentinel rewrite of the real answer in flight, one distinct sentinel per enum-shaped field:
  17 declared, 12 probed, 0 painted raw. Green.
- CA1 (counter-arm) -- `V10LiveExecutionPanel.tsx` clock slot made to paint `plan?.status` (a real
  server field) directly: A3 goes red naming exactly `active_plan.status`. Restored, disk bytes equal
  to the pinned blob.
- CA2 (counter-arm) -- the zh dictionary entry for `exec.clock` given the English word
  ("CLOCK 时钟"): A2 goes red naming `CLOCK`. Restored, disk bytes equal to the pinned blob.

## Instrument defect found and fixed while taking these readings

The first pass of A1 was red on `LEAVE`, `ROUTE`, `LIVE`, `STATUS`, `CURRENT`, `STEP`, and the cause
was mine: the dictionary parser's key class was `[a-z0-9_.]+`, which reads 260 of the 938 English
keys and silently treats the other 678 -- every camelCase key -- as "not authored here". A ruler
that can only fail to find an author can only invent dirty words, so it was a one-sided instrument,
not a product finding. The readings from that pass are preserved as
`a1_en_census_sourced_r1_first_pass_ruler_bug.json` rather than deleted, and the arm now carries a
named self-check (`exec.liveStatus` must parse) so the same blindness cannot pass quietly.

## Channels, stated

- Front end: the built bundle served by `vite preview` on this lane's own port (prod-gate harness).
- Journey: the harness's own `real-seed` setup project, which establishes the journey through the
  product API -- that setup calls `POST /api/v1/demo/reset` once, against this lane's throwaway
  database, and no other. `demo/reset` was not called against the shared preview store, and no
  `_preview.db` write was made.
- A1/A2 read the product's real answers. A3 rewrites the real `/experience` answer in flight; it
  can decide *which of the product's two word sources put a word on screen*, and cannot decide what
  a live provider would answer.
