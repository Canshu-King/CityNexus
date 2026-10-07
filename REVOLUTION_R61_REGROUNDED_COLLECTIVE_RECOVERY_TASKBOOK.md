# REVOLUTION R61 — Re-grounded Collective Recovery Loop

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

Keep this product sentence visible:

> **If the group agreed on a recovery but reality changes before it can be applied, CityNexus no longer asks everyone to vote again on a dead plan. It preserves the old decision as history, re-grounds one fresh recovery from the current world, and only then opens a new shared decision if a real human trade-off still exists.**

This is the continuation of R56–R60:
- R56: I went off route.
- R57: our group split.
- R58: should the group adapt?
- R59: who actually decides?
- R60: how is that exact consent spent once?
- **R61: what happens when the agreed future itself dies before commit?**

Do not turn R61 into a verifier campaign, a retry loop, or a second planning stack.

---

## Starting branch

`gpt/revolution-r33-open-world-journey-adaptation`

Codex R60 implementation:
- `a3549f91eab04790bb3eda4bb6411a70b299fb7e`

Codex R60 result:
- `1663473f1081a5133bd79955a9b7511ce3f89a4d`

R60 truthful boundary:
- authenticated `JOURNEY_UPDATE` spend edge exists;
- server selects the exact proposal;
- generic collective proposal accept is refused;
- apply is exactly-once/idempotent;
- current collective receipt is revalidated before mutation;
- active PlanVersion can move once through the existing atomic replan path;
- stale consent can preserve history and produce a successor decision round;
- R60 product run itself was local/fixture-backed, not provider-live.

Do not upgrade those claims.

---

# 0. GPT post-R60 review fixes already committed — test them first

GPT found a semantic bug after R60:

The apply endpoint treated nearly every downstream HTTP 409 as “consent stale, ask the humans again.”

That is wrong.

Two different failure classes must remain separate:

### A. consent / authority stale

Examples:
- decision epoch changed;
- material-world consent epoch changed;
- candidate-surface fingerprint changed;
- authority receipt stale/missing/mismatched;
- required-member authority changed;
- RecoveryEpoch superseded.

These may require renewed collective authority **after a current grounded surface exists**.

### B. proposal no longer executable

Examples:
- current feasibility fails;
- a new protected/C4 commitment cannot be preserved;
- mobility evidence is missing/invalid;
- current execution cursor cannot map into the candidate;
- the proposal is no longer a safe executable future.

Human beings voting again cannot fix B.

Opening a new room around the same invalid proposal would be authority laundering.

GPT directly committed these post-review fixes:

- `77d3b52fcd96e4315bcd84d73bf72d18f38a742a`
  - separates consent-staleness codes from invalid-plan failures;
  - returns `GROUP_RECOVERY_REPLAN_REQUIRED` for a dead plan;
  - re-consent only sees proposals bound to the current RecoveryEpoch;
  - fixes group-recovery lineage lookup so a re-consent child does not relabel itself as the original R58 root.

- `1d1ac98028e1f91d21a330164cf27eb161840bd6`
  - traveller copy distinguishes “your consent expired” from “this concrete plan is no longer executable.”

- `3a6d23c52c745618d84454bf06ce6e89e15baa88`
  - pins the consent-vs-replan boundary in tests;
  - updates the R60 fixture to compute a real semantic RecoveryEpoch fingerprint instead of a fake literal.

- `3a231ede22790d3f444daedead2107ef831d9b42`
  - a stale consent only returns `...RECONSENT_REQUIRED` when a current grounded decision surface actually exists;
  - if the old RecoveryEpoch was superseded and no current proposals exist, the user receives `GROUP_RECOVERY_REPLAN_REQUIRED`, not a fake empty re-vote.

- `11784864165b976dd6efae1ec3c2a416989aa037`
  - focused regression for the unavailable-reconsent -> replanning boundary.

