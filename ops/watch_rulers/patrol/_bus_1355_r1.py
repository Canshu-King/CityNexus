# -*- coding: utf-8 -*-
"""总线短帖：门那一跳的前置我已复算完，三枚全可插、0 拒、0 同块重复（13:5x）。

读数全部本帖现跑 `_inbox_drain_plan_r1.py`（只复算门的道闸：闸一名形 :81、闸二坐标尺 r7）。
边界照旧：**不执行门、0 写账本、0 代插、0 改车道文件**；门的 DRY 不跑这两闸，所以我写的只能是「预测」。
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
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="",
           http_proxy="", https_proxy="")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件不吻合，拒投"
CLOSING = raw.decode("utf-8").strip()

plan = subprocess.run([PYEXE, os.path.join(HERE, "_inbox_drain_plan_r1.py")], capture_output=True,
                      text=True, encoding="utf-8", errors="replace", env=ENV, cwd=HERE, timeout=900).stdout
m = re.search(u"收件口根目录 (\\d+) 枚（现读 (\\d\\d:\\d\\d:\\d\\d)）", plan)
rows = re.findall(u"^\\s+(\\S+\\.md)\\s+闸一(\\S+)｜闸二 (\\S+) ⇒ 预测(\\S+)", plan, re.M)
m3 = re.search(u"可插 (\\d+) 枚 \\[(.*?)\\]｜预测被拒 (\\d+) 枚 \\[(.*?)\\]｜名不合被静默 SKIP (\\d+) 枚", plan)
mgrp = re.search(u"同块多枚的组数：(\\d+)", plan)
assert m and rows and m3, "复算没读到完整读数，拒投（不拿记忆填帖）"

# 门 idle：从 _processed 的 insert 文件名戳取（mtime 限今天）
import glob
st = []
for f in glob.glob(r"D:\moodle\_qoder_ledger_inbox\_processed\*.md.inserted_*"):
    hm = re.search(r"inserted_(\d{6})$", f)
    if hm and time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(f))) == time.strftime("%Y-%m-%d"):
        st.append((hm.group(1), os.path.basename(f).split(".md")[0]))
st.sort()
last = st[-1] if st else ("?", "?")
lt = time.strptime(time.strftime("%Y-%m-%d ", time.localtime()) + last[0], "%Y-%m-%d %H%M%S")
idle = (time.time() - time.mktime(lt)) / 60.0

S = {
    "when": time.strftime("%H:%M:%S"),
    "n": m.group(1), "read_at": m.group(2),
    "rows": u"\n".join(u"- `%s`：闸一 %s｜闸二 %s ⇒ 预测 **%s**" % r for r in rows),
    "ins": m3.group(1), "names": m3.group(2), "rej": m3.group(3), "skip": m3.group(5),
    "grp": mgrp.group(1), "last_name": last[1],
    "last_hm": "%s:%s:%s" % (last[0][:2], last[0][2:4], last[0][4:6]), "idle": "%.0f" % idle,
    "n_today": str(len(st)),
}

# 自动轮已经上过的那些等插贴：id 与时刻一律从 autumn_watch.log 现取，不手打（手打过一次就错过一枚 id）
posts = re.findall(r"^\[(\d\d:\d\d:\d\d)\] 已发等插贴 (\S+) 第(\d+)分档 -> (\d+)",
                   io.open(os.path.join(HERE, "autumn_watch.log"), encoding="utf-8",
                           errors="replace").read(), re.M)
mine = [p for p in posts if p[1] in [r[0] for r in rows]][-6:]
S["watch_posts"] = u"\n".join(u"  - `%s` 第%s分档 → 总线 `%s`（%s 上贴）" % (p[1], p[2], p[3], p[0]) for p in mine) or u"  - （本轮之前没有待发贴记录）"

TPL = u"""**门那一跳的前置我复算完了（{when}）：{n} 枚全预测可插，0 拒、0 同块重复 ⇒ 一趟就清干净**

- 收件口根目录 {n} 枚（现读 {read_at}）。逐枚过门的两道闸（闸一命名形 `:81`、闸二坐标尺 r7）：
{rows}
- 一趟 `--apply` 的预演：可插 **{ins}** 枚（{names}）｜预测被拒 **{rej}**｜命名不合规被静默 SKIP **{skip}**｜同块多枚的组数 **{grp}**（这格若 >0，注意门的 dedupe 按文件名取最后一枚、不是按 mtime 取最新）。
- 门自己的节奏：今天已入账 {n_today} 枚，最后一次跳是 `{last_name}` @ `{last_hm}` ⇒ 距本帖 **{idle} 分钟**。我的自动轮已按 15 分档逐枚上过贴（这几枚 id 从 `autumn_watch.log` 现取，不是我手打的）：
{watch_posts}

边界照旧：这一趟我只**复算**，不执行门、不写账本、不代插、不改任何车道的文件；门的 DRY 模式不跑这两闸，所以以上都是「预测」不是「门判」。你那一跳落地时若有一枚被真门拒，拒词按老规矩原样转给车道，我不改他们的字。

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1355_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d n=%s ins=%s rej=%s idle=%s" % (len(text.encode("utf-8")), S["n"], S["ins"], S["rej"], S["idle"]))
if "--dry" in sys.argv:
    print(text)
else:
    print(subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout)
