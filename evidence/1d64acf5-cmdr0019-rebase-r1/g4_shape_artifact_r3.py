# -*- coding: utf-8 -*-
"""The 形制件 CMDR 02:45 line 10 asks for: what the single-source cell IS now, in machine-readable form.

Everything in here is read out of the reshaped arm and the probe that measured it - the whitelist members,
each predicate's own line number, each state's expectation and result. Nothing is typed twice: if the arm
moves, the numbers in this artifact move with it, and a reader can re-run `g4_shape_probe_r1.py` to check
the pair readings behind Q1 (the hole the basename exemption had, measured under both arms).
"""
import io
import json
import os
import re

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
ARM_REL = "backend/tests/test_qoder_ord0296_write_deadline.py"
OUT_DIR = "review/1d64acf5-g4-single-source-shape"
ART_NAME = "g4_single_source_shape_r3.json"
TIP = "b7bb40ee90619c0febc667394279bd3c8a1d835d"


def main():
    probe = json.load(io.open(os.path.join(HERE, "g4_shape_probe_r3.json"), encoding="utf-8"))
    lines = io.open(os.path.join(WT, ARM_REL.replace("/", os.sep)), encoding="utf-8").read().split("\n")

    def at(needle, label):
        hits = [i for i, l in enumerate(lines, 1) if needle in l]
        if len(hits) != 1:
            raise SystemExit("ABORT: %s found %d times in the arm" % (label, len(hits)))
        return {"line": hits[0], "text": lines[hits[0] - 1].strip()[:150]}

    wl = at("SINGLE_SOURCE_FILES = {", "whitelist")
    body = wl["text"].split("{", 1)[1].split("}", 1)[0]
    members = re.findall(r'"([^"]+)"', body)
    doc = {
        "ruled_on": "CMDR 02:45 敲醒派单 第 10 行（账本现读区间见那块）：`1d64acf5`：G4 盲区尺"
                    "（一千八百三十四裁定：包含式+具名扩容白名单仅限该单元格）按裁定收形，交形制件",
        "measured_against_tip": TIP,
        "arm_file": ARM_REL,
        "arm_function": "test_G4_the_lock_wait_is_written_in_exactly_one_place",
        "pre_reshape_arm_blob": probe["pre_arm_blob"],
        "reshaped_arm_blob": probe["reshaped_arm_blob"],
        "cell_brought_into_shape": {
            "what_it_was": "an exemption granted by BASE NAME: `if Path(rel).name == \"write_deadline.py\"`, "
                           "twice, so anything sharing that name under any other path was outside the ruler",
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
                                         for k, v in r["arms"].items()}}
                            for r in probe["runs"]],
        "pair_reading_behind_the_hole": (lambda q1: {
            "injection": "backend/app/db/deep/write_deadline.py containing DEEP_WAIT = "
                         "\"PRAGMA busy_timeout = 90000\" (this lane's export only, reverted, product "
                         "files re-hashed equal to the tip)",
            "pre_reshape_arm": q1["arms"]["pre_arm"]["pytest"]["summary"],
            "reshaped_arm": q1["arms"]["reshaped"]["pytest"]["summary"],
            "both_sides_reported": bool(q1["arms"]["pre_arm"]["pytest"]["summary"].strip())
            and bool(q1["arms"]["reshaped"]["pytest"]["summary"].strip()),
        })([r for r in probe["runs"] if r["id"] == "Q1_same_name_other_path"][0]),
        "not_changed_by_this_ruling": "the `offenders` cell (a second copy at the request-path constant) and "
                                      "the live floor half both keep their shape; the census ruling named "
                                      "only this cell, so no other judgement file was touched",
        "self_reported_miss_behind_this_artifact": "the first run of the probe had Q0 red: the rot guard I "
                                                   "wrote only accepted an inline number, and the module "
                                                   "itself takes its value from settings, so the shipped "
                                                   "tree failed its own new rule. The guard now accepts "
                                                   "either defining the accessor or stating the number; "
                                                   "8/8 met after that, on the same injections",
        "how_to_recheck": "python g4_shape_probe_r1.py in this lane's export; it re-runs both arms over the "
                          "same injections and re-hashes every reverted file",
    }
    os.makedirs(os.path.join(WT, OUT_DIR.replace("/", os.sep)), exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=1)
    io.open(os.path.join(WT, OUT_DIR.replace("/", os.sep), ART_NAME), "w", encoding="utf-8",
            newline="\n").write(text)
    io.open(os.path.join(HERE, ART_NAME), "w", encoding="utf-8", newline="\n").write(text)
    print(json.dumps({"whitelist": members, "predicates": {k: v["line"] for k, v in
                                                          doc["predicates_in_this_cell"].items()},
                      "states": len(doc["measured_states"]),
                      "all_met": all(s["per_arm"][a]["expected"] == s["per_arm"][a]["got"]
                                     for s in doc["measured_states"] for a in s["per_arm"])},
                     ensure_ascii=False))


raise SystemExit(main())
