# REVOLUTION R62 — Group Recovery Follow-through / Rejoin Closure

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

Keep this product sentence visible:

> **After a shared recovery is applied, CityNexus does not stop at “the plan changed.” It tells each traveller what they personally need to do next, tracks only explicit authenticated execution progress, recognizes when the separated group has actually rejoined, closes the recovery incident, and resumes normal Journey operation.**

This is the continuation of R56–R61:

- R56: I went off route.
- R57: our group split.
- R58: should the group adapt?
- R59: who actually decides?
- R60: how is that exact collective consent spent once?
- R61: what if the agreed future dies before commit?
- **R62: after recovery succeeds, how does the group actually get back together and continue?**

R62 is not a second collective-authority system, not a verifier round, not a provider campaign, and not a new movement engine.

---

## Starting truth

Branch:

`gpt/revolution-r33-open-world-journey-adaptation`

R61 implementation:

- `05a45d917156f574327b3c92d3f22d517918eb4a`

R61 result:

- `a81c3a7821af5af2d4af89d92529001b722ad010`

Truthful R61 boundary:

- stale collective recovery can be preserved as history and re-grounded against the current RecoveryEpoch;
- old authority/proposals cannot cross into the current recovery generation;
- re-grounding is PLAN_ONLY and cannot mutate the Journey;
- a fresh collective room is opened only from current grounded feasible human trade-offs;
- local domain/API/UI closure passed;
- no real provider-backed Journey or real external Agent run was claimed;
- no WB2api/provider behavior changed.

Do not upgrade those claims.

Keep:

`CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`

Do not rerun R58–R60 historical strikes.

Do not touch WB2api/provider unless a new, reproducible R62 product defect proves it is necessary.

---

# 1. Product gap

R60 can apply one collectively authorized recovery.

R61 can replace a dead agreed future with a fresh current recovery surface.

But the traveller experience can still end at:

> “The shared recovery was applied.”

That is not enough.

A real group trip needs the next loop:

```
shared recovery applied
  -> every current member sees one personal next action
  -> members explicitly report execution progress
  -> CityNexus projects who is moving / arrived / still separated
  -> rendezvous condition becomes true
  -> recovery incident closes once
  -> all members return to one normal Journey execution surface
  -> Guardian/Operator continues from the current active PlanVersion
```

The new user capability is:

> **The group can recover, physically rejoin, and continue the Journey without the recovery room becoming a permanent side-state.**

---

# 2. Do not infer physical reunion

R62 must not claim that people have rejoined from:

- browser refresh;
- elapsed time;
- plan activation;
- route ETA;
- model prediction;
- browser geolocation alone;
- another member's statement;
- provider place/route facts.

Rejoin truth must come from existing authenticated execution actions / explicit member progress that CityNexus already trusts for Journey state, such as existing depart / arrive / begin / complete semantics where applicable.

If the current product has no exact reusable execution signal for one required member, remain:

- `REJOIN_IN_PROGRESS`, or
- `REJOIN_CONFIRMATION_REQUIRED`.

Do not manufacture arrival.

---

# 3. Reuse existing Journey execution, do not build a second state machine

Prefer existing:

- active PlanVersion;
- execution cursor / leg / activity semantics;
- `/depart`, `/arrive`, `/begin`, `/complete` paths where already canonical;
- JourneyMember identity/capability;
- group recovery `incident_key`;
- RecoveryEpoch;
- Operator projection;
- Guardian pulse/drift semantics;
- authenticated traveller actions.

Do not create a parallel:

- GroupExecution table;
- GroupArrival engine;
- second itinerary;
- second active-plan pointer;
- client-owned reunion state.

A small durable server-owned follow-through receipt/state is acceptable only if it binds existing execution truth into the group-recovery incident.

---

# 4. First-class follow-through state

Project one durable group-recovery continuation state after a recovery has actually been applied.

Suggested states:

- `RECOVERY_APPLIED_REJOIN_PENDING`
- `REJOIN_IN_PROGRESS`
- `REJOIN_CONFIRMATION_REQUIRED`
- `REJOINED`
- `RECOVERY_CLOSED`

Use existing names if equivalent states already exist.

Required properties:

- survives refresh;
- is shared across members;
- comes from server/domain truth;
- cannot move to REJOINED because React locally observed a button click;
- cannot regress from closed back into the same recovery incident unless a genuinely new disruption occurs.

---

# 5. Bind follow-through to the exact applied recovery

The follow-through must be tied to:

- Journey id;
- stable group-recovery `incident_key`;
- applied proposal id;
- applied PlanVersion id;
- RecoveryEpoch at application;
- collective authority receipt id where one existed;
- applied-at audit;
- current in-force required traveller set.

