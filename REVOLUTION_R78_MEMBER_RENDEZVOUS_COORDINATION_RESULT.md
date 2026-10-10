# Revolution R78 — Member Rendezvous Coordination Result

**Implementation commit:** `4a8ee7bb0`

**Local branch:** `codex/revolution-r63-planned-parallel-journey`

**Push target:** `origin/gpt/revolution-r33-open-world-journey-adaptation`

## Delivered

An in-force signed Journey member can now explicitly share either `HEADING_TO_RENDEZVOUS` or `NEEDS_COORDINATION` for the exact current shared-plan stop. The consent view names the current audience, states the 45-minute expiry, and explains that GPS origin, observation IDs, private routes, danger, and physical arrival are not being shared or verified. A member can withdraw their own signal. A different signed member can acknowledge one active help request; the durable acknowledgement identifies the responder but does not promise that they will wait at the stop or prove arrival.

Each signal is bound to the signed actor, active PlanVersion, current cursor, server-derived rendezvous Activity and Place, and a SHA-256 digest of the current member audience. Database uniqueness and write-time compare-and-set protect the one-current-signal slot and idempotent retries. A changed audience, plan, cursor, target, expiry, or membership removes the old signal from projections. A new member cannot inherit a previous disclosure; the sender must explicitly share again after reviewing the new audience.

The feature does not invoke route acquisition, location capture, provider calls, Agent, Guardian, Events, PlanVersion changes, bookings, or payments. Signal projections expose only the coarse self-reported state, public stop, attribution, timestamps, and signed acknowledgement.

## Focused verification

All focused commands below completed with exit code 0.

- Backend: `backend\.venv\Scripts\python.exe -m pytest tests\test_r76_journey_membership_invitation.py tests\test_r78_member_rendezvous_coordination.py -q` — **10 passed**.
- Frontend: `npm run typecheck:all` — passed.
- Frontend: `npm run build` — passed. Vite emitted its large-chunk advisory; the build completed.
- Python: `backend\.venv\Scripts\python.exe -m compileall -q app` — passed.
- Diff: `git diff --check` — passed.
- Authoritative E2E: `e2e/r78-member-rendezvous-coordination.spec.ts`, Chromium, `--project=chromium --no-deps` — **1 passed** (`r78-e2e-20261009b`, frontend `18785`, backend `18786`, AI disabled, fresh isolated SQLite).

The browser scenario exercised signed owner, existing companion, new member, and later-added member views. It checked explicit confirmation and cancellation, audience visibility, re-sharing after membership changes, withdrawal, help acknowledgement across reload, and absence of location or route POSTs. The operator projection contained no latitude, longitude, location-observation ID, or route geometry. Focused backend coverage also checks concurrent idempotent submission, stale-audience rejection, expiry, one-active-row uniqueness, forged member fields, and unchanged plan/cursor and side-effect counters.

## Isolated database evidence

For `r78-e2e-20261009b`, the authoritative run reported its own run ID, database filename, Python executable, ports, and disabled AI state. Database counts after the browser scenario:

| Table / effect | Count |
| --- | ---: |
| PlanVersion (demo initialization only) | 1 |
| Journey rendezvous signals | 3: 1 `STALE`, 1 `REVOKED` heading status, 1 `REVOKED` help request |
| Signed help acknowledgements | 1 |
| Location observations | 0 |
| Route acquisition operations | 0 |
| Provider calls | 0 |
| Agent runs | 0 |
| Guardian runs / pulses | 0 / 0 |
| Events | 0 |
| Bookings / transactions | 0 / 0 |

These are local deterministic test identities and an isolated database. They do not establish production identity-provider behavior, live location, real provider behavior, physical co-location, or arrival.

## Verification note

One exploratory combined pytest invocation also selected the existing `test_r57_group_presence_operator.py` module, which contains historical R57/R58 cases. Its 15 failures stopped at their unsigned legacy `plan/select` setup receiving `401`; the focused R76+R78 rerun passed all 10 tests. Those legacy cases were not modified as part of R78.
