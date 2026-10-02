# -*- coding: utf-8 -*-
"""Read the census's 16 near-misses and record, per site, what it actually is.

The census prints candidates; a candidate is only worth reporting after it is opened. Every verdict here is
mine and says so - what was measured is the file, the line and the surrounding source; what is asserted is
whether that shape is a coordinate into the shipped tree (a drift bomb) or something else entirely.
"""
import io
import json
import os

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
VERDICTS = {
    ("backend/tests/test_qoder_ord0307_credential_gate.py", 67): (
        "benign_self_injected",
        "PROBE_REL = backend/app/_ord0307_injected_probe.py - a file the arm writes into its own temporary "
        "root before scanning it; it is never a row of the shipped tree"),
    ("backend/tests/test_qoder_ord0307_credential_gate.py", 97): (
        "benign_self_injected", "same PROBE_REL, same reason"),
    ("backend/tests/test_qoder_ord0307_credential_gate.py", 113): (
        "benign_in_memory_slice", "slices a string the arm built, not a file"),
    ("backend/tests/test_qoder_ord0332_error_receipt.py", 132): (
        "intentionally_strict_derived",
        "owners == ['backend/app/error_receipt.py'] where `owners` is rebuilt every run by walking "
        "backend/app/*.py with the AST for a second literal copy of the field sentence - it names no row, "
        "and a second owner SHOULD go red; that is the guard, not fragility"),
    ("backend/tests/test_qoder_stay_generation_operations.py", 646): (
        "benign_argument_tuple", "retry_after_ms(_Row(RUNNING, 2)) - the number is elapsed seconds, not a line"),
    ("backend/tests/test_qoder_stay_generation_operations.py", 647): ("benign_argument_tuple", "same shape"),
    ("backend/tests/test_qoder_stay_generation_operations.py", 648): ("benign_argument_tuple", "same shape"),
    ("backend/tests/test_qoder_stay_generation_operations.py", 649): ("benign_argument_tuple", "same shape"),
    ("backend/tests/test_qoder_stay_generation_operations.py", 650): ("benign_argument_tuple", "same shape"),
    ("backend/tests/test_qoder_stay_generation_operations.py", 651): ("benign_argument_tuple", "same shape"),
    ("backend/tests/test_qoder_ord0496_calendar_export.py", 530): (
        "benign_in_memory_slice", "physical[7:11] slices the folded iCalendar lines the arm generated"),
    ("backend/tests/test_qoder_ord0496_calendar_export.py", 539): (
        "benign_in_memory_slice", "line[1:2] inspects a continuation line's own first byte"),
    ("backend/tests/test_v1923_final_code_gate.py", 36): (
        "benign_in_memory_slice", "value[11:16] cuts HH:MM out of an isoformat timestamp"),
    ("backend/tests/test_v1923_final_code_gate.py", 453): (
        "benign_in_memory_slice", "splitlines()[0] reads the child process's own stdout"),
    ("backend/tests/test_v7_traveler_twin.py", 81): (
        "benign_argument_range", "activities[1:4] walks rows the test just created"),
    ("backend/tests/_qoder_xproc_caller.py", 39): (
        "benign_argument_range", "sys.argv[1:6] - command-line arguments"),
}


def main():
    doc = json.load(io.open(os.path.join(WORK, "anchor_drift_survey_r1.json"), encoding="utf-8"))
    rows = []
    for r in doc["rows"]:
        key = (r["arm_file"], r["arm_line"])
        v = VERDICTS.get(key, ("UNJUDGED", "no verdict recorded - do not count this row as cleared"))
        r2 = dict(r)
        r2["verdict"] = v[0]
        r2["verdict_reason"] = v[1]
        rows.append(r2)
    unjudged = [r for r in rows if r["verdict"] == "UNJUDGED"]
    drift_bombs = [r for r in rows if r["verdict"] in ("stale_row", "frozen_list_drift")]
    out = {"tip": doc["tip"], "test_files_scanned": doc["test_files_scanned"],
           "candidates": len(rows), "judged": len(rows) - len(unjudged), "unjudged": len(unjudged),
           "by_verdict": {}, "drift_bombs_beyond_the_two_ordered": drift_bombs,
           "patterns_used": ["named_path_with_row", "literal_path_with_row", "index_into_splitlines",
                             "line_slice", "frozen_name_list(multi-line)"],
           "recall_statement": "four shapes only; it would not see a row pinned through a helper that takes "
                               "the number as an argument, nor a dict-key equality. Low recall is declared, "
                               "not hidden.",
           "rows": rows}
    for r in rows:
        out["by_verdict"][r["verdict"]] = out["by_verdict"].get(r["verdict"], 0) + 1
    io.open(os.path.join(WORK, "anchor_survey_verdicts_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"candidates": len(rows), "by_verdict": out["by_verdict"],
                      "beyond_the_two_ordered": len(drift_bombs)}, ensure_ascii=False))


raise SystemExit(main())
