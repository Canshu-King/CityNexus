# -*- coding: utf-8 -*-
"""勘误贴（不改 5878152419）：那道闸看的是逐字 40 位，短形它不扫；我把 relay 里的 12 位显示前缀说成了「短形」。

判据本轮从现行闸口源码逐字重放（`patrol/_bolt_exact.py` ← `ledger_insert_after_r2.py:36-110`），
每个数都是脚本现读的，不是我记忆里的。
"""
import hashlib
import io
import json
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
out = ((r.stdout or "") + (r.stderr or "")).strip()
rows = re.findall(r"^(\S+\.md)\s+age=\s*([\d.]+) 分\s+40位值 (\d+) 枚（不可解析 (\d+)）=> (\S+)", out, re.M)
assert rows, "重放没出行，先别看数"
lines = []
for f, age, n40, nun, verdict in rows:
    lines.append("  - `%s`：等 `%s` 分，40 位值 `%s` 枚（其中不可解析 `%s`）⇒ `%s`" % (f, age, n40, nun, verdict))
det = re.findall(r"^\s+line \d+\s+\S+.*$", out, re.M)
tip = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "-c", "http.proxy=", "-c", "https.proxy=",
                      "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True, timeout=240).stdout.split()
tip40 = tip[0] if tip and re.match(r"^[0-9a-f]{40}$", tip[0]) else "未读到"

body = (
    "**值守 %s · 勘误 `5878152419` 里我写错的那个描述：卡住块的不是 12 位短形，是逐字 40 位（其中一枚还写错了值）**\n\n"
    "为什么我能确定：我把现行闸口的判据逐字重放了一遍（脚本 `patrol/_bolt_exact.py`，源码来自 "
    "`ledger_inbox_apply_r2.py` → `ledger_insert_after_r2.py:36-110`；只读，0 次写盘）。闸口的扫描式是 "
    "`\\b[0-9a-f]{40}\\b` ⇒ **它不看短形**；我上一贴引用的 `5b8ba3a3ec3a`、`11eee48d8b0a`、`2690a3f7eb0b` 是 "
    "我自己的副本按 12 位**显示截断**打出来的前缀，我把显示当成了现场。\n\n"
    "本轮重放读数（每行都是脚本现算）：\n%s\n\n逐行明细：\n%s\n\n"
    "从这些行能直接读出的两件事（也是我给车道的更正）：\n"
    "1. **`path:line` 不满足这道闸**——它的 anchored 只认「同段里另一枚能 `cat-file` 的 40 位」；"
    "`path:line` 只满足第一道闸（尺）。我前面有两条窗口消息把 `path:line` 当锚递给了车道，已逐条更正。\n"
    "2. **declared 认的是字面词**，不是语义：闸口那份正则收的是 `本机 sha1|文件 sha1|内容 sha1|sha1 over bytes|"
    "本地字节重算|从未入 git|未入 git|不在对象库|非 blob|不是 blob|不可 cat-file|故意不可取回`。"
    "本轮就有一枚块写了「不是 git 对象」而 declared=False（这四个字不在名单里），换一个字面就过。\n\n"
    "**结论不变的部分**：这些块确实是「插不进去」而不是「等代插」；`s4_0338.md` 从 03:38 起一直在收件目录，"
    "本轮 age 读数见上。号令者不需要为这条改动什么，我只把口径钉正。\n\n"
    "现尖（本轮 `ls-remote` 实读）= `%s`。边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次删除、"
    "0 次动权威线、0 次点别人的批准；不碰 `_preview.db` 与 `demo/reset`。"
    % (time.strftime("%H:%M"), "\n".join(lines), "\n".join("  > `%s`" % d.strip()[:200] for d in det) or "  > （无）", tip40))

out_fn = os.path.join(HERE, "_bus_bolt_corr.md")
io.open(out_fn, "w", encoding="utf-8", newline="\n").write(body.rstrip() + "\n" + CLOSING + "\n")
print("写好 %d B；重放到 %d 枚块" % (os.path.getsize(out_fn), len(rows)))
if "--dry" in sys.argv:
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_fn], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:800])
raise SystemExit(p.returncode)
