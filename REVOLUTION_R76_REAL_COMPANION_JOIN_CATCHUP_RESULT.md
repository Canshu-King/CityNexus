# CityNexus Revolution R76 — Result

## Delivery

- Local branch: `codex/revolution-r63-planned-parallel-journey`
- Push target: `origin/gpt/revolution-r33-open-world-journey-adaptation`
- Base: `9cc513850cabe9b2201226ec18bf115f79a96b02`
- Implementation commit: `e8b6321e88fcfbe51545b73b2f9dbf9974d67852`
- Scope: an existing signed-in traveler can receive a private invitation to an active Journey, decide whether to join, and reach the current shared Journey without being granted an invented route or arrival claim.

## What changed

- Added durable, 24-hour Journey membership invitations with idempotency, one pending invitation per traveler and Journey, manager authorization, and a bounded recipient inbox. Only the invited traveler can accept or decline. Acceptance creates one `COLLABORATOR` membership and its audit receipt in the same database transaction.
- Closed the signed-mode direct-add path with `RECIPIENT_ACCEPTANCE_REQUIRED`. A manager cannot mark another traveler as already joined.
- Integrated manager invite and recipient inbox/decision controls into the normal Journey experience. After acceptance the companion enters the active Journey and sees its current shared rendezvous. A route is only requested with deliberate private-origin consent; when no eligible route evidence exists, the UI says `UNKNOWN / ROUTE_UNAVAILABLE`.
- Made stale sharing explicit: when the historical addressed member set differs from the current audience, R75 returns `AUDIENCE_CHANGED` and requires the source traveler to review the expanded audience.
- In the membership-accept transaction, mark active R73 shared-stop promotions and their decision envelopes stale, invalidate any associated collective authority receipt, and revoke outstanding R74 scoped grants. The existing votes remain historical evidence but cannot be replayed or applied. The R73 response endpoint now rejects stale decisions before treating an old duplicate vote as successful.

## Verification

Commands run in the configured backend and frontend environments:

```text
backend> .venv\Scripts\python.exe -m pytest tests\test_r75_group_share_reconsent.py -q
3 passed

backend> .venv\Scripts\python.exe -m pytest tests\test_r64_member_side_quest.py -k r75 -q
7 passed, 45 deselected

backend> .venv\Scripts\python.exe -m pytest tests\test_r27_member_surface.py tests\test_r76_journey_membership_invitation.py -q
7 passed

backend> .venv\Scripts\python.exe -m pytest tests\test_r64_member_side_quest.py -k test_r73_shared_stop_reuses_collective_authority_and_applies_one_real_successor -q
1 passed, 51 deselected

backend> .venv\Scripts\python.exe -m compileall -q app
passed

frontend> npm run typecheck:all
passed

frontend> npm run build
passed; Vite reported its existing >500 kB chunk-size warning

frontend> npx playwright test e2e/r76-companion-join-catchup.spec.ts --project=chromium --no-deps --grep "R76 lets a signed nonmember"
1 passed; authoritative isolated run `r76_7ec87a0b85`

git diff --check
passed
```

The authoritative browser run owned frontend `:63296` and backend `:63297`, used a fresh `backend/_r76_7ec87a0b85.db`, disabled AI, and did not reuse an existing server. Its provenance is recorded in `reports/e2e-provenance/authoritative.json`.

## Browser and database evidence

The isolated browser flow used the real Journey interface. It verified that the target was absent from the member set before acceptance, the legacy direct-add API refused, the signed nonmember could see only the bounded invitation fields, and only the target's acceptance added one `COLLABORATOR`. The companion then entered the ordinary Journey view and saw the honest no-route state. Duplicate acceptance returned `409` and did not add a second membership.

Read-only counts from the run's SQLite database:

| Evidence | Result |
| --- | ---: |
| Membership invitations | 1 `ACCEPTED` |
| Accepted member | 1 `COLLABORATOR`, non-null `joined_at` |
| Acceptance audit for that invitation | 1 |
| Journey members / PlanVersions | 2 / 1 |
| AgentRuns / ProviderCalls / GuardianRuns | 0 / 0 / 0 |
| Bookings / Orders / Transactions | 0 / 0 / 0 |

The R76 backend integration also seeded an old A+B R73 decision envelope and accepted R74 grant in SQLite, accepted C's Journey invitation, and verified the promotion and grant became stale/revoked in that transaction. Replaying either old vote and attempting to apply the old promotion returned `409`; the active PlanVersion stayed unchanged.

The browser used trusted test-issued signed traveler tokens, not a production identity-provider login. No live route provider, device GPS, physical arrival, or live navigation was verified. The visible `UNKNOWN / ROUTE_UNAVAILABLE` state is the tested result when qualifying route evidence is absent.
