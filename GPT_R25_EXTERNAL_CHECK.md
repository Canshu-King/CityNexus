# GPT external check — R25 -> R26

Inspected:
- uploaded `REVOLUTION_R25_STRATEGIC_HORIZON_STEWARD_RESULT.md`;
- remote code commit `096b196fdd67de2663764b4cf0f8c49a23a8d679`;
- report-binding head `f1fbb8e8d67fe2946c0b0adde5d92586503850a3`;
- R25 horizon projection, DEFER Gateway validation, Hermes-compatible runtime and focused tests.

## R25 verdict

R25 is a real Revolution milestone.

It proves:
- a fresh ACTIVE provider-backed Nara Journey;
- a real Hermes-compatible `cn:glm-5.3-flash` AgentRun;
- two grounded future choices visible to the Agent;
- W1 and W2 each individually affordable under the stated optional envelope;
- combined cost exceeds the envelope;
- later preference fit is higher;
- the model chose typed `NO_ACTION + DEFER`;
- server validation rejected prose-only authority and rechecked the horizon;
- W1 was deliberately skipped with zero optional spend;
- W2 later executed through the normal HTTP state machine;
- Journey reached COMPLETED;
- actual route edges remained provider-grounded/live-authority where execution required it;
- no deterministic fallback prose, mock mobility, synthetic event or fake reservation was counted.

This is the first machine proof that CityNexus can deliberately decline a feasible present action to preserve scarce resources for a more valuable later action.

## Important qualification 1 — W2 was already on the active plan

The later Todaiji Museum activity was already part of the selected active PlanVersion.

After W1 was skipped, `authoritative-compose` generated a separately revalidated candidate for the remaining route, but that candidate was not selected. The unchanged active plan continued to W2.

Therefore R25 proves:

> strategic deferral between already-authorized future activities

more strongly than it proves:

> defer now for a later outside-plan option, then dynamically activate that new option through Gateway.

This is still a valid capability leap. Do not reopen R25 to force the stronger variant.

## Important qualification 2 — GROUNDED is weaker than FEASIBLE

Current `_remaining_opportunity_horizon()` marks a window `GROUNDED` when:
- canonical cost is known;
- a route fact exists.

The DEFER Gateway then checks:
- two windows;
- both status GROUNDED;
- each cost <= optional budget;
- combined cost > optional budget;
- later preference_fit > first preference_fit.

This does NOT yet mean the server has re-proven:
- opening covers the actual window;
- visit duration fits;
- travel + safety buffer fits;
- protected commitment slack survives;
- full deterministic feasibility passes.

The current error label `DEFER_REQUIRES_EACH_WINDOW_TO_BE_FEASIBLE` is stronger than the implemented invariant.

R26 must tighten this before using DEFER as a human-intent-sensitive decision surface.

Required negative regression:

```text
known cost
+ route evidence
+ later preference higher
BUT opening/time/slack infeasible
=> DEFER rejected
```

## Important qualification 3 — optional budget must reserve unavoidable future obligations

R25 correctly stopped subtracting every future optional activity as if it were pre-reserved.

However the current optional budget formula subtracts:
- declared stay allocation;
- already consumed activity cost.

It does not explicitly reserve future unavoidable known monetary obligations such as:
- protected/locked paid activities;
- committed bookings/payments that the Journey cannot freely skip.

R26 must distinguish:
- future OPTIONAL opportunity cost: not pre-reserved;
- future UNAVOIDABLE committed cost: reserved from optional envelope.

Do not regress to subtracting every future candidate.

## R25 test gap

Current R25 focused tests cover:
- typed DEFER completion semantics;
- plain NO_ACTION behavior;
- external model timeout/fallback.

Add direct server-bound regressions for:
- false-grounded-but-infeasible later window;
- unavoidable future-cost reservation;
- DEFER refusal when preference evidence is too uncertain for an autonomous value judgment.

## Revolution frontier

Do NOT make R26 "more horizon optimization".

R25 exposes a deeper autonomy problem:

When two grounded/feasible strategies differ mainly by human value preference, TravelerTwin may be:
- weak;
- conflicted;
- stale;
- learned-only;
- close to a tie.

In that case the correct next capability is not another score.

The Agent should know:

> I do not lack world facts; I lack the traveler's value judgment.

R26 should implement decision-critical clarification:

> ask exactly one bounded question only when the user's answer can materially change the action, persist the answer as explicit journey-scoped intent by default, resume the same decision, and avoid asking when the answer would not matter.

This is collaborative autonomy, not a chat feature.
