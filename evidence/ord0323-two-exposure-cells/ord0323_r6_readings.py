"""ORD-0323 requirement (3) on the commander's current ruler: r6 (blob 6a251d3a), AST taint + module graph.

r6 says of itself that it supersedes r5 with "same decision, scope reporting added", so this run is not a
re-measurement for its own sake: it is the check that the number I am about to publish is the one the current
instrument gives, and it records r6's own scope fields instead of my paraphrase of them.

Method is the one the ruler's usage trap forces: `--tree` on a generation exported from the commit being
judged (`git archive <ref> frontend`), never the shared working tree, and never per-file -- r6's own mode
arms say `--file` is neither an upper nor a lower bound on `--tree`.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0323_20260926")
R6 = pathlib.Path(r"D:\moodle\_qoder_spike_20260921\ui_exposure_taint_ast_r6.cjs")
R6_BLOB = "6a251d3a6bea70329e06581384a81d5ef54c96a6"
R6_PUBLISHED_PATH = "evidence/ord0331-ast-crossfile-S4/ui_exposure_taint_ast_r3.cjs"
R6_ADDED_BY = "f3614b5c"
BASE = "9a669c8bec863fadf31d5158f4a1be66aec49f23"
MINE = ("ProductErrorBoundary.tsx", "JourneyInboxWorkbench.tsx", "PlanWithAiSheet.tsx")


def g(args, binary=False):
    r = subprocess.run(["git", "-C", str(LANE), *args], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace").strip()


def export(ref, dest):
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    p = subprocess.run(f'git -C "{LANE}" archive {ref} frontend | tar -x -C "{dest}"', shell=True)
    if p.returncode != 0:
        raise SystemExit(f"the export of {ref[:12]} did not complete")
    return dest / "frontend" / "src"


def scan(src, out):
    r = subprocess.run(["node", str(R6), "--tree", str(src), "--out", str(WORK / out)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(WORK), timeout=1200)
    if r.returncode != 0 or not (WORK / out).exists():
        raise SystemExit("r6 --tree failed: " + ((r.stdout or "") + (r.stderr or ""))[-400:])
    return json.loads((WORK / out).read_text(encoding="utf-8"))


def cells_of(body):
    return sorted("%s:%s[%s]" % (str(h["file"]).replace("\\", "/").split("/")[-1], h["line"],
                                 h.get("rule")) for h in (body.get("hits") or []))


def shapes_of(body):
    return sorted({"%s[%s]" % (str(h["file"]).replace("\\", "/").split("/")[-1], h.get("rule"))
                   for h in (body.get("hits") or [])})


def mine_of(lst):
    return [c for c in lst if any(m in c for m in MINE)]


blob = g(["hash-object", str(R6)])
if blob != R6_BLOB:
    raise SystemExit(f"the r6 on disk is not the published one: {blob} != {R6_BLOB}")
path_at_adding_commit = g(["show", "--name-only", "--format=", R6_ADDED_BY]).splitlines()
if R6_PUBLISHED_PATH not in path_at_adding_commit:
    raise SystemExit(f"{R6_ADDED_BY} did not add {R6_PUBLISHED_PATH}: {path_at_adding_commit}")
blob_of_that_path = g(["rev-parse", f"{R6_ADDED_BY}:{R6_PUBLISHED_PATH}"])
if blob_of_that_path != R6_BLOB:
    raise SystemExit(f"the published {R6_PUBLISHED_PATH} is {blob_of_that_path}, not {R6_BLOB}")
selftest = json.loads(subprocess.run(["node", str(R6), "--selftest"], capture_output=True, text=True,
                                     encoding="utf-8").stdout)
CAND = g(["rev-parse", "HEAD"])
before = scan(export(BASE, WORK / "gen6_before"), "r6_before_tree.json")
after = scan(export(CAND, WORK / "gen6_after"), "r6_after_tree.json")
b_all, a_all = cells_of(before), cells_of(after)
b_mine, a_mine = mine_of(b_all), mine_of(a_all)
b_shape, a_shape = shapes_of(before), shapes_of(after)
gone_shape, new_shape = sorted(set(b_shape) - set(a_shape)), sorted(set(a_shape) - set(b_shape))
moved = sorted(set(b_mine) - set(a_mine))
still = sorted(set(a_mine) & set(b_mine))
renumbered = sorted(set(a_mine) - set(b_mine))
outside = sorted({c.split(":")[0] for c in set(b_all) ^ set(a_all)} - set(MINE))

r5 = json.loads((WORK / "ord0323_r5_readings.json").read_text(encoding="utf-8"))
if r5["generations"]["after"] != CAND or r5["generations"]["before"] != BASE:
    raise SystemExit("the r5 artifact is not on this generation pair, so it cannot cross-check r6")
r5b = json.loads((WORK / "r5_before_tree.json").read_text(encoding="utf-8"))
r5a = json.loads((WORK / "r5_after_tree.json").read_text(encoding="utf-8"))
r5b_cells, r5a_cells = cells_of(r5b), cells_of(r5a)
agree = {"before_same": r5["tree_wide"]["before_hits"] == len(b_all),
         "after_same": r5["tree_wide"]["after_hits"] == len(a_all),
         "my_cells_before_same": sorted(r5["in_my_three_files"]["before"]) == b_mine,
         "my_cells_after_same": sorted(r5["in_my_three_files"]["after"]) == a_mine}

report = {
    "schema": "CNX_ORD0323_R6_READINGS_R1", "order": "ORD-0323", "lane": "B c01d72a3",
    "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "ruler": {"published_path": R6_PUBLISHED_PATH, "published_blob": R6_BLOB,
              "local_git_hash_object": blob, "bytes": len(R6.read_bytes()),
              "added_by_commit": R6_ADDED_BY, "blob_at_published_path": blob_of_that_path,
              "selftest": selftest["verdict"], "n_fixtures": selftest["n_fixtures"],
              "n_mode_arms": selftest["n_mode_arms"], "n_mode_arms_met": selftest["n_mode_arms_met"],
              "n_cross_file_arms_met": selftest["n_cross_file_arms_met"],
              "supersedes": selftest["ruler"].get("supersedes"),
              "supersedes_blob": selftest["ruler"].get("supersedes_blob"),
              "also_supersedes_r4": selftest["ruler"].get("also_supersedes_r4"),
              "mode_arms": selftest.get("mode_arms")},
    "mode": {"used": "--tree", "why": "r6 自己的 mode_arms 判 --file/--ref 既不是 --tree 的上界也不是下界；"
                                      "逐文件跑答的是另一个问题",
             "scope_as_the_ruler_reports_it": {"before": before.get("scope"), "after": after.get("scope"),
                                               "before_note": before.get("scope_note"),
                                               "upper_bound_claim": before.get("upper_bound_claim")}},
    "generations": {"before": BASE, "after": CAND,
                    "exported_with": "git archive <ref> frontend | tar -x -C <dir>", "scanned": "frontend/src"},
    "tree_wide": {"before_hits": len(b_all), "after_hits": len(a_all), "delta": len(a_all) - len(b_all),
                  "changed_files_outside_my_three": outside},
    "in_my_three_files": {
        "before": b_mine, "after": a_mine,
        "cell_ids_gone": moved, "cell_ids_untouched": still, "cell_ids_only_at_candidate": renumbered,
        "counts": {"before": len(b_mine), "after": len(a_mine), "gone": len(moved),
                   "untouched": len(still), "only_at_candidate": len(renumbered)},
        "by_shape_identity": {"before": b_shape, "after": a_shape, "cleared": gone_shape, "new": new_shape},
    },
    "cross_check_against_r5": {"r5_artifact": "ord0323_r5_readings.json",
                               "r5_tree_wide": [r5["tree_wide"]["before_hits"], r5["tree_wide"]["after_hits"]],
                               "r6_tree_wide": [len(b_all), len(a_all)],
                               "r5_reading": r5["reading"], "agreement": agree,
                               "all_agree": all(agree.values()),
                               "cells_only_r5_reports": {
                                   "before": sorted(set(r5b_cells) - set(b_all)),
                                   "after": sorted(set(r5a_cells) - set(a_all))},
                               "cells_only_r6_reports": {
                                   "before": sorted(set(b_all) - set(r5b_cells)),
                                   "after": sorted(set(a_all) - set(r5a_cells))},
                               "the_same_difference_on_both_generations":
                                   sorted(set(r5b_cells) - set(b_all)) == sorted(set(r5a_cells) - set(a_all))
                                   and sorted(set(b_all) - set(r5b_cells)) == sorted(set(a_all) - set(r5a_cells)),
                               },
    "reading": (f"r6 --tree 全树 {len(b_all)} -> {len(a_all)} (delta {len(a_all) - len(b_all)}); "
                f"我这三枚 {len(b_mine)} -> {len(a_mine)} 格; 按 shape 身份 {len(gone_shape)} 形清除 / "
                f"{len(new_shape)} 形新增; 树内不属于我的文件变动 {len(outside)}; "
                f"与 r5 逐项一致 = {all(agree.values())}"),
    "claim_kind": "ast_module_graph_determined",
    "claimed_result": None, "derived_result": None,
}
txt = json.dumps(report, ensure_ascii=False, indent=1)
(WORK / "ord0323_r6_readings.json").write_text(txt, "utf-8", newline="\n")
print(report["reading"])
print("cleared by shape:", json.dumps(gone_shape, ensure_ascii=False))
print("new by shape:", json.dumps(new_shape, ensure_ascii=False))
print("only at candidate:", json.dumps(renumbered, ensure_ascii=False))
print("outside my three:", json.dumps(outside, ensure_ascii=False))
print("scope:", json.dumps(report["mode"]["scope_as_the_ruler_reports_it"], ensure_ascii=False)[:300])
print("selftest:", report["ruler"]["selftest"], "mode arms",
      f"{selftest['n_mode_arms_met']}/{selftest['n_mode_arms']}", "blob ok:", blob == R6_BLOB)
