# REVOLUTION R60 — Collective Recovery Commit + Re-consent

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

Keep this sentence visible while implementing:

> **When the group has really agreed on a shared recovery, CityNexus can safely carry that exact agreement into the active Journey once — and if the world changes before the commit, the old consent expires and CityNexus opens one fresh decision round instead of silently applying stale authority or dead-ending the trip.**

This is not a verifier round. It is the missing bridge from **shared decision** to **shared execution**.

---

## Starting truth

Branch:

`gpt/revolution-r33-open-world-journey-adaptation`

R59 implementation:
- `0a8cecd902a4442d2d2fd484d4ef5e800f3edfd1`

R59 result:
- `bd4fd3381e3e4510681ae1baa05dced6015c4e6d`

R59 truthful closure:
- one server-owned collective room;
- two distinct signed test principals;
- one response per member slot;
- replay-safe responses;
- disagreement remains disagreement;
- world/surface change stales authority;
- one existing `CollectiveAuthorityReceipt` can be issued for aligned authenticated responses;
- active PlanVersion remained unchanged;
- external Agent/provider not called;
- proposal surface was deterministic test-seeded, explicitly **not** provider-grounded;
- therefore R59 proves the server-native decision/authority handoff, not a live group-recovery execution.

Do not rewrite that as provider-grounded or physically executed.

---

# 0. GPT post-R59 review fixes already committed — test first

GPT found one real authority seam after Codex's R59 push:

The UI already hid collective response controls from roles without `JOURNEY_UPDATE`, but the backend response endpoint did not independently enforce that capability. A signed read-only member could therefore potentially answer a dirty/legacy required slot.

GPT directly committed a fail-closed fix:

### Gateway required-member derivation
`d94aac84fe01d0c009473e479a0118bcbb2146aa`

- a member may still affect fairness / decision semantics;
- but only current members with `can_authorize_mutation=true` can enter the required signature set.

### HTTP response boundary
`17717bfc3f74ec6a9d6e8ebaec1d897db55ff751`

- signed identity is not authority by itself;
- `answer_collective_clarification` now independently checks the member's current role has `JOURNEY_UPDATE`.

### Focused regression
`19eab1e0b8888c3cffbfdba1b543c2259de1149b`

Adds:
- read-only member is excluded from the current signing set;
- a signed read-only member cannot answer a legacy/dirty required slot;
- no receipt is minted from that refused response.

**These GPT commits have not yet been run by Codex locally.**

First run the narrow R59/R60 authority tests. If they fail, repair the actual seam. Do not remove the backend capability check and do not widen VIEWER authority.

---

# 1. What R60 must change for the traveller

R59 ends at:

> “The group has authorized this exact proposal; normal approval and acceptance still apply.”

That is truthful, but the product still leaves the travellers standing in a doorway.

R60 must make the next step real:

> **“Everyone who needed to decide agreed on this exact shared recovery. An authorized traveller can now apply it. If the route, place facts, membership, plan, or recovery generation changed after the vote, CityNexus refuses the stale commit and asks only for a fresh current decision.”**

The result must be one coherent Journey, not a receipt museum.

---

# 2. Two concrete gaps to close

## Gap A — collective authority has no identity-aware spend edge

The current generic UI still calls:

`POST /api/v1/replans/{proposal_id}/accept`

without traveller auth.

Important nuance:
- this is **not currently a collective-authority bypass** because `_accept_replan_impl` re-runs `collective_authority_preflight`;
- without spendable collective authority, shared mutation should still fail.

But it is still the wrong product boundary for R60:
- the server does not know which in-force Journey member is spending the group decision;
- it does not enforce `JOURNEY_UPDATE` on that final human action;
- every viewer can still see generic “Accept new plan” controls for pending proposals;
- the UI is proposal-centric, not the one current collective decision.

R60 must make the **collective spend action identity-bound and server-derived**.

## Gap B — stale consent currently has no clean renewal path

R59 correctly marks a room stale when:
- active plan changes;
- candidate surface changes;
- physical/material world epoch changes;
- relevant membership/capability changes.

But a stale/resolved clarification is preserved as durable history and `request_collective_decision` reuses it rather than overwriting it.

That is correct for history, but the user needs a forward path.

R60 must allow:

```
same group-recovery incident
  -> old room becomes STALE
  -> old responses/receipt remain immutable history
  -> one fresh round/mission is created
  -> new decision epoch
  -> only current required members respond
```

No overwrite, no fake continuity, no duplicate spam.

---

# 3. Do not build a second mutation plane

Reuse:
- `group_recovery_incident_key`;
- existing R58 recovery mission lineage;
- `request_replan`;
- `request_collective_decision`;
- `CollectiveAuthorityReceipt`;
- `collective_authority_preflight`;
- `_collective_resolution_for_child`;
- `_accept_replan_impl` and/or the existing Gateway acceptance boundary;
- RecoveryEpoch;
- atomic active-plan switch;
- existing Operator / collective projections.

Do not create:
- GroupPlan table;
- GroupCommit service;
- second authority receipt;
- separate shared-trip state machine;
- client-side plan mutation.

