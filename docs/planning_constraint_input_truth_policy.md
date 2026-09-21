# CityNexus Planning Constraint Input Truth Policy

Status: arbiter contract note for ORD-0152 and R7 input parity.

## 1. Problem class

A planning engine can be perfectly deterministic and still lie if the normalized constraints entering it are wrong.

Therefore R7 parity has two layers:

1. **input truth parity**: AI and direct planning must consume the same normalized user constraints;
2. **planner parity**: the same normalized input must enter the same deterministic feasibility core.

A parser bug that turns an explicit budget into zero is a P0 truth defect, not a user-budget problem.

## 2. Zero is data, not "unknown"

The system must never use numeric zero as a fallback for missing, uncertain, failed, or unparsed budget input.

Required distinction:

- explicit zero -> 0;
- no budget supplied -> null / absent / UNKNOWN;
- extraction uncertain -> NEEDS_CONFIRMATION / BLOCKED input state;
- extraction failed -> PARSE_ERROR / equivalent named diagnostic;
- explicit positive amount -> normalized positive amount.

Do not silently coerce any of the last three cases to 0.

## 3. Canonical budget shape

Equivalent repository field names are allowed, but the normalized meaning must preserve:

```yaml
budget:
  amount_minor: 160000
  currency: CNY
  scope: TRIP_TOTAL
  party_size: 2
  raw_text: "两个人三天全部加起来别超过一千六百块"
  extraction_status: CONFIRMED
  source: USER_TEXT
```

For the fixed HJ-P1 regression sentence, "一千六百块" means CNY 1600 total for the whole trip because the user explicitly says "两个人三天全部加起来".

If the product has a different canonical money model, map into that model without losing amount, currency, and scope.

## 4. One normalized PlanningConstraints object

Natural-language extraction may happen upstream, but the planner must not re-parse the original user sentence.

AI and direct planning both consume one server-owned normalized `PlanningConstraints` representation.

The normalized object should be observable in bounded diagnostics/tests so parity can be proven without exposing sensitive free text unnecessarily.

## 5. Persistence/readback parity

ORD-0152 must locate the first stage where truth changes:

```text
raw user input
-> extraction
-> normalization
-> persistence
-> readback
-> planner request
-> feasibility core
```

At each boundary record/assert the budget value and unit.

The first boundary that turns 1600 CNY into 0 is the defect boundary.

Do not patch only the final planner comparison if persistence already contains the wrong value.

## 6. User-facing failure semantics

If the product loses or cannot confidently parse an explicit budget:

- do not tell the user "adjust your budget";
- do not classify the plan as mathematically infeasible due to budget;
- return a product/input-processing reason such as `BUDGET_INPUT_UNRESOLVED` or the repository's equivalent stable code;
- offer correction/confirmation of the parsed value.

"Your budget is too low" is allowed only when the normalized positive budget used by the planner matches what the user supplied.

## 7. Exact regression gate

Use the original user sentence as a fixed regression input:

```text
两个人三天全部加起来别超过一千六百块
```

Required assertions:

1. normalized amount is 1600 CNY trip-total;
2. minor-unit representation is correct if used by the repository;
3. party size is 2;
4. scope remains whole-trip total, not per-person and not per-day;
5. persisted/read-back value matches normalized value;
6. AI planning and direct planning see the same normalized budget;
7. planner never receives 0 unless user explicitly supplied zero;
8. mutation "missing/parse failure -> 0" is killed;
9. user-facing infeasibility copy is not emitted when the product itself lost the budget value.

## 8. Relationship to R7

R7 remains:

> AI may change soft preferences, but not deterministic world facts or feasibility rules.

This document adds:

> AI/direct parity begins before the planner. They must share the same normalized hard constraints, including money.

A single planner core cannot compensate for divergent or corrupted inputs.
