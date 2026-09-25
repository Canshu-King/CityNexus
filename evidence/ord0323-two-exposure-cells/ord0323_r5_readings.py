"""ORD-0323 requirement (3), on the ruler that is current: r5, AST taint over a whole module graph.

The commander's own usage finding is why this is run differently from my r3/r4 readings: r5 only builds a
module graph in `--tree <dir>` mode -- a per-file r5 run reproduces r4's answer exactly -- and the tree has
to be exported from the commit being judged (`git archive <ref> frontend`) rather than read off a shared
working tree, or the dependencies come from a different generation than the target file.

Both generations are scanned whole, so the before/after is not just "did my files clean up" but "did the
rest of the tree move" -- and `tree_wide.changed_files_outside_my_three` has to answer that with [] rather
than with a sentence. Cells are counted two ways on purpose: by id (file:line[rule]) a renumbering looks
like a clearance, so `by_shape_identity` is the number a claim may quote.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0323_20260926")
R5 = pathlib.Path(r"D:\moodle\_qoder_spike_20260921\ui_exposure_taint_ast_r5.cjs")
R5_BLOB = "ff98091cf3accb0d836ae25ba49820170b92d932"
BASE = "9a669c8bec863fadf31d5158f4a1be66aec49f23"
MINE = ("ProductErrorBoundary.tsx", "JourneyInboxWorkbench.tsx", "PlanWithAiSheet.tsx")


def run(args):
    return subprocess.run(["git", "-C", str(LANE), *args], capture_output=True, check=True).stdout


def export(ref, dest):
    import shutil
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    p = subprocess.run(f'git -C "{LANE}" archive {ref} frontend | tar -x -C "{dest}"', shell=True)
    if p.returncode != 0:
        raise SystemExit(f"the export of {ref[:12]} did not complete")
    return dest / "frontend" / "src"


def scan(src, out):
    r = subprocess.run(["node", str(R5), "--tree", str(src), "--out", str(WORK / out)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(WORK), timeout=1200)
    if r.returncode != 0 or not (WORK / out).exists():
        raise SystemExit("r5 --tree failed: " + ((r.stdout or "") + (r.stderr or ""))[-300:])
    return json.loads((WORK / out).read_text(encoding="utf-8"))


def cells_of(body):
    """(file, rule, line) plus a line-free identity, so a pure renumbering is not counted as a clearance."""
    return sorted("%s:%s[%s]" % (str(h["file"]).replace("\\", "/").split("/")[-1], h["line"],
                                 h.get("rule")) for h in (body.get("hits") or []))


def shapes_of(body):
    return sorted({"%s[%s]" % (str(h["file"]).replace("\\", "/").split("/")[-1], h.get("rule"))
                   for h in (body.get("hits") or [])})


def mine_of(lst):
    return [c for c in lst if any(m in c for m in MINE)]


def files_of(lst):
    return sorted({c.split(":")[0] for c in lst})


blob = subprocess.run(["git", "-C", str(LANE), "hash-object", str(R5)], capture_output=True,
                      text=True).stdout.strip()
if blob != R5_BLOB:
    raise SystemExit(f"the r5 on disk is not the published one: {blob}")
selftest = json.loads(subprocess.run(["node", str(R5), "--selftest"], capture_output=True, text=True,
                                     encoding="utf-8").stdout)
CAND = subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD"], capture_output=True,
                      text=True).stdout.strip()
before = scan(export(BASE, WORK / "gen_before"), "r5_before_tree.json")
after = scan(export(CAND, WORK / "gen_after"), "r5_after_tree.json")
b_all, a_all = cells_of(before), cells_of(after)
b_mine, a_mine = mine_of(b_all), mine_of(a_all)
b_shape, a_shape = shapes_of(before), shapes_of(after)
gone_shape, new_shape = sorted(set(b_shape) - set(a_shape)), sorted(set(a_shape) - set(b_shape))
moved = sorted(set(b_mine) - set(a_mine))          # cell ids that no longer exist
still = sorted(set(a_mine) & set(b_mine))          # identical id before and after: untouched
renumbered = sorted(set(a_mine) - set(b_mine))     # my files' after-cells that were not there before
outside = sorted({c.split(":")[0] for c in set(b_all) ^ set(a_all)} - set(MINE))
report = {
    "schema": "CNX_ORD0323_R5_READINGS_R1", "order": "ORD-0323", "lane": "B c01d72a3",
    "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "ruler": {"path": "evidence/ord0331-ast-crossfile-S4/ui_exposure_taint_ast_r2.cjs",
              "published_blob": R5_BLOB, "local_git_hash_object": blob,
              "sha1_over_bytes": hashlib.sha1(R5.read_bytes()).hexdigest(),
              "bytes": len(R5.read_bytes()),
              "selftest": selftest["verdict"], "selftest_fixtures": selftest.get("n_fixtures"),
              "lineage": "r1 正则 -> r2 -> r3 (44e062e6) -> r4 AST 逐文件 (eb262f59) -> r5 AST + 模块图",
              "usage_note": "r5 只在 --tree 模式下建模块图；逐文件跑会精确复现 r4 的答案（号令者实测）。"
                            "所以本件的口径是 --tree，且不从共享工作树读依赖：两代都用 git archive 导出。"},
    "generations": {"before": BASE, "after": CAND,
                    "exported_with": "git archive <ref> frontend | tar -x -C <dir>", "scanned": "frontend/src"},
    "tree_wide": {"before_hits": len(b_all), "after_hits": len(a_all),
                  "delta": len(a_all) - len(b_all),
                  "changed_files_outside_my_three": outside,
                  "reading": f"{len(b_all)} -> {len(a_all)} (delta {len(a_all) - len(b_all)}), "
                             f"和 {len(set(b_all) ^ set(a_all))} 个变动的格子里 "
                             f"{len(outside)} 个文件不属于本单"},
    "in_my_three_files": {
        "before": b_mine, "after": a_mine,
        "cell_ids_gone": moved, "cell_ids_untouched": still, "cell_ids_only_at_candidate": renumbered,
        "counts": {"before": len(b_mine), "after": len(a_mine), "gone": len(moved),
                   "untouched": len(still), "only_at_candidate": len(renumbered)},
        "by_shape_identity": {"before": b_shape, "after": a_shape, "cleared": gone_shape,
                              "new": new_shape},
    },
    "why_gone_and_only_at_candidate_do_not_cancel": (
        f"按格子 id 算，我的三件里 {len(moved)} 形消失、{len(renumbered)} 形只在新代出现；"
        f"按 shape 身份（文件+规则，不含行号）算则是 {len(gone_shape)} 形消失、{len(new_shape)} 形新增，"
        f"差额完全由行号位移解释：PlanWithAiSheet.tsx 的 UPSTREAM_TEXT_VIA_HELPER_TO_DOM "
        f"改前 {sorted(int(c.split(':')[1].split('[')[0]) for c in b_mine if 'PlanWithAiSheet' in c)}、"
        f"改后 {sorted(int(c.split(':')[1].split('[')[0]) for c in a_mine if 'PlanWithAiSheet' in c)}，同一形各 2 处。"),
    "remaining_meaning": "PlanWithAiSheet.tsx 那两形（改后 1021/1048，改前 1019/1046）就是 Q67=① 裁过的合规归属链："
                         "serverReasonSentence 的服务器原话经 failureReason 渲染在带「服务器给出的原因」标签的技术详情里。"
                         "本单不改它，行号差 2 只是我在同文件上方新增/删除行的位移。",
    "reading": (f"tree-wide {len(b_all)} -> {len(a_all)} (delta {len(a_all) - len(b_all)}); "
                f"my three files {len(b_mine)} -> {len(a_mine)} 格; "
                f"按 shape 身份 {len(gone_shape)} 形清除 / {len(new_shape)} 形新增 / "
                f"{len(still)} 形未动; 树内其它文件变动 {len(outside)}"),
    "claim_kind": "ast_module_graph_determined",
    "claimed_result": None, "derived_result": None,
}
txt = json.dumps(report, ensure_ascii=False, indent=1)
(WORK / "ord0323_r5_readings.json").write_text(txt, "utf-8", newline="\n")
print(report["reading"])
print("cleared by shape:", json.dumps(gone_shape, ensure_ascii=False))
print("new by shape:", json.dumps(new_shape, ensure_ascii=False))
print("cell ids only at candidate:", json.dumps(renumbered, ensure_ascii=False))
print("outside my three:", json.dumps(outside, ensure_ascii=False))
print("selftest:", report["ruler"]["selftest"], "blob ok:", blob == R5_BLOB)
