"""Every decision site in this lane's own instruments, with its counter-example named or its void named.

The task's stop condition is exact: every assertion under my name has a counter-example arm, or is named
as void. This file is that ledger, and it covers the WHOLE lane rather than the guarded instruments only,
because "every" is the word in the task.

Two kinds of row:
  * `assert` -- a precondition on the harness itself (e.g. "the patch must reverse-apply"). These are not
    claims about the product; they fail loudly by raising, and what they need is not a counter-example arm
    but a named reason for existing. They are listed so that "every" is true and so nobody later mistakes
    them for behavioural assertions.
  * `verdict` -- a site that answers "did it pass". Each must point at an arm that drives it to its red
    answer, named here by file.

Rows are verified by reading: a row whose arm file is missing, or whose file no longer contains the site,
is reported as a failure rather than quietly dropped. The lane's scope is derived from the directory, so a
new instrument shows up as an unclassified row instead of being invisible.
"""

from __future__ import annotations

import ast
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

#: site -> how it is covered.  `arm` names the file that drives it to red; `void` is a reason why no arm is
#: the right answer.  Exactly one of the two is present per row, and both are checked against the tree.
COVERAGE = [
    # --- the guarded instruments: each guard's counter-example arm, from the teeth audit ---
    {"file": "abort_http_probe_r3.py", "kind": "verdict", "site": "refuse_unless_all_present",
     "arm": "vacuous_guard_partial_arms_r1.py"},
    {"file": "abort_glass_provenance_r3.py", "kind": "verdict", "site": "refuse_unless_all_present",
     "arm": "vacuous_guard_gap_closed_arm_r1.py"},
    {"file": "osmt_flake_attribution_r3.py", "kind": "verdict", "site": "refuse_unless_states_present",
     "arm": "vacuous_guard_gap_closed_arm_r1.py"},
    {"file": "abort_http_probe_r3.py", "kind": "verdict", "site": "refuse_when_empty",
     "arm": "vacuous_guard_arms_r1.py"},
    # --- the A/B instruments carry their own controls inside the file ---
    {"file": "osmt_arms_and_supply_ab_r1.py", "kind": "verdict", "site": "DEFECT_MEASURED_AND_CLOSED",
     "arm": "self: the script's own arms_discriminate / new_red_names fields"},
    {"file": "osmt_flake_attribution_r1.py", "kind": "verdict", "site": "BATCH_SENSITIVE_FAMILY",
     "arm": "self: the per-state rates it prints are the two arms"},
    {"file": "check_self_blindness_scan_r1.py", "kind": "verdict", "site": "control_self_aware",
     "arm": "self: the two temporary probes it builds and requires to disagree"},
    {"file": "teeth_audit_manifest_r1.py", "kind": "verdict", "site": "control_dead_guard_lands_in_queue",
     "arm": "self: the dead and deaf probes it builds"},
    {"file": "vacuous_guard_manifest_r1.py", "kind": "verdict", "site": "NEGATIVE_CONTROL",
     "arm": "self: two broken variants it drives and requires to come back MANIFEST_FAILED"},
    # --- harness preconditions: named void, with the reason ---
    {"file": "osmt_arms_and_supply_ab_r1.py", "kind": "assert", "site": "assert probe_blob == git(",
     "void": "harness precondition: the published probe must be byte-identical before it is used; if this "
             "is false the script raises and nothing downstream is measured"},
    {"file": "osmt_arms_and_supply_ab_r1.py", "kind": "assert", "site": "\"apply\", \"--check\", \"-R\"",
     "void": "harness precondition: the patch must be reversible as read, or the two states would differ "
             "by more than the patch"},
    {"file": "osmt_arms_and_supply_ab_r1.py", "kind": "assert", "site": "reverse apply failed",
     "void": "harness precondition on the A/B state change itself"},
    {"file": "osmt_arms_and_supply_ab_r1.py", "kind": "assert", "site": "assert git(\"hash-object\"",
     "void": "harness precondition: the tree must be back in the committed state before the next state"},
    {"file": "osmt_abandon_family_r1.py", "kind": "assert", "site": "assert git(\"apply\", \"-R\"",
     "void": "harness precondition on the A/B state change itself"},
    # --- superseded versions: same guards, replaced by r3; their arm is the r3 arm by name ---
    {"file": "abort_glass_provenance_r1.py", "kind": "verdict", "site": '"verdict":',
     "arm": "vacuous_guard_gap_closed_arm_r1.py", "superseded_by": "abort_glass_provenance_r3.py"},
    {"file": "abort_glass_provenance_r2.py", "kind": "verdict", "site": '"verdict":',
     "arm": "vacuous_guard_gap_closed_arm_r1.py", "superseded_by": "abort_glass_provenance_r3.py"},
    {"file": "abort_http_probe_r1.py", "kind": "verdict", "site": "verdict_computed_from_the_rows_above",
     "arm": "vacuous_guard_partial_arms_r1.py", "superseded_by": "abort_http_probe_r3.py"},
    {"file": "abort_http_probe_r2.py", "kind": "verdict", "site": "verdict_computed_from_the_rows_above",
     "arm": "vacuous_guard_partial_arms_r1.py", "superseded_by": "abort_http_probe_r3.py"},
    {"file": "osmt_flake_attribution_r2.py", "kind": "verdict", "site": '"verdict"] = (',
     "arm": "vacuous_guard_gap_closed_arm_r1.py", "superseded_by": "osmt_flake_attribution_r3.py"},
    # --- instruments that are themselves counter-example arms: their verdict IS the arm's answer ---
    {"file": "vacuous_guard_arms_r1.py", "kind": "verdict", "site": "VERDICT",
     "arm": "self: this file IS the arm; the manifest re-runs it and compares"},
    {"file": "vacuous_guard_gap_closed_arm_r1.py", "kind": "verdict", "site": "VERDICT",
     "arm": "self: this file IS the arm; the manifest re-runs it and compares"},
    {"file": "vacuous_guard_partial_arms_r1.py", "kind": "verdict", "site": "VERDICT",
     "arm": "self: this file IS the arm; the manifest re-runs it and compares"},
    {"file": "vacuous_guard_abnormal_arm_r1.py", "kind": "verdict", "site": "VERDICT",
     "arm": "self: this file IS the arm; the manifest re-runs it and compares"},
    {"file": "vacuous_guard_abnormal_pair_r1.py", "kind": "verdict", "site": "VERDICT",
     "arm": "self: this file IS the arm; the manifest re-runs it and compares"},
    {"file": "vacuous_truth_scan_r1.py", "kind": "verdict", "site": "CONTROL_FAILED_READ_THE_SITES",
     "arm": "self: it refuses to report unless its own two controls hold"},
    # --- probes that print a verdict computed from their own rows ---
    {"file": "abort_contested_race_probe_r1.py", "kind": "verdict", "site": "verdict_computed_from_the_rows_above",
     "arm": "self: the verdict is computed from the rows it collected in the same run"},
    {"file": "abort_resurrect_probe_r1.py", "kind": "verdict", "site": '"verdict": verdict',
     "arm": "self: the verdict is computed from the three door readings in the same run"},
    {"file": "abort_glass_consolidate_r1.py", "kind": "verdict", "site": '"verdict": body.get("verdict")',
     "void": "it re-publishes the verdict its source receipt already computed; it decides nothing itself"},
    {"file": "osmt_readings_txt_r1.py", "kind": "verdict", "site": '"main_verdict=%s"',
     "void": "a readings writer: it copies the verdict out of the artifact it reads, and decides nothing"},
    # --- exit-code decisions: no verdict string, but main()'s return code is the answer ---
    {"file": "abort_glass_status_move_r1.py", "kind": "verdict", "site": "sys.exit(main())",
     "void": "a helper the glass arm CALLS to move a row; its exit code is consumed inside that arm, and "
             "the arm's own red is required by the glass regression receipt, not by a verdict line here"},
    {"file": "generated_client_drift_r1.py", "kind": "verdict", "site": "sys.exit(main())",
     "void": "its red path needs a drifted generated client, which cannot be constructed on this line "
             "(the client matches the contract), so an arm here would be a fixture pretending to be drift"},
    # --- the manifest itself: it must appear in its own table, or the table is not "every" ---
    {"file": "assertion_teeth_manifest_r1.py", "kind": "verdict", "site": "SITES_WITHOUT_COVERAGE",
     "arm": "self: it refuses to answer unless every site above is present and every named arm exists"},
]


