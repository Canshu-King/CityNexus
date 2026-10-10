# Revolution R70 — Bring Everyone Here: Invite Companions Into a Real Discovery

## Product baton

The same Revolution branch continues; do not start a new project or a verifier campaign.

- Codex R69 implementation: `a997706dcef58e3138d5980a0d426787cea1713c`.
- R69 already lets a returning traveler report reaching the *shared* rendezvous and receive a signed peer acknowledgement, safely ending only their own R63 planned split. It does **not** prove physical presence or all-group reunion.
- GPT performed R69 code review and committed narrow truth/usability fixes on this same branch:
  - A new planned split must not inherit the prior split's `PEER_ACKNOWLEDGED` state, even before the new side quest is complete. The latest current split + quest controls owner reporting.
  - In a 3+-person Journey, only the real acknowledging member is shown `You and Alice reported meeting`; other companions see `Alice and Bob reported meeting`, without being impersonated.
  - Backend regression tests cover both cases.
- These review commits still require **one focused local R69 test / frontend typecheck pass**. Fix actual failures, then immediately implement R70. Do not run R58–R69 campaigns or spend the strike collecting evidence.

## Why this is worth a Revolution strike

R63–R69 form a valuable individual side-trip loop: plan a split, find a real place, check return time, launch walking maps, come back, and confirm meeting.

But travel is often social. An explorer discovers something wonderful and wants to ask:

> “This little museum is amazing. Want to join me?”

Today the app treats that find as a purely private stop, so companions must manually re-find the place and invent their own detour.

**R70's promise** is a user-initiated, explicitly disclosed invitation from a *real member-owned R64 private stop* to the other current Journey members. A recipient can see the exact invited public Place, accept or decline under their own identity, and—on accepting—obtain **their own** R63/R64 personal trip to the same Place, with R65/R68 navigation and the original group rendezvous intact.

This is a product capability, **not** shared-plan mutation, collective approval circumvention, or an autonomous Agent run.

## Natural Journey Live UX

### Inviting member A

When A has one current, active-plan-bound R63 planned split and a current R64 `EXACT_KNOWN_PLACE` stop in `READY`, `EN_ROUTE` or `ARRIVED`, show:

**“Invite companions to this place” / “邀请同行者一起来看看”**

1. Preview the exact public Place name, its source (e.g. OSM/known catalog), current shared rendezvous name/time, and invite expiry (10–20 min).
2. Clearly warn: **“This will reveal your selected stop's Place name and exact public pin to current Journey companions. It will NOT share your current device location, original search coordinates, private note, route, or browsing history.”**
3. A explicitly confirms. Only then may the server expose the destination to companions.
4. A sees a simple recipient status (pending, joined/planning their visit, declined, expired). Do not imply recipients are physically present.
5. A can withdraw the invitation. Withdrawal prevents new acceptance; it does not silently cancel a recipient's already accepted personal side quest.
6. No invitation is created by simply selecting a R67 OSM lead, mounting a card, or opening external Maps.

### Companion B

B sees an in-Journey invitation card:

> “Alice invited you to [real public Place]. 500 m straight-line distance is **not** walk time. The shared meetup remains [exact rendezvous].”

Prefer not to include B's distance unless B explicitly provides their own location; a generic invitation never needs B's location. The card must carry factual public Place identity, source, and exact common rendezvous.

B can:

- **Join this stop** — explicit consent to leave the ordinary group flow for their own temporary visit, then enter the existing authenticated R63 separation + R64 private quest. They can request R65 fit preview and open exact walking directions with R68. Do not auto-launch maps or ask for location.
- **Not for me** — decline; only A's invitation response status changes.
- **View place pin** — after B's own deliberate external Maps disclosure; do not silently share origin/device location.

Joining is not physical arrival, group reunion, or collective approval. A's original private stop and B's new personal stop are separate owner-scoped execution objects, still attached to **one active shared PlanVersion**.

The shared PlanVersion, common activities, protected commitments and group execution cursor must not change merely because A invited and B opted into an individual visit.

## Server authority / data boundaries

Use a minimal durable `MemberPlaceInvitation` (plus per-recipient response, or equivalent focused model). Bind one invitation to:

- Journey, inviting current owner member, its exact R63 split intent, its R64 quest, active PlanVersion and exact shared rendezvous target;
- server-resolved canonical Place ID and provider identity, never a client-supplied arbitrary new destination;
- expiry, status, creation/withdrawal timestamps;
- per-recipient response identity and state.

First strike may invite **all current in-force companions**, no need for elaborate friend selectors. Respect member removal/expiry and new members joining after an invitation: no implicit invite expansion without an explicit user action. If there is only one in-force member, show a useful 'No companions available' outcome, not fake recipients.

All writes require signed principal and proper role/owner checks:

- only A can invite or withdraw, never another member using A's quest ID;
- only the exact addressed B may accept/decline with B's own signed identity;
- no client-submitted traveler_id, owner_member_id, PlanVersion ID, coordinates or route can be spent as authority;
- once A's split/quest/place changes, or A's quest reaches COMPLETED/CANCELLED/INVALIDATED, the invitation becomes stale for new acceptances;
- rendezvous terminal, shared plan changed, owner/member removed, request expired or different current quest => reject stale actions, no silent rebind.

