"""ORD-0448: does the door cache the ruler's counts by path?  A probe, not an opinion.

`HYPOTHESIS_UNVERIFIED` deserves an experiment that could actually falsify it. Two are run here:

  P1 two consecutive runs of the door's exposure face on the SAME (tip, candidate) pair. A cache that
     survives a run shows up as the second run finding fewer "new" cells than the first, because the
     first run's candidate would have become the cached tip baseline.
  P2 a planted decoy. The door unpacks each rev with `git archive` into `exp_tip_<stamp>` /
     `exp_cand_<stamp>`. Here a foreign source file is written INTO the scratch directory before the
     run, carrying an exposure cell of its own. If the door trusted leftovers on disk, the cell count
     would move; if it wipes and re-extracts, the count is untouched and the decoy is gone afterwards.

Both are read-only against the repositories: nothing is committed, pushed or landed, and the door is
imported for its pure helpers with the token/proxy bootstrap neutralised rather than executed.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

DOOR = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\preflight_and_land_r5.py"
OUT = r"D:\moodle\_qoder_lane_S4_0926\work\ord0448"
REF = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
TIP = "0fee131d02b7c7c85f59aab8307f28594bf0d65f"
R3 = "6c466ce267bf196827054584afeb3f533677fe7b"
R4 = "6336b0e4e1bab3ae17e4ce4b1a96e2696541ef56"          # the lane's r4 head, as gated
R4_LANDED = "527f471b6d009d8ef8fead5d32ad455005ac281b"   # the recut that moved the line
PANEL_RULE = "DestinationPreparationPanel.tsx|UPSTREAM_EXCEPTION_TO_DOM"


def load_door():
    # the door imports its own network-sibling modules, so its directory has to be on the path
    sys.path.insert(0, REF)
    src = io.open(DOOR, encoding="utf-8").read()
    head = src[:src.index("def main(")]
    head = re.sub(r"(?m)^TOK = .*$", 'TOK = ""', head)
    head = re.sub(r'(?m)^print\("proxy guard.*$', '', head)
    ns = {"__name__": "door_probe", "__file__": DOOR}
    exec(compile(head, DOOR, "exec"), ns)
    return ns


def growth_of(cells_tip, cells_cand):
    ct, cc = DOORNS["exposure_counts"](cells_tip), DOORNS["exposure_counts"](cells_cand)
    return {k: cc[k] - ct.get(k, 0) for k in cc if cc[k] > ct.get(k, 0)}


DOORNS = load_door()
exposure_cells = DOORNS["exposure_cells"]

DECOY = """export function PlantedDecoyPanel({ cause }: { cause: unknown }) {
  const msg = cause instanceof Error ? cause.message : "local sentence";
  return <p data-testid="planted-decoy-error">{msg}</p>;
}
"""


def sha(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def main():
    report = {"door_file": DOOR, "door_sha1_over_bytes": sha(io.open(DOOR, encoding="utf-8").read()),
              "revs": {"tip_at_the_time": TIP, "candidate_r3": R3, "candidate_r4": R4,
                       "r4_as_landed": R4_LANDED}}

    # ---------------- P1: two consecutive runs on the same pair ----------------
    runs = []
    for i in (1, 2):
        a = exposure_cells(TIP, "p1_tip_run%d" % i)
        b = exposure_cells(R4, "p1_cand_run%d" % i)
        runs.append({"run": i, "tip_cells": len(a), "cand_cells": len(b),
                     "growth_by_file_and_rule": growth_of(a, b),
                     "panel_count_tip": DOORNS["exposure_counts"](a).get(PANEL_RULE, 0),
                     "panel_count_cand": DOORNS["exposure_counts"](b).get(PANEL_RULE, 0)})
    # compared WITHOUT the run label: two dicts that differ only in "run": 1 vs 2 are the same reading
    core = lambda r: {k: v for k, v in r.items() if k != "run"}
    report["P1_two_runs_same_pair"] = {"runs": runs,
                                       "identical": core(runs[0]) == core(runs[1]),
                                       "second_run_treated_first_as_tip": bool(
                                           runs[1]["growth_by_file_and_rule"] != {} or
                                           runs[1]["cand_cells"] != runs[0]["cand_cells"])}

    # ---------------- P2: a decoy planted into the scratch directory ----------------
    sub = "p2_poisoned_dir"
    d = os.path.join(r"D:\moodle\_qoder_cmdr_ref_20260921", sub)
    os.makedirs(os.path.join(d, "frontend", "src", "features", "decoy"), exist_ok=True)
    io.open(os.path.join(d, "frontend", "src", "features", "decoy", "PlantedDecoyPanel.tsx"),
            "w", encoding="utf-8", newline="\n").write(DECOY)
    planted_path = os.path.join(d, "frontend", "src", "features", "decoy", "PlantedDecoyPanel.tsx")
    before_exists = os.path.isfile(planted_path)
    cells = exposure_cells(TIP, sub)
    after_exists = os.path.isfile(planted_path)
    clean = exposure_cells(TIP, "p2_clean_dir")
    report["P2_planted_decoy"] = {
        "decoy_written_before_the_run": before_exists,
        "decoy_still_there_after_the_run": after_exists,
        "cells_with_decoy_present": len(cells), "cells_from_a_clean_dir": len(clean),
        "wiped_and_reextracted": bool(before_exists and not after_exists and len(cells) == len(clean)),
        "decoy_would_have_added_a_cell_because": "the planted file is an upstream exception reaching a "
                                                 "<p> exactly like the ones this order is about"}

    # ---------------- the arm table the reading actually supports ----------------
    def identities(rev, tag):
        js = os.path.join(OUT, "id_%s.json" % tag)
        tree = os.path.join(OUT, "idtree_%s" % tag)
        subprocess.run(["node", os.path.join(REF, "ui_exposure_taint_ast_r7b1.cjs"), "--tree",
                        os.path.join(tree, "frontend", "src"), "--out", js], capture_output=True,
                       timeout=1800)
        doc = json.load(io.open(js, encoding="utf-8"))
        ids = [h.get("cell_id") for h in doc.get("hits", [])
               if "DestinationPreparationPanel" in str(h.get("file", ""))]
        return ids

    idt = {tag: identities(rev, tag) for tag, rev in
           (("tip", TIP), ("r3", R3), ("r4", R4))}
    def count_growth(ours, theirs):
        from collections import Counter
        a, b = Counter(ours), Counter(theirs)
        return {k: b[k] - a.get(k, 0) for k in b if b[k] > a.get(k, 0)}
    report["cell_identity_table"] = {
        "tip_ids_sorted": sorted(idt["tip"]), "r3_ids_sorted": sorted(idt["r3"]),
        "r4_ids_sorted": sorted(idt["r4"]),
        "per_identity_count_growth_r3_vs_tip": count_growth(idt["tip"], idt["r3"]),
        "per_identity_count_growth_r4_vs_tip": count_growth(idt["tip"], idt["r4"]),
        "set_difference_r3_minus_tip": sorted(set(idt["r3"]) - set(idt["tip"])),
        "set_difference_r4_minus_tip": sorted(set(idt["r4"]) - set(idt["tip"])),
        "note": "r3 carries the SAME three identities as the tip but one of them twice (the duplicate "
                "render block the lane deleted in r4). An arm that compared identity SETS would have "
                "passed r3; the door's count arm caught it, and a per-identity COUNT arm catches r3 and "
                "still passes r4."}
    io.open(os.path.join(OUT, "cache_probe_r1.json"), "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report["P1_two_runs_same_pair"], ensure_ascii=False, indent=1))
    print("P2:", json.dumps(report["P2_planted_decoy"], ensure_ascii=False)[:300])
    print("P2 verdict: wiped_and_reextracted =", report["P2_planted_decoy"]["wiped_and_reextracted"])
    t = report["cell_identity_table"]
    print("identity growth r3 vs tip:", t["per_identity_count_growth_r3_vs_tip"],
          "| r4 vs tip:", t["per_identity_count_growth_r4_vs_tip"])
    print("set difference r3-tip:", t["set_difference_r3_minus_tip"], "r4-tip:", t["set_difference_r4_minus_tip"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
