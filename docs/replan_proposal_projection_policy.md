# H10b Replan Parity Correction Note

Status: **SUPERSEDES the previous projection-gap premise in this file.**

The earlier version of this note incorrectly treated the 12-field and 4-field proposal shapes as
two different product/Agent surfaces. That premise is withdrawn.

## 1. Corrected observation

The Agent Gateway response itself contains two different keys with intentionally different shapes:

- singular `proposal` -> the rich generated proposal object;
- plural `proposals` -> a compact list/summary of proposal rows.

The rich proposal is therefore already available on the Agent side.

A test that reads plural `proposals` and compares it with the richer product proposal is reading
the wrong key. That is a test/comparator defect, not evidence that the Agent surface lacks a rich
proposal projection.

Do not open or continue a "canonical projection" product project on the basis of that mistaken
12-vs-4 comparison.

## 2. H10b corrected status

H10a remains:

    HTTP Agent Gateway vs MCP adapter parity = PASS

H10b becomes:

    TEST-SIDE FIXABLE, then re-run after argument parity is established

The comparator must read the singular rich `proposal` object on the Agent response.

H10b must still preserve independent entry paths. The previous independence lesson remains valid:
do not replace the product-direct comparator with another call through the Agent Gateway merely to
make the parity test green.

## 3. Remaining product defect: argument-boundary parity

The remaining product/API-contract defect is not proposal projection. It is parameter handling,
currently tracked separately as ORD-0176.

For any semantically relevant argument such as `solver_mode`, an adapter/boundary must do one of
two things:

1. accept the argument, validate it against the server-owned allowed domain, forward it, and expose
   the effective value; or
2. reject it with a named machine-readable error.

A third state is forbidden:

    caller sends parameter
    -> boundary silently discards it
    -> call succeeds
    -> downstream uses a different default

Freeze sentence:

> **Parameter discarded is not boundary honoured.**

If two parity legs request different/effectively different solver modes, any downstream proposal,
utility, score, or feasibility difference is confounded until solver-mode parity is restored.

## 4. H10b rerun requirements

Before interpreting semantic differences:

1. use equivalent pre-state / cloned DBs;
2. use semantically equivalent trigger/input;
3. product-direct leg and Hermes/MCP leg must report the same effective solver mode;
4. Agent comparator must read singular `proposal`;
5. normalize only legitimate surface metadata such as request/trace ids;
6. compare the rich semantic fields that both legs actually expose;
7. if semantic differences remain, only then classify them as planner/domain parity defects.

At minimum compare, where applicable:

- hard-feasibility verdict;
- stable reason codes;
- commitment preservation;
- proposed change semantics / diff;
- utility/scoring;
- proposed/base plan-version relations;
- cost/time/schedule deltas;
- evidence/provenance classes.

## 5. Independence gate

The H10b test must prove its two entry paths remain independent before they converge on intended
shared deterministic product logic.

Mutation requirement:

    route the product-direct side through the same Agent Gateway used by Hermes
    -> H10b independence gate must turn RED

A parity test that compares two calls through the same gateway proves adapter consistency, not
product-direct-vs-Hermes semantic parity.

## 6. Relationship to current ORD work

- ORD-0176 owns the solver_mode / argument-boundary product defect.
- ORD-0173/Hermes owns the corrected H10b rerun.
- ORD-0175 is NOT to be used for proposal-projection work; that identifier is already used by a
  different current task.
- ORD-0167 and ORD-0172 remain unrelated to this implementation.

## 7. Retraction

The previous claim:

    product ReplanProposal surface = 12 fields
    Agent/MCP surface = 4 fields
    therefore H10b is BLOCKED_BY_PROJECTION

is withdrawn.

The corrected claim is:

    Agent response already exposes a rich singular proposal;
    the parity test read the compact plural summary;
    solver_mode/argument parity must be fixed before semantic parity is interpreted.

## 8. Freeze sentence

**Read the right object, align the effective inputs, preserve independent entry paths, then compare semantics.**