**Privacy:** A has explicitly decided to reveal one public Place to invited people, not their entire private side quest. Recipient projection must contain only A's display name, public Place info, shared rendezvous/time and response state; not A's search location, personal route, origin, private note or current location. Users who are not active invitees must not get the private relation through a guessed ID. Do not write the private A→Place relationship to globally readable Journey events/audit bodies.

Use honest state labels: `INVITED`, `ACCEPTED_OWN_STOP_READY`, `DECLINED`, `WITHDRAWN`, `EXPIRED`, `STALE` or small equivalents. `ACCEPTED` means B chose to make a trip, not that B walked there.

## Reuse R63/R64 rather than making a second execution engine

On B's explicit Join:

1. Resolve B's own current membership, active PlanVersion and exact shared rendezvous **again at acceptance time**.
2. Check that A's offered Place and split remain current and the invitation is unexpired.
3. Check B's current R63/R64 context. Never overwrite an `EN_ROUTE` or `ARRIVED` private quest without B's express decision. If B already has an incompatible split or an active protected commitment, show a clear recoverable outcome.
4. Bind B's personal R63 planned separation using the **existing** protected/authenticated scope resolution, if B needs a new split.
5. Create B's own current R64 exact-known-place quest to the invitation's public Place. Do not clone A's quest or borrow A's identity.
6. Return an immediate B-owned Journey Live projection displaying the new stop and existing R65 fit and R68 map buttons.

If the R63 creation and quest creation cannot be atomic with existing helpers, preserve an explicit `ACCEPTANCE_NEEDS_COMPLETION` state and a safe idempotent retry. **Never claim accepted if B was left with only half a product setup.** Do not permit repeated taps to mint duplicate splits or side quests.

A's R69 handshake to regroup at the original shared rendezvous remains available when their trip is later finished. B's own route/return/meetup is separate. One participant's return cannot mark the others physically rejoined.

## Time / commitment boundary

A public Place may be far away, closed, inaccessible or incompatible with a protected shared commitment.

- Display the shared meetup time and a plain note: invitation is a social idea, **not a promise that the visit fits**.
- Do not rank safe return by straight-line distance, guessed walk-speed, or invented provider fact.
- After B accepts, reuse R65's real-provider-backed fit preview. When route evidence unavailable, return `UNKNOWN` with an actionable fallback, not 'safe to go'.
- Existing C3/C4 commitments and collective authority gates are not relaxed. This invitation does not mutate the group plan. If B requests a **shared** plan change, route through the existing collective authority product path, never piggyback on R70 acceptance.

## Product visibility and delivery

Implement directly in `MemberSideQuestCard` (A invitation) and `LiveRecovery` group area (B invitee card), with a compact Chinese/English UX. Do not create a separate demo UI or chat subsystem.

Use current Journey operator projection or narrow authenticated endpoints to deliver invitations. At minimum a manual refresh and refresh-after-write must work. If you can safely update on page focus, it is useful; no provider polling or covert background location.

A's status persists across page refresh. B's accepted quest persists and can actually be navigated through the normal R68 target API. Withdraw and expiry have clear actionable copy.

## Focused implementation and one bounded closure

First run tests directly affected by GPT R69 post-review fixes and frontend typecheck. Then implement R70 in one actual fresh isolated SQLite DB with **two signed browser contexts**, plus a narrow 3-member API regression for audience privacy.

Minimal focused cases:

1. A's exact R64 private stop is NOT shared by default; read group projection before invitation.
2. Only current A can explicitly invite; invitation reveals just the chosen public Place, not origin, notes or route.
3. B accepts with B's own token, obtains B-owned R63 split + R64 exact Place quest, navigable through existing R68 owner target API; no A mutation.
4. B declines; no B split/quest; A sees decline.
5. Invite withdrawal, expiry, A stop completion, active PlanVersion drift, rendezvous closure, member removal and invalid target reject acceptance.
6. Owner can't accept for B; peer can't spoof A; non-invited/expired member cannot inspect invite.
7. Repeat invite/accept requests are idempotent and do not mint duplicate Place, splits or quests.
8. Three-person test: responses attributed individually; no 'everyone agreed' if only one peer accepted.
9. One protected commitment remains unchanged and R65 unverified ETA remains UNKNOWN when live route unavailable.
10. No shared Activity insertion, new PlanVersion, group cursor movement, Guardian trigger or Agent run from simple invitation.
11. Complete the two-browser real-write loop: A sends invite → B reads → B accepts → B sees owner-bound quest and launchable exact Place map handoff → A sees B's response. No mocked R70 mutation API.

Run focused backend, targeted dual-context Playwright, TS typecheck/build, Python compileall, `git diff --check`. One isolated DB closure; one short, honest result document. No external provider/Agent/physical location proof required.

## Definition of done

One traveler discovers a real place privately, **explicitly invites** companions, another traveler **independently opts into** that Place as their own navigable temporary visit, and both can later return to the original shared rendezvous. All private data and authority boundaries remain intact, and the shared Journey is not secretly replanned.

This expands CityNexus from a private navigation assistant to an **in-the-moment group travel coordinator**.

**No R58–R69 historical campaign, no new generic verifier, no synthetic live-provider win, no collecting evidence instead of building the user experience.**
