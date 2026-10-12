# Revolution R30 — Consent Epoch Shock Recovery

## Binding state

Branch:

`gpt/revolution-r30-consent-epoch-shock-recovery`

Base commit:

`c524092cd6d0adda85bb376e5fae08359e519f35`

That commit closes R29's causal contract with:

- R29 machine verdict: 13 PROVEN / 0 NOT_PROVEN / 0 CONTRADICTED
- inherited R28 verdict: 14 PROVEN / 0 NOT_PROVEN / 0 CONTRADICTED
- a real external round-1 AgentRun
- a real external mediator AgentRun
- renewed authenticated member consent
- a new compound grounded future rather than laundering either disputed round-1 option
- same-run approval and exactly-once continuation

Do **not** reopen R29 as R29.1.

## Why R30 exists

R29 proved that CityNexus can respect social authority when people disagree.

R30 must prove something harder:

> human consent is authority only for the material reality in which that consent was given.

Today the system already catches several stale cases:

- the active base plan changed;
- the selected proposal is no longer PRESENTED;
- the selected plan is no longer a CANDIDATE;
- hard feasibility revalidation fails;
- a newer resolved mediation supersedes an older one.

But there is a remaining semantic authority gap.

The collective decision epoch currently fingerprints the base plan, proposal/plan identities, statuses, member roles/capabilities/preferences, and trigger identity. It does **not** yet prove that the material world facts supporting the selected future are still the same when renewed consent is consumed.

A selected plan can remain technically selectable while the facts that made the trade-off meaningful have changed: travel duration, opening evidence, cost evidence, affected optional experience, or another decision-material provider observation.

R30 makes consent fact-bound rather than merely ID-bound.

## Revolution intent

Do not turn this into another receipt project.

The product capability is:

> CityNexus can survive a real post-consent shock without silently spending stale human authority.

The desired behavior is:

```text
people converge on future A
  -> consent becomes bound to decision-material reality epoch E1
  -> reality materially changes before A is consumed
  -> old consent is rejected, not stretched
  -> autonomous recovery creates a new grounded future
  -> only decision-relevant humans are asked again
  -> renewed consent binds to E2
  -> execution resumes exactly once
```

The system must also avoid the opposite failure:

> irrelevant evidence churn must not invalidate consent.

R30 is therefore about **semantic staleness**, not timestamp staleness.

---

# Phase 0 — one surgical R29 regression, then move on

R29 added generic compound opportunity replanning in production code. Add only one narrow regression test so the capability cannot silently disappear while R30 changes authority logic.

Prove:

- two provider-grounded opportunity candidates can form one compound replan proposal;
- both inserted Place IDs are persisted in the proposed plan;
- the protected anchor remains locked/preserved;
- canonical route evidence is required for every newly adjacent leg;
- no hand-built proposal bypasses normal `request_replan` construction.

Do not build a new R29 suite.

After that, leave R29 closed.

---

# Phase 1 — define a decision-material authority epoch

## Existing useful machinery

Reuse rather than replace:

- `collective_decision_epoch`
- `collective_proposal_receipt`
- `pending_resolved_mediation_selection`
- `collective_mutation_gate`
- plan evidence / integrity hashes already persisted on candidate plans
- provider observations and incident recovery evidence
- active Journey member roles/capabilities/preferences

Do **not** create a second parallel truth store.

## Required semantic contents

The authority epoch used for renewed collective consent should include only material inputs needed to interpret the decision.

At minimum investigate and bind:

1. Journey ID.
2. Active/base plan version ID.
3. Selected proposal ID and selected plan version ID.
4. The selected plan's immutable plan/evidence fingerprint or integrity hash.
5. Decision-relevant member IDs.
6. Their in-force role/capability state.
7. Their explicit Journey-scoped preferences used in the decision.
8. The selected candidate's fit subject:
   - changed optional Place IDs;
   - changed optional tags/categories.
9. The hard-feasibility evidence identity that materially supports the selected future:
   - route/mobility snapshot identity for relevant legs;
   - opening/cost provider evidence identity where already represented by canonical plan evidence.