Do not accidentally attach old R58/R59/R60 history to a later unrelated split.

If the active PlanVersion changes for an unrelated later reason, the old follow-through must not pretend it still owns current execution.

---

# 6. Per-member next action

After a shared recovery is applied, each in-force member should see a personal next action derived from the same active Journey.

Examples:

- “Head to the current rendezvous.”
- “Continue to the next activity; Alex is catching up.”
- “You have arrived. Waiting for one traveller.”
- “The group has rejoined. Continue together.”

The server should derive enough structured data for the UI to render this without inventing semantics from list order.

Suggested projection:

```json
{
  "state": "REJOIN_IN_PROGRESS",
  "incident_key": "...",
  "active_plan_version_id": "...",
  "rendezvous": {
    "place_id": "...",
    "display_name": "..."
  },
  "viewer": {
    "member_id": "...",
    "status": "MOVING_TO_RENDEZVOUS",
    "next_action": "ARRIVE_AT_RENDEZVOUS"
  },
  "members": [
    {"member_id": "...", "status": "ARRIVED"},
    {"member_id": "...", "status": "MOVING_TO_RENDEZVOUS"}
  ],
  "rejoined": false
}
```

Privacy-safe labels are enough. Do not expose raw coordinates or hidden preference/profile data.

---

# 7. Member progress must be identity-bound

When strict auth is configured:

- progress comes from a signed traveller principal;
- principal must map to the in-force JourneyMember whose progress is changing;
- one member cannot mark another member arrived;
- a VIEW-only member cannot mutate Journey execution merely because they can see the group recovery;
- retain existing capability checks for Journey execution.

If existing execution endpoints already enforce this correctly, reuse them.

Do not add a weaker R62-only update endpoint.

---

# 8. Define the rendezvous condition from the active plan

R62 needs one server-owned answer to:

> What does “we are back together” mean for this applied recovery?

Prefer deriving it from the applied/current plan and the recovery incident.

A valid rendezvous condition may be:

- all required current travelling members have explicitly arrived at the same recovery rendezvous activity/place; or
- the active plan's recovery branch has advanced to the first shared post-recovery activity and every required current member has explicit execution state consistent with joining it.

Do not use:

- same city;
- same ETA;
- same browser GPS vicinity;
- the recovery proposal being ACCEPTED;
- collective receipt existence.

If the exact rendezvous cannot be resolved from current domain truth, return `REJOIN_CONFIRMATION_REQUIRED` and keep the incident open.

---

# 9. Membership changes while rejoining

Membership may change after recovery application.

Handle current in-force membership deliberately:

- removed/expired members must not block reunion forever;
- newly added members must not silently become part of the old recovery incident unless current policy/domain semantics say they are part of the active travelling group;
- capability changes must remain fail-closed for mutation;
- old collective signatures remain history and are not rewritten.

If membership change creates a new decision-relevant disruption, that is a new recovery problem, not a reason to corrupt R62 closure.

---

# 10. Close exactly once

When the reunion condition becomes true:

1. persist one terminal recovery-follow-through result;
2. mark the stable group-recovery incident closed/resolved using existing event semantics where possible;
3. do not mutate the active PlanVersion merely to close the incident;
4. retire/hide stale recovery CTA surfaces;
5. preserve the full prior collective/re-ground history;
6. make Operator projection return to normal active Journey execution.

Repeated GETs, refreshes, progress replays, or duplicate arrival calls must not create duplicate closure events.

Suggested terminal audit:

```json
{
  "kind": "GROUP_RECOVERY_REJOINED",
  "incident_key": "...",
  "applied_plan_version_id": "...",
  "recovery_epoch_id": "...",
  "member_ids": ["..."],
  "rendezvous_place_id": "...",
  "closed_at": "...",
  "plan_unchanged_by_closure": true
}
```

---

# 11. Guardian / Operator continuation

This is the important Revolution connection.

Once R62 closes the recovery incident:

- the Operator should no longer foreground the old recovery room;
- the same active Journey remains the source of truth;
- normal live-progress drift/catch-up monitoring may continue;
- a later genuine disruption may create a new incident;
- no “recovery mode forever” after success.

Do not add a special Guardian polling loop only for R62.

Use existing durable events/state so the continuously operating Journey loop naturally continues.

---

# 12. UI behavior

The group recovery surface should visibly transition.

### After recovery apply

Show:

> “The shared recovery is active. Rejoining the group.”

Each member gets their own current action.

### While another member is still moving

Show a privacy-safe status such as:

> “1 traveller has arrived; 1 is still on the way.”

Do not expose precise location unless already authorized elsewhere.

### Viewer has arrived

Show:

> “You’re at the rendezvous. Waiting for the rest of the group.”

### Reunion complete

Show:

