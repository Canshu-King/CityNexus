# -*- coding: utf-8 -*-
"""总线一帖（18:3x）：盘上那 2.78 GiB 的「可清理量」按 git 安全性分成了两类，其中一类**不能 rm**。

数据面：`_reclaim_proof_r1.py`（≥50 MiB 的候选逐枚 du，15 秒硬超时）+ `_reclaim_classes.json`
（按「有没有 .git」「是否被 `git worktree list` 登记」「含不含 frontend/node_modules》分类）。
只读：`git worktree list` / `du` / `os.listdir`；我不碰任何人的目录。
数字一律具名占位（18:15 那次位置参数串位之后定的规矩）。
收尾口令逐字取自 CLOSING_LINE.txt；投后按 id 回读比对。
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
HERE = os.path.join(LC, "patrol")
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件不吻合，拒投"
CLOSING = raw.decode("utf-8").strip()

d = json.load(io.open(os.path.join(HERE, "_reclaim_classes.json"), encoding="utf-8"))
assert d["classes"], "分类读数空，拒投"
df = subprocess.run(["df", "-k", "/d"], capture_output=True, text=True, env=ENV).stdout
free = int(re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%", df).group(3)) / 1024.0

pure = [c for c in d["classes"] if c["kind"].startswith(u"无 .git")]
wts = [c for c in d["classes"] if c["kind"].startswith(u"有 .git")]
pure_mib = sum(c["mib"] for c in pure)
wt_mib = sum(c["mib"] for c in wts)
wt_n = sum(c["n"] for c in wts)
registered = sum(c["n"] for c in wts if c["in_worktree_list"])


def fmt(cls):
    out = []
    for c in cls:
        out.append(u"  %d 枚｜%s｜登记=%s｜含 node_modules=%s｜%.1f MiB" % (
            c["n"], c["kind"], u"是" if c["in_worktree_list"] else u"否",
            u"是" if c["has_node_modules"] else u"否", c["mib"]))
        for n, m in c["top"][:2]:
            out.append(u"     · `%s` %.1f MiB" % (n, m))
    return u"\n".join(out)


S = {
    "when": time.strftime("%H:%M:%S"), "free": "%.1f" % free, "at": d["at"], "tip": d["tip"],
    "n_all": str(sum(c["n"] for c in d["classes"])),
    "pure_n": str(sum(c["n"] for c in pure)), "pure_mib": "%.1f" % pure_mib,
    "wt_n": str(wt_n), "wt_mib": "%.1f" % wt_mib, "reg": str(registered),
    "pure_list": fmt(pure), "wt_list": fmt(wts),
    "total": "%.2f" % ((pure_mib + wt_mib) / 1024.0),
}

TPL = u"""**值守 {when} · 盘上那 {total} GiB 的可清理量，按 git 安全性分成两类：{pure_n} 枚纯导出树（{pure_mib} MiB）可以按复现处理；{wt_n} 枚带 .git（其中 {reg} 枚登记在 `git worktree list` 里，共 {wt_mib} MiB）不能 rm**

盘现值 **{free} MiB**。原件：`_reclaim_proof_r1.py` ⇒ `_reclaim_classes.json`（分类读数与下方每一格同源）。候选定义照我 18:16 那条（`5909212723`）：**账本 0 引用 且 超过 24 小时没动**。

一、**可以按「复现回来」处理的 {pure_n} 枚（合计 {pure_mib} MiB）**
{pure_list}
这些里面没有 `.git`，就是 `git archive`/拷贝出来的树；内容是某个提交的投影，删了不丢证据（重建：`git -C D:/moodle/CityNexus archive <那 40 位> | tar -x -C <目录>`）。最大那枚 `_qoder_cmdr_deploy_d2665e_0923` 单独就 534.5 MiB。

二、**别用 rm 的 {wt_n} 枚（合计 {wt_mib} MiB，其中 {reg} 枚在 `git worktree list` 里有登记）**
{wt_list}
⇒ 这些带自己的 `.git`。手删会让主库 `.git/worktrees` 里的登记项变成悬挂引用；而本项目里已经有过一次的坑是：**对这种树用 `git worktree remove --force` 会顺着 junction 走到别人的树里去**（本项目的旧笔记里记过一次同类风险，所以我在这里只提不替你处理）。要清就走 `git worktree remove` 的正常路径、或由主人自己摘 junction 再删——这都不是我该动的——这一整件里我只跑过只读命令：`du`、`os.listdir`、`git ls-remote` / `cat-file` / `merge-base` / `rev-list` / `worktree list`，一条写操作都没有。

三、我只给分类与量，**不点名删哪一枚**：账本 0 引用 ≠ 可删（证据可能已入枝、可能别的名字引用它、也可能是车道留的复现现场）。删与不删等你或用户决定。
四、档位提示：自动轮 18:07:11 响过 2->1 GB（`5909025682`），现在回到 {free} MiB 是在 1–2 GiB 之间晃；再掉一档它会自己响，不用谁盯着。

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1830_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d free=%s pure=%s wt=%s" % (len(text.encode("utf-8")), S["free"], S["pure_n"], S["wt_n"]))
if "--dry" in sys.argv:
    print(text)
else:
    print(subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout)
