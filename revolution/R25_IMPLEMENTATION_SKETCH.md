# R25 implementation sketch — shortest path

## 1. Fix evidence replay without redesign

Use `related_ids_json` as the ingestion identity source.

For an existing TravelerPreferenceEvidence row:
- load existing related outcome IDs;
- compute new IDs;
- if empty: return without changing created_at / expires_at / evidence_count / strength;
- if non-empty: merge once and recompute aggregate.

Do not use request time as the evidence birth time on replay.

Prefer preserving first evidence time plus last_evidence_at separately if needed.

## 2. Aggregate reinforcement simply

Across active evidence rows for one dimension/direction:
- decay each row;
- combine bounded independent evidence;
- keep cap <= 1;
- expose raw count + effective aggregate.

Simple formula is fine, e.g. bounded noisy-OR style:
`1 - product(1 - decayed_strength_i)`
or another documented monotonic cap.

Contradictory directions remain separate and the effective preference layer can neutralize/discount them.

No opaque ML score.

## 3. Real Agent causal A/B

Use identical grounded candidates on cloned/fresh equivalent Journeys.

Run A:
- learned cleared / neutral.

Run B:
- learned signal active.

The mission text must be materially identical and contain no candidate name/ID.

The Agent should see both F4 proposals through request_replan/list_replans.

Persist:
- candidates;
- score breakdown;
- TravelerTwin context;
- selected proposal ID;
- hard facts.

If the model makes the same choice despite the ranking flip, do not fake success. Adjust only the product comparison surface so the model can see the deterministic preference provenance; do not put the desired answer in mission text.

## 4. Horizon projection

Implement a small function near existing opportunity-window/Twin code, conceptually:

`remaining_opportunity_horizon(session, journey) -> list[WindowSummary]`

Use remaining Activities + C4 anchors.

Bound to max 2.

No persistence needed initially if deterministic from current reality.

## 5. Future evidence labels

A future window summary can carry candidate planning facts, but label mobility:
- `PLANNING_ONLY_PROVIDER_CAPTURE` or `FROZEN_PLAN_EVIDENCE`.

On current W2 activation:
- discard authority from planning label;
- recapture through normal runtime mobility;
- F4 gate decides.

## 6. Strategic resource envelope

Expose:
- optional_budget_remaining_minor;
- current candidate cost;
- future candidate cost;
- can_take_both boolean;
- current/later slack.

This can be deterministic.

Do not let the model calculate hidden budget arithmetic from prose.

## 7. Strategic decision marker

Reuse `conclude_recovery(NO_ACTION)` if possible, but persist a structured resolution reason for OpportunityWindow:
- OPPORTUNITY_DECLINED_BY_AGENT;
- DEFERRED_FOR_HIGHER_VALUE_HORIZON.

Do not introduce a new mutation tool just to say "wait".

## 8. Do not reserve fake future reality

A defer decision may record intent/reasoning, but must not:
- reserve a Place;
- spend budget;
- mark a later proposal accepted;
- lock future mobility.

Later opportunity must pass current truth again.

## 9. R25 focused tests

1. reflect replay without new OutcomeEvent does not refresh TTL.
2. new independent evidence strengthens aggregate once.
3. repeated same HTTP replay is idempotent.
4. opposite learned direction reduces/net-neutralizes fit.
5. explicit preference still suppresses learned conflict.
6. real-current candidate list contains >1 valid F4 proposal.
7. horizon projection max 2 windows.
8. future mobility is never labeled current-live authority.
9. can_take_both arithmetic is deterministic.
10. strategic defer leaves active PlanVersion unchanged.
11. later W2 revalidation requires fresh/live mobility.
12. later insertion consumes actual remaining budget.
13. explicit override reverses defer/take policy in comparable setup.
14. R20-R23 focused regression suite passes once after implementation.

No new harness.
