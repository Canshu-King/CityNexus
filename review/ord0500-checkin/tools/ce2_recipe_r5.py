"""ORD-0500 r5: write the counter-example recipe from the trees it describes, not from memory.

The r4 page cited a recipe document that named that generation's throwaway trees and its own tool
prefix; carrying the file forward would have shipped stale names.  This regenerates it: the CE-1
mutation is read as the actual diff between the pristine tip tree and the mutant backend tree, the
CE-2 mutation as the diff between the delivered candidate and the front-end mutant, and the tool and
face names come out of `gen9_build_r1.py` itself.  If a name in this file ever stops matching the
trees, the numbers below stop matching too -- that is the point of generating it.
"""
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
MAIN = "backend/app/main.py"
ITIN = "frontend/src/features/trip/TripItinerary.tsx"
# Each pair is (label, tree A + file, tree B + file).  CE-1 is measured against the DELIVERED
# candidate, not the tip: diffing the tip against the mutant would fold my own named-refusal change
# into the number and call it the mutation.
CE1 = ("CE-1 -- the server's own duplicate check removed", "服务端那枚反件",
       ("wt22", MAIN), ("mutgen9", MAIN))
CE2 = ("CE-2 -- the on-screen mark taken from the plan instead of the footprint read",
       "屏上那枚反件", ("wt22", ITIN), ("wt24", ITIN))


def read(tree, rel):
    p = os.path.join(LANE, tree, rel)
    return open(p, encoding="utf-8").read().splitlines(), p


def pair(label, what, a_spec, b_spec):
    a_tree, a_rel = a_spec
    b_tree, b_rel = b_spec
    la, pa = read(a_tree, a_rel)
    lb, pb = read(b_tree, b_rel)
    diff = [x for x in difflib.unified_diff(la, lb, lineterm="", n=0)
            if x[:1] in "+-" and x[:3] not in ("+++", "---")]
    added = [x for x in diff if x.startswith("+")]
    removed = [x for x in diff if x.startswith("-")]
    return {"label": label, "what": what, "files": [os.path.relpath(pa, LANE),
                                                    os.path.relpath(pb, LANE)],
            "a_tree": a_tree, "b_tree": b_tree,
            "a_sha256": hashlib.sha256(open(pa, "rb").read()).hexdigest(),
            "b_sha256": hashlib.sha256(open(pb, "rb").read()).hexdigest(),
            "changed_lines": len(diff), "added": added, "removed": removed,
            "identical": la == lb}


def faces():
    text = open(os.path.join(LANE, "tools", "gen9_build_r1.py"), encoding="utf-8").read()
    return re.findall(r'\("([A-Za-z0-9_]+)", "([a-z0-9]+)", "([^"]+)"\)', text)


def main():
    tip = subprocess.run(["git", "-C", os.path.join(LANE, "wt23"), "rev-parse", "HEAD"],
                         stdout=subprocess.PIPE, timeout=60).stdout.decode().strip()
    cand = subprocess.run(["git", "-C", os.path.join(LANE, "wt22"), "rev-parse", "HEAD"],
                         stdout=subprocess.PIPE, timeout=60).stdout.decode().strip()
    p1 = pair(*CE1)
    p2 = pair(*CE2)
    fs = faces()
    builds = json.load(open(os.path.join(LANE, "evidence", "gen9_builds_r1.json"), encoding="utf-8"))
    entry = {f.get("label"): (f.get("entry") or {}).get("entry_asset") for f in builds["faces"]}
    L = []
    A = L.append
    A("# ORD-0500 r5 -- how to rebuild the two counter-example trees (neither is ever committed)")
    A("")
    A("写于 `%s`；读数那一代的基座树 `%s`，交付候选 `%s`。每一枚反件都跟**交付候选**比，不跟基座比——"
      "跟基座比会把我自己那笔具名拒绝混进差异行数里，那就不叫反件了。这一页由 `tools/ce2_recipe_r5.py` "
      "对着那两枚树现算生成，不是手抄上一代的配方——上一代的页眉里写的还是它那一代的树名。" %
      (datetime.now().astimezone().isoformat(), tip, cand))
    A("")
    for p in (p1, p2):
        A("## %s（%s）" % (p["label"], p["what"]))
        A("")
        A("- 对照的两棵树：`%s`（`%s`，本机字节 sha256 `%s`）与 `%s`（`%s`，本机字节 sha256 `%s`）。"
          % (p["a_tree"], p["files"][0], p["a_sha256"], p["b_tree"], p["files"][1], p["b_sha256"]))
        A("- 差异共 %d 行（增 %d、删 %d）。sha256 是本机字节的，不是 git 物件，不可 cat-file。"
          % (p["changed_lines"], len(p["added"]), len(p["removed"])))
        A("- 摘掉的就是这几行：")
        A("")
        A("  ```")
        for x in (p["removed"] + p["added"])[:14]:
            A("  " + x)
        A("  ```")
        A("")
    A("## 造面与跑法（本代的实名）")
    A("")
    A("- 三面由 `tools/gen9_build_r1.py` 的 FACES 建，outDir 与入口资产名回读自 `evidence/gen9_builds_r1.json`：")
    for label, tree, out in fs:
        A("  - `%s` ← 树 `%s` → outDir `%s`，入口 `%s`" % (label, tree, out, entry.get(label)))
    A("- CE-1 的配对跑在 `tools/gen9_ce1_r1.py`（pytest 两侧），树的差异收据在 `tools/gen9_ce1_proof_r1.py`；"
      "后者存在的原因写在其文件头：一次配对里第四枚红是被改树缺一枚文件造成的，那是仪器的事，不是结论。")
    A("- CE-2 的臂跑在 `tools/gen9_carrier_r1.py` + `tools/gen9_carrier_arms_r1.py`，"
      "会咬人的是 `ord0500-2`，它的报错句子同时带屏上枚数与门里行数。")
    A("- 曝光尺（第三种反件形制，同一枚实例三趟）：")
    A("  `node <cmdr live_checks>/ui_exposure_taint_ast_r7b.cjs --tree <tree>/frontend --out <file>`")
    A("  对基座树与候选树各一趟，两趟都必须在同一代、同一把尺上跑。")
    A("")
    A("## 两枚反件树与反件面不进任何枝")
    A("")
    A("- 反件树 `%s`、`%s` 与它的三面之一 `faces/o0500_clientbool9` 只是被建出来挨判的，不提交、不推送；"
      "候选 `%s` 自己一行没被它们影响（`candidate_tree_untouched` 在 `evidence/gen9_ce1_r1.json` 里）。"
      % (p1["b_tree"], p2["b_tree"], cand))
    out = os.path.join(LANE, "evidence", "CE2_MUTANT_RECIPE_r5.md")
    text = chr(10).join(L) + chr(10)
    open(out, "w", encoding="utf-8", newline="").write(text)
    print(json.dumps({"wrote": out, "bytes": len(text.encode("utf-8")),
                      "ce1_changed_lines": p1["changed_lines"],
                      "ce2_changed_lines": p2["changed_lines"],
                      "faces": fs}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