- `759b0681ffc875033c0f7d03dc6bceb3e8d1789a`
  - exposes group-recovery 409s through CityNexus' existing typed error envelope;
  - the product code is carried in `error.reason_code` and structured state in `error.details`, rather than being stringified inside `HTTPException.detail`.

- `f4e698a33323dc5e7d486b045e600721c5dd390e`
  - makes LiveRecovery read that real CityNexus error envelope;
  - `GROUP_RECOVERY_REPLAN_REQUIRED` now gets different traveller copy from stale-consent/re-consent.

- `b25a9d73ef7961795ee76251c8f63f581b495935`
  - pins the typed conflict envelope in the focused R60 tests.

These GPT commits have **not** been run locally by Codex yet.

First run the narrow R60 file plus directly affected collective authority tests. Repair only real failures. Do not loosen the new boundary.

---

# 1. Product gap

R60 can now say:

> “The group agreed, but this proposal can no longer be safely applied.”

That is correct, but it still leaves the traveller with a dead end.

R61 must continue:

> “I kept the old agreement as history. I am grounding a new shared recovery against what is true now. I will not ask the group again until there is something current and feasible to decide.”

The critical product chain is:

```
old collective authorization
  -> apply attempt
  -> current proposal becomes unexecutable / RecoveryEpoch rolls
  -> old consent becomes historical / unspendable
  -> one bounded re-ground mission
  -> current provider / Place / route / commitment truth
  -> current feasible proposal surface
  -> if human trade-off remains: one fresh collective room
  -> otherwise: truthful no-action / dominant / blocked state
```

No mutation occurs in R61 merely because replanning succeeded.

R60 remains the only collective apply/spend edge.

---

# 2. First-class R61 state

Add a durable server-owned group recovery state, not just an HTTP error message.

Suggested states:

- `RECOVERY_REPLAN_REQUIRED`
- `RECOVERY_REGROUNDING`
- `RECOVERY_REGROUNDED_NO_ACTION`
- `RECOVERY_REGROUNDED_DOMINANT`
- `RECOVERY_REGROUNDED_DECISION_REQUIRED`
- `RECOVERY_REGROUND_EXTERNAL_AGENT_BLOCKED`
- `RECOVERY_REGROUND_NO_FEASIBLE_OPTION`

Do not infer this only from a transient React error.

The state must survive:
- refresh;
- another member opening the Journey;
- the original spender closing their browser.

Use durable mission/audit/domain truth.

---

# 3. Stable incident, new recovery generation

R61 remains the same group-recovery incident when:
- Journey active plan is still the same;
- affected member/rendezvous identity is still the same;
- the group is still solving the same separation/lateness problem.

But it may move to a **new RecoveryEpoch**.

Keep separate identities:

- `group_recovery.incident_key` = product incident;
- `RecoveryEpoch.id/generation` = executable world generation;
- collective clarification id = one human decision round.

Never use one as a substitute for another.

A new RecoveryEpoch does not erase the incident.
A fresh decision round does not create a new incident.
A new proposal does not inherit old consent.

---

# 4. Durable replan-required receipt

When R60 apply returns `GROUP_RECOVERY_REPLAN_REQUIRED`, persist enough truth to resume without the original browser.

Suggested audit/state payload:

```json
{
  "kind": "GROUP_RECOVERY_REPLAN_REQUIRED",
  "incident_key": "...",
  "failed_proposal_id": "...",
  "failed_decision_mission_id": "...",
  "old_authority_receipt_id": "...",
  "old_recovery_epoch_id": "...",
  "current_recovery_epoch_id": "...",
  "cause_class": "PROTECTED_COMMITMENT_CHANGED",
  "cause": "...",
  "plan_unchanged": true
}
```

Do not expose raw provider payloads or coordinates.

