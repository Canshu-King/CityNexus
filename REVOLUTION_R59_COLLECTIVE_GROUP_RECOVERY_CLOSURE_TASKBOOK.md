# REVOLUTION R59 — Collective Group Recovery Closure / Decision Room

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

Keep this sentence visible while implementing:

> **When one traveller is late enough that the shared Journey may need to change, “Adjust together” becomes a real shared decision room: CityNexus prepares grounded recovery options, asks exactly the affected in-force members, preserves disagreement instead of majority-voting it away, and only makes a shared-plan change after the existing server-owned collective authority says that authority is actually spendable.**

If this turns into another verifier-only round, a new voting subsystem, a new GroupRecoveryAgent, a fake consensus shortcut, or UI polish without a real member-decision transition, stop and correct course.

---

## Starting truth

Use branch:

`gpt/revolution-r33-open-world-journey-adaptation`

R58 bounded strike is recorded at:

`dce81182faafcdbb6642d7a2e6164292d86052bd`

R58 implementation checkpoint:

`d6926613202ec380c954c1aa3c776c421f9ebd44`

R58 truthful live outcome:
- fresh shared Journey;
- FOREGROUND_WEB member presence remained advisory;
- provider route was a real current Valhalla provider capture, not claimed as live traffic;
- member lateness reached `ADVISORY_MEMBER_LATE`;
- exactly one user-requested `Adjust together` escalation was recorded;
- one durable PLAN_ONLY group-recovery mission was created;
- native Hermes was unavailable and the mission ended `FAILED_EXTERNAL`;
- no proposal;
- no collective round;
- no plan mutation;
- no retry to force mutation.

That is a valid R58 outcome. Do not rewrite it as failure and do not rerun the R58 live strike.

---

## GPT pre-baton seam fix already committed

GPT found one capability gap after R58:

A `PLAN_ONLY + COLLECTIVE_JOURNEY_RECOVERY` mission could call `request_replan` but could not call the already-existing non-mutating `request_collective_decision`. Therefore even a healthy Hermes could create proposals but could not itself move the R58 incident into the existing member-response / collective-authority flow.

GPT has already committed the narrow fix:

- `3285d83f2c5cc117ad57e78ed2942c0fb507fd0c`
  - allows `request_collective_decision` only for `PLAN_ONLY` missions carrying `COLLECTIVE_JOURNEY_RECOVERY`;
  - adds an explicit collective-decision mission-plan step;
  - does **not** grant `accept_replan`, standby activation, rescheduling, booking, or any other execution tool.

GPT also added focused tests:

- `52a405c8775445ef3e21278a29a06edb6205c877`
- `backend/tests/test_r59_collective_group_recovery_plan.py`

Before R59 work, run those focused tests once. Repair only if the real seam fails. Do not broaden PLAN_ONLY authority.

---

# 1. Product gap

R58 can now say:

> “Sam is late enough that the group may need to adjust. Keep the plan, or ask CityNexus to prepare a shared recovery.”

But “Adjust together” still has not been proven as one continuous product chain:

```
member risk
  -> grounded group-impacting proposal(s)
  -> server-owned collective decision round
  -> each required signed member responds
  -> disagreement is preserved/mediated
  -> collective authority receipt
  -> normal governed acceptance boundary
```

R59 closes that chain.

This is not about inventing new collective machinery. Most of it already exists.

---

# 2. Reuse the existing collective stack

R59 must compose, not duplicate:

- `request_replan`;
- `request_collective_decision`;
- `collective_proposal_receipt`;
- existing `COLLECTIVE_TRADEOFF` clarification;
- signed member response endpoint;
- existing disagreement mediation;
- `CollectiveAuthorityReceipt`;
- `collective_authority_preflight`;
- normal proposal accept / approval continuation;
- existing `collective_operator_projection`;
- existing LiveRecovery collective UI.

Do not create:
- `GroupVote`;
- `GroupDecisionAgent`;
- `RendezvousRecoveryAgent`;
- a second authority receipt type;
- a majority vote shortcut.

---

# 3. R59 mission authority

For `PLAN_ONLY + COLLECTIVE_JOURNEY_RECOVERY`:

Allowed:
- inspect Journey/Twin;
- inspect proposals;
- search bounded candidates if already allowed by the envelope;
- `request_replan`;
- `request_collective_decision`.

