# -*- coding: utf-8 -*-
"""Census round 3 verdicts: what I judge each site to be, against what the ruler computed and what the red produced.

Three readings are kept apart on purpose. The survey's regex only knows the left hand is derived from
something; the arms script's `states_growth_is_the_defect` predicate looks for a prohibition anywhere in the
enclosing function, which is too coarse - a comment about one assertion was enough to mark a different
assertion in the same function as a closed-set guard, and the produced red at
`test_qoder_ord0476_checkins.py:500` names exactly that mistake. So every site also carries a hand verdict,
and the disagreement list is the deliverable rather than something to smooth over.
"""
import io
import json
import os

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"

#: (file, line) -> (verdict, why) - `why` quotes nothing that is not re-read from the tip below
HAND = {
    "backend/tests/test_qoder_ord0332_error_receipt.py:132": (
        "growth_is_the_defect_guard",
        "the set is every file in backend/app holding this field sentence; a second one IS the defect the "
        "message names, so it cannot be loosened to a subset test"),
    "backend/tests/test_qoder_ord0402_recycle_bin.py:305": (
        "drift_prone_open_equality",
        "required of a schema component; any later order that legitimately adds a required bin fact reddens "
        "a door that only promised these two"),
    "backend/tests/test_qoder_ord0434_share_grants.py:413": (
        "drift_prone_open_equality",
        "roles read back from a live ACL response; a fourth role is an ORD-0434-side decision this arm "
        "cannot distinguish from an unrelated edit"),
    "backend/tests/test_qoder_ord0444_collections.py:481": (
        "drift_prone_open_equality",
        "documented response codes of one door - the class the produced red demonstrates one floor down"),
    "backend/tests/test_qoder_ord0476_checkins.py:499": (
        "drift_prone_open_equality",
        "documented response codes of the write door, same class as the read-door equality two lines down"),
    "backend/tests/test_qoder_ord0476_checkins.py:500": (
        "drift_prone_open_equality",
        "documented response codes of the read door - THIS is the arm that went red on the added 429"),
    "backend/tests/test_qoder_ord0476_checkins.py:505": (
        "growth_is_the_defect_guard",
        "request-body properties of the create door, and its own comment says the caller supplies no time "
        "and no target-kind; a new key here is the thing being refused"),
    "backend/tests/test_qoder_ord0496_calendar_export.py:944": (
        "drift_prone_open_equality",
        "documented response codes of the export door"),
    "backend/tests/test_qoder_ord0503_member_doors.py:499": (
        "growth_is_the_defect_guard",
        "self-exit body keys plus additionalProperties False; the docstring names a grown member_id as "
        "another order's door, so growth is the finding"),
    "backend/tests/test_v192_shadow_trial_gate.py:104": (
        "not_product_derived",
        "the two rows are literals handed to canon() in the same statement - no product artifact can "
        "drift this line"),
    "backend/tests/test_qoder_ord0307_credential_gate.py:67": (
        "self_injected_probe",
        "PROBE_REL is a path this arm builds for its own scanner input, so the ruler's TARGET_NOT_IN_TREE "
        "is the ruler not seeing a file that was never meant to exist in the tree"),
}


def main():
    arms = json.load(io.open(os.path.join(WORK, "census_r3_arms_r1.json"), encoding="utf-8"))
    counter = json.load(io.open(os.path.join(WORK, "census_r3_counterarm_r1.json"), encoding="utf-8"))
    red_arms = {s.split("::")[0].replace("tests/", "backend/tests/") for s in counter["newly_red"]}
    #: the failing line as the receipt's own location string reports it, so a three-site function does not
    #: get credited with three reds when one line bit
    red_lines = set()
    for w in counter["what_each_red_says"]:
        parts = w["what_it_says"].replace("\\", "/").split(":")
        hits = [p for p in parts if p.isdigit()]
        if hits and w["arm"].startswith("tests/"):
            red_lines.add(("backend/" + w["arm"].split("::")[0], int(hits[-1])))
    rows = []
    for j in arms["sites_out"]:
        key = "%s:%s" % (j["file"], j["line"])
        verdict, why = HAND.get(key, ("UNJUDGED", "no hand entry for this site"))
        mechanical = {"closed_set_guard": "growth_is_the_defect_guard",
                      "open_set_equality": "drift_prone_open_equality",
                      "unresolved_by_ruler": "self_injected_probe"}[j["class"]]
        rows.append({"site": key, "arm": j["nodeid"], "arm_ran_as": j["arm_ran_as"],
                     "named_entries": j["named_entries"], "left_hand_reads": j["left_hand_reads"],
                     "mechanical_class": j["class"], "mechanical_reading": mechanical,
                     "hand_verdict": verdict, "hand_why": why,
                     "agree": mechanical == verdict,
                     "arm_red_on_the_429_add": j["file"] in red_arms,
                     "this_line_is_the_bitting_line": (j["file"], j["line"]) in red_lines})
    out = {"tip": arms["tip"], "sites": len(rows),
           "hand_verdicts": {v: sum(1 for r in rows if r["hand_verdict"] == v)
                             for v in sorted({r["hand_verdict"] for r in rows})},
           "mechanical_agrees": sum(1 for r in rows if r["agree"]),
           "mechanical_disagrees": [r["site"] + " ruler=" + r["mechanical_reading"]
                                    + " hand=" + r["hand_verdict"] for r in rows if not r["agree"]],
           "counter_arm": {"mutation": counter["mutation"], "clean_summary": counter["runs"]["clean"]
                           ["summary"], "mutated_summary": counter["runs"]["mutated"]["summary"],
                           "newly_red": counter["newly_red"],
                           "bitting_lines": ["%s:%s" % (f, n) for f, n in sorted(red_lines)],
                           "restored_byte_equal": counter["restored_byte_equal"]},
           "all_arms_green_as_shipped": all(r["arm_ran_as"] == "PASSED" for r in rows),
           "rows": rows}
    io.open(os.path.join(WORK, "census_r3_verdicts_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"sites": out["sites"], "hand": out["hand_verdicts"],
                      "agree": out["mechanical_agrees"], "disagree": out["mechanical_disagrees"],
                      "all_green": out["all_arms_green_as_shipped"],
                      "newly_red": out["counter_arm"]["newly_red"]}, ensure_ascii=False, indent=1))


raise SystemExit(main())
