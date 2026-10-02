# -*- coding: utf-8 -*-
"""Census r2 verdicts - the same judgement table, applied to a second generation of the tip.

Two things are re-measured rather than reused: which sites the four patterns find on this tip, and whether
each site is still the one I opened by hand. A site whose line number moved is matched again by the literal
text and reported as MOVED, because a census that silently re-uses last generation's row numbers is the
same failure mode the anchor order was written to kill.
"""
import io
import json
import os

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
#: keyed by (test file, line, form) from the r1 pass, with the literal text kept so a moved line can be
#: re-matched instead of trusted
TABLE = [
    ("backend/tests/test_qoder_ord0307_credential_gate.py", 67, "named_path_with_row",
     "benign_self_injected",
     "PROBE_REL names a file this arm writes into its own temporary root before scanning it"),
    ("backend/tests/test_qoder_ord0307_credential_gate.py", 97, "named_path_with_row",
     "benign_self_injected", "the same injected probe, asserted as (path, line)"),
    ("backend/tests/test_qoder_ord0307_credential_gate.py", 113, "line_slice",
     "benign_in_memory_slice", "slices a string the arm built"),
    ("backend/tests/test_qoder_ord0332_error_receipt.py", 132, "frozen_name_list",
     "intentionally_strict_derived",
     "owners is rebuilt every run by an AST walk for a second literal copy of the field sentence"),
    ("backend/tests/test_qoder_ord0496_calendar_export.py", 530, "line_slice",
     "benign_in_memory_slice", "slices the folded iCalendar lines the arm generated"),
    ("backend/tests/test_qoder_ord0496_calendar_export.py", 539, "line_slice",
     "benign_in_memory_slice", "inspects a continuation line's own first byte"),
    ("backend/tests/test_v1923_final_code_gate.py", 36, "line_slice",
     "benign_in_memory_slice", "cuts HH:MM out of an isoformat timestamp"),
    ("backend/tests/test_v1923_final_code_gate.py", 453, "index_into_splitlines",
     "benign_in_memory_slice", "reads the first line of a child process's own stdout"),
    ("backend/tests/test_v7_traveler_twin.py", 81, "line_slice",
     "benign_argument_range", "walks activity rows the test just created"),
    ("backend/tests/_qoder_xproc_caller.py", 39, "line_slice",
     "benign_argument_range", "sys.argv slice"),
]
for n in (646, 647, 648, 649, 650, 651):
    TABLE.append(("backend/tests/test_qoder_stay_generation_operations.py", n, "named_path_with_row",
                  "benign_argument_tuple", "retry_after_ms(_Row(STATUS, seconds)) - a duration, not a row"))


def main():
    doc = json.load(io.open(os.path.join(WORK, "anchor_drift_survey_r2.json"), encoding="utf-8"))
    rows = []
    for r in doc["rows"]:
        by_line = [t for t in TABLE if t[0] == r["arm_file"] and t[1] == r["arm_line"] and t[2] == r["form"]]
        moved = [t for t in TABLE if t[0] == r["arm_file"] and t[2] == r["form"]
                 and t[3:4] and t[4][:24] == (r["literal"][:24] if r.get("literal") else "")[:24]]
        pick = by_line or moved
        if pick:
            verdict, reason = pick[0][3], pick[0][4]
            status = "same" if by_line else "MOVED_line_number_changed"
        else:
            verdict, reason, status = "UNJUDGED", "no table entry matched this site", "new"
        rows.append(dict(r, verdict=verdict, verdict_reason=reason, match_status=status))
    out = {"tip": doc["tip"], "test_files_scanned": doc["test_files_scanned"], "candidates": len(rows),
           "judged": sum(1 for r in rows if r["verdict"] != "UNJUDGED"),
           "unjudged": sum(1 for r in rows if r["verdict"] == "UNJUDGED"),
           "moved_sites": [r["arm_file"] + ":" + str(r["arm_line"]) for r in rows
                           if r["match_status"] == "MOVED_line_number_changed"],
           "new_sites": [r["arm_file"] + ":" + str(r["arm_line"]) for r in rows
                         if r["match_status"] == "new"],
           "by_verdict": {},
           "drift_bombs_beyond_the_two_ordered": [r for r in rows if r["verdict"] == "stale_row"],
           "patterns_used": ["named_path_with_row", "literal_path_with_row", "index_into_splitlines",
                             "line_slice", "frozen_name_list(multi-line)"],
           "rows": rows}
    for r in rows:
        out["by_verdict"][r["verdict"]] = out["by_verdict"].get(r["verdict"], 0) + 1
    io.open(os.path.join(WORK, "anchor_survey_verdicts_r2.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"tip": out["tip"], "candidates": out["candidates"], "judged": out["judged"],
                      "unjudged": out["unjudged"], "moved": len(out["moved_sites"]),
                      "new": len(out["new_sites"]), "by_verdict": out["by_verdict"]},
                     ensure_ascii=False))


raise SystemExit(main())
