# Revolution R70 — Bring Everyone Here: Result

## Delivered

- A member can review the exact public Place and shared rendezvous details, explicitly invite current Journey companions, and withdraw an open invitation.
- Each invitee sees only invitations addressed to them. Accepting requires that member's signed identity and separate confirmation to disclose/open the exact map pin; it creates that member's own R63 split and R64 Place visit, with the existing R68 navigation handoff.
- Invitations bind the audience, source quest, active plan, rendezvous, and a frozen disclosure snapshot. Expiry, withdrawal, changed context, or recipient removal blocks further responses. A recipient's existing split or visit is never replaced.
- Acceptance and decline are serialized with Journey writes. Decline now validates the invitation state, expiry, and bound context before recording a response.
- SQLite startup migration adds the disclosure snapshot column to existing databases; legacy invitations without a valid snapshot fail closed.

## Verification

- Backend R70 focused tests: **10 passed**.
- Backend R69 focused tests: **5 passed**.
- Authoritative Playwright: **2 passed** (real-seed setup and two-signed-context R70 flow) on fresh isolated SQLite run `r70-f114b776970540a295d350fa7c27a868`; database `backend/_r70-f114b776970540a295d350fa7c27a868.db`.
- Frontend TypeScript typecheck: passed.
- Frontend production build: passed. Vite reports the existing large JavaScript chunk warning.
- Python compileall and `git diff --check`: passed.

The focused tests cover recipient privacy and attribution, independent B-owned state, R65 `UNKNOWN` when location is unavailable, R68 navigation, no shared-plan or agent/guardian side effects, C3/C4 commitments, retries, expiry/withdrawal, stale contexts, and audience changes.