Classify causes server-side into a small product set:
- `RECOVERY_EPOCH_CHANGED`
- `FEASIBILITY_CHANGED`
- `PROTECTED_COMMITMENT_CHANGED`
- `MOBILITY_EVIDENCE_INVALID`
- `EXECUTION_CURSOR_CHANGED`
- `PROPOSAL_NO_LONGER_CURRENT`
- `UNKNOWN_FAIL_CLOSED`

The raw internal exception remains audit/debug detail, not traveller copy.

---

# 5. One re-ground mission, no retry storm

For one current:

`incident_key + current RecoveryEpoch`

there may be at most one current re-ground mission.

Repeated:
- page refresh;
- apply retry;
- another member viewing;
- Guardian pulse

must reuse that mission.

Stable key suggestion:

```
group-recovery-reground:
  journey
  incident_key
  current_recovery_epoch_id
```

Do not key it by:
- click id;
- old proposal id;
- model run id;
- observation UUID.

If the RecoveryEpoch changes again while re-grounding, the old re-ground mission becomes stale and a new generation may begin.

---

# 6. Planning authority

Re-grounding is non-mutating.

Use:
- `PLAN_ONLY`;
- existing Hermes/native mission runtime;
- existing `request_replan`;
- existing bounded place/route acquisition tools where already allowed;
- existing protected commitment and feasibility gates;
- existing proposal identity/dedup.

Do not grant:
- `accept_replan`;
- booking/payment mutation;
- commitment mutation;
- direct PlanVersion activation.

The group already asked CityNexus to help adapt.
R61 does not need a second “Adjust together” click merely to **plan again** after the agreed candidate became impossible.

But a new shared mutation still needs current collective authority.

---

# 7. Do not reuse old proposals across RecoveryEpochs

Hard rule:

A proposal from a superseded RecoveryEpoch is history.

It may help explain:
> “what the group had chosen before the world changed”

It may not be:
- presented as a current option;
- copied into a fresh decision room;
- accepted;
- used to mint a new receipt;
- treated as grounded by current provider facts.

R61 proposals must be created/revalidated in the current RecoveryEpoch.

Add a server test that a semantically identical old proposal UUID cannot cross this boundary.

---

# 8. Re-ground current world facts

For the current incident, derive only the facts needed to produce a new feasible shared future.

Potential inputs:
- current active PlanVersion;
- current member-risk / rendezvous context;
- current protected commitments;
- current canonical Place opening/cost truth;
- current route evidence;
- current member capabilities;
- current explicit Journey-scoped preferences;
- current RecoveryEpoch.

Preserve provenance exactly:
- LIVE_PROVIDER_CAPTURE remains live provider capture, not live traffic unless it actually is;
- CAPTURED_REPLAY stays replay;
- USER_REPORTED stays user-reported;
- browser location remains advisory.

Do not upgrade evidence because R61 needs an answer.

---

# 9. Proposal output

A re-ground mission may produce:

### NO_ACTION
The current active Journey is now the safest answer.

### ONE DOMINANT GROUNDED FUTURE
There is one current feasible shared recovery and no material human trade-off under existing collective policy.

Do not auto-apply it in R61.
Project it truthfully and let existing policy decide what next authority is required.

### HUMAN TRADE-OFF
At least two current grounded futures differ materially for decision-relevant members.

Only now create one fresh collective room.

### NO FEASIBLE OPTION
Keep current active Journey and explain that CityNexus could not find a safe shared adaptation.

### EXTERNAL BLOCKED
Agent/provider unavailable.
No deterministic mutation fallback.

---

# 10. Fresh collective room only after grounding

R61 must not create a new `COLLECTIVE_TRADEOFF` room just because old consent went stale.

Required order:

1. old authority becomes unspendable/history;
2. current RecoveryEpoch is established;
3. current proposals are produced;
4. deterministic feasibility passes;
5. current member-fit/collective classification is computed;
6. **only if HUMAN_TRADEOFF_REQUIRED**, call/open `request_collective_decision`;
7. fresh room gets:
   - new clarification id;
   - new decision epoch;
   - current candidate surface;
   - current required signers;
   - empty responses.

