# -*- coding: utf-8 -*-
"""The 形制件 for this generation, built out of the three-leg probe rather than typed twice.

What is new relative to the r3/r4 artifacts: the artifact now names all three arms by blob and states which of
them the authoritative line carries, because the leg the earlier artifacts called `pre_reshape_arm` was my own
branch's intermediate commit (blob 395662e3...) and not the line (blob d3e21e90...).  Every line number here is
taken from the arm as it stands in this lane's export; if the arm moves, these numbers move with it.
"""
import io
import json
import os
import re

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
ARM_REL = "backend/tests/test_qoder_ord0296_write_deadline.py"
OUT_DIR = "review/1d64acf5-g4-single-source-shape"
ART_NAME = "g4_single_source_shape_r5.json"
TIP = os.environ["CNX_PROBE_TIP"]  # the live authoritative sha, handed over by the driver that runs this probe


def main():
    probe = json.load(io.open(os.path.join(HERE, "g4_shape_probe_r5.json"), encoding="utf-8"))
    lines = io.open(os.path.join(WT, ARM_REL.replace("/", os.sep)), encoding="utf-8").read().split("\n")

    def at(needle, label):
        hits = [i for i, l in enumerate(lines, 1) if needle in l]
        if len(hits) != 1:
            raise SystemExit("ABORT: %s found %d times in the arm" % (label, len(hits)))
        return {"line": hits[0], "text": lines[hits[0] - 1].strip()[:150]}

    wl = at("SINGLE_SOURCE_FILES = {", "whitelist")
    members = re.findall(r'"([^"]+)"', wl["text"].split("{", 1)[1].split("}", 1)[0])
    by_id = {r["id"]: r for r in probe["runs"]}

    def leg_reading(state, leg):
        arms = by_id[state]["arms"]
        if leg not in arms:
            return {"present": False}
        return {"present": True, "expected": arms[leg]["expect"], "got": arms[leg]["got"],
                "summary": arms[leg]["pytest"]["summary"], "bitting_line": arms[leg]["pytest"]["bitting_line"]}

    holes = probe["holes_open_on_the_line"]
    doc = {
        "ruled_on": "CMDR 02:45 敲醒派单 第 10 行（账本现读区间见那块）：`1d64acf5`：G4 盲区尺"
                    "（一千八百三十四裁定：包含式+具名扩容白名单仅限该单元格）按裁定收形，交形制件",
        "measured_against_tip": TIP,
        "arm_file": ARM_REL,
        "arm_function": "test_G4_the_lock_wait_is_written_in_exactly_one_place",
        "three_arms_measured": {
            "line_arm": {"blob": probe["arm_blobs"]["line_arm"],
                         "what_it_is": "the bytes the authoritative line carries today: exemption granted by "
                                       "base name, and no predicate at all for a sub-floor inline copy",
                         "sub_floor_predicate_present": not probe["line_arm_has_no_sub_floor_predicate"]},
            "branch_pre": {"blob": probe["arm_blobs"]["branch_pre"],
                           "what_it_is": "my own branch's commit before the reshape - base-name exemption, "
                                         "sub-floor predicate already present. This is the leg the r3/r4 "
                                         "artifacts labelled `pre_reshape_arm`",
                         "sub_floor_predicate_present": probe["branch_pre_has_sub_floor_predicate"]},
            "reshaped": {"blob": probe["arm_blobs"]["reshaped"],
                         "what_it_is": "the cell as ruled: named path whitelist, one member as shipped, a "
                                       "named member must justify itself, sub-floor predicate kept"},
        },
        "cell_brought_into_shape": {
            "what_it_was": "an exemption granted by BASE NAME: `if Path(rel).name == \"write_deadline.py\"`, "
                           "so anything sharing that name under any other path was outside the ruler",
            "what_it_is_now": "an exemption granted by a named path whitelist with one member as shipped; "
                              "naming is the only way to expand it, and a named member must justify itself",
            "whitelist_as_shipped": members,
            "whitelist_line": wl,
        },
        "predicates_in_this_cell": {
            "offenders_still_the_same": at('assert offenders == {}', "offenders"),
            "request_path_scale": at("a lock wait at request-path scale is stated inline", "unsourced assert"),
            "sub_floor_consumer_copy": at("already asks the module for the lock wait also states one inline",
                                          "consumer_writes assert"),
            "whitelist_cannot_rot": at("neither defines the accessor nor states a lock-wait", "rot assert"),
            "floor_is_read_live_not_written": at("scale = WD.busy_timeout_ms()", "live scale"),
        },
        "expansion_rule": "a later order that wants a second inline lock-wait writes its own path into "
                          "SINGLE_SOURCE_FILES in the same commit; that path must then either define "
                          "`def busy_timeout_ms(` or state `busy_timeout = <int>`, or the whitelist assert "
                          "reddens - so the table cannot collect names that no longer mean anything",
        "measured_states": [{"id": r["id"], "note": r["note"],
                             "per_arm": {k: {"expected": v["expect"], "got": v["got"],
                                             "bitting_line": v["pytest"]["bitting_line"],
                                             "summary": v["pytest"]["summary"]}
                                         for k, v in r["arms"].items()},
                             "hole_in_this_leg": r["hole_in_this_leg"]}
                            for r in probe["runs"]],
        "holes_open_on_the_line": {
            "states": holes,
            "Q1_same_name_other_path": {
                "injection": "backend/app/db/deep/write_deadline.py containing DEEP_WAIT = "
                             "\"PRAGMA busy_timeout = 90000\" (this lane's export only, reverted, product "
                             "files re-hashed equal to the tip)",
                "line_arm": leg_reading("Q1_same_name_other_path", "line_arm"),
                "branch_pre": leg_reading("Q1_same_name_other_path", "branch_pre"),
                "reshaped": leg_reading("Q1_same_name_other_path", "reshaped"),
            },
            "Q4_sub_floor_consumer_copy": {
                "injection": "backend/app/main.py with SUB_SCALE_COPY = \"PRAGMA busy_timeout = 1200\" "
                             "appended (1200 is below the live floor, and the file already asks settings for "
                             "the number), reverted and re-hashed",
                "line_arm": leg_reading("Q4_sub_floor_consumer_copy", "line_arm"),
                "branch_pre": leg_reading("Q4_sub_floor_consumer_copy", "branch_pre"),
                "reshaped": leg_reading("Q4_sub_floor_consumer_copy", "reshaped"),
            },
            "all_sides_reported": all(by_id[h]["arms"][a]["pytest"]["summary"].strip()
                                      for h in holes for a in by_id[h]["arms"]),
        },
        "not_changed_by_this_ruling": "the `offenders` cell (a second copy at the request-path constant) and "
                                      "the live floor half both keep their shape; the census ruling named "
                                      "only this cell, so no other judgement file was touched",
        "self_reported_miss_behind_this_artifact": "two things, and neither changes a reading that was "
                                                   "published. (a) the first run of this probe's r4 expected "
                                                   "the line's arm to be red on the sub-floor state; it read "
                                                   "green, which is how I found that the leg I had been "
                                                   "calling `pre` was my branch's own intermediate commit "
                                                   "rather than the line, so the pair is now three legs and "
                                                   "the r4 run's output stays unpublished. (b) earlier still, "
                                                   "the rot guard I wrote accepted only an inline number, so "
                                                   "the shipped tree failed its own new rule until the guard "
                                                   "was changed to accept either defining the accessor or "
                                                   "stating the number",
        "how_to_recheck": "CNX_PROBE_TIP=<the live tip> python g4_shape_probe_r5.py in this lane's export: it "
                          "materialises each leg, proves its blob, runs the three over the same injections "
                          "and re-hashes every reverted file",
    }
    os.makedirs(os.path.join(WT, OUT_DIR.replace("/", os.sep)), exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=1)
    io.open(os.path.join(WT, OUT_DIR.replace("/", os.sep), ART_NAME), "w", encoding="utf-8",
            newline="\n").write(text)
    io.open(os.path.join(HERE, ART_NAME), "w", encoding="utf-8", newline="\n").write(text)
    print(json.dumps({"artifact": ART_NAME, "whitelist": members,
                      "predicates": {k: v["line"] for k, v in doc["predicates_in_this_cell"].items()},
                      "states": len(doc["measured_states"]), "holes": holes,
                      "all_met": all(s["per_arm"][a]["expected"] == s["per_arm"][a]["got"]
                                     for s in doc["measured_states"] for a in s["per_arm"]),
                      "every_side_has_a_summary": doc["holes_open_on_the_line"]["all_sides_reported"]},
                     ensure_ascii=False))


raise SystemExit(main())
