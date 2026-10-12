# Revolution R108 — Private Pocket Walk GO MODE

Date: 2026-10-12  
Branch: `codex/revolution-r63-planned-parallel-journey`  
Scope: R108 only; no R58–R107 historical campaign was rerun.

## Delivered

R108 adds a signed, member-private GO MODE for the saved two-stop Pocket Walk:

- `MemberDraftPocketWalk` now carries a conditional `revision`; refreshing a
  current signed OSM snapshot or changing the ordered pair advances it once and
  clears progress bound to the old snapshot;
- `MemberDraftPocketWalkProgress` stores only the member-scoped state machine,
  ordered shortlist identities, Pocket Walk revision, progress revision, and
  idempotency key. It stores no GPS, provider arrival, route, PlanVersion,
  Guardian, or execution fact;
- the signed GET/POST GO endpoints enforce DRAFT/no-PlanVersion, exact member
  ownership, exact ordered stop identities, Pocket Walk revision, and expected
  progress revision. Duplicate idempotency keys return the same state without a
  second advance; stale revisions fail with a named conflict;
- states are `NOT_STARTED`, `HEADING_TO_FIRST`,
  `FIRST_STOP_DONE_SELF_REPORTED`, `HEADING_TO_SECOND`,
  `WALK_DONE_SELF_REPORTED`, and `PAUSED`. Pause/resume and undo preserve the
  last self-report semantics;
- every response labels the evidence as `USER_REPORTED_PROGRESS` /
  `GO_MODE_USER_REPORTED_PROVEN` and
  `NOT_PHYSICAL_ARRIVAL_PROVEN`. ETA remains `UNKNOWN` unless an existing
  validated walkability fact is present;
- the mobile panel keeps stop navigation and walking map controls separate from
  self-report controls. Identity, Journey, Pocket Walk, and response-generation
  fences prevent a late owner response from appearing in another member's view;
- a controlled 390×844 Chromium flow covers start, reload, destination-only map
  navigation without progress advance, both self-reports, pause/resume, finish,
  undo, collaborator isolation, held-response identity switching, and reset on
  re-save;
- current signed discovery refreshes the same OSM identity in place, preserving
  the shortlist row ID while replacing the snapshot only when its observation is
  not older than the saved one. A two-stop refresh increments the Pocket Walk
  revision once, then resets GO progress.

## Controlled signed A/B evidence

Run: `r108-go-20261012d`  
Viewport: `390x844`, Chromium, signed owner and collaborator  
Frontend: `:45111`  
Backend: `:55111`  
Database: `frontend/../backend/_r108-go-20261012d.db`  
AI: disabled  
Result: **2 passed** (authoritative real-seed plus the R108 GO MODE flow)

The declared loopback city-search and Overpass fixtures supplied three
`TEST_PROVIDER` candidates. The owner saved two in order, started GO MODE,
reloaded, navigated both map controls without advancing state, reported stop 1,
headed to stop 2, paused and resumed, reported completion, and undid the latest
self-report. The collaborator saw an empty private board. A held owner save
response was released after switching to the collaborator bearer and did not
repopulate that member's state. Returning to the owner after a fresh save showed
the Pocket Walk still present with GO progress reset to `NOT_STARTED`.

No real public Overpass request was made; the run stayed within the explicit
loopback `TEST_PROVIDER` boundary and remained `LIVE_BLOCKED` for public data.

## Focused checks

- `py -3.13 -m pytest -q backend/tests/test_r108_pocket_walk_go_mode.py` — **3 passed**.
- `py -3.13 -m pytest -q backend/tests/test_r108_pocket_walk_go_mode.py backend/tests/test_r107_discovery_to_my_pocket_walk.py backend/tests/test_r102_shared_city_outing.py backend/tests/test_r106_human_consented_public_discovery.py` — **31 passed**.
- `npm run test:e2e -- e2e/r108-pocket-walk-go-mode.spec.ts --project=chromium` in the fresh authoritative environment — **2 passed**.
- `npm run typecheck:all` — passed.
- `npm run build` — passed; Vite emitted only its existing large-chunk advisory.
- `py -3.13 -m compileall -q backend/app backend/tests` — passed.
- `git diff --check` — passed.

The broader `py -3.13 -m compileall -q backend` command still reaches the
pre-existing literal `\\n` syntax residue at `backend/run_r39_live.py:305`;
R108 did not alter that historical file.

当前:CityNexus R108 private Pocket Walk GO MODE / signed revision-bound self-report state, A/B isolation, map separation, refresh reset, focused backend tests, authoritative Chromium flow, typecheck and build complete / commit and push this result, then return the exact authorized review handoff to the existing GPT window
