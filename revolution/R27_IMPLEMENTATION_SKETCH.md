# R27 implementation sketch — shortest path

## 1. Reuse Qoder membership primitives

Use existing JourneyMember, JourneyRoleCapability, member-state logic, member APIs, and role-capability endpoint.

Add one internal projection helper:
active_journey_members_with_capabilities(session, journey_id)

Do not create GroupMember v2.

## 2. Reuse TravelerTwin separately per traveler

For each active member:
- read that traveler's snapshot;
- merge that traveler's current journey-scoped explicit preference;
- keep learned soft separate.

Journey.traveler_id may remain the compatibility owner, but it cannot stand in for every member once shared mediation is active.

## 3. Member-specific explicit preference

Reuse traveler_id + journey_id preference storage if possible.

If R26 current_explicit_mission is mission-local to one traveler, add the smallest member-scoped shared-decision answer projection.

Do not create a generic message store.

## 4. Candidate matrix

Wrap existing verified preference breakdown per member.

Return explicit, learned, conflict, and effective fit.

Hard feasibility is world truth and is not averaged across people. Member capability facts may contribute hard constraints only if they are explicit server facts.

## 5. Mediation classifier

Small pure function:
classify_group_decision(candidates, member_fits, policy)

Return:
UNANIMOUS_DOMINANCE
COMPROMISE_AVAILABLE
HUMAN_TRADEOFF_REQUIRED
AUTHORITY_CONFLICT
INSUFFICIENT_WORLD_FACTS

INSUFFICIENT_WORLD_FACTS always routes to provider acquisition.

## 6. Fairness receipt

For every candidate persist:
- minimum member fit
- maximum regret from each member's personal best
- mean fit
- unacceptable-member IDs if any

Prefer highest minimum fit, then lowest max regret, then mean.

Keep exact per-member contributions inspectable.

## 7. Compromise discovery

When current options conflict:
- let Agent search up to three real candidates;
- acquire canonical facts only for candidates that could improve worst-member fit;
- recompute matrix/classification.

Agent chooses search strategy. Server owns facts and fairness arithmetic.

## 8. Multi-member clarification

Extend R26, do not replace it.

Shared decision state:
- decision_epoch
- options
- required_member_ids
- capability basis
- responses by member
- WAITING_FOR_MEMBERS / RESOLVED / STALE

Response identity must match JourneyMember and Traveler.

## 9. Authority freshness

Before acting:
- recompute member state;
- recompute role capabilities;
- stale the decision if a required member expired, withdrew, or changed role.

Do not cache authorization from question time.

## 10. R26 hygiene tests first

- ordinary user skip EN_ROUTE / ARRIVED / IN_PROGRESS parity restored;
- clarified defer still refuses after departure;
- strategic skip uses preference_learning_eligible=false rather than fake forced_by_disruption;
- post-skip routing uses shared routing identity and fails closed without identity.

## 11. Focused R27 tests

- active members only;
- role capabilities from server table;
- no cross-member TravelerTwin leakage;
- per-member explicit > learned;
- unanimous dominance asks nobody;
- factual unknown acquires provider fact;
- conflict cannot be hidden by mean score;
- compromise gate uses min-fit/max-regret;
- bounded search can change classification;
- only required authorized members receive clarification;
- expired/withdrawn response rejected;
- role change stales pending decision;
- one member cannot answer for another;
- shared resolution does not widen Agent authority;
- resolved group choice changes actual execution;
- R20-R27 focused lineage once at end.

No new harness.


## 13. State-aware ordinary skip truth

When repairing R26 skip parity, do not reuse the clarified pre-depart origin rule for all states.

Required behavior:
- ACTIVE / NOT_STARTED: prior completed physical origin -> next activity, capture direct edge if adjacency changes.
- ARRIVED / IN_PROGRESS: current activity is the physical origin; use/revalidate current->next.
- EN_ROUTE: require a truthful current-position routing seam. If the runtime cannot route from current observed position, return a named REVALIDATION_REQUIRED refusal rather than guessing.

This is a truth upgrade, not a reason to silently remove the old user operation.
