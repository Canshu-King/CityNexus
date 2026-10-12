# Revolution R74 — Scoped Real-Group Co-Planning Result

## Delivery

- Implementation commit: `2c73c9df50abadb5f1de71d177eb9827e40a1570`
- Starting R74 taskbook commit: `d078d086013918e56530173bb4ba46409662ca99`
- Working branch: `codex/revolution-r63-planned-parallel-journey`
- Push target: `origin/gpt/revolution-r33-open-world-journey-adaptation`

## Product outcome

An OWNER can offer one current collaborator a 24-hour `R73_SHARED_STOP_ONLY` grant tied to the exact R70 invitation and active base PlanVersion. The collaborator accepts or declines under their own signed traveler identity. When a promotion is created, the grant binds to that promotion and the existing collective decision epoch. Revocation, expiry, membership or role changes, and stale plan or invitation context prevent use of the consent.

The grant does not add `JOURNEY_UPDATE` to collaborators. It permits only their own response to the bound shared-stop decision. Generic plan selection, generic replan acceptance, member management, and post-apply replay remain denied. Membership creation, withdrawal, and reads now require a signed in-force member; writes require `MEMBER_MANAGE`, the inviter is server-bound to the authenticated manager, preferences are self-only, and only an OWNER may assign OWNER or ADMIN.

## Focused acceptance evidence

- Signed backend member-surface tests: **2 passed** (`test_r27_member_surface.py`). Covers unsigned and foreign membership writes, self-assigned OWNER, mismatched `invited_by`, unsigned withdrawal, and authenticated membership listing.
- R73 backend tests: **3 passed** (`test_r64_member_side_quest.py -k r73`). Covers no-route fail-closed behavior and a real OWNER/COLLABORATOR/COLLABORATOR collective apply. It also verifies expiry and revocation block a proposal until consent is renewed; two concurrent accepts succeed idempotently and produce one acceptance audit; collaborators cannot use generic select/replan/withdraw, another Journey, premature apply, or post-apply replay.
- Signed multi-context Playwright: **1 passed** using a fresh isolated SQLite database and the repository Python environment. A remained OWNER; B and C remained COLLABORATORs; C was outside the R70 invitation audience but still had to opt in and approve. All three saw the same grounded candidate, and A applied one successor PlanVersion containing the invited Place once while the rendezvous commitment remained on the successor.
- `npm run typecheck`: passed.
- `npm run build`: passed. Vite emitted its existing large-chunk advisory (>500 kB).
- `python -m compileall -q backend/app backend/tests`: passed.
- `git diff --check`: passed.

## Evidence boundary

The browser closure used the explicitly labelled `TEST_REPLAY` route fixture `R73-TEST-REPLAY-EXPLICIT-FIXTURE` with `EXPLICIT_FROZEN_FIXTURE` facts. This proves the signed authorization and shared-plan flow under controlled route evidence; it is not a live-provider or real-GPS result. AgentRun, ProviderCall, and route-acquisition counts were unchanged from the pre-run baseline.

## Test-only boundary

Removed the old `/__test/r73/authorize-members/{journey_id}` helper that promoted test members to OWNER. The retained loopback fixture is only for deterministic opportunity-window and route evidence setup; it does not change member roles or submit member decisions.