10. The social decision lineage / trigger identity.

Do not hash arbitrary database timestamps.

Do not include unrelated provider observations.

The goal is that two worlds with the same decision meaning produce the same authority epoch, and materially different decision worlds do not.

## Store the resolved epoch

When a collective round becomes `RESOLVED`, the exact epoch that was validated for the final member response must remain durably attached to that resolved social authority.

Do not recompute history and overwrite what people originally agreed to.

---

# Phase 2 — enforce consent freshness at the mutation core

The final protection belongs in `collective_mutation_gate`, not only in Agent Gateway or the HTTP route.

Before allowing a pending renewed-consent selection to activate:

1. Recompute the current decision-material authority epoch.
2. Compare it to the resolved consent epoch.
3. Preserve the existing hard feasibility check.
4. If the epoch changed materially, reject the mutation even if the plan remains technically selectable.

Use a specific fail-closed result, for example:

`COLLECTIVE_CONSENT_EPOCH_STALE`

with classification:

`RENEWED_COLLECTIVE_CONSENT_STALE`

Do not silently fall back to algorithmic `COMPROMISE_AVAILABLE`.

Do not let a sibling proposal consume the stale authority.

Do not fall back to an older resolved mediation.

## Important distinction

These two failures are different and should remain distinguishable:

- selected plan is physically no longer valid:
  `COLLECTIVE_SELECTED_PLAN_REVALIDATION_REQUIRED`
- selected plan may still be feasible, but the material decision world changed:
  `COLLECTIVE_CONSENT_EPOCH_STALE`

That distinction matters to the Agent's next action.

---

# Phase 3 — selective recovery, not full conversation reset

When consent becomes epoch-stale, the Agent should not restart the entire Journey.

It should:

1. inspect the new material fact;
2. preserve unaffected locked/anchored commitments;
3. preserve unrelated completed execution truth;
4. generate/replan only the affected future;
5. recompute collective fit;
6. identify the genuinely decision-relevant member set;
7. open a fresh server-owned collective round only if human value authority is again required.

If the new world produces a clear unanimously acceptable grounded future under existing authority, normal autonomous execution may continue without asking everyone again.

If the material trade-off still requires human choice, ask only the relevant in-force members.

Do not reuse their old responses.

Do not manufacture consent from similarity.

---

# Phase 4 — R30 live strike

Build a bounded provider-backed live harness from the current R29 world.

The preferred causal story is:

## A. Establish real renewed consent

Reproduce the already-proven R29 social flow far enough that:

- two members disagree;
- external mediator produces a genuinely improved grounded future;
- both relevant signed Journey principals renew consent;
- the selected proposal remains PRESENTED / CANDIDATE;
- **pause before final acceptance consumes the authority**.

This is the critical interlock point.

## B. Inject a real decision-material shock

Before acceptance, introduce one provider-backed or canonical incident that changes the selected future.

Preferred live shock:

- a closure / opening change / incident mobility change on one of the selected compromise stops or one of its required legs.

The shock must be represented through the normal event/provider evidence path.

Do not edit the candidate row by hand merely to make a hash change.

Do not directly mutate the stored consent epoch.

## C. Prove stale authority is rejected

Attempt the old selected mutation through the normal path.

It must fail because the consent epoch is stale.

The old renewed consent must not activate the plan.

If the shock also makes the old plan hard-infeasible, that is valid for the live story, but add a focused deterministic test where the selected plan remains feasible while a decision-material fact changes, so epoch freshness is proven as a distinct authority layer rather than merely an alias for hard feasibility.

## D. Autonomous recovery

Run a configured external Agent.

It must:

- inspect the shock;
- preserve the protected anchor;
- create a new server-owned recovery proposal or decision surface;
- avoid resurrecting the invalidated consent;
- avoid choosing for the humans if the new surface still contains a material value trade-off.

## E. Renew only what is necessary

If collective authority is required again:

