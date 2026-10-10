# Revolution R69 — Rendezvous Handshake: Meet, Acknowledge, Continue

## Why this is the next Revolution capability

R63–R68 now cover an extraordinary real-world loop:

- R63 planned temporary separation from a shared Journey;
- R64 member-private stop execution;
- R65 timebox + member-owned return action;
- R66/R67 known and opt-in live OpenStreetMap place discovery;
- R68 consented exact walking-navigation handoff to the chosen private stop and then the **shared** rendezvous.

**The unfinished user story:** A navigates to the meeting point, sees their friends, and wants to tell CityNexus “I'm here; we're back together.” Today R63 can end a planned split unilaterally by an owner command, and R62 can collect authenticated arrival confirmations for an **applied group recovery**, but the ordinary, non-recovery R63 side-trip has no peer-visible, countersigned rendezvous handoff.

R69 should give that real everyday group moment a product surface:

> "I'm at our meeting point." → "Alice says she's here." → "Yes, I'm with Alice." → "Your planned split has ended; the shared Journey continues."

This is **user-action coordination**, not a location verifier or another Guardian/recovery system. Avoid spending the strike writing verification machinery or a generic messaging platform.

## Exact starting point

Branch: `gpt/revolution-r33-open-world-journey-adaptation`.

- Codex R68 implementation SHA: `4ac0f05748f94b808c00b8266cdd1450fb04123b`.
- GPT R68 post-review fixes immediately after the implementation:
  - `ecd22a928215fc5b5dbd34a4943e2c4116841a5e` uses official Google Maps URL fields (`destination`, `travelmode=walking`, `dir_action=navigate`), removes undocumented `destination_label`;
  - `df1691b91493755c4eee4daf5eecfe9b7c703300` updates Playwright URL assertions;
  - `3ae2801cc91fdb0f454202ae06f1044c883fe998` makes map-location privacy copy match the actual link.
- The Maps URL rules were checked against the current official Google Maps URLs documentation and OSM wiki. The exact WGS84 pin remains server-selected; the user's origin remains omitted.
- GPT edits are committed but **not locally verified by GPT**. Run direct R68 focused frontend/typecheck once, fix actual regressions, then implement R69.
- R68 implements an owner-only `GET /journeys/{id}/member-side-quests/{id}/navigation-targets`. Its browser E2E intercepts external Maps; no physical phone journey is proven.
- Checked R68 implementation did not include a fresh GitHub CI status or an independent R68 result file. The existing `reports/e2e-provenance/authoritative.json` still referred to R67. Do not invent a result or create a verifier loop.

## Existing systems — reuse instead of cloning

1. `backend/app/execution/group_presence.py`: `planned_separation_for_member`, `rendezvous_target`, and owner-bound current split semantics; one authoritative PlanVersion.
2. `backend/app/execution/member_side_quest.py`: durable quest state and `MemberSideQuestReturnReport`, `_active_split`, `_current_binding_matches`, `invalidate_member_side_quests_for_intents`, and owner/non-owner projection.
3. `backend/app/main.py`: `_run_planned_separation_command(..., action="END")` currently closes only the acting **member's** split, sets `physical_reunion_claimed: false`, and invalidates its side quests. Extract/share this **scoped** end-of-split operation if necessary, but never make another member's generic command silently spend A's authority.
4. `backend/app/execution/group_recovery_followthrough.py` and `backend/app/main.py` around group recovery execution: R62 already has a **recovery-only** group rejoin process. R69 must **not** interfere with an active recovery followthrough or claim to close a recovery incident.
5. `frontend/src/features/execution/MemberSideQuestCard.tsx`: after `COMPLETED/CANCELLED`, the owner sees navigation back and explicit head-back. Add the third **"I'm at our meetup"** action here.
6. `frontend/src/features/execution/LiveRecovery.tsx`: Journey group-presence surface. A current peer sees a small incoming meetup request there and can respond with their **own authenticated principal**.

## The new user experience

### A. Returning member reports arrival

For a member with an **active, current R63 split** and latest R64 private quest `COMPLETED/CANCELLED`:

- Show `I'm at our meeting point` / `我已到共同会合点`.
- The member explicitly confirms: `I'm reporting that I reached the exact shared rendezvous. This is my report, not GPS/device proof.`
- Server records one durable, member-owned **MEETUP_REPORTED** request bound to:
  - journey_id;
  - owner_member_id and authenticated traveler id;
  - active PlanVersion id;
  - exact R63 planned separation intent id;
  - exact shared rendezvous activity/place id;
  - current latest R64 quest id;
  - timestamp and short expiration (e.g. 30 min).
- No foreign or expired member can submit this. No freeform client-supplied member id, coordinates, activity id, PlanVersion or target.
- Do not automatically close R63 on A's report. Return a visible `Awaiting a travel companion's acknowledgement` state.
- Reporting is **not** device-verified presence; optional one-time consented location may be used as advisory context but is never required or silently shared.

### B. Companion acknowledges actual meeting

An in-force **different** member B viewing the **same shared Journey** sees:

`Alice says she's at [shared rendezvous]. Are you together?`

Two explicit actions:

1. `Yes, we're together` — B states, using B's own signed identity, that B has actually met A. This **countersigns a user-reported co-presence claim**; it does not become `physical_presence_verified=true`.
2. `Not yet / Can't confirm` — B does not affirm. Leave A's split current, reflect coarse actionable `not yet acknowledged` status, and keep the map return action. An unanswered request simply remains pending until expiry. Do not coerce acknowledgement.

When B confirms, atomically:
- revalidate B's current Journey membership and that B != A;
- revalidate A still in force and the same current R63 split, same latest R64 quest and active plan/rendezvous, nonterminal rendezvous, and fresh pending meetup request;
- persist B's acknowledgement as a signed user execution/report receipt;
- end **only A's** planned separation using the existing R63 lifecycle semantics;
- invalidate A's private quest execution as required by R63 without erasing its history;
- publish `USER_REPORTED_REJOIN_ACKNOWLEDGED` / `PLANNED_SPLIT_ENDED` as owner/group-safe historical feedback;
- do not mutate shared Activity, create a PlanVersion, insert a proposal, close a recovery incident or mark the entire group physically together.

For Journeys with 3+ people, **one** current co-member acknowledgement is enough to close **A's own planned separation**, but **not** enough to claim that all members of the Journey are together. Existing group presence/real location evidence remains authoritative for group cohesion.

### C. Return to normal shared Journey

Owner sees:

`You and [companion] reported meeting at [shared rendezvous]. Your planned side trip ended; the shared Journey can continue.`

Companion sees an equivalent coarse success state. This should survive browser refresh through a small durable history/read projection; don't let the success message disappear immediately when the split becomes inactive.

Crucial language boundary:

- `MEETUP_REPORTED` = A personally reported arriving.
- `PEER_ACKNOWLEDGED` = B personally reported they met A.
- `PLANNED_SPLIT_ENDED` = product no longer considers A's temporary planned separation active.
- **None** of these are device-certified physical co-location, actual arrival proof, or an all-group reconciliation guarantee.
- Use “we both reported meeting” instead of “the system verified you are together.”

### D. Edge cases must be product-resolved

- No active peer (e.g. single-member Journey): explain there's nobody to confirm. Preserve R63's existing explicit own-end action; do not fabricate B.
- A reports then changes personal destination/starts another quest: pending meetup expires or invalidates. B cannot spend the old request.
- PlanVersion/rendezvous drift or terminal activity: pending request becomes stale; display a re-grounding action, never silently move it.
- One of A/B is removed, expired or no longer current: reject. A's prior history remains honest.
- Repeated owner report and double acknowledgement are idempotent (or conflict-safe), without duplicate termination/audit side effects.
- If B declines, A can still navigate to rendezvous and try again with a deliberate new request; no automatic polling/Agent calls.
- If **R62 recovery followthrough** is active and still waiting for group member arrivals, direct users to the existing recovery-arrival flow rather than closing anything through R69.
- Never end the split on a map click, route ETA, R65 `HEAD_BACK` report or ordinary browser location alone.

## Data, API and privacy guidance

Use a small durable `PlannedSplitMeetupHandshake` / `MemberRendezvousCheckIn` with a tight state machine, e.g.:

