# CityNexus Revolution R75 — Result

## Delivery

- Local branch: `codex/revolution-r63-planned-parallel-journey`
- Push target: `origin/gpt/revolution-r33-open-world-journey-adaptation`
- Base: `bd49708825f799f67f50de233d5b80f47afa4588`
- Implementation commit: `286235e8ab2d8260e10a2d4c349eda5d8c85212b`
- Scope: an ordinary COLLABORATOR can discover a public Place, invite A, and decide whether to disclose that Place to the current whole Journey. A may sponsor the existing shared-stop proposal only with real `JOURNEY_UPDATE` authority and an accepted invitation. B and C accept their own narrow grants and vote independently; the existing authoritative apply path creates one successor plan.

## What changed

- Added a durable, source-owned group-share receipt bound to the exact invitation, public Place snapshot, inviter split and rendezvous, active plan and cursor, signed member/traveler identity, and sorted current-member audience. The receipt expires after 24 hours. Preview, confirmation, and withdrawal are separate signed actions; confirmation revalidates all three snapshot hashes.
- Gated grant offers, grant responses, promotion creation, collective resolution, and projections on current group-share authority. Before B confirms, C cannot learn the Place or B's private side-quest; after confirmation C sees the public Place but not B's private quest or origin observation. Withdrawal stops future projection and proposals while explaining that previously seen information cannot be unseen.
- Preserved role boundaries. Sharing never adds `JOURNEY_UPDATE`; the sponsor must already hold it and be a signed accepted recipient. B's discovery consent remains separate from B's grant acceptance and vote.
- Added a database-backed active grant slot with a unique partial index for each Journey/invitation/plan/member. Concurrent offer attempts converge on one active grant. Grant binding uses a conditional database update for the whole validated cohort inside a savepoint. Existing SQLite rows receive an additive compatibility migration that retains the newest unexpired grant per scope and preserves older rows as inactive history.
- Scoped the Operator's precise presence projection to the signed viewer's own `journey_member_id`. Background and unsigned projections return unavailable rather than selecting another member's latest location.
- Extended the existing Journey invitation screen with exact audience preview, explicit confirmation, withdrawal, and actionable status text. The browser journey uses normal OWNER/COLLABORATOR roles and does not upgrade members in a test fixture.

## Verification

Commands were run in the repository's configured backend and frontend environments:

```text
backend> .venv\Scripts\python.exe -m pytest tests\test_r64_member_side_quest.py -k "r75 or r73_read_only_collaborator or r73_shared_stop_reuses_collective_authority" -q
9 passed, 43 deselected

backend> .venv\Scripts\python.exe -m pytest tests\test_r74_grant_atomicity.py tests\test_r64_member_side_quest.py -k "r74 or r73" -q
4 passed, 49 deselected

backend> .venv\Scripts\python.exe -m pytest tests\test_grounded_presence.py tests\test_r28_execution_truth.py -q
13 passed

backend> .venv\Scripts\python.exe -m compileall -q app
passed

frontend> npm run typecheck
passed

frontend> npm run build
passed; Vite reported its existing >500 kB chunk-size warning

frontend> npm exec playwright test -- --config=playwright.r73.config.ts
1 passed (16.8s); authoritative isolated R75 journey

git diff --check
passed
```

The browser run was `CITYNEXUS_E2E_RUN_ID=944a9ec280`, frontend `:53825`, backend `:53826`, with a fresh `sqlite:///./_r75_944a9ec280.db`, AI disabled, and `reuseExistingServer=false`. The persisted provenance is in `reports/e2e-provenance/authoritative.json`. A separate SQLite migration smoke check selected the newest unexpired active grant per scope and created the unique index successfully.

## Browser and database evidence

The fresh browser run exercised the real Journey screen from B's discovery and A-only invitation through A's acceptance, B's explicit current-audience review, scoped B/C grant acceptance and separate votes, and A's idempotent promotion apply. Assertions verified that C saw no Place or source quest before consent; after consent C saw the public Place but neither the quest ID nor B's location-observation ID. The Place appears once in the resulting shared itinerary, and B's private side-quest remains separate.

Read-only counts from the run's isolated SQLite database:

| Evidence | Result |
| --- | ---: |
| AgentRuns / AgentRunSteps | 0 / 0 |
| ProviderCalls | 0 |
| GuardianRuns | 1 completed `NO_ACTION`; active plan unchanged |
| GuardianPulses | 1 completed using replay fixture signals |
| Group-share receipts | 1 active |
| Scoped grants | 2 accepted and bound to the promotion |
| Promotions / collective proposals | 1 `APPLIED` / 1 `ACCEPTED` |
| PlanVersions | 2 total: 1 `ACTIVE`, 1 `SUPERSEDED` |
| Bookings / Orders / Transactions | 0 / 0 / 0 |
| Location observations | 1 signed foreground test observation |

The itinerary route and Guardian signals were explicit `TEST_REPLAY`/fixture evidence. No live route provider call, device GPS, or physical-arrival proof occurred. The single location observation was test input for the identity/privacy boundary, not a claim about a person being at the Place.

## Remaining boundaries

- The existing `/members` onboarding path still lets a Journey manager add a member as joined without that target traveler accepting membership. This run used that existing path for C and does not claim invitee-acceptance validation.
- The test establishes the signed collaboration and plan-apply flow against frozen replay evidence; it does not establish live routing, real-world arrival, booking, payment, or model-agent behavior.
