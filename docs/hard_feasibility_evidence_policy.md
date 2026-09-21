# CityNexus Hard-Feasibility Evidence Policy

Status: arbiter contract note. This document refines R5 without opening a new top-level R12 rule.

## 1. Governance decision

Do **not** open R12 as a separate top-level rule.

Keep one umbrella invariant:

> A plan may be SELECTABLE/ACTIVE only when every hard-feasibility fact it actually relies on is backed by policy-eligible evidence.

For implementation and tests, split that umbrella into typed sub-gates instead of mixing unlike facts:

- **R5-M — Mobility evidence for used legs**
- **R5-T — Temporal/place-availability evidence for used activities**

R5-M and R5-T share the same truth principle but retain different schemas and reason codes.

Do not call opening-hours validation a "used-edge" check. Mobility is edge evidence; opening hours are activity/place temporal evidence.

## 2. R5-M: mobility fact-quality eligibility

The planner must evaluate mobility evidence **only for the legs actually used by a candidate**.

A snapshot may contain synthetic/default facts for unused pairs without poisoning an otherwise valid candidate.

### Required eligibility policy

There must be one server-owned allow-list/policy for hard-feasible mobility fact quality.

Use the existing local `HARD_FEASIBLE_QUALITIES` concept if present, or an equivalent single authoritative policy. Do not duplicate the enum decision in planner, API, and frontend code.

Normative assertions:

- `EXPLICIT_FROZEN_FIXTURE` is hard-eligible for the deterministic/golden fixture paths where that evidence class is intentionally supported.
- accepted real-provider captured evidence is hard-eligible only when its provenance/freshness requirements pass the existing truth policy.
- `SYNTHETIC_DEFAULT` is **never** hard-eligible for an Anywhere/live selectable plan.
- missing/unknown evidence is not hard-eligible.
- stale/partial evidence is not hard-eligible unless the existing server-owned policy explicitly classifies that exact evidence state as hard-feasible.
- simulated/mock evidence may be eligible only inside the frozen CNX-DEMO Simulation policy. It must never be upgraded to live/Anywhere truth.

The planner should consume a derived server-owned boolean/equivalent decision such as `hard_eligible`, rather than every caller re-implementing enum comparisons.

## 3. Candidate-level mobility rule

For a candidate with activities A1..An, define its used legs as the consecutive mobility legs required by that candidate.

A normal candidate is mobility-feasible only when every used leg has policy-eligible evidence.

In plain terms:

```
candidate mobility hard-feasible
iff
for every used leg:
    evidence exists
    AND evidence.fact_quality is hard-eligible
    AND provenance is valid for the current product mode
```

Consequences:

- one used leg with `SYNTHETIC_DEFAULT` => that leg is a mobility gap;
- any mobility gap => candidate is PARTIAL/NON_SELECTABLE;
- the candidate must not report `hard_constraints_passed=true`;
- it must not become SELECTED/ACTIVE or be accepted as a replan;
- it must not create downstream Booking/Commitment based on the invalid candidate.

Do not downgrade a candidate merely because unrelated rows elsewhere in the mobility snapshot are synthetic.

The Beijing regression case is the canonical positive example: 8 stops, 7 used legs, all 7 resolved to `EXPLICIT_FROZEN_FIXTURE`; unrelated `SYNTHETIC_DEFAULT` rows elsewhere in the snapshot do not invalidate those 7 used legs.

## 4. Mobility gap details

A mobility gap response must not use `details=null`.

At minimum each missing/ineligible used leg exposes:

```yaml
from_place_id: "..."
to_place_id: "..."
reason_code: MOBILITY_DATA_UNAVAILABLE
fact_quality: SYNTHETIC_DEFAULT | null | <actual quality>
hard_eligible: false
provider: "..." | null
evidence_state: "..."
observed_at: "..." | null
expires_at: "..." | null
source_identity: "..." | null
provider_observation: {}
```

A synthetic default is reported as an ineligible fact, not as "no row exists".

## 5. Provider capability truth must not be an empty object

`provider_capabilities = {}` is not an acceptable terminal contract shape.

Represent provider capability state explicitly. Equivalent field names are allowed, but semantics must distinguish:

- capability known and supported;
- capability known and unavailable;
- capability not checked/unknown;
- provider currently unreachable/rate-limited/partial.

For example:

```yaml
provider_capabilities:
  status: KNOWN | UNAVAILABLE | UNKNOWN
  providers:
    - provider: VALHALLA
      role: MOBILITY
      runtime_status: OK | RATE_LIMITED | UNREACHABLE | PARTIAL
      observed_at: "..."
  reason_code: null | MOBILITY_DATA_UNAVAILABLE
```

Do not let an empty dictionary silently mean all four states.

## 6. R5-T: temporal/place-availability evidence

Do not create a separate R12 governance number. Record ORD-0138 under R5-T.

R5-T is not mobility and must keep its own reason codes/details.

### Known opening hours

If a place/activity has known, traceable opening-hours evidence, a visit that requires the place to be open must lie within a valid local-time availability window.

Known closed/out-of-window => hard-feasibility violation.

The current Beijing regression example is mandatory:

- Forbidden City evidence: 08:30-17:00
- scheduled visit: 22:00-00:00
- expected: NON_SELECTABLE
- forbidden: `hard_constraints_passed=true`

### Missing or unpropagated opening hours

Distinguish:

- `KNOWN`: the backend has usable opening-hours evidence;
- `UNKNOWN`: the source does not currently provide usable evidence;
- `NOT_PROPAGATED`: evidence exists in backend/catalog but planner/projection/UI failed to carry it.

`NOT_PROPAGATED` is always a product defect. It must never be rendered as "no data".

For `UNKNOWN`, the planner must not claim that the opening-hours hard constraint was verified. Whether the whole candidate is non-selectable is decided by the server-owned activity-availability policy for that activity type, not by the frontend or LLM. A place type that requires verified access cannot become SELECTABLE while availability remains unknown.

## 7. Temporal details contract

A known-hours violation must include non-null details:

```yaml
place_id: "..."
scheduled_start: "..."
scheduled_end: "..."
opening_window_start: "..."
opening_window_end: "..."
local_timezone: "..."
availability_evidence_state: KNOWN
source_provider: "..."
source_identity: "..."
observed_at: "..."
reason_code: OPENING_HOURS_VIOLATION
```

The outer compatibility error may remain `PLACE_CLOSED` if current API compatibility requires it, but the details must carry the precise temporal reason.

Comparisons use the place's local timezone.

## 8. R5-M and R5-T are independent gates

A candidate can pass mobility and fail temporal availability, or vice versa.

Do not collapse both into one generic reason code.

Examples:

- all used legs explicit, museum closed at scheduled time -> R5-M PASS, R5-T FAIL;
- museum open, one used leg synthetic default -> R5-T PASS, R5-M FAIL;
- both valid -> both PASS;
- both incomplete -> both gaps are reported.

The candidate is SELECTABLE only when every hard-feasibility sub-gate required by that candidate passes.

## 9. Focused gate requirements

### Mobility gates

1. Beijing positive case: all 7 used legs `EXPLICIT_FROZEN_FIXTURE` -> mobility PASS.
2. Mutate exactly one used leg to `SYNTHETIC_DEFAULT` -> candidate NON_SELECTABLE and exact leg appears in gaps.
3. Add 100 unrelated `SYNTHETIC_DEFAULT` rows not used by the candidate -> candidate remains mobility PASS.
4. Remove one used-leg fact -> NON_SELECTABLE, gap names the pair.
5. Replace an accepted provider fact with stale/ineligible quality -> NON_SELECTABLE.
6. Mutation that adds `SYNTHETIC_DEFAULT` to the hard-eligible allow-list must be killed by tests.

### Temporal gates

1. Forbidden City 08:30-17:00 scheduled 22:00-00:00 -> NON_SELECTABLE.
2. Same place scheduled inside valid window -> temporal PASS.
3. Backend has opening hours but projection omits them -> NOT_PROPAGATED defect.
4. Known-hours violation details are non-null and contain place/time/provenance.
5. A mutation bypassing the temporal check must be killed.

## 10. Planner/capability parity consequence

R11 capability readiness must use the same hard-feasibility policy as the shared planner.

A city must not be declared READY merely because a route can be assembled with `SYNTHETIC_DEFAULT` legs.

Conversely, a city/candidate with partial global mobility coverage may still be READY/selectable when the actual candidate's used legs all carry hard-eligible evidence.

This preserves the distinction:

- **global coverage completeness** describes the destination/catalog;
- **candidate hard feasibility** describes the actual plan.

They must not be inferred from one another by raw row counts or snapshot-head sampling.
