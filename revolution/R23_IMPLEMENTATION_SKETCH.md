# R23 implementation sketch — shortest path

## 1. Reuse TravelerTwin; do not build memory v2

The required tables/services already exist:
- JourneyOutcomeEvent
- TravelerPreferenceEvidence
- TravelerTwinSnapshot
- learn_from_journey
- refresh_snapshot
- planning_preference_items

R23 is a correctness + causal-use upgrade.

## 2. Fix _event_signal first

Current shortcut:
- ACTIVITY_COMPLETED indoor -> indoor preference
- ACTIVITY_SKIPPED indoor -> outdoor preference

Remove that unconditional behavior.

Preferred rule:
- explicit feedback event -> strong signal;
- optional opportunity accepted/executed -> weak/medium positive evidence;
- explicit rejection -> strong/medium negative;
- plain completion -> no signal unless payload identifies a voluntary choice context;
- disruption-caused skip -> no preference signal.

Use outcome payload/proposal linkage and activity commitment/locked state where possible.

## 3. Add narrow feedback event types only if needed

Possible event types:
- USER_LIKED_ACTIVITY
- USER_DISLIKED_ACTIVITY

Or keep USER_ACCEPTED/USER_REJECTED but require an explicit payload flag like:
`preference_feedback=true`.

Prefer the contract that is least ambiguous.

Do not infer explicit feedback from generic acceptance of a Gateway approval.

## 4. Evidence weighting

Use simple bounded constants by evidence class.

Example shape, not mandatory exact values:
- EXPLICIT_FEEDBACK: strong/confident;
- VOLUNTARY_CHOICE: medium;
- EXECUTION_TELEMETRY: weak.

The important contract:
- the class is persisted;
- weights are capped;
- one weak event cannot dominate.

## 5. Candidate vocabulary

When learning from a Place:
- include canonical category;
- include bounded normalized tags;
- ignore unknown/free-form tags that are not useful interests.

When scoring a candidate:
- include Place.category in the candidate tag set in addition to tags_json.

This lets "museum" learning compare with future museum Places without name matching.

## 6. Multiple F4 candidate proposals

Generalize the singular R22 `opportunity_choice`.

For an OPPORTUNITY_WINDOW with `place_ids=[A,B,C]`:
- validate each ID independently;
- reject already-active/unknown-fact candidates individually;
- capture the needed directed mobility edges;
- create at most N feasible F4 specs/proposals;
- keep failure reasons per candidate.

Do not fail the entire request because candidate B is bad if A/C are valid.

Bound N to 3.

## 7. Preference fit must be visible in proposal receipt

For each F4 proposal persist:
- candidate Place;
- explicit preference fit contribution;
- learned-soft fit contribution;
- effective preference fit;
- hard feasibility facts separately.

This enables A/B proof.

Do not fabricate precision beyond existing deterministic weights.

## 8. Compact TravelerTwin in inspect trace

Add:
`traveler_context`

to inspect_journey or inspect_twin:
- explicit preference keys;
- learned soft dimensions/directions;
- strength/confidence;
- conflict/override state.

No history dump.

## 9. Baseline vs learned A/B

Make baseline and learned tests use the same grounded candidate identities if practical.

If provider freshness requires new snapshots, okay.

The proof must show:
- opening/cost identities unchanged;
- both candidates hard feasible in both comparisons;
- ranking delta comes from preference context.

## 10. Explicit override

planning_preference_items already suppresses learned dimensions when an explicit dimension exists.

Test and strengthen this behavior instead of replacing it.

If explicit opposite direction currently cannot suppress the learned candidate cleanly, fix the representation minimally.

## 11. Opportunity threshold

Add a named minimum window threshold in the current positive-signal function.

Focused tests:
- below threshold => no event;
- above threshold + real mobility => event.

## 12. Focused R23 regressions

Add direct tests:
1. plain ACTIVITY_COMPLETED creates no strong preference evidence.
2. C4/locked completion creates no learned taste.
3. disruption-caused skip creates no negative taste.
4. explicit feedback creates bounded evidence.
5. repeated/choice-bearing evidence accumulates but caps.
6. contradictory evidence surfaces conflict.
7. expired evidence stops ranking.
8. explicit preference overrides learned soft.
9. clear-learned removes effect.
10. candidate category participates in preference fit.
11. multiple F4 hints create multiple grounded proposals.
12. learned preference changes F4 ranking, not feasibility.
13. below-minimum opportunity does not wake Agent.
14. inspect trace exposes compact learned context.
15. live Agent path still uses canonical facts/live mobility/Gateway.

Then run the existing R22 focused suite once.

No new harness.