- open a new collective round;
- prove the required member set is recomputed from current reality;
- accept fresh signed responses;
- bind them to a new authority epoch E2.

Do not copy E1 responses into E2.

## F. Resume execution

After fresh authority and normal approval boundaries:

- accept exactly one proposal;
- preserve exactly-once semantics;
- continue the Journey;
- keep R28/R29 safety and social-authority invariants intact.

---

# Phase 5 — non-invalidation control case

R30 is not proven if every provider update destroys consent.

Add a focused control:

- create an unrelated provider observation or evidence update that does not affect the selected plan, its relevant legs, its fit subject, required members, or current authority envelope;
- recompute the epoch;
- prove it remains equivalent;
- the pending consent remains consumable.

This prevents a crude "any new event => ask humans again" implementation.

---

# Required machine-verdict claims

Create an R30 verifier only after the product path exists.

The verifier should prove at least:

1. R29 inherited causal invariants remain PROVEN.
2. Renewed consent had a durable resolved authority epoch E1.
3. A new decision-material provider/event fact occurred after E1 and before consumption.
4. The material world fingerprint changed.
5. Old consent could not activate the selected plan.
6. The rejection occurred at the core mutation boundary.
7. No sibling plan consumed E1 authority.
8. No older resolved mediation resurrected.
9. External Agent recovery ran after the shock.
10. Locked/protected commitments survived.
11. Completed execution truth survived.
12. A fresh server-owned decision surface was produced when needed.
13. Required member scope was recomputed.
14. Fresh responses were authenticated and not copied from E1.
15. Fresh consent bound to E2.
16. E2 differs from E1 for a concrete material reason.
17. Exactly one final recovery proposal was accepted.
18. Same Journey execution continued.
19. Unrelated evidence churn does not invalidate otherwise-current consent.

Prefer causal facts over prose assertions.

---

# Code map for Codex

Start here:

- `backend/app/collective_mediation.py`
  - `collective_decision_epoch`
  - `pending_resolved_mediation_selection`
- `backend/app/main.py`
  - `collective_mutation_gate`
  - collective clarification response handling
  - `collective_proposal_receipt`
  - replan/provider evidence already attached to plans
- `backend/app/agent/gateway.py`
  - collective round creation
  - mediation continuation
  - stale-decision behavior
- existing R28/R29 live harnesses
- existing provider observation / recovery evidence helpers

Before inventing a new fingerprint source, inspect the selected PlanVersion's current evidence payload and reuse its authoritative integrity identity if it already covers the relevant physical facts.

---

# Test strategy

Do not rerun the whole repository after every edit.

Use narrow tests while developing:

- R29 collective mediation tests;
- the new consent-epoch tests;
- relevant replan/provider-evidence tests;
- authenticated principal tests;
- durable approval continuation tests.

Then run one broader backend regression before the live strike.

Frontend changes are required only if the current UI cannot truthfully represent:

- stale consent / world changed;
- fresh member response required.

Do not create frontend churn for invisible backend semantics.

---

# Anti-cheat rules

R30 is NOT proven by:

- changing only a timestamp;
- manually invalidating the proposal status;
- editing consent JSON directly;
- changing the active plan before the stale-consent check;
- making the selected plan impossible and calling the existing hard-feasibility rejection "epoch binding";
- reusing R29 member responses in the new round;
- forcing all members to answer again when only a subset is decision-relevant;
- creating a second verifier-only world model not used by product code;
- accepting a deterministic-controller fallback as proof of an external Agent recovery;
- claiming physical travel.

---

# Stop rule

When the R30 live strike is machine-PROVEN, commit:

- product changes;
- focused regression tests;
- R30 live harness;
- R30 machine verdict;
- one concise result report.

Then stop R30.

No R30.1 receipt pass.

The next Revolution must cross another product boundary, not restate this proof.

---

# One-sentence mission

**Make human consent a lease on meaning, not a permanent token on a database row: when the world materially changes, CityNexus must know that yesterday's yes is no longer authority, recover autonomously, and ask only the people whose choice actually matters.**
