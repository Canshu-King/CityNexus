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

## 9. Evidence-package freeze rule

When a lane ships a validation ZIP, manifest integrity is part of the evidence contract.

Required order:

    finish the last probe / script / DB write
    -> freeze evidence payloads
    -> generate manifest from the frozen payloads
    -> build the archive
    -> verify archive payloads against that manifest

A manifest generated before later evidence rewrites is STALE and cannot be cited as proof of the
final package contents.

At minimum:

- every included evidence payload that the report relies on must either match the manifest's
  recorded size/hash or be explicitly declared unmanifested;
- a file modified after the manifest generation time must trigger manifest regeneration;
- the manifest must not claim a self-hash by pretending the manifest file was zero bytes;
- if the manifest intentionally covers a superset of the delivered ZIP, the report must say so;
- final acceptance reports must distinguish historical evidence from the exact scripts that can
  reproduce it now.

Package-integrity mismatch does not automatically invalidate a measured product observation, but
it blocks any claim that the delivery is a self-consistent reproducible evidence bundle.

## 10. Mutation evidence receipt

Every mutation claimed as KILLED must carry a compact, replayable receipt.

Required fields:

    base_source
    base_sha
    base_tree_kind = WORKTREE | ARCHIVE_EXPORT
    target_nodeid
    baseline_target_result = GREEN
    mutation_file
    mutation_line_or_symbol
    mutation_summary
    mutation_collect_result
    mutated_target_result = RED
    mutated_failure_excerpt
    cleanup_or_restore_result

Rules:

1. The target nodeid must be named **before** the mutation result is interpreted.
2. The baseline target must be GREEN on the exact same base source.
3. The mutation tree must still collect; import/collection failure is INVALID_MUTATION_EVIDENCE.
4. The mutated target must fail for the intended semantic assertion, not for an unrelated setup error.
5. Report the exact file:line (or stable symbol when line numbers are not stable) where the mutation was applied.
6. Include the first relevant failure/assertion excerpt that demonstrates the intended GREEN -> RED transition.
7. If the baseline target is already RED, record `NOT_MEASURABLE_RED_BASE`.
8. Diagnostic mutations on red baselines are allowed, but they do not count toward kill totals.
9. After an in-place mutation, prove the tree was restored before any later baseline is reported.
10. Prefer an isolated mutation worktree or disposable archive extraction over mutating a shared lane tree.

A campaign summary should count separately:

    KILLED
    SURVIVED
    NOT_MEASURABLE_RED_BASE
    INVALID_MUTATION_EVIDENCE

Do not collapse these categories into a single "mutation pass" number.

## 11. Common-cause proof rule

Multiple tests failing at the same time do **not** prove a common root cause.

A cluster may be called common-cause only when at least one of these is demonstrated:

1. removing/fixing cause A makes the whole claimed cluster turn GREEN while preserving the
   individual business assertions; or
2. the tests are shown to consume the same corrupted predicate/state/value and that shared
   predicate is the reason each test fails.

Merely observing simultaneous RED results is correlation, not causal proof.

For network-isolation work specifically:

- a default no-network boundary is test-environment hygiene;
- it is not a product fix;
- product assertions that remain RED with the boundary enabled remain product/test-contract
  failures until separately resolved.

Freeze sentence:

> **Co-red is not co-causal. Prove the shared cause.**

### Batch disappearance rule

A test that disappears from a batch result is not automatically GREEN.

If a previously RED test is absent from a later batch, classify it by a targeted rerun or record
it as NOT_RUN / BATCH_SENSITIVE / ORDER_DEPENDENT as appropriate.

Do not count "not seen in this batch" as "fixed".

## 12. Identifier and claim provenance

Human-typed identifiers are not evidence by themselves.

Whenever a lane cites a commit SHA as proof, attach the raw output of:

    git log -1 --format='%h %ad %s' --date=format:'%H:%M' <sha>

or an equivalent repository-native canonical lookup that proves:

- the commit exists in the claimed repository;
- the short/full SHA resolves to that commit;
- timestamp and subject match the claimed work.

If the commit is not present locally but is verified by a repository API, include the canonical
repository/ref/commit response instead.

Do not accept a bare hand-typed SHA in an ORD delivery.

Before copying another lane's or arbiter's implementation claim into an execution order, verify
the relevant code once at the cited SHA/ref when the claim affects architecture, ownership,
acceptance, or remediation scope.

Examples that require re-verification before propagation:

- "endpoint A and endpoint B use different resolvers";
- "Agent surface exposes only four proposal fields";
- "this commit contains scoped reset";
- "this branch already includes the fix".

A quoted conclusion without a replayable identifier/code check must remain attributed and
unverified, not silently promoted to project fact.

## 13. Test-instrument semantic equivalence

A test harness may block real external I/O, but the block should preserve the semantic failure
class that production code is designed to handle.

For HTTPX-based code, a synthetic network denial should normally surface through the
`httpx.TransportError` family (or the exact typed failure the contract intends to exercise),
not an unrelated bare `RuntimeError`, unless the test explicitly targets that unexpected-error
path.

The instrument is allowed to change **whether** external I/O happens. It must not accidentally
change **what kind of failure** the product observes, because that confounds the test.

Likewise, command-line reporting quirks are not collection failures. A collection gate must use
the pytest exit code / collection error signal and collected node data, not depend solely on one
specific quiet-mode summary line such as `N tests collected`.

## 14. Independent verification depth

Acceptance language must state how much of a claimed result was independently reproduced.

Use these evidence classes:

    REPRODUCED
    FORMAT_CHECKED
    SELF_REPORTED

Definitions:

- `REPRODUCED`: the reviewer independently reran the relevant command/probe against the stated
  source and observed the claimed behavior.
- `FORMAT_CHECKED`: the reviewer verified that the receipt/package contains the required fields,
  provenance, and internal structure, but did not rerun the semantic experiment.
- `SELF_REPORTED`: the result is supplied by the implementation lane and has not yet received
  independent reproduction or complete receipt validation.

A mixed delivery must report the split explicitly, for example:

    ACCEPTED-1-REPRODUCED-2-FORMAT-CHECKED

and must not collapse that into "3 verified".

Rules:

1. FORMAT_CHECKED is useful evidence but is weaker than REPRODUCED.
2. SELF_REPORTED evidence may support triage but cannot by itself close a hard acceptance gate
   that requires independent proof.
3. Sampling is allowed when the order explicitly permits it, but the sample size and unrerun
   remainder must be named.
4. Independent reproduction must use the exact source/provenance rules in this document.
5. Mutation receipts independently rerun by the reviewer may be marked REPRODUCED; merely checking
   the presence of the 10 receipt fields is FORMAT_CHECKED.

Freeze sentence:

> **State what you reran, what you only inspected, and what you merely received.**

## 15. Upstream-gate reachability rule

A probe cannot conclude that a downstream guard is absent unless the request has first reached
that guard.

If authentication, authorization, routing, validation, or another upstream gate rejects the
request first, the downstream guard result is:

    INCONCLUSIVE_UPSTREAM_GATE

and not PASS/FAIL for the downstream control.

Examples:

- anonymous request -> 401 before preview-reset guard:
  this does NOT prove PREVIEW_GUARDED is absent;
- authenticated request -> 403 PREVIEW_GUARDED:
  this is evidence that the reset guard was reached and enforced;
- malformed request -> 422 before authorization:
  this does NOT prove authorization is permissive.

Every guard probe should record:

    target_guard
    upstream_prerequisites
    identity/authentication used
    observed_status
    observed_machine_reason
    reached_target_guard = true | false

A negative conclusion such as "guard missing" requires `reached_target_guard=true`.

Freeze sentence:

> **No reachability, no downstream verdict.**

## 16. Freeze sentence

**No collection, no denominator; no denominator, no red/green count.**