Not allowed:
- `accept_replan`;
- `activate_standby`;
- `replace_activity`;
- `reschedule_activity`;
- booking/payment mutation;
- commitment mutation;
- any direct PlanVersion activation.

Opening a member-decision round is not the same as accepting that decision.

Keep that distinction visible in code and tests.

---

# 4. When to open the collective decision

Do not automatically ask everyone whenever a proposal exists.

A collective round is appropriate only when server-owned proposal facts show a real group-impacting human trade-off.

Examples:
- waiting preserves one member but delays others;
- skipping/reordering a flexible stop changes the group experience;
- two grounded recovery options fit different members differently.

If there is only one materially dominant future with no decision-relevant human trade-off, reuse existing dominance semantics rather than manufacturing a vote.

If no grounded feasible proposal exists:
- keep plan / NO_ACTION / BLOCKED;
- no empty collective round.

The model never supplies:
- voter ids;
- candidate ids;
- social policy.

The server derives all of them.

---

# 5. Incident continuity

The R59 collective round belongs to the same R58 group-recovery incident.

Stable identity remains based on:
- Journey;
- active plan / recovery generation;
- affected member;
- shared rendezvous / commitment.

Do not use:
- latest click;
- location observation id;
- route operation id;
- model run id

as the social-decision identity.

Repeated “Adjust together” clicks during the same incident must not create:
- another mission;
- another proposal family;
- another collective clarification.

One incident -> one current decision room.

---

# 6. R58 USER_CHANGE is request authority, not physical truth

R58’s advisory escalation creates a user-request Event with:
- provenance `USER_REPORTED`;
- event type `USER_CHANGE`;
- `physical_presence_claim=false`;
- advisory location authority.

R59 may use that Event as the causal trigger for:
- planning requested by the user;
- proposal generation;
- a collective decision request.

It must not reinterpret that Event as:
- verified lateness;
- device-attested presence;
- provider disruption.

The group is deciding whether to adapt based on advisory evidence that members explicitly chose to share.

If a genuine R57 trusted member-risk Event exists, retain its stronger authority without creating a duplicate R59 incident.

---

# 7. Proposal generation

The R59 Agent may call `request_replan` once per current incident/recovery generation when grounded recovery is useful.

Requirements:
- proposals are normal `ReplanProposal` rows;
- hard constraints remain deterministic;
- protected commitments stay enforced;
- route/provider provenance remains exact;
- no proposal may become active merely because the Agent generated it;
- semantic duplicate proposals remain deduplicated by existing identity rules.

Do not prescribe one fixed solution like WAIT_AS_GROUP.

Hermes may discover:
- a wait-shaped proposal;
- reorder;
- skip flexible stop;
- another grounded shared future;
- NO_ACTION.

The product capability is governed choice, not a hardcoded recovery strategy.

---

# 8. From proposals to one collective round

After grounded proposals exist, Hermes may call `request_collective_decision`.

That call must:
- reuse the R58 mission id;
- reuse the correct trigger Event;
- let the server derive current proposals;
- let the server derive decision-relevant in-force members;
- produce one durable `COLLECTIVE_TRADEOFF` clarification when a real trade-off exists.

Expected mission state:

`WAITING_FOR_MEMBERS`

Expected Operator state should make clear:

> “A shared recovery choice is waiting for the travellers it affects.”

Do not call this an approval yet.

---

# 9. Viewer-specific decision room

Two signed members viewing the same Journey must share the same decision round while retaining separate identity.

Each viewer should see:
- the same grounded option set;
- how many required members exist;
- how many have responded;
- their own `viewer_has_responded`;
- whether they personally may respond;
- coarse member response state.

Each viewer must not see:
- another member’s bearer;
- another member’s raw coordinates;
- hidden private location evidence;
- a forged ability to answer as another member.

The existing signed collective-clarification endpoint is the authority path.

Do not add a browser-supplied “acting member” override.

---

# 10. Response semantics

Each decision-relevant member may submit exactly their own server-derived option.

Server checks must remain:
- member still in force;
- member has JOURNEY_UPDATE capability;
- member is required for this decision;
- proposal belongs to the current server-derived option surface;
- decision epoch is current;
- material world epoch is current.

