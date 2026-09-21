# CityNexus Test Execution Truth Policy

Status: arbiter contract note for ORD-0166 / ORD-0168 and all multi-agent acceptance reports.

## 1. Core rule

A test suite that cannot complete collection has no valid pass/fail baseline.

If `pytest --collect-only` exits non-zero or reports a collection/import error, then:

- executed test count = 0 for any suite whose execution was prevented;
- pass count = UNKNOWN;
- fail count = UNKNOWN;
- skip count = UNKNOWN;
- "red set" / "green set" size is UNKNOWN;
- no agent may quote a historical or partial pass/fail denominator as the current-tip result.

Do not replace UNKNOWN with the most recent number from another SHA.

## 2. Collection is a first-class gate

Before reporting any suite result, record and validate:

1. exact git SHA / worktree path;
2. interpreter/runtime version;
3. exact pytest command;
4. collection exit code;
5. collection error count;
6. collected node count;
7. execution exit code;
8. executed/pass/fail/skip counts.

A valid acceptance report must distinguish:

    COLLECTION
    COLLECTED
    EXECUTED
    PASSED
    FAILED
    SKIPPED
    ERRORS

"1083 passed / 10 failed" is invalid if collection never completed on that exact tree.

## 3. No import masking

When a production symbol is renamed or removed, tests must be updated intentionally.

Forbidden techniques for making collection green:

- `try/except ImportError` that silently substitutes another symbol;
- conditional skip because an expected production symbol is missing;
- broad `pytest.importorskip` for repository-owned modules;
- aliases added only to keep stale tests green without a compatibility decision.

If backwards compatibility is intended, document and test the compatibility alias explicitly.
Otherwise repair the stale test import and assertions.

## 4. Exact-tip provenance

Every reported baseline must be attributable to one exact source state.

At minimum include:

    repo/worktree
    git rev-parse HEAD
    git status --short
    command
    exit code
    elapsed time
    collection summary
    execution summary

If the worktree is dirty, include the diff/stat or state that the result is from a dirty tree.

A clean `git archive <sha>` export is a valid alternative to `git status --short` because the
export contains exactly the tracked tree of that commit and has no `.git` metadata. In that case
the report must explicitly state:

    source = git archive <exact-sha>
    git_status = NOT_APPLICABLE_ARCHIVE_EXPORT
    archive contains tracked files from that commit only

Do not claim an archive export proves anything about untracked/staged/unstaged files from the
source worktree; it proves the tracked commit tree only.

A result from commit A must not be reported as the baseline of commit B.

## 5. Partial and targeted runs

A targeted test run may be useful evidence, but it must be labeled targeted.

For example:

    TARGETED: 5 passed
    FULL SUITE: UNKNOWN (collection blocked)

Never infer the full-suite red/green set from a targeted subset.

## 6. Renamed-symbol regression

For the current ORD-0166 class of failure:

- production rename `UNRESOLVED_PREFIX -> PENDING_PREFIX`;
- stale import/assertion in `test_qoder_anywhere_capability_from_store.py`;
- module import fails during collection.

Acceptance requires:

1. stale import repaired intentionally;
2. stale assertions updated to current contract;
3. no compatibility shim added merely to appease the test;
4. targeted collect-only succeeds;
5. full collect-only succeeds;
6. only then may the current-tip red/green baseline be measured.

## 7. Multi-agent reporting rule

Any lane reporting pass/fail counts must attach the exact source provenance above.

If another lane independently reproduces a different count, the count is disputed until the SHA,
dirty state, command, environment, and collection status are reconciled.

No one may "average" or choose the prettier number.

## 8. Mutation / gate integrity

A mutation test is meaningful only after collection and the unmutated baseline both execute.

Required sequence:

    collect baseline
    -> execute baseline
    -> apply isolated mutation
    -> collect mutation tree
    -> execute mutation
    -> verify intended gate goes red

A mutation that fails only because the suite no longer imports does not prove the business gate works.

### Red-baseline mutation rule

A mutation is only measurable against a gate that is GREEN on the unmutated baseline.

If the target gate is already RED before mutation, the mutation result MUST be recorded as:

    NOT_MEASURABLE_RED_BASE

and MUST NOT be reported as "killed", "survived", or "mutation passed".

Required sequence for a measurable mutation:

    baseline target gate = GREEN
    -> apply one isolated semantic mutation
    -> target gate becomes RED
    -> mutation = KILLED

If the baseline target gate is RED, first repair or choose a different independent GREEN gate.
Do not use an already-failing assertion as evidence that the mutation framework has teeth.

A mutation campaign may still include RED-baseline probes for diagnosis, but those probes are
diagnostic only and do not count toward mutation-kill acceptance totals.

## 9. Freeze sentence

**No collection, no denominator; no denominator, no red/green count.**