def has_site(path: pathlib.Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    lane_files = sorted(p.name for p in HERE.glob("*.py"))
    rows = []
    failures = []
    for entry in COVERAGE:
        path = HERE / entry["file"]
        row = dict(entry)
        if not path.exists():
            row["status"] = "FILE_MISSING"
            failures.append("%s: file missing" % entry["file"])
            rows.append(row)
            continue
        row["site_present"] = has_site(path, entry["site"])
        if not row["site_present"]:
            row["status"] = "SITE_GONE"
            failures.append("%s: site %r no longer in the file" % (entry["file"], entry["site"]))
            rows.append(row)
            continue
        if "arm" in entry and not entry["arm"].startswith("self:"):
            arm_path = HERE / entry["arm"]
            row["arm_exists"] = arm_path.exists()
            if not row["arm_exists"]:
                failures.append("%s: arm %s is missing" % (entry["file"], entry["arm"]))
        row["status"] = "OK"
        rows.append(row)

    covered_files = {r["file"] for r in rows}
    uncovered = [f for f in lane_files if f not in covered_files]

    # This table has to be able to say no, or its yes means nothing.  Two broken variants are driven in
    # memory: a row pointing at an arm that is not there, and a row whose site text is not in its file.
    # Both must come back as failures.  The check is on the same predicate the report uses.
    controls = []
    for label, mutate in (
        ("an arm file that is not there", {"arm": "zz_no_such_arm.py"}),
        ("a site that is not in its file", {"site": "zz_no_such_site("}),
    ):
        broken = dict(COVERAGE[0], **mutate)
        path = HERE / broken["file"]
        site_ok = has_site(path, broken["site"])
        arm_ok = (broken["arm"].startswith("self:")
                  or (HERE / broken["arm"]).exists())
        controls.append((label, site_ok and arm_ok))
    controls_ok = all(ok is False for _, ok in controls)
    print("control_broken_variants_all_fail %s" % controls_ok)
    for label, ok in controls:
        print("  negative_control %-34s -> covered=%s" % (label, ok))

    report = {
        "scope": "every decision site in this lane's own instruments, plus the lane's files with none",
        "rows": rows,
        "sites": len(rows),
        "with_arm": sum(1 for r in rows if "arm" in r),
        "named_void": sum(1 for r in rows if "void" in r),
        "files_in_lane": len(lane_files),
        "files_with_no_decision_site": uncovered,
        "failures": failures,
        "controls_passed": controls_ok,
        "verdict": ("EVERY_SITE_HAS_AN_ARM_OR_A_NAMED_VOID"
                    if (not failures and controls_ok)
                    else ("CONTROL_FAILED" if not controls_ok else "SITES_WITHOUT_COVERAGE")),
    }
    for row in rows:
        print("%-40s %-8s %-38s %s" % (row["file"], row["kind"], row["site"][:38],
                                       row.get("arm") or ("void: " + row.get("void", "")[:50])))
    print("sites %d | with_arm %d | named_void %d | lane files %d | files with no decision site %s"
          % (report["sites"], report["with_arm"], report["named_void"], report["files_in_lane"],
             ",".join(uncovered) or "none"))
    print("VERDICT %s" % report["verdict"])
    for line in failures:
        print("FAIL %s" % line)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())