`PENDING`, `PEER_ACKNOWLEDGED`, `NOT_CONFIRMED`, `EXPIRED`, `INVALIDATED`.

Suggested product endpoints (adapt to existing style):

- `POST /journeys/{id}/member-side-quests/{quest_id}/meetup-report` — signed owner.
- `GET /journeys/{id}/meetup-handshakes/current` — viewer-specific, public-safe projection; no private destination.
- `POST /journeys/{id}/meetup-handshakes/{handshake_id}/acknowledge` — signed other member.
- `POST /journeys/{id}/meetup-handshakes/{handshake_id}/not-yet` — explicit nonconfirmation.
- Optionally `POST .../withdraw` by A.

Use existing DB concurrency/idempotency patterns; do **not** rely solely on an in-process lock for state transitions or multiple concurrent acknowledgements. Avoid a separate events framework.

Public-safe peer projection may contain A's display name, shared rendezvous, current report/acknowledgement state and expiry; it **must not** include A's private stop Place, exact private route geometry, private interest/OSM candidates or member current coordinates. A signed partner's acknowledgement should not cause new geolocation permission prompts.

No generic `journey/agent` command from B may impersonate A to close the split. If reusing the END code, factor a narrow internal operation whose actor is explicitly B's permitted acknowledgement over the exact current handshake, with A's scoped split as target.

Avoid storing private meetup details in generic globally readable audit after bodies. Server audit can record only safe member ids, action/status, exact **shared** rendezvous and source, not the private side destination.

## One bounded real product flow

In a fresh isolated SQLite DB using 2 normal signed members:

1. Start one shared Journey + one active PlanVersion.
2. A's R63 split → A's exact R64 stop (can be selected via existing R66/R67) → R68 navigation target from owner-only API.
3. A completes/cancels R64, optionally reports R65 HEAD_BACK (but not required).
4. A taps `I'm at our meetup`; B sees an accurate self-reported pending request; the owner sees waiting state.
5. B taps `Yes, we're together` via authenticated product API.
6. A's **specific** R63 planned split ends; A's prior private stop remains durable history; active shared PlanVersion/cursor unchanged.
7. Both members see truthful user-reported acknowledgement feedback; B never receives A's private Place or link.
8. A can resume group Journey without a leftover planned-split warning. Existing R62 recovery gate is unchanged.

The product boundary is completed through real member UI/API writes, **not** a manually injected row, and no external Agent/provider/physical visit needs to succeed.

## Focused tests only

Backend:
- Correct owner report; spoofed owner/foreign journey/id denied.
- Only an in-force different current member can countersign.
- Decline/no acknowledgement doesn't close R63.
- Duplicate / concurrent confirm doesn't duplicate END/handshake/audit.
- Stale PlanVersion, current quest replacement, terminal rendezvous, ended split, member withdrawal/expiry reject.
- Pending expiry re-scopes correctly, no stale acknowledgement resurrection.
- Three-person Journey acknowledgement closes only A's split, never claims all physically together.
- Non-owner projections never disclose private stop, private route, location or discovery history.
- R62 pending recovery gate is respected.
- Shared PlanVersion, shared execution cursor, Guardian pulses/proposals count unchanged by ordinary meetup handshake.

Frontend/E2E:
- Two real authenticated browser contexts, **real R69 mutation API**, not mocked.
- Owner sees exact shared rendezvous and starts self-reported check-in.
- Companion sees and explicitly acknowledges from their own login.
- Owner sees refresh-safe success; group view shows only safe status; private destination never leaks.
- No physical presence claim and no external geolocation/provider access needed.
- Old/stale check-in cannot complete after plan/split change.

Run focused backend, one two-member Playwright, TypeScript/build, compileall and `git diff --check`; one isolated bounded product flow. No historical R58–R68 verification campaign; no new general verifier, no extra Agent invocation, no chasing mutation counts.

## Definition of done

A genuine signed member can **finish a private real-world detour, report reaching the shared meetup, receive acknowledgement from another member and return to normal shared Journey execution**, without a fabricated physical-location proof, private-place leak, duplicate plan or recovery bypass.

**The product is the deliverable.**
