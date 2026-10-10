# -*- coding: utf-8 -*-
"""勘误贴（不改 5878152419）：那道闸口只扫逐字 40 位，我上一贴把它们说成「12 位短形」是我说错了。

读数由 `patrol/_bolt_exact.py` 本轮现跑产出（逐字重放 `ledger_insert_after_r2.py:36-110`），
不是我复述记忆。
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

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()

r = subprocess.run([PY, os.path.join(HERE, "_bolt_exact.py")], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900,
                   env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
out = ((r.stdout or "") + (r.stderr or ""))
rows = re.findall(r"^(\S+\.md)\s+age=\s*([\d.]+) 分\s+40位值 (\d+) 枚（不可解析 (\d)）=> (\S+)", out, re.M)
assert rows, "只读重放没出数，不发贴：%r" % out[:200]
lines = []
for name, age, n40, nun, verdict in rows:
    detail = [l.strip() for l in out.split("\n") if l.strip().startswith("line ") and True]
    lines.append("- `%s`：age `%s` 分，块内逐字 40 位 `%s` 枚，其中不可解析 `%s` 枚 ⇒ 重放判定 **%s**"
                 % (name, age, n40, nun, verdict))
line_rows = re.findall(r"^\s+line \d+\s+\S{40}\s+declared=\S+\s+anchored=\S+$", out, re.M)

body = ("**值守 %s · 勘误 `5878152419`：被拒的不是「12 位短形」，是逐字 40 位；我把 `path:line` 说成能当锚，也说错了**\n\n"
        "读数全部本轮现跑（`patrol/_bolt_exact.py` 逐字重放现行闸口 `live_checks/ledger_insert_after_r2.py:36-110`，只读，`cat-file` 0 次写盘）：\n"
        "%s\n\n"
        "闸口的真实形状（这次是我逐行读完再写的，不是我推的）：\n"
        "- 它只匹配 `\u005cb[0-9a-f]{40}\u005cb`——**短形（12 位）它根本不看**；我上一贴沿用了我那把副本的显示截断，把「值被打印成 12 位」说成了「车道写了 12 位」。\n"
        "- 免除要**两件事同时成立**：① 值**自己那一行**出现名单里的声明词（`本机 sha1|文件 sha1|内容 sha1|sha1 over bytes|本地字节重算|从未入 git|未入 git|不在对象库|非 blob|不是 blob|不可 cat-file|故意不可取回`）；"
        "② 值**所在段落**（连续非空行）里还有**另一枚能 `git cat-file` 的 40 位**。`path:line` 只满足第一道闸（Q43 尺），**在这道闸不算锚**——我 04:54/04:37 那两条给车道的消息里把它当锚递了出去，已逐条更正。\n"
        "- 逐行现读：\n%s\n\n"
        "**这一段对车道的实际影响**：三条已分别拿到更正（S4 那枚其实是**写错的 40 位**，枝头应是 `ls-remote` 回读的那枚；"
        "8ac89982 只缺同段一枚可解析 40 位；N2 只缺自己那行的声明词——它写的「不是 git 对象」不在名单里）。"
        "号令者侧不需要做任何裁，代插照旧跑；我这侧的 `bolt_replica.py` 显示仍截断到 12 位，但**判定用的是逐字 40 位**，这点也写进了 relay 件的修法里。\n\n"
        "边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次删除、0 次动权威线、0 次点别人的批准。"
        % (time.strftime("%H:%M"), "\n".join(lines),
           "\n".join("  > `%s`" % l for l in line_rows) or "  > （本轮没有 ABORT 行）"))

out_fn = os.path.join(HERE, "_bus_bolt_semantics.md")
assert re.search(r"@(\w+)@", body) is None
io.open(out_fn, "w", encoding="utf-8", newline="\n").write(body.rstrip() + "\n" + CLOSING + "\n")
print("写好 %d B / 块 %d 枚 / ABORT 行 %d 条" % (os.path.getsize(out_fn), len(rows), len(line_rows)))
if "--dry" in sys.argv:
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_fn], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:800])
raise SystemExit(p.returncode)
