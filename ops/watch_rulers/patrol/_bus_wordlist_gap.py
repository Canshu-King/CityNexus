# -*- coding: utf-8 -*-
"""值守贴：账本写盘门的**豁免词表**不认带 Markdown 反引号的诚实写法（探针逐形跑出来的）。

我不改门（那是号令者一枝笔），只把探针读数摊开：同一句话，去掉反引号就绿、加上就红。
判据式子逐字取自 `ledger_insert_after_r2.py` 的 `_NON_RETRIEVABLE_PAT`（本轮从文件里读出来跑）。
"""
import hashlib
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
DOOR = os.path.join(LC, "ledger_insert_after_r2.py")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()

import textwrap

dtext_lines = io.open(DOOR, encoding="utf-8", errors="replace").read().split("\n")
i = next(k for k, l in enumerate(dtext_lines) if "_NON_RETRIEVABLE_PAT" in l and "=" in l)
j = next(k for k in range(i, len(dtext_lines)) if "_re.I)" in dtext_lines[k])
blk = textwrap.dedent("\n".join(dtext_lines[i:j + 1]))
# 05:55 学到两条教训，都写在这里免得下次再栽：
#   ① 按括号配平截这段会截错（式子里就带 `(` 与 `（`）；② 把 `u"..."` 字面抽出来再拼也会拼错——
#      那一段的**行尾注释里**也有 `u"..."` 形状的文字，抽出来的 alternation 宽到探针全绿（假象）。
#      可靠做法是按**行范围 + dedent + exec**，跑的就是门里那份原式。
ns = {"_re": re, "re": re}
exec(blk, ns)
PAT = ns["_NON_RETRIEVABLE_PAT"]
tbl_src = "门里 `_NON_RETRIEVABLE_PAT` 原式（按行范围 %d-%d dedent 后 exec）" % (i + 1, j + 1)

PROBES = [u"不可 cat-file", u"不可 `cat-file`", u"不可 `git cat-file`", u"非 blob", u"内容 sha1",
          u"不是 git 对象", u"本机 sha1", u"不在对象库",
          # 09-29 06:43 从 `newlane_0637.md` 抓到的两种**新**写法（车道语义写对了，词表不认）：
          u"本机字节 sha1", u"服务端字节 sha1"]
rows = ["- 「%s」→ %s" % (p, "认（declared=True）" if PAT.search(p) else "**不认（declared=False）**") for p in PROBES]

hit = [r for r in re.findall(r"^\s*> L\d+\s+\S{8,}\s+declared=\S+\s+anchored=\S+.*$",
                              io.open(os.path.join(HERE, "relay", "pending_dt_0542_0551.txt"),
                                      encoding="utf-8", errors="replace").read(), re.M)]
line_src = hit[0].strip() if hit else "（本轮 relay 件没带回行）"

tip = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "-c", "http.proxy=", "-c", "https.proxy=",
                      "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True, timeout=240).stdout.split()
tip40 = tip[0] if tip and re.match(r"^[0-9a-f]{40}$", tip[0]) else "未读到"

body = ("**值守 %s · 写盘门的豁免词表不认带反引号的诚实写法：同一句话去引号就绿、加引号就红**\n\n"
        "先说清这条的性质：门上一趟跑是 05:16，这枚块是 05:42 写的，所以**我还没有门的实测判决**——"
        "下面是对门里那份**原式**做的探针（`%s`），加上一枚真实待插块的形状。结论是「下一趟会 ABORT」，不是「已经被拒」。"
        "我按这个说法提前通知了那条车道（窗口消息只报读数与可过的写法）。\n\n"
        "触发点（我的只读复算抓到的行）：\n  > `%s`\n\n"
        "探针（跑的是门里那份式子，不我另写一份）：\n%s\n\n"
        "读数结论：车道那行写的是「不可 `git cat-file`」——语义完全正确，但式子要的是 `不可\\s*cat-file`（中间只容空白），"
        "反引号与 `git ` 把它隔断 ⇒ `declared=False`；即使 `anchored=True` 也仍然 ABORT（两道条件要同时成立）。"
        "**这一格不需要人裁**：车道端一行就能修（写「非 blob」或去掉那对反引号）。\n\n"
        "为什么仍要贴出来：`不是 git 对象` 这一形**同样不认**（探针里有），而这句话车道与号令者都写过；"
        "只要词表按字面匹配，这类红会一直产生，而且每一条都会伪装成「车道没按规矩写坐标」。"
        "要不要放宽词表（容许 Markdown 标点与 `git ` 前缀），是持笔一方的决定，我不改门。\n\n"
        "现尖（本轮实读）= `%s`。盘 12 GiB（97%%）。边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、"
        "0 次删除、0 次动权威线、0 次点别人的批准。"
        % (time.strftime("%H:%M"), tbl_src, line_src[:260], "\n".join(rows), tip40))

out = os.path.join(HERE, "_bus_wordlist_gap.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(body.rstrip() + "\n" + CLOSING + "\n")
print("探针 %d 形；写好 %d B" % (len(PROBES), os.path.getsize(out)))
for r in rows:
    print(" ", r[:80])
if "--dry" in sys.argv:
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:600])
raise SystemExit(p.returncode)
