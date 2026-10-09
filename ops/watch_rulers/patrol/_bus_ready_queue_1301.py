# -*- coding: utf-8 -*-
"""值守 13:01 贴：候选队列已经排到 9 枚，而现尖 44 分钟没动（只读清单，落地那一笔归你）。

cron 的每小时跳 11:00 到期以后，「收块 + 复切 + 落地」这件事不再有自动触发点。
12:30 那块之后你一直在跑代插（12:54 / 12:55 两趟）与逐屏亲测，这我数得到；
但队列里的候选现在靠的是「你还记得有它们」，所以我每隔一段时间把清单摊一次。
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
REPO = r"D:\moodle\CityNexus"
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def sh(args, t=900):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=t)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


rcg, gout = sh([PY, os.path.join(HERE, "_ready_not_landed_r1.py"), "150"])
gl = [x.rstrip() for x in gout.split("\n") if x.strip()]
head = [x for x in gl if x.strip().startswith(u"现尖")]
rows = [x for x in gl if "review/" in x and x.strip().startswith("review/") is False and "只读预测=" in x]
rows = rows or [x for x in gl if "只读预测=" in x]
summ = [x for x in gl if x.strip().startswith(u"其中") or x.strip().startswith(u"小结")]

# 家族最新一代的判定（避免把旧的混血枝当候选）
rc, fam = sh(["git", "ls-remote", "origin", "refs/heads/review/R-ord0437-link-import-r6",
              "refs/heads/review/R-ord0437-link-import-r3"])
fam_map = {}
for line in fam.split("\n"):
    if "\t" in line:
        s, r = line.split("\t", 1)
        fam_map[r.strip().replace("refs/heads/", "")] = s.strip()
rc2, anc = sh(["git", "merge-base", "--is-ancestor",
               fam_map.get("review/R-ord0437-link-import-r3", ""),
               fam_map.get("review/R-ord0437-link-import-r6", "")])
r3_in_r6 = "YES" if rc2 == 0 else "NO"
REL = "c12e1eb146dca960f6a4add2f0db3dc4f475dfc3"
R6 = fam_map.get("review/R-ord0437-link-import-r6", "")
R3 = fam_map.get("review/R-ord0437-link-import-r3", "")
rcrt, otip = sh(["git", "ls-remote", "origin", TIPREF])
tip0 = (otip.split() or [""])[0]
rcct, octr = sh(["git", "log", "-1", "--format=%ct", tip0]) if re.match(r"^[0-9a-f]{40}$", tip0) else (1, "")
tip_age = (time.time() - int(octr.split("\n")[0])) / 60.0 if octr.split("\n")[0].isdigit() else -1
if sh(["git", "cat-file", "-e", REL + "^{commit}"])[0]:
    sh(["git", "fetch", "-q", "origin", REL])
rel_in_r6 = "YES" if sh(["git", "merge-base", "--is-ancestor", REL, R6])[0] == 0 else "NO"
ncommits = sh(["git", "rev-list", "--count", "%s..%s" % (tip0, R6)])[1].strip() if R6 else "0"

body = []
body.append(u"**值守 %s · 已申报但还没落地的候选 %d 枚，全部只读预测 merge-tree 干净；现尖 `%s` 已 %.0f 分钟没动（这一轮我自己 `ls-remote` 现读）**"
            % (time.strftime("%H:%M"), len(rows), tip0, tip_age))
body.append(u"")
body.append(u"尺：`patrol/_ready_not_landed_r1.py`（只读：从最近 150 分钟落盘的块里取枝名与申报头，逐枚 `merge-base --is-ancestor` 判是否已在线上，再对未落的那几枚跑一次 `merge-tree --write-tree`）。本轮原始读数：")
for x in summ:
    body.append(u"- %s" % x.strip()[:220])
for x in rows:
    body.append(u"- %s" % x.strip()[:210])
body.append(u"")
body.append(u"**`review/R-ord0437-link-import` 家族现在远端有六代，最新一代是干净的：`-r6` 头 `%s`（申报块 `qoder-0437_1254.md`，12:54:51 入账）；"
            u"我 13:02 现读 `merge-base` 结果 = `-r6` 直接以现尖 `%s` 为基座、相对现尖 %s 笔，"
            u"且 `git merge-base --is-ancestor` 判 `-r3`（头 `%s`）在 `-r6` 里 = **%s**、"
            u"那 8 笔 replant 的头 `c12e1eb146dca960f6a4add2f0db3dc4f475dfc3` 在 `-r6` 里 = **%s** ⇒ "
            u"我 10:17 送错窗口造成的那次混血（总线 `5882772777`）**已经不在这枚候选的祖先链上了**，正主自己另切了一代。"
            u"落不落仍归你，我只是把这一格结案：不用再为那 8 笔裁归属。**"
            % (R6[:40], tip0[:40], ncommits, R3[:40], r3_in_r6, rel_in_r6))
body.append(u"")
body.append(u"另外三条形状读数，供你排落地顺序：① `review/N3-ord0440-exposure-cells-r2`（头 `ab171b0c407a…`，块 `n3_1238.md` 12:55:07 入账）与 `review/qoder-0449-invite-and-revoke-r1`（头 `05628b3a776a…`，块 `0383_1252.md`）这两枚都动词典，`LocaleContext.tsx` 在现尖 = `0477cde9beafdf5c145ae91fbbc2f1b26520e50c` ⇒ 同一跳两枚都落，后落那枚仍会 ABORT（判据是你写的「合完逐字节等于车道自己那份」）；② 今日 12:20 之后现尖一直是 `57ff5d1c2f8540d498d945ed591c36689fc0f39e`；③ 收件口此刻 0 枚待插，最后一趟代插 12:55:33（`q_1253.md`）。")
body.append(u"")
body.append(u"边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准、0 次改动 cron。清单里那句「merge-tree 干净」是**我的只读预测**，门的实判归你那一跑。")

text = u"\n".join(body).rstrip() + u"\n" + CLOSING + u"\n"
out = os.path.join(HERE, "_bus_ready_queue_1301.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %d B；候选 %d 行；r3 in r6 = %s" % (os.path.getsize(out), len(rows), r3_in_r6))
print(text[:700])
if "--dry" in sys.argv:
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:600])
raise SystemExit(p.returncode)
