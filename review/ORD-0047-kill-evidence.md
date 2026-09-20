# ORD-0047 — the 115-second wait, made honest

Lane `e345b9d6` (M3-B / M3-C). Tree `_qoder_ui_overnight_20260920`. Commits `74a38bf`
(the waiting experience), `58d808b` (Today's three faces, each with its own test id), plus
the outcome-aware empty-state copy that consumes ORD-0049's `generation.outcome`.

Scope as re-ruled by arbitration `5749041556`: the 115 s itself and the empty first page
belong to the backend (ORD-0049, `8c66aa92`). This lane owns only what the traveller sees
while waiting, and what a zero-result answer looks like when it arrives. Nothing here
lengthens a timeout, disables a real call, or touches the optimiser.

## 1. What the screen says now

| moment | before | after |
|---|---|---|
| t=0 … t=115s after 确认创建 | nothing at all; the button looked idle, so the traveller tapped again | `正在搜索住宿 · 已等待 N 秒`, phase named only from the list of stages actually awaited, plus a note that the server reports nothing mid-flight |
| giving up | not possible | `停止等待` aborts **this browser's** request and says so plainly: the search may still be running server-side, nothing you typed is lost |
| `200` with `top_k: []` | Today, as if the trip were simply fine | a named empty block on Today with a retry, the attempt count, and the reason the server reported |
| `500` from the search | "no journey was created" (false: the row exists) | "the trip was created, the stay search did not finish" |

Why "stop" and not "cancel": `POST /api/v1/journeys/{id}/stay-options/generate`
(`backend/app/main.py:2386`) is a synchronous route with no `operation_id`, no job table and
no cancel endpoint (the only `cancel` route in the file is `POST /api/v1/bookings/{id}/cancel`).
Aborting the fetch closes the traveller's eyes, not the server's work, so the UI says exactly
that.

## 2. Kill evidence — `review/ord0047_kill_drivers.py`, table in `review/ord47-kill-table.txt`

One mutant per named node, each a defect of that node's own shape; baseline restored from
`git show HEAD:<path>` and re-verified by sha1 after every case.

| # | mutant | node | result |
|---|---|---|---|
| a | the waiting block is removed from the wizard | `gen-wait-phase-stays-visible` | KILLED — "no waiting block appeared for en" |
| b | the clock is frozen at 0 | `gen-wait-phase-stays-visible` | KILLED — "the waiting number never advanced ([0,0,0,0,0,0,0,0,0,0,0,0])" |
| c | `停止等待` sets a flag but never aborts | `gen-wait-stop-waiting-aborts` | KILLED — "after stopping, the screen said nothing about what just happened" |
| d | `top_k.length === 0` counted as success | `gen-empty-options-is-not-success` | KILLED — "zero stay options were presented as an ordinary Today" |
| e | a refused search borrows the empty face | `gen-three-states-distinguishable` | KILLED — "a refused retry from Today rendered no state at all" |
| f | the failure notice denies a trip whose row exists | `gen-three-states-distinguishable` | KILLED — "the notice denies a journey that exists: …no journey was created. Request failed (500)" |
| g | the cause the server reported is thrown away | `gen-empty-reason-comes-from-the-server` | KILLED — "the server named the providers and the screen said something else" |
| h | a silence is filled with a cause nobody reported | `gen-empty-reason-comes-from-the-server` | KILLED — "the screen blamed the providers without being told to" |

Tables: `review/ord47-kill-table.txt` (a–f) and `review/ord47-kill-table-gh.txt` (g–h);
per-case logs `review/kill47-*.log`. All eight restored their file to the HEAD baseline by
sha1 after the run.

## 3. Instrument corrections found while writing these gates

- `gen-wait-stop-waiting-aborts` first asserted `trial-city` still held its value. `trial-city`
  is a step-1 field and the traveller is on step 3, so the assertion was checking an element
  that is legitimately absent. It now asserts the survived state where a traveller meets it:
  still on step 3, the review row still showing the city, and both typed values intact after
  walking back.
- The shared `hub-stay-search` test id served two different faces (searching and refused). A
  locator on it races its own `data-stay-search` attribute, which produced a red that read
  "expected failed, received searching" — a harness artefact, not a product state. Each face
  now has its own test id.
- The delayed mock answered routes the traveller had already abandoned, and Playwright threw
  `Route is already handled`, stranding the next state. The handler now catches that, so an
  abandoned request stays abandoned.

## 4. The 114.98 s → 2.52 s question

Requirement 3 asked what the difference is. It is not this lane's measurement to make and I
did not pretend otherwise: `8c66aa92` delivered ORD-0049 with segment timing in-tree
(`CITYNEXUS_PROVIDER_TIMING=1`), and the answer is the provider chain -- one attempt spent
77 930 ms in Overpass (three mirrors in series, one HTTPStatusError and two ReadTimeouts)
plus 42 153 ms in Nominatim, which was 99.999 % of that request's wall time, while the
application-side work (nodes, legs, solve) measured ~60 ms. So the cold number is remote I/O
retried in series, not optimiser warm-up, and the fast repeat is the same calls meeting a
warmer provider path. Nothing in this lane changes any of it; the frontend half is that the
wait is now named, counted and stoppable, and that its empty outcome is drawn as empty.
The two numbers stay in different columns: they are API operation latencies, and document
navigation latency was not measured here.

One caveat to hold this lane to: I could not verify the `generation.outcome` names from any
tree I can reach -- `D:\moodle\CityNexus` sits at `a9c2504` and has no such enum, and
`e981b46` is not in that object store. `stayOutcomeLine` therefore maps the four names as
written in the ORD-0049 delivery, and **anything unrecognised falls back to "nothing came
back, and no reason was given"** -- including the case where the field turns out to be named
differently. Mutant `g` proves the fallback cannot quietly pass for a reported reason, and
mutant `h` proves a silence cannot be dressed as one.
