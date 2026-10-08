# REVOLUTION R63 — Planned Parallel Group Journey / Intentional Split + Rendezvous Guard

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

Keep this product sentence visible:

> **A traveller can intentionally peel off from the group for a temporary personal side trip without CityNexus treating the separation itself as a disruption. CityNexus keeps the shared Journey authoritative, tells everyone where the next shared rendezvous is, watches whether the personal branch is still compatible with that commitment, and escalates into the existing group-recovery machinery only when the return actually becomes risky.**

This is the continuation of the same product story:

- R56: I went off route.
- R57: our group split unexpectedly.
- R58: should the group adapt?
- R59: who decides?
- R60: how is exact collective consent spent?
- R61: what if the agreed future dies before commit?
- R62: after recovery succeeds, how do members rejoin and return to normal Journey execution?
- **R63: what if the group wants to split on purpose for a while?**

R63 is not a verifier round, not a second GroupPlan, not a second active itinerary pointer, and not a reason to weaken R57–R62 authority.

---

# 0. Starting truth

Branch:

`gpt/revolution-r33-open-world-journey-adaptation`

R61:
- implementation: `05a45d917156f574327b3c92d3f22d517918eb4a`
- result: `a81c3a7821af5af2d4af89d92529001b722ad010`
- truthful boundary: local server/domain/API/UI closure; no provider-live or real external Agent run claimed.

R62:
- taskbook: `REVOLUTION_R62_GROUP_RECOVERY_FOLLOW_THROUGH_TASKBOOK.md`
- Codex implementation checkpoint: `1725a449a50898e1c63889f0e7c0a81f347a7a1f`
- Codex created the real product loop:
  - shared recovery apply binds a follow-through snapshot;
  - members report their own authenticated arrival through the existing Journey execution route;
  - reunion closes exactly once;
  - no fake physical presence is claimed merely because a plan was applied;
  - recovery closure does not change the active PlanVersion.

Codex did **not** create a separate R62 result document before moving on.

That is not a reason for a verifier campaign. The first step below is a narrow closeout of the post-review fixes, then move straight into R63.

Keep:

`CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`

Do not rerun R58–R61 historical campaigns.

Do not touch WB2api/provider unless a new, reproducible R63 product defect requires it.

---

# 1. GPT post-R62 review fixes already committed — test these first

GPT accepted the R62 product direction but found four real multi-member truth seams after Codex's `1725a449...` push.

These commits are already on the branch and have **not** been locally validated by Codex yet.

### Durable member reunion truth

`d648f773ead98c1c93d60acc46ae99b5eedbc61c`

R62 already wrote one independent durable `group_recovery.execution_arrival` receipt per member, but the read model was reconstructing reunion only from one shared `Activity.metadata_json.execution_truth_history`.

That shared JSON document is a concurrent last-writer surface.

The projection now uses the independent member-bound receipts as current reunion truth and keeps Activity history only as a compatibility/movement fallback.

`629283827d6c4e6c8b1f16ed00c2510f2e6f1846`

Each durable arrival receipt is explicitly bound to:
- Journey;
- incident;
- applied PlanVersion;
- RecoveryEpoch;
- rendezvous Activity;
- JourneyMember;
- Traveler;
- role-at-apply;
- execution truth kind.

`d7abfa08f7652a31308e24f44df79d5f3d891527`

Regression:
- erase the shared Activity execution-history blob after member A has arrived;
- member A must still be remembered from the durable receipt;
- member B can arrive;
- recovery still closes exactly once.

### Exact physical-presence provenance

`7e6afba23c08f628eb39b1ee24f793c37cd24fea`

The original group-level value was effectively:

`physical_presence_verified = any(member is device verified)`

That wrongly upgrades one member's physical evidence into a claim about the whole reunion.

Now:
- every member exposes their own `confirmation_kind`;
- every member exposes their own `physical_presence_verified`;
- group-level physical presence is true only when **all currently required members** are device/location verified;
- `physical_presence_verified_member_count` is explicit.

Tests:
- `d71baf92d8408e19831beda2e60da8838aecc2f8`
- cleanup `9c64ece8069514a0e26346175adb73cf4202aed7`