---

# 4. Introduce one product-level collective apply action

Preferred product shape:

`POST /api/v1/journeys/{journey_id}/group-recovery/apply`

or an equivalently narrow server-owned action.

The client should **not** send an arbitrary proposal id as authority.

Server derives:
- current group-recovery incident;
- current collective room in that incident lineage;
- current selected proposal;
- current authority receipt;
- current RecoveryEpoch.

Request authority:
- signed traveller principal required when strict auth is configured;
- principal must map to an in-force JourneyMember;
- that member's current role must have `JOURNEY_UPDATE`.

The action is an explicit final user action to spend already-collected group authority.

It must not:
- manufacture group consent;
- choose another proposal;
- accept a sibling proposal;
- upgrade a stale receipt.

---

# 5. Exact pre-commit gates

Immediately before the active-plan switch, all of these must still agree:

- Journey id;
- incident lineage;
- selected proposal id;
- proposed PlanVersion id;
- active/base PlanVersion;
- proposal still PRESENTED/current;
- trigger still actionable;
- hard feasibility;
- protected commitments;
- current RecoveryEpoch;
- collective decision epoch;
- material-world epoch;
- candidate-surface fingerprint;
- current required-member set;
- current valid collective authority receipt;
- spender is an in-force `JOURNEY_UPDATE` member.

If any material fact changed:
- 0 active-plan mutation;
- old receipt cannot be spent;
- return a typed re-consent outcome;
- do not silently regenerate consent.

---

# 6. Re-consent / fresh-round semantics

A stale room is history, not a template to edit.

For the same stable R58/R59 incident:

- preserve old mission;
- preserve old clarification id;
- preserve old responses;
- preserve old receipt with stale/invalid status as appropriate;
- create exactly one new current decision round through a child/successor mission;
- carry the same `group_recovery.incident_key`;
- recompute current proposal surface;
- recompute current required members/capabilities;
- create a new decision epoch and clarification id.

Suggested lineage:

```
R58 group-recovery mission
  -> R59 collective round #1
      -> stale because world/membership changed
          -> R60 re-consent child round #2
```

Do not create a new R58 incident just because consent expired.

Repeated refresh/clicks must reuse the current fresh round.

---

# 7. If the world changed but the same proposal is still feasible

Do not say:

> “It is basically the same plan, so the old yes still counts.”

If any authority-bound epoch changed, renewed consent is required according to existing stale rules.

The new room may present the same semantic option if it is genuinely still current, but:
- new clarification id;
- new decision epoch;
- new authenticated response audits;
- new receipt.

Consent is to the current world, not a proposal UUID.

---

# 8. If only observation churn happened

Do not force re-consent for meaningless duplicate provider observations.

Reuse the current material-world semantic dedupe:
- equal physical facts should not move the world epoch;
- DETECTED -> ACKNOWLEDGED alone is workflow progress, not a physical-world change.

R60 should preserve that distinction.

---

# 9. UI — one selected shared recovery, not generic proposal buttons

When collective state is:

### WAITING_FOR_MEMBERS
- show collective options;
- no “Accept new plan” button.

### MEDIATING
- show disagreement/mediation;
- no accept/apply button.

### COLLECTIVE_STALE
- say the previous choices expired because the trip/facts changed;
- show/trigger fresh current decision path;
- no accept/apply button.

### COLLECTIVE_AUTHORIZED
Show one current server-derived selected shared recovery.

For a viewer with `JOURNEY_UPDATE`:
- show **Apply shared recovery**.

For a read-only viewer:
- show “The group agreed; waiting for an authorized trip editor to apply it.”

Do not show generic “Accept new plan” controls for sibling/non-selected proposals inside this collective incident.

The UI must not infer selected proposal from list order.

---

# 10. Authenticated spend audit

When an authorized member applies:

Audit must identify:
- traveller principal;
- JourneyMember id;
- role;
- selected proposal;
- collective authority receipt id;
- decision epoch;
- material-world epoch;
- RecoveryEpoch;
- before active plan;
- after active plan;
- result.

Suggested actor type:
`AUTHENTICATED_TRAVELER`

The receipt still represents group consent.
The spend audit represents who executed the already-authorized transition.

Do not rewrite one as the other.

---

# 11. One atomic shared-plan handover

On success:
- old active plan superseded once;
- selected proposed plan becomes ACTIVE once;
- Journey.active_plan_version_id changes once;
- execution cursor is mapped through existing acceptance logic;
- trigger Event resolves through existing semantics;
- stale sibling proposals/standbys retire through existing rules;
- selected ReplanProposal becomes ACCEPTED;
- no duplicate active PlanVersion;
- no second mutation on replay.

Every member's Operator projection must now read the same active Journey.

---

# 12. Group recovery projection after commit

Add/finish a truthful terminal projection such as:

`RECOVERY_APPLIED`

It should expose:
- selected proposal id;
- before/after plan ids;
- authority receipt id;
- applied_at;
- applied_by_member role/id only where privacy-safe;
- current recovery generation.

Traveller headline:

> “The shared recovery was applied. Everyone is now following the updated Journey.”

