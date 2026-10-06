# -*- coding: utf-8 -*-
"""Flatten the ORD-0574 readings into one TSV row per number, so the ledger block can anchor each value.

Every value is read out of the artifacts produced by the real runs; nothing is typed here. Missing key = ABORT.
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
J = lambda n: json.loads(io.open(os.path.join(HERE, n), encoding="utf-8").read())


def verdict_of(text):
    """The flip leg's stdout was stored truncated, so read the verdict out of it rather than re-parsing it."""
    m = re.search(r'"verdict":\s*"([A-Z_]+)"', text)
    if not m:
        raise SystemExit("ABORT: no verdict in the stored flip output - the value would be invented")
    return m.group(1)

R = J("ord0574_l1_rerun_r2.json")          # before: shipped tool on the both-empty fixture + exit-code legs
T = J("test_ord0574_r2.json")              # after: the r2 candidate, isolated tree, all legs
B = J("build_ord0574_r2.json")             # the two candidate files and their blobs
P = J("ord0574_both_empty_r1.json")        # first pass (single-sided + real-ledger controls in the same run)

rows = []
rows.append(("ref_used", R["ref"]))
rows.append(("remote_fixture_path", R["path"]))
rows.append(("remote_fixture_zero_bytes", R["remote_side_verified_zero_bytes"]))
rows.append(("before_shipped_verdict", R["L1_verdict"]))
rows.append(("before_shipped_exit_code", R["L1_exit_code"]))
rows.append(("before_local_blob", R["L1_local_blob"]))
rows.append(("before_remote_blob", R["L1_remote_blob"]))
rows.append(("before_local_bytes", R["L1_local_bytes"]))
rows.append(("before_remote_bytes", R["L1_remote_bytes"]))
rows.append(("before_points", "%d/%d" % (R["L1_points_matched"], R["L1_points_compared"])))
rows.append(("before_repeat_verdict", R["L1_repeat_verdict"]))
rows.append(("before_stable_across_two_runs", R["L1_stable"]))
rows.append(("before_cli_no_token_rc", R["L4_no_token_rc"]))
rows.append(("before_docstring_promise_kept", R["L4_promise_kept"]))
rows.append(("before_importer_refusal_leg", R["L4c_importer_leg"]))
rows.append(("control_local_empty_verdict", P["L2_verdict"]))
rows.append(("control_real_ledger_verdict", verdict_of(P["L3_real_ledger"]["stdout"])))
rows.append(("control_selftest_rc", P["L5_selftest"]["rc"]))

rows.append(("after_candidate_verdict", T["T1_candidate"]["verdict"]))
rows.append(("after_candidate_exit_code", T["T1_candidate"]["exit_code"]))
rows.append(("after_candidate_process_rc", T["T1_rc"]))
rows.append(("after_candidate_floor_flag", T["T1_candidate"]["emptiness_floor"]))
rows.append(("after_shipped_same_fixture_verdict", T["T1b_shipped_r1"]["verdict"]))
rows.append(("after_shipped_same_fixture_exit_code", T["T1b_shipped_r1"]["exit_code"]))
rows.append(("after_one_sided_empty_verdict", T["T2_candidate_local_empty"]["verdict"]))
rows.append(("after_one_sided_empty_rc", T["T2_candidate_local_empty"]["rc"]))
rows.append(("after_real_ledger_verdict", T["T3_candidate_real_ledger"]["verdict"]))
rows.append(("after_real_ledger_rc", T["T3_candidate_real_ledger"]["rc"]))
rows.append(("after_real_ledger_floor_flag", T["T3_candidate_real_ledger"]["emptiness_floor"]))
rows.append(("after_cli_no_token_rc", T["T4_cli_no_token_rc"]))
rows.append(("after_cli_no_token_stderr", T["T4_cli_stderr"][:60]))
rows.append(("after_selftest_rc", T["T5_selftest_rc"]))
rows.append(("after_selftest_arms_all_correct", T["T5_arms_all_correct"]))
rows.append(("after_hook_selftest_rc", T["T6_hook_selftest_rc"]))
rows.append(("after_hook_arms_all_correct", T["T6_hook_arms_all_correct"]))
rows.append(("after_flip_arm_rc", T["T7_flip"]["rc"]))
rows.append(("after_flip_arm_verdict", verdict_of(T["T7_flip"]["stdout"])))
rows.append(("after_hook_on_empty_returned_exit_code", T["T8_hook_returned_exit_code"]))
rows.append(("after_hook_on_empty_trail_appended", T["T8_hook_trail_appended"]))
rows.append(("after_all_arms_green", T["all_arms_green"]))
rows.append(("isolation_removed", T["isolation_removed"]))

rows.append(("candidate_check_file", os.path.basename(B["check_r2"]["path"])))
rows.append(("candidate_check_bytes", B["check_r2"]["bytes"]))
rows.append(("candidate_check_blob", B["check_r2"]["git_blob"]))
rows.append(("candidate_check_parent_blob", B["check_r2"]["parent_blob"]))
rows.append(("candidate_check_edits", B["check_r2"]["edits"]))
rows.append(("candidate_hook_file", os.path.basename(B["hook_r2"]["path"])))
rows.append(("candidate_hook_bytes", B["hook_r2"]["bytes"]))
rows.append(("candidate_hook_blob", B["hook_r2"]["git_blob"]))
rows.append(("candidate_hook_parent_blob", B["hook_r2"]["parent_blob"]))
rows.append(("candidate_hook_edits", B["hook_r2"]["edits"]))
rows.append(("published_check_blob_still_readable", B["published_blobs_still_readable"][0]["t"]))
rows.append(("published_hook_blob_still_readable", B["published_blobs_still_readable"][1]["t"]))

out = os.path.join(HERE, "ord0574_flat_r1.tsv")
with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
    for i, (k, v) in enumerate(rows, start=1):
        fh.write("%d\t%s\t%s\n" % (i, k, v))
print(json.dumps({"rows": len(rows), "out": out, "bytes": os.path.getsize(out)}, ensure_ascii=False))