> “Everyone has rejoined. CityNexus is continuing the Journey.”

Then leave/retire the recovery decision UI and return attention to normal execution.

Do not keep:

- Apply shared recovery;
- answer old collective room;
- stale proposal buttons;
- “re-grounding” spinner

visible after terminal rejoin closure.

---

# 13. No new authority inflation

R62 may autonomously:

- project current member execution state;
- recognize that explicit existing execution facts satisfy the reunion condition;
- close the recovery incident;
- resume normal non-mutating Operator guidance.

R62 may not autonomously:

- change the active PlanVersion;
- mark a traveller arrived;
- create fake execution events;
- accept a replan;
- spend collective authority;
- change a protected commitment;
- book/pay/cancel;
- infer consent.

If another plan mutation becomes necessary, return to existing recovery/authority machinery.

---

# 14. Failure / ambiguous states are product states

If only one of two members has authenticated progress:

- stay open.

If one member cannot be mapped to the rendezvous:

- `REJOIN_CONFIRMATION_REQUIRED`.

If active plan lineage changed unexpectedly:

- fail closed and do not close the old incident as successful reunion.

If an execution action is replayed:

- preserve idempotency.

If Agent/provider is unavailable:

- irrelevant unless R62 truly needs new external reasoning. Do not manufacture an Agent run just to call the round “live.”

---

# 15. Focused implementation targets

Codex should first inspect, not rewrite blindly:

- group recovery projection in `backend/app/operator_projection.py`;
- R60/R61 collective recovery state in `backend/app/main.py`;
- existing Journey execution progress/state transition endpoints;
- existing event/recovery incident resolution semantics;
- `frontend/src/features/execution/LiveRecovery.tsx`;
- the normal Journey execution UI that should become primary again after closure.

Prefer the smallest domain addition that connects these already-existing systems.

Do not move WB2api/provider code unless a focused failing R62 test demonstrates a real dependency defect.

---

# 16. Required focused tests

Add only tests that prove the new capability.

At minimum:

1. **two-member follow-through**
   - one shared recovery is already applied;
   - member A explicitly reaches the rendezvous;
   - state remains `REJOIN_IN_PROGRESS`;
   - member B explicitly reaches it;
   - state becomes `REJOINED/RECOVERY_CLOSED`;
   - active PlanVersion does not change during closure.

2. **identity boundary**
   - member A cannot submit execution progress for member B.

3. **no inferred reunion**
   - elapsed ETA / GET / refresh / plan acceptance alone cannot close the incident.

4. **replay**
   - duplicate authenticated arrival/progress does not emit duplicate recovery closure.

5. **UI**
   - two distinct member contexts receive member-specific copy;
   - final state retires old recovery controls and returns to normal Journey continuation.

Do not broaden into a historical R58–R61 regression campaign.

Run only directly affected lineage tests necessary to catch real regressions.

---

# 17. One bounded product experiment

The stop condition is one fresh R62 Journey, not a verifier carousel.

Preferred experiment:

1. create/use one fresh two-member Journey with signed distinct principals;
2. get to one applied shared recovery using the shortest truthful setup available;
3. do **not** rerun historical R58–R60 strikes merely to prove their old claims;
4. submit authenticated execution progress for member A;
5. observe server/UI still says one member pending;
6. submit authenticated execution progress for member B;
7. observe one terminal reunion closure;
8. verify active PlanVersion stayed the applied recovery plan;
9. verify the old recovery decision controls are gone and normal Journey execution is primary.

Evidence may be local/domain-backed if that is what the environment genuinely supports.

Do not claim:

- physical-world reunion unless the inputs were actually physical-world signals with appropriate provenance;
- live provider grounding if no provider was called;
- live Agent execution if no Agent ran.

The product closure here is the **identity-bound follow-through loop**, not provider freshness.

---

# 18. Stop rules

Stop and report honestly if:

- the existing Journey execution model cannot identify a rendezvous without inventing a second state machine;
- signed member progress cannot be connected without weakening auth;
- closure would require guessing physical presence;
- implementation reveals a concrete upstream product defect.

If there is a real upstream defect, fix the narrow defect and continue.

Do not respond by rerunning old strikes.

Do not turn R62 into another receipt/verifier series.

---

# 19. Definition of done

R62 is done when a normal user can observe this full new loop:

> “Our shared recovery was applied. I can see what I personally need to do. My companion can see their own next step. When each of us explicitly reaches the shared rendezvous, CityNexus recognizes that we are together again, closes the recovery incident once, and continues managing the same Journey.”

And the technical truth remains:

- same active Journey;
- no fake location;
- no fake consent;
- no authority inflation;
- no duplicate closure;
- no historical proposal/response reuse;
- no provider provenance upgrade;
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.

That is the R62 product leap.
