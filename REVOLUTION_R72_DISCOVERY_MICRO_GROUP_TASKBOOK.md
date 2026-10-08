# Revolution R72 — From “Join My Find” to a Real Micro-Adventure Together

## Baton and truth
Continue ONLY on `gpt/revolution-r33-open-world-journey-adaptation`, starting from `8e9d3cdbd5bad9b10ede22d68b5172b04ecae044`.

- R70 implementation `5b8491e979b6ebb0626fea99d311b04d67c9b410`: explicit public-Place invitation, member-specific acceptance with independent R63/R64 stops.
- R71 implementation `3fe401eff807283f12007c016752a2b28fd4bc59`, result `REVOLUTION_R71_CAN_WE_MAKE_IT_RESULT.md`, result commit `9ad8cdc67cb2c3679370b15a2339b6c37aed5d8c`: authenticated recipient-only feasibility preview, grounded evidence or honest UNKNOWN. Its two-context fresh browser run had **no geolocation permission / no live mobility-provider route** and returned UNKNOWN; it did not validate a live CAN_MAKE_IT in-browser.
- GPT post-review commits: `c82f08bb180adbd6cac4e2c5e68c46c7ea2deec9` corrects location-sharing copy and avoids mislabelling failed preview requests as valid UNKNOWN; `d8b925d1b4c1ea995c19f07b5d59f74a0e46fafe` and `8e9d3cdbd5bad9b10ede22d68b5172b04ecae044` expose a member-selected 10/20/30-minute visit duration in the frontend. **These GPT edits are NOT locally tested.** Run one directly affected frontend typecheck and a focused UI scenario before implementing R72. Fix any actual regression; no historical strike reruns.

## Revolution user story
A discovers a real Place and invites B. R71 lets B choose a timebox and make an informed decision, and R70 creates B's independent visit. But **acceptance is not arrival**: today A cannot know whether B has actually reported reaching the invited Place, whether B has started heading back, or whether the spontaneous social outing has run its course.

R72 delivers a **small, consented, multi-member micro-adventure progress board on the existing Journey screen**:

> A: “I found this place. Come join me.”
> B: “I'm coming.” [already R70]
> B: “I've reached our invited place. Share that status with A.” [new]
> A: “B reports they're here; I can explicitly share mine too.” [new]
> Each: “Head back to the shared rendezvous.” [reuse R65/R68]
> A/B: “We both reported heading back; the shared Journey remains the same.” [new, member-scoped]

This is social coordination in the physical world, NOT a new shared PlanVersion, a group travel replan, a generic messaging platform, or a synthetic co-location verifier.

## Deliver one actual vertical slice
1. Add a minimal durable participant-owned *opt-in* signal for a specific R70 invitation and member: `AT_INVITED_PLACE_SELF_REPORTED` and (after R65 member-owned explicit return action) `HEADING_BACK_SELF_REPORTED`. Include signal time, exact invitation / active PlanVersion / public Place / own split and own R64 quest binding, consent version. Choose a small table or constrained existing schema with DB unique constraints and idempotent transitions. A is the inviter's own separate participant; B is an accepted addressed recipient.
2. **Do not infer either signal automatically** from R64 `ARRIVED`, route ETA, GPS, navigation click, invitation acceptance, or quest completion. Require a second explicit “Share my reported status with joined companions” action from that member. For `AT_INVITED_PLACE_SELF_REPORTED`, require own authenticated R64 quest state ARRIVED bound to the invited public Place; that still is a member execution report, not physical verification. For `HEADING_BACK_SELF_REPORTED`, reuse a real R65 HEAD_BACK receipt or introduce an explicit owner-reported departure with equally honest semantics; do not claim observed travel.
3. Viewer-specific projection on existing invite/side-quest area. Only A and accepted participants can see opted-in coarse progress of that accepted cohort; pending invitees and non-recipients see no place-progress disclosure. Never project another member's current/previous precise location, route geometry, original private Place search history, interest, exact origin, or private notes. Recipients already consented to this one public Place: showing an opted-in status about *this* Place is permitted; no broader location sharing.
4. Make the UI natural and localized: inviter sees names and statuses “joined / reported here / reported heading back”; B sees own “report here” and “share heading back” controls when relevant, plus the existing R65/R68 return-navigation action. Show last-report timestamp and clear “member-reported, not GPS verified.” Explicit consent before displaying the new status to others. The user can withdraw a status from **future** projections; don't claim to retract already-seen information. No automatic map launching, background location request or passive external provider calls.
5. Keep the existing R69 handshake at the **original shared PlanVersion rendezvous** distinct. A/B reporting arrival at the invited side Place must NOT end anyone's R63 split, satisfy R62 recovery followthrough, move the group execution cursor, trigger Guardian or imply the entire Journey group is physically together.
6. Expiry/withdrawal semantics: an OPEN invitation can expire or be withdrawn and prevent new joins, **but B's already accepted independent quest and opted-in participant progress must not be silently revoked**. Once original R63 split ends, own quest replaced, participant removed, public Place no longer bound or active plan changes, reject new progress signals; retain safe historical disclosure receipts. A user who declines/never accepted must not contribute a progress report. Multi-process race/retries must not double-signal or rewrite another member's state.
7. Ensure errors expose useful and accurate outcomes. A failed provider preview must not become a fake feasible result; don't pretend an R71 UNKNOWN means an unsafe trip was proven safe. Preserve the R71 user-selected 10/20/30-minute estimate, revalidate if changed, and make "timing unverified" visible next to timeboxed social progress.