Only say that when active plan actually changed.

Do not derive RECOVERY_APPLIED from receipt existence alone.

---

# 13. Stale-before-click experiment

Add a first-class test where:

1. two members resolve one room;
2. receipt exists;
3. before apply, mutate one authority-bound current fact:
   - provider place fact,
   - route/material-world fact,
   - active plan,
   - relevant membership/capability,
   - or recovery generation;
4. apply attempt returns typed stale/re-consent response;
5. active plan remains unchanged;
6. old receipt is not spendable;
7. one fresh decision round is available;
8. old responses remain historical only.

This is a core R60 product path, not an edge case.

---

# 14. Capability-change test

Specific authority regression:

1. OWNER + ADMIN agree;
2. receipt exists;
3. ADMIN loses `JOURNEY_UPDATE` or membership expires before commit;
4. old receipt cannot carry the mutation if the required-member/authority set is no longer current;
5. fresh round derives current required members;
6. read-only/expired member cannot spend the apply action.

No UI-only enforcement.

---

# 15. Focused tests

First run GPT post-review tests.

At minimum R60 adds:

1. read-only decision-relevant member is not required signing authority.
2. signed read-only member cannot answer a dirty required slot.
3. signed read-only member cannot apply collective recovery.
4. unauthenticated collective apply is rejected under strict auth.
5. signed JOURNEY_UPDATE member can invoke apply only for the server-selected current proposal.
6. sibling proposal cannot be selected by request payload.
7. no receipt -> no apply.
8. wrong receipt/proposal -> no apply.
9. stale decision epoch -> no apply.
10. stale material-world epoch -> no apply.
11. stale candidate surface -> no apply.
12. stale RecoveryEpoch -> no apply.
13. stale base active plan -> no apply.
14. protected commitment regression -> no apply.
15. valid current receipt -> exactly one atomic plan handover.
16. replay -> same outcome / no second mutation.
17. old trigger resolved only after actual successful handover.
18. all signed viewers observe same new active PlanVersion.
19. non-selected proposal no longer renders as actionable collective apply.
20. stale room creates/reuses one fresh successor room without deleting old responses.
21. TypeScript.
22. focused two-context Playwright.

Do not rerun historical R33-R59 campaigns.

---

# 16. Focused two-browser Playwright

Use two authenticated contexts on one shared Journey.

### Authorized path
- both see same selected collective proposal;
- one context is current JOURNEY_UPDATE member;
- other can be read-only or another updater;
- only valid updater sees Apply shared recovery;
- one click;
- both refresh into same new active plan;
- no old collective response/accept buttons remain;
- UI says applied only after backend plan id changed.

### Stale path
- both agree;
- inject authority-bound world change before click;
- apply returns stale/re-consent;
- both still see old active plan;
- old decision visibly expires;
- one fresh room appears;
- no duplicate room spam.

Mocks are acceptable for UI rendering. Backend authority/apply tests must use real server/domain code.

---

# 17. Bounded product experiment

Preferred closure: one fresh shared Journey with real provider-backed route/place facts.

Do not rerun R58.

Target chain:

```
fresh member risk
-> grounded shared recovery proposal
-> one collective room
-> signed member responses
-> current authority receipt
-> signed JOURNEY_UPDATE apply
-> one active plan handover
-> both viewers see updated Journey
```

If the current environment cannot produce a genuinely grounded shared proposal:
- do **not** fabricate it;
- record `BLOCKED_NO_GROUNDED_SHARED_PROPOSAL`;
- still run the server-native spend/re-consent closure on deterministic test data;
- clearly separate that from live-provider evidence.

If external Hermes remains unavailable:
- do not retry the R58 external-Agent strike just to make R60 green;
- R60 is about spending/expiring collective authority, not proving model availability.

---

# 18. Result document

Write:

`REVOLUTION_R60_COLLECTIVE_RECOVERY_COMMIT_RECONSENT_RESULT.md`

Include:
- exact implementation SHA;
- GPT post-R59 fix test counts;
- focused R60 tests;
- TypeScript/build/Playwright;
- fresh Journey id;
- member ids/roles (no secrets);
- selected proposal id;
- collective clarification id;
- authority receipt id;
- spender member id/role;
- decision/material/surface/recovery epochs;
- active PlanVersion before/after;
- mutation count;
- replay result;
- stale-before-click result;
- fresh successor decision round id if applicable;
- provider provenance;
- external Agent status;
- limitations.

Never write:
- “applied” when only receipt exists;
- “everyone agreed” if the current receipt is stale;
- “authorized traveller applied” without signed principal evidence;
- “live provider grounded” for seeded fixtures.

---

# Stop condition

Stop when CityNexus can truthfully answer:

> **“The group agreed to this exact shared recovery in the current world. A currently authorized trip member spent that exact consent once. If anything material changed before the commit, CityNexus refused the stale authority and opened one fresh decision round without losing history.”**

End-user capability:

> **“When our group agrees on a recovery, CityNexus can actually move the whole trip onto it safely — and if reality changes before we commit, it asks us again instead of using yesterday's yes.”**
