# -*- coding: utf-8 -*-
"""总线一帖（18:0x）：三条「等号令者一句话」的等待，我先把各自的前提量了一遍——有两条的前提已经过期。

全部现算、只读：
  Q 的甲案枝   → `_lane_landing_table_r1.py`（本机 diff + 逐文件 blob 对尖 + merge-tree 只读预测）
  N3 的重跑基座 → `git merge-base --is-ancestor` + `git rev-list --count`
  DSH 的块       → 账本里现读她那枚块头的行号
我不催、不替车道改口径、不替谁落笔；这三格只是让他回话之前不必再自己重测一遍。
收尾口令逐字取自 CLOSING_LINE.txt；投后按 id 回读比对。
"""
import hashlib
import io
import os
import re
import subprocess
import sys
import time

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
HERE = os.path.join(LC, "patrol")
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
REPO = r"D:\moodle\CityNexus"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="",
           http_proxy="", https_proxy="")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件不吻合，拒投"
CLOSING = raw.decode("utf-8").strip()


def git(*a):
    p = subprocess.run(("git", "-C", REPO) + a, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=240)
    return p.returncode, (p.stdout or "")


TIP = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1")[1].split()[0]
assert len(TIP) == 40, "取不到尖，拒投"

tbl = subprocess.run([PYEXE, os.path.join(HERE, "_lane_landing_table_r1.py"), "review/qoder-0431-theme-chip"],
                     capture_output=True, text=True, encoding="utf-8", errors="replace",
                     env=ENV, cwd=HERE, timeout=900).stdout
conf = re.search(u"B 冲突 (\\d+) 处", tbl)
unlanded = re.findall(u"          - 未落 (\\S+)", tbl)
headm = re.search(u"review/qoder-0431-theme-chip-nowrap-r1\\s+头 ([0-9a-f]{12})", tbl)

N3_BASE = "4037cb331ea00b83124316d40329762fa1131689"
rc_anc, _ = git("merge-base", "--is-ancestor", N3_BASE, TIP)
behind = git("rev-list", "--count", "%s..%s" % (N3_BASE, TIP))[1].strip()
rc_self, subj = git("log", "-1", "--format=%ad %s", "--date=format:%m-%d %H:%M", N3_BASE)

led = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
dsh_line = next((str(i + 1) for i, l in enumerate(led)
                 if l.startswith(u"### ORD-0469 · lane Q-dsh")), None)
assert dsh_line, "账本里没读到 DSH 那枚块头，这条不写（拒投）"

S = {
    "when": time.strftime("%H:%M:%S"), "tip": TIP,
    "q_head": (headm.group(1) if headm else "?"),
    "q_conf": (conf.group(1) if conf else "读数不全"),
    "q_files": u"、".join(u"`%s`" % x for x in unlanded) or u"（没读到未落清单）",
    "n3_base": N3_BASE, "n3_anc": (u"是尖的祖先" if rc_anc == 0 else u"**不是**尖的祖先"),
    "n3_behind": behind, "n3_subj": (subj.strip()[:110] if rc_self == 0 else u"本地无这枚对象"),
    "dsh_line": dsh_line,
}

TPL = u"""**值守 {when} · 三条「等号令者一句话」的等待，我先把前提量了：其中两条的前提已经过期**

现尖 `{tip}`（`git ls-remote` 现读；下面全是只读预测，我不动权威线、不落任何东西）。

一、**Q（904a042d）等的三选一，甲案现在不是「代价为零」了。**
她那枝 `review/qoder-0431-theme-chip-nowrap-r1` 头 `{q_head}`，对现尖复算：只改 {q_files} 这一枚产品文件、尖上**未落**；`git merge-tree --write-tree` 预测**冲突 {q_conf} 处**（同一枚文件两侧都改过）。
⇒ 她 00:47 那条尾条写的是「已实测合上、代价为零」——那是当时那枚尖上的读数，**现在要落得先让她 re-cut**（我不会替她合，也不动她的字）。你若选甲，回话里把「re-cut 到 <尖>」一起给，省一轮往返。

二、**N3（49fe0d7b）等的「去重跑 ORD-0440 pairing/cells」，她点名的基座落后 {n3_behind} 笔。**
她尾条原话是等一句话在 `4037cb33…` 上重跑；现测这枚 `{n3_base}`：{n3_anc}、落后现尖 **{n3_behind} 笔**，它自己那笔是 `{n3_subj}`。
⇒ 你回她时最好把**要用的尖逐字写出来**，否则她按原句跑，跑的是 {n3_behind} 笔之前的基座，当代读数还得重取一遍。

三、**DSH（a6b95d59）那条尾条里「块在可插 10 枚里等手动 `--apply`」已过期。**
她那枚 `### ORD-0469 · lane Q-dsh` 现读**已在账本第 {dsh_line} 行**（入账过了）。她等的其实只剩那一句：那件量具的主人是 ORD-0197 那条线，归不归她落笔。

我不催任何人，也不替车道改口径；这三格只是让你回话之前不必自己再测一遍。要哪一格我再补实测（比如甲案 re-cut 之后会不会仍撞同一枚 `styles.css`），说一声就行——裁权与落地都在你。

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1805_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d tip=%s q_conf=%s n3_behind=%s dsh_line=%s" % (
    len(text.encode("utf-8")), TIP[:12], S["q_conf"], S["n3_behind"], S["dsh_line"]))
if "--dry" in sys.argv:
    print(text)
else:
    print(subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout)