### Recovery must leave the foreground after success

`5f38f095aee174d7f723d0220682664f3fe7b3fa`

R62 taskbook required:
> no recovery mode forever.

The old read model kept projecting `RECOVERY_CLOSED` into the foreground forever while the applied plan stayed active.

Now closure remains durable history, but:
- `group_recovery.foreground=false` after terminal reunion;
- normal Journey execution becomes primary again.

Supporting frontend/type work:
- `1468fbdd0eab5e3ae91e1c0d7bdffbc0fb48c739`
- `9c362564bb2a00fbec80e2b5843b92e96e0258fa`
- `2a723d92368138390dec95de4b5955aac396efbe`

The final member receives one explicit success message, then future reads no longer foreground the recovery card.

### Shared Journey cursor must wait for reunion

`f317077151a4789f7c112a1e98c2caa27572e113`

The original R62 test allowed the first-arrived member to push the shared rendezvous Activity from `ARRIVED` to `IN_PROGRESS` while another member was still missing.

That makes two incompatible claims:
- group recovery: member still absent;
- shared Journey cursor: common activity already started.

Now the shared rendezvous cannot `begin` until R62 reunion closes.

Individual members can still bind their own arrival receipts.

Test update:

`f4b72a07f94866c7dca26da6a4de4f5487bb3407`

It proves:
- early begin is blocked;
- early complete is blocked;
- second member arrival closes reunion;
- then normal shared Journey `begin` resumes;
- Operator preserves closure history while `foreground=false`.

Current pre-R63 HEAD:

`f4b72a07f94866c7dca26da6a4de4f5487bb3407`

---

# 2. First step — narrow R62 closeout, not R62.1

Before R63 implementation, run only the directly affected checks needed to validate the GPT review patches.

Required:

1. `backend/tests/test_r62_group_recovery_followthrough.py`
2. directly affected R60 group-recovery apply tests because R62 follow-through is attached at the R60 spend seam;
3. the narrow execution-truth tests that cover authenticated execution attestation;
4. frontend TypeScript;
5. R62 Playwright spec;
6. production build only if TypeScript passes and the changed frontend surface warrants it;
7. `git diff --check`.

Repair only real failures.

Do **not**:
- weaken member identity binding;
- go back to shared Activity JSON as sole reunion truth;
- change group-level physical verification back to `any()`;
- leave `RECOVERY_CLOSED` permanently foregrounded;
- allow shared rendezvous `begin` before reunion closure;
- rerun R58–R61 campaigns.

After these fixes are green, write one concise:

`REVOLUTION_R62_GROUP_RECOVERY_FOLLOW_THROUGH_RESULT.md`

It must distinguish:
- Codex original R62 work;
- GPT post-review fixes;
- local/domain/UI evidence;
- any real product experiment if one actually exists.

Do not claim physical-world reunion unless all evidence really supports that statement.

Then proceed immediately to R63.

---

# 3. R63 new capability

CityNexus newly learns to:

> **Coordinate an intentional temporary group split without treating the split itself as a failure.**

Example:

> Alice: “I want to go look at the bookshop by myself for a while. I’ll meet everyone at the museum.”

Current CityNexus can observe “the group is split.”

R63 must understand:

> “This split is intentional, member-scoped, temporary, and still subordinate to the shared Journey.”

The active shared Journey remains the one executable plan.

The side trip is **not** a second itinerary.

---

# 4. Reuse JourneyIntent as the authority for planned separation

The existing `JourneyIntent` already has the correct durable shape:

- `created_by_traveler_id`;
- `created_by_member_id`;
- bounded temporal scope;
- source text;
- semantic envelope;
- status;
- PLAN_ONLY steering;
- no global preference mutation;
- traveller-specific projection.

Extend that system rather than creating:
- GroupPlan;
- MemberPlan;
- ParallelPlanVersion;
- a second active-plan pointer;
- a second execution state machine.

Suggested intent kind:

`PLANNED_SEPARATION`

or:

`PERSONAL_EXCURSION`

Choose one canonical name and use it consistently.

The canonical dimension must be member-scoped. One member starting a side trip must not supersede another member's temporary intent.

A useful semantic key is conceptually:

`journey-intent:planned-separation:<member_id>`

Do not put raw member ids into user copy.

---

# 5. Signed member ownership

A planned split can only be created for the authenticated member making the request.

The client may say:

> “I’m going to the garden alone.”

It may not submit:

`member_id = Bob`

to create Bob's side trip.

Server owns:
- principal -> Traveler;
- Traveler -> current JourneyMember;
- intent owner;
- rendezvous;
- scope;
- current active Journey.

One member cannot schedule another member's personal separation.

Owner/admin authority over the shared Journey does not allow impersonating another traveller's personal execution intent.

---

# 6. Natural-language entry through the existing Operator

Preferred entry:

the existing authenticated live Journey command / steering surface.

Examples:

- “I’m going to browse the shops alone for the next hour. I’ll meet everyone at the next shared stop.”
- “I want to get coffee by myself, then meet you at Nara Park.”
- “I’m splitting off until the museum.”
- “I’m back with the group.”

Do not make R63 depend on a hidden developer-only endpoint.

The semantic model may interpret the request, but the server must resolve:
- current member;
- scope;
- known destination identity when one is required;
- shared rendezvous Activity;
- protected commitment;
- authority.

If the request is ambiguous:
- ask one bounded clarification;
- do not guess a physical place or time.

---

# 7. Server-owned rendezvous

For a planned separation, CityNexus must produce one exact current answer to:

> Where must this member rejoin the shared Journey?

Prefer existing active-plan truth.

Resolution priority:

1. an explicitly referenced existing future shared Activity if the user named it unambiguously;
2. otherwise the next current C3/C4 protected shared commitment;
3. otherwise the next exact future active-plan stop returned by the existing rendezvous semantics;
4. otherwise `RENDEZVOUS_UNRESOLVED`.

Do not:
- invent a midpoint;
- use model prose as a Place id;
- accept a client-owned rendezvous id without server validation.

Persist on the planned separation:
- rendezvous Activity id;
- rendezvous Place id if available;
- scheduled time / safe buffer if available;
- active PlanVersion id at creation.

If the active PlanVersion changes, re-resolve before continuing to claim the old rendezvous is current.

---

# 8. Side destination truth

A planned separation does not require CityNexus to rewrite the shared plan.

If the member names a side destination:

- use an existing canonical Place when exact identity is already available;
- otherwise use the existing discovery/fact-acquisition path if a bounded lookup is appropriate;
- otherwise keep the destination unresolved and ask the member.

Do not store model-generated coordinates as physical truth.

Do not call a fixture provider “live.”

The product can still support a planned split whose side destination is only descriptive, as long as CityNexus does **not** claim a verified route from that destination.

The critical authoritative target is the **shared rendezvous**, not the side trip fantasy.

---

# 9. Intentional split must be distinct from unexpected split

Today group presence can say:

`GROUP_SPLIT_ADVISORY`

R63 needs a server-owned distinction.

Suggested group states:

- `PLANNED_SPLIT`
- `PLANNED_SPLIT_ON_TRACK`
- `PLANNED_SPLIT_RETURN_RISK`
- `PLANNED_SPLIT_RETURN_UNKNOWN`

Use equivalent existing naming if clearer.

A member may count as intentionally separated only when:
- their signed active planned-separation intent is current;
- intent is bound to this Journey/member;
- active PlanVersion still matches or rendezvous was revalidated;
- scope has not expired/cancelled;
- rendezvous is current.

Do not classify a random distant member as intentional merely because they once had an old intent.

---

# 10. Do not wake recovery merely because intentional members are apart

This is the core product change.

When members are geographically split and the split is covered by valid planned-separation intent:

> **separation alone is not the disruption.**

Do not open R57/R58 group recovery solely because coarse location says `SPLIT_FROM_GROUP`.

Instead ask:

> Can the separated member still make the next protected shared rendezvous?

Reuse:
- current member location authority;
- current route evidence;
- `rendezvous_commitment_risk`;
- existing C3/C4 buffer semantics.

This is risk-aware suppression, not blindness.

---

# 11. Safe / advisory / trusted risk semantics

Keep provenance exact.

### No current route

State:

`PLANNED_SPLIT_RETURN_UNKNOWN`

Copy:

> “This side trip is planned, but CityNexus does not currently have a reliable return ETA.”

No recovery mutation.

### Advisory browser location + route

You may show:

> “Your current advisory route may leave little time to rejoin.”

But preserve existing rule:

browser foreground location alone cannot create trusted physical truth or silently authorize Guardian mutation.

### Trusted/current route risk

If existing trusted member-location + route truth shows the next protected shared commitment is materially at risk:

`PLANNED_SPLIT_RETURN_RISK`

At that point the intentional split has become a real recovery problem.

Do **not** invent a second planned-split recovery system.

Hand off into the existing R57–R61 group recovery path.

The original planned-separation intent remains history/context.

---

# 12. Handoff into existing group recovery

The transition should read:

```
intentional split
  -> return still safe
     -> no recovery
  -> return risk becomes material
     -> existing group-recovery incident
     -> existing planning
     -> existing collective authority
     -> existing apply
     -> existing R62 follow-through/rejoin
```

Do not create:
- `PlannedSplitRecoveryReceipt`;
- a second authority receipt;
- a second collective room type.

If a shared-plan change is needed, normal collective authority still governs it.

The fact that Alice chose to split does not authorize Alice to change everyone else's plan.

---

# 13. Member-specific UX

The member on the planned side trip should see something like:

> **You’re on a planned side trip**
>
> Rejoin the group at **Nara Park** before **15:00**.
>
> Current return status: **on track**.

Another member should see:

> **Alice is on a planned side trip**
>
> The shared Journey is unchanged. You’re meeting again at **Nara Park**.

Privacy:
- do not expose Alice's exact coordinates;
- do not expose hidden personal preference/profile data;
- show only the minimum coarse status needed for coordination.

---

# 14. Personal next action

For the separating member, project one server-owned next action:

Possible values:

- `CONTINUE_PERSONAL_EXCURSION`
- `ROUTE_TO_RENDEZVOUS`
- `RETURN_SOON`
- `REJOIN_NOW`
- `CLARIFY_RENDEZVOUS`

When an existing member location sample is available, the existing route-to-group/rendezvous path should remain usable.

Do not create a new route provider stack.

If the member asks “Take me back to the group,” reuse the existing route acquisition path.

---

# 15. Ending the planned separation

Ending a planned separation and proving physical reunion are different facts.

A member may explicitly say:

> “I’m back.”
> “I’m done with my side trip.”
> “We’re together again.”

That can end/cancel/supersede **their planned-separation intent**.

It must not automatically claim:
- trusted physical co-location;
- all members have rejoined;
- device-verified presence.

After the intent ends:

- if current group presence truth says together, project `TOGETHER`;
- if location truth is missing/advisory/unknown, say the planned separation ended but current physical togetherness is unknown;
- if members are still materially split with no active planned-separation cover, ordinary R57 split semantics become current again.

Do not keep suppression forever after the intent ends.

---

# 16. Scope expiry

A planned separation must have a bounded lifecycle.

Allow scopes such as:
- until the next shared stop;
- until an explicit future active-plan Activity;
- until a bounded time before a shared commitment.

Do not create an indefinite “Alice may always be away” flag.

When the scope expires:
- the intent becomes expired;
- planned-split suppression ends;
- current group truth is reevaluated.

Expiry does not prove reunion.

---

# 17. Shared Journey must remain unchanged in the safe case

A safe planned split is a coordination overlay on the current Journey.

The safe path must have:

- active PlanVersion unchanged;
- current shared commitments unchanged;
- no replan proposal;
- no collective authority receipt;
- no group recovery incident;
- no Agent mutation.

This is a real product success.

Do not call `NO_MUTATION` a failure.

---

# 18. Guardian integration

R63 should connect to the continuous Operator without adding another polling loop.

Guardian may observe:
- planned split active;
- current return ETA;
- next shared commitment;
- remaining buffer.

Safe planned split:
- no recovery wake merely because members are apart.

Risk becomes material:
- use the existing disruption/recovery event boundary;
- one stable incident;
- no duplicate wake on repeated identical observations.

If route evidence changes from safe to risky, that is meaningful product progress.

