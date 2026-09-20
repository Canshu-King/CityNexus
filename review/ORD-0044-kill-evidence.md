# ORD-0044 — kill evidence and measured envelopes

Lane `e345b9d6` (M3-B / M3-C). Tree `_qoder_ui_overnight_20260920`, branch
`agent/ui-overnight-20260920`. Commits: `26d5555`, `5feaa83` (core), `4516777` (the three
refinements), `ca65483` (gates frozen on the measured envelope).

Driver: `review/ord0044_kill_drivers.py`. One mutant per named node, each mutant of that
node's own shape, baseline restored from `git show HEAD:<path>` and verified by sha1 after
every case (`restored … OK` on all nine rows below). Table: `review/ord44-kill-table.txt`,
per-case logs: `review/kill44-*.log`.

## 1. The mutants

| # | mutant (one defect each) | node it must name | result |
|---|---|---|---|
| a | `createJourney` throws right after the journey row is written (the observed stall shape) | `legal-window-create-advances` | KILLED |
| b | success path never calls `setSetupOpen(false)` — shell stays shut behind a live journey | `legal-window-create-advances` | KILLED |
| c | `step1Ready` ignores the anchor fields | `missing-anchor-is-named-before-submit` | KILLED |
| d | drop the `message={message}` prop (the ORD-0034 gap) | `a 500 stays silent` + `named reason inside trial-create-error` + `backend-reason-lands-on-its-own-field` | KILLED (3 nodes) |
| e | arrival input stops declaring `aria-required` | `missing-anchor-is-named-before-submit` | KILLED |
| f | arrival input's `aria-describedby` no longer points at the visible reason | `missing-anchor-is-named-before-submit` | KILLED |
| g | review page renders a blank anchor as `—` again | `review-page-says-missing-anchor-is-required` | KILLED |
| h | `fieldProblem` stops routing by `loc` (`/.*/` for both fields) | `backend-reason-lands-on-its-own-field` | KILLED |
| i | the client stops stating the status it can honestly know | `a 500 stays silent` | KILLED |

Red messages, as rendered (not derived):

```
a  :: legal-window-create-advances — a legal 4-day trip never reached the app: the create stopped after the journey row was written
c  :: missing-anchor-is-named-before-submit — the anchor fields are required by the API but the wizard gives no reason for the blocked Next
e  :: missing-anchor-is-named-before-submit — trial-arrival is required by the API but does not say so
f  :: missing-anchor-is-named-before-submit — trial-arrival is blocked as required but is not tied to the visible reason
g  :: review-page-says-missing-anchor-is-required — review-arrival renders "— · 2026-09-21 10:00" in en; a bare "—" reads as an acceptable blank
h  :: backend-reason-lands-on-its-own-field — a complaint about the arrival anchor was smeared onto the departure field too
i  :: a 500 stays silent — the notice hides the only fact the server actually sent
```

## 2. Correction to my own instrument, recorded here

The first version of refinement (1b) put the "no bare dash on the review page" check at the
end of `missing-anchor-is-named-before-submit`, after the fields had been filled in. That
assertion could not fail: the gate in the same node makes a blank anchor unreachable on the
review page, so no mutant of the `—` wording could ever turn it red — a pass that proves
nothing, reported as a pass.

It is now its own node, `review-page-says-missing-anchor-is-required`, driven through the
path a blank anchor can genuinely take: the wizard's own persisted draft (ORD-0036 d)
restores step 3 with the anchors empty, which is the last honest signal before submit. Both
language arms are run, because the wording is locale-picked, and the rendered text is
recorded:

```json
{"en.review-arrival": "not filled in · required · 2026-09-21 10:00",
 "en.review-departure": "not filled in · required · 2026-09-23 20:00",
 "zh-CN.review-arrival": "未填写 · 必填 · 2026-09-21 10:00",
 "zh-CN.review-departure": "未填写 · 必填 · 2026-09-23 20:00"}
```

Mutant `g` proves the node can fail.

## 3. The envelope the gates are frozen on (`review/probe-envelope.py`)

The ledger froze "the envelope that really arrives". Measured against this tree's backend,
not assumed:

```
unhandled exception (starlette 1.6.0, app registers handlers only for
  RequestValidationError and HTTPException — main.py:395, :406):
    status 500 · content-type text/plain; charset=utf-8 · body "Internal Server Error"
    carries the raised code text? False
blank anchor location → POST /api/v1/journeys:
    422 {"error":{"code":"VALIDATION_ERROR","message":"Request validation failed",
        "trace_id":"…","details":{"errors":[{"loc":["body","arrival_anchor","location"],
        "msg":"String should have at least 1 character","type":"string_too_short"}]}}}
9-day window → POST /api/v1/journeys: 201 (no entry gate in this tree — ORD-0033's gate is
    in the authoritative backend, this lane's `backend/app/**` is untouched)
9-day window → POST …/stay-options/generate:
    500 text/plain "Internal Server Error" in 0.01s, carries V13_JOURNEY_DAYS_OUT_OF_BOUNDS: False
```

Consequence, and it is a defect in my own gate: `qoder-onboarding-failure.spec.ts`'s first
node mocked `{"detail":"V13_JOURNEY_DAYS_OUT_OF_BOUNDS:9"}` on `POST /api/v1/journeys`. That
is the string the server *raises* (`backend/app/core/temporal.py:37`), not what a client can
ever receive: an escaping `ValueError` leaves the process as plain-text `Internal Server
Error`, and the raise site (`stay_mobility.py:201`) is on the generate call, not on create.
The node now serves the measured 500 and asserts both halves of the honest statement — the
notice must name the status it did receive, and must not name a reason the server never sent
(`ca65483`). The 422 node already reads the generic `VALIDATION_ERROR` envelope with
`details.errors[].loc/msg`.

## 4. `GET /twin` 39–40 calls per visit: designed polling, not a loop

`review/count-twin-polls.mjs`, real routes, 75 s per route, counting network requests:

```
/v8/hub : 6 twin calls out of 13 API calls in 75s
/v8/live: 6 twin calls out of 20 API calls in 75s
```

6 in 75 s is one initial fetch plus a 15 s interval — `refetchInterval: 15_000` at
`src/api/v12Authoritative.ts:45`. 39–40 calls is therefore ≈8 minutes of one page left
open, not a re-entry loop and not the service worker re-driving `load()`. No change made;
this is the answer to the question, with its denominator.