This is the core R61 invariant.

---

# 11. Preserve the previous group decision as history

The UI should be able to say:

> “Earlier, the group agreed to Garden recovery. Before it was applied, a protected booking changed. That agreement is preserved in history but can no longer be used.”

Then:

> “CityNexus is checking new options against the current trip.”

Do not delete:
- old clarification;
- old responses;
- old receipt;
- old proposal;
- old audit.

Mark them stale/invalid/retired according to existing domain semantics.

History is not current authority.

---

# 12. Operator projection

Connect the R60 `journey.group_recovery.replan_required` audit/state into `group_recovery`.

Minimum projection fields:

```json
{
  "state": "RECOVERY_REGROUNDING",
  "incident_key": "...",
  "failed_proposal_id": "...",
  "cause_class": "PROTECTED_COMMITMENT_CHANGED",
  "old_decision": {
    "clarification_id": "...",
    "authority_receipt_id": "...",
    "selected_proposal_id": "..."
  },
  "current_recovery_epoch_id": "...",
  "reground_mission": {
    "id": "...",
    "status": "RUNNING"
  }
}
```

Normal UI must not expose:
- raw exception stack;
- exact member coordinates;
- raw provider payloads;
- bearer/token identifiers.

---

# 13. Traveller UX

### RECOVERY_REPLAN_REQUIRED

> **The agreed plan is no longer safe to apply.**
>
> The group’s earlier choice is saved, but something material changed before it could be used.
>
> CityNexus is checking a new shared recovery against the current trip.

No “vote again” button yet.

### RECOVERY_REGROUNDING

> **Checking a new shared recovery**
>
> Your current Journey remains active while CityNexus verifies new options.

### Fresh trade-off ready

> **The situation changed, so there is a new decision**
>
> The earlier answers do not carry over. These options are grounded in the current trip.

Then reuse the R59 decision room.

### No feasible option

> **No safe shared adjustment is available right now**
>
> Your current Journey has not changed. You can keep regrouping on the existing route or handle the next commitment manually.

---

# 14. Automatic vs explicit start

Preferred behavior:

A valid `GROUP_RECOVERY_REPLAN_REQUIRED` transition schedules/creates exactly one non-mutating re-ground mission automatically.

Why this is allowed:
- the travellers already explicitly asked CityNexus to adjust together;
- planning is non-mutating;
- the old selected proposal failed at the final spend boundary;
- restarting planning is continuation of the same request, not a new physical action.

Do not auto-start if:
- the original group recovery was never user-requested and only advisory;
- incident no longer exists;
- Journey is completed;
- no in-force Journey member can authorize updates;
- active plan changed into a different product incident.

In those cases project a stopped/blocked state.

---

# 15. External Agent unavailable

Do not repeat R58’s strike merely to prove the provider is offline again.

If Hermes is unavailable during R61:
- one bounded start attempt;
- `RECOVERY_REGROUND_EXTERNAL_AGENT_BLOCKED`;
- current plan unchanged;
- no fake proposal;
- no stale-proposal reuse;
- no deterministic substitute pretending to be Hermes.

The UI should still preserve:
- old group decision history;
- current rendezvous guidance if independently available.

---

# 16. Focused tests

First run GPT’s post-R60 tests and repair only genuine failures.

Then add R61 tests:

1. invalid-plan 409 -> `GROUP_RECOVERY_REPLAN_REQUIRED`, not automatic re-consent.
2. old room remains historical; old receipt is not silently reminted.
3. superseded RecoveryEpoch proposals cannot enter current decision surface.
4. replan-required state survives a new HTTP request/browser.
5. first replan-required transition creates one re-ground mission.
6. repeated click/view reuses the same mission for incident + current RecoveryEpoch.
7. new RecoveryEpoch creates a new re-ground generation, not reuse of stale run.
8. re-ground mission is PLAN_ONLY and has no accept/mutation tools.
9. no current grounded proposal -> no collective room.
10. one grounded option -> no fake two-option vote.
11. HUMAN_TRADEOFF_REQUIRED with current options -> exactly one fresh collective room.
12. fresh room has new clarification id/decision epoch and zero inherited responses.
13. old signed responses remain historical only.
14. current required members are recomputed from in-force roles/capabilities.
15. raw coordinates are absent from the re-ground mission context.
16. provider/replay provenance remains exact.
17. external Agent unavailable -> BLOCKED + 0 mutation.
18. successful current proposal generation still does not mutate active PlanVersion.
19. generic old proposal accept remains refused.
20. TypeScript/build.
21. one focused two-context Playwright.

Do not rerun R33–R60 historical campaigns.

---

# 17. Focused Playwright

Two signed contexts on one shared Journey.

Start from a state where:
- previous collective decision exists;
- old selected proposal cannot be applied;
- R61 re-ground is active or completed.

Prove:

1. both viewers see the same prior decision history;
2. neither sees an apply button for the dead proposal;
3. neither sees stale proposal generic accept controls;
4. while re-grounding, both see current Journey unchanged;
5. once a fresh trade-off exists, both see the same new room;
6. new room starts at 0/N responses;
7. earlier answers are visibly not carried over;
8. each member still answers only their own slot.

UI data may be mocked for rendering; backend state transitions must be real domain/API tests.

---

# 18. One bounded R61 product experiment

Do not rerun the R58/R59/R60 historical strikes.

Preferred:
- one fresh shared Journey;
- at least two signed members;
- one honest group-risk context;
- one provider-grounded initial recovery surface if the environment supports it;
- establish one collective choice;
- before apply, introduce one **real current material change** that makes that selected future stale/unexecutable;
- verify old authority cannot be spent;
- run exactly one R61 re-ground generation;
- observe one truthful outcome.

Valid outcomes:

- `REGROUNDED_COLLECTIVE_DECISION_REQUIRED`
- `REGROUNDED_DOMINANT_OPTION`
- `REGROUNDED_NO_ACTION`
- `REGROUNDED_NO_FEASIBLE_OPTION`
- `REGROUND_EXTERNAL_AGENT_BLOCKED`

Do not retry to force a proposal.

If provider-grounded initial proposals cannot be obtained:
- use one server-native bounded closure;
- explicitly label it test/domain evidence;
- do not claim live product execution.

---

# 19. Result document

Write:

`REVOLUTION_R61_REGROUNDED_COLLECTIVE_RECOVERY_RESULT.md`

Include:
- exact implementation SHA;
- GPT post-R60 fix test counts;
- R61 focused test counts;
- TypeScript/build/Playwright;
- fresh Journey id if product experiment exists;
- incident key;
- old RecoveryEpoch id/generation;
- current RecoveryEpoch id/generation;
- failed old proposal id/status;
- old clarification id/status;
- old receipt id/status;
- replan-required cause class;
- re-ground mission id/status;
- Agent/provider provenance;
- current proposal ids/statuses;
- collective classification;
- fresh clarification id if created;
- required member count;
- inherited response count (must be 0);
- active PlanVersion before/after;
- mutation count;
- limitations.

Never claim:
- old consent became current again;
- an old proposal crossed RecoveryEpoch generations;
- re-grounding applied a plan;
- a seeded route was live provider truth.

---

# Stop condition

Stop when CityNexus can truthfully answer:

> **“The group’s chosen recovery stopped being executable before commit. I kept their old decision as history, discarded its stale executable authority, grounded a new recovery from the current world, and only asked the group again once there was a new current choice worth deciding.”**

End-user capability:

> **“If reality changes after we agree, CityNexus does not make us approve a broken plan again. It finds a new safe group option first, then asks us only if there is a real new choice.”**