If no route evidence exists, stay unknown rather than inventing risk.

---

# 19. No authority inflation

R63 may autonomously:

- persist the authenticated member's temporary planned-separation intent;
- resolve the shared rendezvous from current server truth;
- project privacy-safe member coordination state;
- compute return risk from existing route/commitment truth;
- suppress false split alarms while the planned intent is valid;
- expire the intent;
- hand a real risk to existing group recovery.

R63 may not autonomously:

- change the active PlanVersion;
- change another member's intent;
- move another member's execution state;
- create consent;
- accept a replan;
- book/pay/cancel;
- claim physical reunion from self-report alone.

---

# 20. Do not misuse JOURNEY_EXECUTION_UPDATE

R62 introduced `JOURNEY_EXECUTION_UPDATE` to express authenticated execution reporting.

R63 planned-separation intent is not the same authority.

Creating/ending your own temporary personal intent should use the existing signed JourneyIntent/member boundary.

Do not require or grant `JOURNEY_UPDATE` merely to say:
> “I’m taking a side trip.”

Do not let `JOURNEY_EXECUTION_UPDATE` become a generic shared-plan mutation permission.

If a shared Journey change becomes necessary, use the existing shared authority machinery.

---

# 21. Durable planned-split projection

Add one server-owned projection, preferably under Operator/group presence, that survives refresh.

Suggested shape:

```json
{
  "state": "PLANNED_SPLIT_ON_TRACK",
  "active_plan_version_id": "...",
  "rendezvous": {
    "activity_id": "...",
    "title": "...",
    "scheduled_at": "..."
  },
  "members": [
    {
      "display_name": "Alice",
      "is_viewer": true,
      "planned_separation": true,
      "return_state": "ON_TRACK",
      "route_provenance": "CAPTURED_REPLAY"
    },
    {
      "display_name": "Bo",
      "is_viewer": false,
      "planned_separation": false
    }
  ],
  "viewer_next_action": "CONTINUE_PERSONAL_EXCURSION",
  "shared_plan_changed": false
}
```

Member ids may be present only where existing privacy rules permit them. Do not expose raw coordinates.

---

# 22. Safe coexistence with R62

R62 is post-recovery reunion.

R63 is pre-incident intentional separation.

Keep them separate.

A safe planned split should **not** mint an R62 recovery follow-through record.

If an R63 split becomes risky and goes through existing group recovery/apply, then R62 naturally becomes relevant after the recovery is applied.

Do not use an R62 closure receipt to pretend an ordinary planned side trip physically rejoined.

---

# 23. Existing files to inspect first

Prefer modifying the existing systems rather than adding a parallel stack:

- `backend/app/agent/journey_intent.py`
- live Journey intent compiler / command path in `backend/app/main.py`
- `backend/app/execution/group_presence.py`
- existing route-to-rendezvous acquisition path
- existing R57/R58 group-recovery incident creation
- Guardian/watch logic that reacts to group risk
- `backend/app/operator_projection.py`
- `frontend/src/features/execution/LiveRecovery.tsx`
- the regular Operator intent surface

Use a small helper module only if it cleanly joins these systems.

---

# 24. Required focused tests

After the narrow R62 closeout, add only tests that prove R63.

At minimum:

1. **signed member ownership**
   - Alice creates planned separation for herself;
   - client cannot create Bob's personal intent.

2. **member-scoped supersession**
   - Alice replacing her planned split does not supersede Bob's unrelated temporary intent.

3. **shared plan unchanged**
   - safe planned split creates 0 PlanVersion mutation and 0 replan proposal.

4. **server-owned rendezvous**
   - model/client cannot force arbitrary Activity/Place identity.

5. **planned split suppresses false disruption**
   - coarse member separation + valid planned intent does not by itself open group recovery.

6. **unknown return evidence stays unknown**
   - no route -> no invented ETA/risk.

7. **safe return**
   - current route has adequate buffer -> ON_TRACK; no recovery.

8. **advisory return**
   - foreground browser evidence stays advisory; no provenance upgrade.

9. **trusted material return risk**
   - trusted current route threatens protected shared commitment -> existing group-recovery path wakes once.