If one member leaves/expires while waiting:
- do not silently count their missing answer as yes;
- recompute/stale the old decision according to existing authority rules.

History remains durable.

---

# 11. Disagreement is product truth

If required members choose different proposals:

Do not:
- majority vote;
- let OWNER break the tie by default;
- choose the highest utility automatically;
- invent consensus.

Use the existing collective mediation path.

Valid outcomes include:
- a grounded compromise is produced;
- a fresh member decision round is needed;
- mediation remains unresolved;
- external Agent is blocked.

All are legitimate if truthful.

The product must show disagreement as a state, not as system failure.

---

# 12. Unanimous / valid collective resolution

When all currently required decision-relevant members resolve onto one valid proposal through the existing path:

- preserve the selected proposal id;
- preserve decision epoch;
- preserve material-world epoch;
- preserve candidate-surface fingerprint;
- issue/reuse the existing `CollectiveAuthorityReceipt`;
- create the normal server-owned continuation mission if existing semantics require it.

Do not mutate yet merely because the receipt exists.

The receipt means:

> the group authority required for this exact shared future exists and is still current.

It does not erase other policy/approval boundaries.

---

# 13. Mutation boundary

A shared proposal may become active only through the existing governed acceptance path.

`accept_replan` already calls:
- `_collective_resolution_for_child`;
- `collective_authority_preflight`.

Keep that as the final social-authority gate.

R59 must prove:
- no receipt -> shared mutation denied;
- stale/mismatched receipt -> denied;
- correct current receipt -> collective preflight may pass;
- any additional normal confirmation/step-up rule still applies;
- PLAN_ONLY parent mission cannot itself call accept.

Do not weaken the Gateway just to make R59 close.

---

# 14. Group recovery projection should tell one coherent story

R58 has `group_recovery`.
The Operator already has a separate `collective` projection.

R59 should connect them semantically without merging the control planes.

Suggested group_recovery states after planning begins:
- `RECOVERY_EXTERNAL_AGENT_BLOCKED`
- `RECOVERY_PROPOSAL_READY`
- `COLLECTIVE_DECISION_REQUIRED`
- `COLLECTIVE_WAITING_FOR_MEMBERS`
- `COLLECTIVE_MEDIATING`
- `COLLECTIVE_AUTHORIZED`
- `RECOVERY_APPLIED`

Do not duplicate collective member response data inside a second database structure.

It is fine for `group_recovery` to reference/summarize the existing collective state.

---

# 15. UI — make “Adjust together” become a room, not a spinner

After a decision round exists, the member should no longer see only:

> “CityNexus is preparing a governed group-recovery option.”

They should see the existing shared-trip decision UI:
- option labels/deltas;
- who has responded in coarse terms;
- their own action buttons;
- waiting state;
- mediation state;
- authorized state.

Suggested traveller language:

> **Shared recovery**
>
> Sam may miss the protected entry window.
>
> CityNexus found two ways to keep the trip feasible. This changes the shared itinerary, so the affected travellers need to choose.
>
> You · waiting
>
> Sam · answered

Never say “everyone agreed” unless the server projection is `COLLECTIVE_AUTHORIZED`.

---

# 16. Attention routing

If the current viewer must answer the group recovery:
- existing Operator attention should surface `RESPOND_COLLECTIVE`;
- do not bury it under a generic “AI working” card.

If the viewer already answered:
- show waiting, not another action.

If collective state becomes stale:
- do not keep displaying old response buttons.

---

# 17. Focused tests

First run GPT’s pre-baton test:

```bash
cd backend
python -m pytest -q tests/test_r59_collective_group_recovery_plan.py
```

Then add focused R59 capability tests.

Minimum:

1. `COLLECTIVE_JOURNEY_RECOVERY + PLAN_ONLY` allows `request_collective_decision`.
2. same mission still forbids `accept_replan` and all execution tools.
3. unrelated PLAN_ONLY mission does not gain collective-decision capability.
4. R58 USER_CHANGE trigger can generate grounded proposals without becoming verified physical truth.
5. grounded group trade-off -> one `request_collective_decision` -> `WAITING_FOR_MEMBERS`.
6. repeated request for same incident reuses the decision room.
7. required members are server-derived.
8. signed Alice cannot answer for Bob.
9. one response increments one response only.
10. same response replay is idempotent or deterministically rejected according to existing contract.
11. disagreement does not issue authority receipt.
12. disagreement enters existing mediation path.
13. unanimous/current resolution issues the existing collective authority receipt.
14. removed/expired member cannot provide current authority.
15. stale decision epoch invalidates old response surface.
16. `accept_replan` without spendable collective authority is denied.
17. PLAN_ONLY R59 mission cannot itself execute accepted proposal.
18. normal governed continuation can consume valid current collective authority.
19. raw member coordinates never appear in collective projection / Hermes context.
20. TypeScript.
21. one focused two-context Playwright for shared decision room.

Do not rerun R33-R58 historical campaigns.

---

# 18. Focused Playwright

Use two authenticated browser contexts on one shared Journey.

The visible contract:

1. both viewers see the same shared recovery incident;
2. both see the same decision options;
3. each sees themselves correctly;
4. Alice cannot submit as Bob;
5. Alice answers once;
6. Alice sees “answered”; Bob sees one response recorded but retains his own action;
7. Bob answers;
8. if both answers resolve to the same proposal, UI reflects collective authorization;
9. no shared plan mutation occurs merely from rendering/answering;
10. no raw coordinates appear.

The provider/model can be mocked for this UI contract as long as the backend collective authority integration is tested separately.

---

# 19. One bounded R59 product experiment

Do not rerun the R58 strike.

Use one fresh shared Journey and one current group-recovery incident.

Preferred closure does **not** require a final PlanVersion mutation.

Steps:

1. create/select/start one fresh shared Journey;
2. have at least two authenticated in-force members;
3. establish one honest member-risk context;
4. create one grounded feasible group-impacting proposal surface through the normal recovery path;
5. open exactly one collective decision;
6. verify state `WAITING_FOR_MEMBERS`;
7. member A responds through signed normal endpoint;
8. member B responds through signed normal endpoint;
9. if they agree, verify a current collective authority receipt;
10. if they disagree, verify mediation state instead;
11. do not fabricate agreement;
12. do not auto-accept a proposal just to get a mutation;
13. verify active PlanVersion unchanged unless a separately governed acceptance is genuinely exercised;
14. stop.

Valid outcomes:
- `GROUP_RECOVERY_WAITING_FOR_MEMBERS`
- `GROUP_RECOVERY_MEDIATION_REQUIRED`
- `GROUP_RECOVERY_COLLECTIVE_AUTHORIZED`
- `GROUP_RECOVERY_EXTERNAL_AGENT_BLOCKED`
- `GROUP_RECOVERY_NO_GROUNDED_TRADEOFF`

If the configured external Hermes is still unavailable, **do not repeat the R58 provider strike**. Prove the server-native proposal -> collective-decision authority handoff with existing Gateway/domain machinery and record external orchestration as the limitation.

R59’s product target is the shared decision room, not proving the model vendor is online.

---

# 20. Result document

Write:

`REVOLUTION_R59_COLLECTIVE_GROUP_RECOVERY_CLOSURE_RESULT.md`

Include:
- exact implementation SHA;
- GPT pre-baton seam test result;
- focused R59 test counts;
- TypeScript;
- Playwright;
- fresh Journey id;
- member ids (non-secret only);
- risk authority;
- proposal ids/statuses;
- trigger Event id/type/provenance;
- mission id/status;
- collective clarification id;
- required member ids/count;
- response count;
- mediation state if any;
- collective authority receipt id if any;
- active PlanVersion before/after;
- mutation count;
- external Agent status;
- limitations.

Never write:
- “everyone agreed” without a valid current authority receipt;
- “applied” when only authorized/pending;
- “verified location” for browser GPS;
- “live traffic” for a route provider capture that is not live traffic.

---

# Stop condition

Stop when CityNexus can truthfully answer:

> **“This recovery would change the shared Journey. Which travellers actually need to decide, who has responded, are we in disagreement, and do we have a current collective authority receipt that can legally carry this exact proposal forward?”**

End-user capability:

> **“Adjust together is now genuinely together: CityNexus can put a shared recovery in front of the people it affects, keep each person’s answer separate, preserve disagreement instead of faking consensus, and only let the shared Journey move forward when the group’s real authority is there.”**
