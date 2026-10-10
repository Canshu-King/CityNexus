"""Rewrite generation_transfer_check.py's self-test so judge correctness never depends on the network.

Lane F's critique (bus 5821975506, 2026-09-25T04:4x+08) was correct: the r1-r3 self-test used
`PlanWithAiSheet.tsx` as its live positive control, so either a future frontend order changing that file or
one TLS-truncated response turned a JUDGE failure red - the two causes were indistinguishable in one cell.

r4 pins every control pair's expected blob at BOTH generations in this source, runs the judge offline
against those pinned values, and keeps exactly one live read-back cell whose failure is named separately
(`EXTERNAL_READBACK_...`) so a flaky link can never masquerade as a broken judge, and a changed neighbour
file reports as `CONTROL_PREMISE_DRIFT` with the observed/expected pair printed.
"""
import ast
import io

P = "generation_transfer_check.py"
s = io.open(P, encoding="utf-8", newline="\n").read()

# ---- 1. pinned control pairs (measured with `git rev-parse <ref>:<path>` in the local object store) -----
anchor = 'ONLY_IN_B_FILE = "backend/tests/test_qoder_ord0272_continuation.py"'
assert s.count(anchor) == 1, "anchor 1"
s = s.replace(anchor, anchor + r'''

# r4: every control pair carries its EXPECTED blob at both generations, measured 2026-09-25T04:4x+08 with
# `git rev-parse <ref>:<path>`.  A positive control that is only "whatever this file happens to be today"
# is a premise, not a control - lane F caught that mine could silently stop being identical.
CONTROL_PAIRS = [
    # path, expected at GEN_A (c79e2b4f), expected at GEN_B (dcae1bc96), role
    ("frontend/src/features/planning/PlanWithAiSheet.tsx",
     "58c0580bbb603c939592ae8b911c4a291b4eb60a",
     "58c0580bbb603c939592ae8b911c4a291b4eb60a", "identical"),
    ("backend/app/schemas.py",
     "679ac2eb34b11f4e1a9dc7295292ae1df75c05cb",
     "2e6e26ce17a9e25a40dd8d686f64def5ef1bff0e", "differing"),
    ("contracts/openapi.yaml",
     "4bc58e2e95a09ae46e346d9b243b165a03f58be8",
     "484c64cdaaa41e72d252563b84cef915cb4e80eb", "differing"),
]
EXTERNAL_OK = "EXTERNAL_READBACK_MATCHES_PINNED_EXPECTATIONS"
EXTERNAL_DRIFT = "EXTERNAL_READBACK_CONTROL_PREMISE_DRIFT"
EXTERNAL_UNRESOLVED = "EXTERNAL_READBACK_UNRESOLVED_THIS_RUN"


def pinned_reader(pairs):
    """A reader that answers from the pinned table - so judge correctness is decided offline, deterministically."""
    table = {}
    for path, a, b, _role in pairs:
        table[(GEN_A, path)] = a
        table[(GEN_B, path)] = b

    def read(ref, path):
        return table.get((ref, path))
    return read''', 1)

