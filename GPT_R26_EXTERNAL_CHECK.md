# GPT external check — R26 -> R27

Reviewed the uploaded R26 result, remote implementation at 761670f24ff29fbd40293a233b8ab0ce16575d1e, current report-only head e135c5cba3c4860f69767f784324a759da395805, clarified-choice mutation, skip execution mobility override, completion contract, and JourneyMember / JourneyRoleCapability foundations.

## R26 verdict

R26 closes REVOLUTION_C.

Machine facts now hold:
- server detects decision-critical human-value uncertainty;
- real Agent can produce machine-valid CLARIFICATION_REQUIRED;
- answer defaults to THIS_JOURNEY;
- parent/child mission preserves authority;
- TAKE_LATER becomes explicit journey-scoped intent;
- child Agent can execute a server-owned clarified-choice mutation;
- W1 becomes SKIPPED;
- changed physical adjacency gets fresh live provider mobility;
- frozen PlanVersion evidence remains immutable;
- W2 executes;
- Journey completes;
- NO_ACTION + DEFER without mutation is UNRESOLVED.

R26 D is directionally proven but not a perfectly symmetric model A/B because the TAKE_NOW model rerun occurred after the current activity had advanced. Do not reopen R26 merely to polish that symmetry.

## Inline blocker 1 — generic skip parity regressed

Before the R26 behavioral refactor, ordinary user skip accepted ACTIVE, NOT_STARTED, EN_ROUTE, ARRIVED and IN_PROGRESS. The new shared helper accepts only ACTIVE and NOT_STARTED, so the public user skip behavior was unintentionally narrowed.

Fix inline:
- ordinary user skip keeps prior allowed states;
- clarified strategic defer remains stricter and may only skip before departure;
- shared helper may accept caller-specific allowed states;
- add direct parity regression.

## Inline blocker 2 — false disruption provenance

Clarified strategic skip currently records forced_by_disruption=true.

That is false. It was likely used to prevent TravelerTwin from learning a category dislike, but TAKE_LATER is an explicit value decision, not a disruption.

Replace with truthful provenance such as:
- decision_scope = CLARIFIED_HORIZON_CHOICE
- preference_learning_eligible = false
- skip_reason = CLARIFIED_DEFER_FOR_LATER_OPTION

Teach TravelerTwin suppression from truthful decision provenance.

## Inline blocker 3 — route identity

The clarified skip helper currently captures a changed direct edge only when predecessor and next activity both have place_id. R15+ already has the product routing identity helper _activity_routing_key.

Use the shared routing identity so city-service or semantic activities do not bypass live recapture. Fail closed when changed physical adjacency has no routable identity.

## Revolution frontier

R20-R26 are still fundamentally single-traveler autonomy.

The product now also has real shared-journey primitives from the Qoder/Commander line:
- JourneyMember
- OWNER / ADMIN / COLLABORATOR
- membership expiry / withdrawal
- JourneyRoleCapability
- JOURNEY_READ / JOURNEY_UPDATE / PLACE_EDIT / MEMBER_MANAGE / SHARE_GRANT_MANAGE
- server-owned member/share endpoints

R27 should connect these worlds.

R27 thesis:

CityNexus should mediate a real shared Journey for multiple travelers with different explicit/learned preferences and different roles, find a mutually good grounded option when one exists, and ask only decision-relevant authorized people when a true human trade-off remains.

This is collective autonomous travel mediation, not a voting app and not a group chat.


## Clarification on skip parity — restore behavior without lying about physical origin

Do not merely widen the shared helper back to every old state using the same predecessor-origin logic.

State-aware truth is required:

- ACTIVE / NOT_STARTED: the physical origin can be the nearest previously completed/routable activity.
- ARRIVED / IN_PROGRESS: the traveler is already at the current activity; post-skip routing starts from the current activity location, so the existing current->next route may remain authoritative if still fresh/eligible.
- EN_ROUTE: the traveler may be physically between activities. Do not pretend the origin is the previous stop or the destination. Use a real current-location/routable-position seam if available; otherwise fail closed with a specific revalidation-required reason rather than inventing an edge.

The public skip contract should not be accidentally narrowed, but truth authority is more important than blind compatibility. Add state-specific regressions.