## Implementation seams
- `backend/app/execution/member_place_invitation.py`, `MemberPlaceInvitationRecipient` and server-side member authorization, `backend/app/operator_projection.py`.
- `backend/app/execution/member_side_quest.py`: R64 states and R65 `MemberSideQuestReturnReport`, source of authentic signed member reports. Avoid public generic route/read stores.
- `backend/app/execution/planned_split_meetup_handshake.py` and R69: original shared rendezvous completion; do **not** reuse its “yes, we're together” as proof of gathering at the side Place.
- `frontend/src/features/execution/MemberPlaceInvitationPanel.tsx`, `MemberSideQuestCard.tsx`, `LiveRecovery.tsx`: render one compact, persistent user journey, not a separate demo.
- `frontend/src/api/citynexus.ts` updated for user-selected dwell. Do not silently reset dwell to 20 in the UI.
- Location check currently calls the generic `POST /journeys/{id}/location`, saving a Journey-scoped observation. Coarse group-presence projection can change from that observation. GPT corrected consent copy; do not reintroduce a misleading “only used once and never affects others” assertion.

## Tests / one bounded live product closure
Run narrow GPT-post-review typecheck and focused R71 UI first. Then:
- Signed A starts R63/R64 invited exact Place; A invites B; B accepts with explicit UNKNOWN acknowledgement in a fresh isolated SQLite run (unknown is valid when route provider/location absent).
- A and B navigate/mark ARRIVED through their real member-bound R64 execution paths, then **independently opt in to share public-Place arrival status**; show those two reports on authorized screens after reload.
- A and B individually initiate real R65 HEAD_BACK and opt in to coarse return-sharing; preserve their separate state and original common rendezvous.
- Add C uninvolved or pending; assert C sees no new private progress; test B not sharing means A sees only B joined, never “B arrived.”
- Test forgery, ID guessing, no signed identity, pending/declined member, expiry after acceptance, invitation withdrawal after acceptance, stale/new own quest, member removal, plan drift, duplicate and cross-process CAS where practical.
- Check counts or DB state: active PlanVersion and shared cursor unchanged; 0 unintended AgentRun, Guardian pulse, proposal, money/booking changes. No R69/R62 premature closure.
- Focused backend tests, one fresh two-/three-signed-context Playwright (real API mutation), typecheck/build, compileall, diff check. Existing direct regression only; **no R58–R70 archival strike loop**. State exactly what did/did not use external providers or real hardware. No claim of GPS-verified physical presence.

## Definition of done
The existing Journey product supports a full new socially visible user journey: **discover → invite → member-specific decide → visit independently → voluntarily report progress to that invited micro-group → independently head back to shared rendezvous**. It is privacy- and authority-correct, persistent, and does not fabricate world truth.

Commit `REVOLUTION_R72_DISCOVERY_MICRO_GROUP_RESULT.md` with exact commands, outcomes, SHA, provider/Agent truth; push to the SAME branch. Keep the emphasis on useful code and actual human actions, not proof paperwork.