10. **same risk replay**
    - repeated identical observation does not create duplicate incidents.

11. **intent expiry**
    - planned-split suppression ends at scope expiry; expiry does not claim reunion.

12. **member says “I’m back”**
    - their intent ends;
    - physical/group state remains whatever current evidence actually supports.

13. **privacy**
    - another member sees coordination status but no exact coordinates/private profile data.

14. **active plan changes**
    - old planned rendezvous cannot silently remain authoritative; server revalidates or marks it stale.

15. **R62 separation**
    - safe R63 planned split does not create an R62 follow-through receipt.

16. TypeScript.

17. One focused two-context Playwright.

Do not create a broad R57–R62 regression campaign.

---

# 25. Focused two-context Playwright

Two signed members on one shared Journey.

Prove a user-visible loop:

1. Alice submits/has an active planned separation.
2. Alice sees:
   - “You’re on a planned side trip.”
   - next shared rendezvous;
   - personal return status.
3. Bo sees:
   - “Alice is on a planned side trip.”
   - the same shared rendezvous;
   - shared Journey unchanged.
4. Neither sees ordinary unexpected-split recovery CTA while the planned split is safe.
5. Exact coordinates are absent.
6. When return becomes risky in the mocked read model:
   - both see that the shared commitment is at risk;
   - UI transitions to the existing recovery semantics, not a new R63 recovery UI.
7. When planned intent is ended/expired in a safe case:
   - planned-split card retires;
   - normal group presence/Journey surface resumes.

UI data may be mocked. Backend intent/risk/incident transitions must be covered by real API/domain tests.

---

# 26. One bounded R63 product experiment

Do not rerun old strikes.

Preferred experiment:

1. one fresh active two-member Journey with distinct signed principals;
2. existing shared future rendezvous / protected commitment;
3. member A explicitly creates one planned-separation intent;
4. active PlanVersion before/after must match;
5. show the group can be physically/coarsely separated without automatic recovery solely because of that separation;
6. acquire or reuse one honest member return-route evidence if available;
7. observe one truthful outcome:

Valid outcomes:

- `PLANNED_SPLIT_ON_TRACK`
- `PLANNED_SPLIT_RETURN_UNKNOWN`
- `PLANNED_SPLIT_RETURN_RISK_ESCALATED`
- `PLANNED_SPLIT_AGENT_BLOCKED`
- `PLANNED_SPLIT_RENDEZVOUS_UNRESOLVED`

Do not retry to force risk.

If using captured replay:
- call it captured replay.

If using browser foreground location:
- call it advisory.

If no provider/Agent is involved:
- do not claim provider-live or Agent-live.

A safe `ON_TRACK + 0 mutation` result is a successful R63 product closure.

---

# 27. R63 result document

Write:

`REVOLUTION_R63_PLANNED_PARALLEL_GROUP_JOURNEY_RESULT.md`

Include:
- implementation SHA;
- post-R62 narrow validation results;
- R62 result document SHA;
- R63 focused test counts;
- TypeScript/build/Playwright as actually run;
- fresh Journey id if a product experiment exists;
- member count;
- planned-separation intent id/owner role;
- active PlanVersion before/after;
- rendezvous Activity id;
- side destination evidence/provenance if one exists;
- route provenance;
- return-risk state;
- whether group recovery was opened;
- recovery incident id/key if escalation occurred;
- mutation count;
- external Agent/provider status;
- limitations.

Never claim:
- a self-report proved physical reunion;
- a planned split was a disruption merely because members were apart;
- browser location was trusted device presence;
- a side destination was provider-verified if it was model text;
- safe 0-mutation was a failure.

---

# 28. Stop condition

Stop when CityNexus can truthfully answer:

> **“Alice intentionally left the group for a while. I know this is planned, so I am not treating separation itself as a failure. The shared Journey is still authoritative. Everyone can see where they meet again. I am watching whether Alice can still make that shared commitment, and I will only wake the recovery system if that return actually becomes risky.”**

End-user capability:

> **“We can split up on purpose without confusing CityNexus. It keeps our shared trip intact, helps us coordinate where to meet again, and only intervenes if one person's side trip starts putting the group plan at risk.”**