# ---- 2. replace the network-dependent part of selftest with pinned + one live read-back cell -----------
old_block_start = '    results = {}\n    ok_same, rows_same = judge_cell("pos_transferable"'
old_block_end = '    derived = "SELFTEST_ALL_GREEN" if all(results.values()) else "RED_CELLS:" + ",".join(\n        k for k, v in results.items() if not v)'
i0 = s.index(old_block_start)
i1 = s.index(old_block_end)
new_block = r'''    results = {}
    pr = pinned_reader(CONTROL_PAIRS)
    pos = [c for c in CONTROL_PAIRS if c[3] == "identical"]
    neg = [c for c in CONTROL_PAIRS if c[3] == "differing"]
    ok_same, rows_same = judge_cell("pos_transferable", GEN_A, GEN_B, [pos[0][0]], reader=pr,
                                    claim_kind=CODE_DETERMINED)
    results["positive_identical_file_is_TRANSFERABLE"] = ok_same["verdict"] == TRANSFERABLE
    ok_neg1, _ = judge_cell("neg_schemas", GEN_A, GEN_B, [neg[0][0]], reader=pr, claim_kind=CODE_DETERMINED)
    ok_neg2, _ = judge_cell("neg_openapi", GEN_A, GEN_B, [neg[1][0]], reader=pr, claim_kind=CODE_DETERMINED)
    results["negative_changed_file_is_NOT_TRANSFERABLE"] = (
        ok_neg1["verdict"] == NOT_TRANSFERABLE and ok_neg2["verdict"] == NOT_TRANSFERABLE)
    ok_missing, rows_missing = judge_cell("neg_only_one_generation", GEN_A, GEN_B, [ONLY_IN_B_FILE],
                                          reader=lambda g, p: None if p == ONLY_IN_B_FILE else pr(g, p),
                                          claim_kind=CODE_DETERMINED)
    results["missing_side_is_CITED_BLOB_MISSING_not_pass"] = ok_missing["verdict"] == MISSING
    ok_mixed, rows_mixed = judge_cell("mixed_pair", GEN_A, GEN_B, [pos[0][0], neg[0][0]], reader=pr,
                                      claim_kind=CODE_DETERMINED)
    results["one_changed_file_poisons_the_whole_cell"] = ok_mixed["verdict"] == NOT_TRANSFERABLE
    ok_empty, _ = judge_cell("no_citations", GEN_A, GEN_B, [], reader=pr, claim_kind=CODE_DETERMINED)
    results["cell_citing_nothing_fails_closed"] = ok_empty["verdict"] == MISSING
    # ---- comparison-laxness killers: the SAME judge, fed tampered pairs through the injected reader.
    real = pos[0][1]
    near = real[:-1] + ("0" if real[-1] != "0" else "1")          # one hex different, same length
    prefix = real[:20]                                            # prefix-equal, half the length
    def reader_near(g, p):
        return real if g == GEN_A else near
    def reader_prefix(g, p):
        return real if g == GEN_A else prefix
    def reader_equal(g, p):
        return real
    v_near, _ = judge_cell("killer_near_miss", GEN_A, GEN_B, [pos[0][0]], reader=reader_near,
                           claim_kind=CODE_DETERMINED)
    v_prefix, _ = judge_cell("killer_prefix_only", GEN_A, GEN_B, [pos[0][0]], reader=reader_prefix,
                             claim_kind=CODE_DETERMINED)
    v_equal, _ = judge_cell("control_identical_pair", GEN_A, GEN_B, [pos[0][0]], reader=reader_equal,
                            claim_kind=CODE_DETERMINED)
    results["K1_one_hex_different_is_NOT_TRANSFERABLE"] = v_near["verdict"] == NOT_TRANSFERABLE
    results["K2_prefix_equal_but_shorter_is_NOT_TRANSFERABLE"] = v_prefix["verdict"] == NOT_TRANSFERABLE
    results["K3_identical_pair_control_stays_TRANSFERABLE"] = v_equal["verdict"] == TRANSFERABLE
    results["K4_missing_side_reader_is_NOT_transferable"] = (
        judge_cell("killer_one_side_none", GEN_A, GEN_B, [pos[0][0]],
                   reader=lambda g, p: real if g == GEN_A else None,
                   claim_kind=CODE_DETERMINED)[0]["verdict"] == MISSING)

    def reader_throws(g, p):
        raise RuntimeError("simulated IncompleteRead on a truncated response")
    v_throw, _ = judge_cell("killer_transport_throw", GEN_A, GEN_B, [pos[0][0]], reader=reader_throws,
                            claim_kind=CODE_DETERMINED)
    results["K5_transport_exception_is_CITED_BLOB_MISSING_not_a_crash_not_a_pass"] = v_throw["verdict"] == MISSING

    # ---- r3 killers, from the ORD-0279 lesson the red team caught me in: identical blobs do not license
    #      a claim whose truth is not determined by those bytes, and not declaring a kind is not a pass.
    v_runtime, _ = judge_cell("killer_runtime_measured", GEN_A, GEN_B, [pos[0][0]], reader=reader_equal,
                              claim_kind=RUNTIME_MEASURED)
    results["K6_runtime_measured_with_identical_blobs_is_STILL_NOT_TRANSFERABLE"] = (
        v_runtime["verdict"] == NOT_TRANSFERABLE
        and v_runtime.get("why") == "RUNTIME_MEASURED_NOT_LICENSED_BY_BLOB_IDENTITY")
    v_undeclared, _ = judge_cell("killer_undeclared", GEN_A, GEN_B, [pos[0][0]], reader=reader_equal)
    results["K7_undeclared_claim_kind_is_NOT_a_pass"] = v_undeclared["verdict"] == UNDECLARED

    # ---- r4: ONE live read-back cell, separate from judge correctness.  It can fail for exactly two named
    #      reasons, and neither of them is allowed to look like "the judge is broken".
    live = []
    unresolved = []
    drift = []
    for path, exp_a, exp_b, role in CONTROL_PAIRS:
        got_a, got_b = blob_at(GEN_A, path), blob_at(GEN_B, path)
        row = {"path": path, "role": role, "expected_a": exp_a, "expected_b": exp_b,
               "observed_a": got_a, "observed_b": got_b}
        if not got_a or not got_b:
            row["state"] = "UNRESOLVED"
            unresolved.append(path)
        elif got_a != exp_a or got_b != exp_b:
            row["state"] = "DRIFT"
            drift.append(path)
        else:
            row["state"] = "MATCH"
        live.append(row)
    external_result = EXTERNAL_OK if not unresolved and not drift else (
        EXTERNAL_UNRESOLVED if unresolved else EXTERNAL_DRIFT)
    results["K8_live_readback_cell_exists_and_is_separate_from_judge_checks"] = bool(live)
    judge_derived = "JUDGE_ALL_GREEN" if all(results.values()) else "RED_CELLS:" + ",".join(
        k for k, v in results.items() if not v)
'''
s = s[:i0] + new_block + s[i1:]

# ---- 3. receipt fields: keep judge result and external result distinct ---------------------------------
old_receipt = '        "checks": results,\n        "derived_result": derived,'
assert s.count(old_receipt) == 1, "receipt anchor"
s = s.replace(old_receipt, '        "checks": results,\n        "judge_derived_result": judge_derived,\n        "external_readback_result": external_result,\n        "external_rows": live,\n        "control_pairs_pinned": [list(c) for c in CONTROL_PAIRS],\n        "derived_result": ("SELFTEST_ALL_GREEN" if judge_derived == "JUDGE_ALL_GREEN" and external_result == EXTERNAL_OK\n                             else "JUDGE:" + judge_derived + " | EXTERNAL:" + external_result),', 1)

old_print = '    print("derived_result =", derived)'
assert s.count(old_print) == 1, "print anchor"
s = s.replace(old_print, '    print("judge_derived_result =", judge_derived)\n    print("external_readback_result =", external_result)\n    for row in live:\n        print("  %-58s %-9s obs_a=%s" % (row["path"][-58:], row["state"], (row["observed_a"] or "-")[:12]))\n    print("derived_result =", ("SELFTEST_ALL_GREEN" if judge_derived == "JUDGE_ALL_GREEN" and external_result == EXTERNAL_OK else "SEE_TWO_FIELDS"))', 1)

ast.parse(s)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched", P, len(s.encode("utf-8")), "B; syntax OK")
