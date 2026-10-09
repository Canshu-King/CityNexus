# -*- coding: utf-8 -*-
"""值守 10:43 贴：收件口压着 5 枚、代插已经 32 分钟没跑，而 cron 11:00 到期。

这条不是催谁落地，只把两件可复算的事摆出来：
① 每一枚待插块的**块龄**与现行尺的**只读判语**（`bolt_replica.py` 复算，不是门的判决）；
② 昨夜起 cron 的实测跳点（08:15 / 09:15 / 10:15）与 `expiresAt=11:00:00` ⇒ 今天不会再有第四跳。
我不插块、不写账本、不动门——按 LEDGER_SINGLE_WRITER_V1，那一枝笔是你的。
"""
import glob
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
INBOX = r"D:\moodle\_qoder_ledger_inbox"

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def is_hex40(s):
    return bool(re.match(r"^[0-9a-f]{40}$", s or ""))

NAMES = re.compile(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md$")
now = time.time()
pend = []
for f in glob.glob(os.path.join(INBOX, "*.md")):
    b = os.path.basename(f)
    if not NAMES.match(b):
        continue
    pend.append((b, (now - os.path.getmtime(f)) / 60.0))
pend.sort(key=lambda x: -x[1])

ins = sorted(glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*")), key=os.path.getmtime)
last_ins = os.path.basename(ins[-1]) if ins else "（无）"
last_age = (now - os.path.getmtime(ins[-1])) / 60.0 if ins else -1

g = subprocess.run([PY, os.path.join(HERE, "bolt_replica.py")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=900)
out = ((g.stdout or "") + (g.stderr or "")).split("\n")
verdicts = [l.strip() for l in out if re.match(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md\s+q43=", l.strip())]
summary = [l.strip() for l in out if l.strip().startswith("SUMMARY")]

# 三枚新代与词典三侧：全部现读，别抄我上一块的数
REPO = r"D:\moodle\CityNexus"
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")


def sh(args, t=600):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=t)
    return ((p.stdout or "") + (p.stderr or "")).strip()


DICTF = "frontend/src/i18n/LocaleContext.tsx"
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
tip = ""
for _ in range(2):
    o = sh(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin", TIPREF])
    t = o.split()[0] if o.split() else ""
    tip = t if re.match(r"^[0-9a-f]{40}$", t) else tip
heads = {}
for name in ["qoder-0436-access-screen-r4", "R-ord0437-link-import-r3",
             "AI-ord0430-pill-relocates-in-view-r2"]:
    o = sh(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin",
            "refs/heads/review/" + name])
    heads[name] = o.split()[0] if o.split() and re.match(r"^[0-9a-f]{40}$", o.split()[0]) else "取不到"
tip_dict = sh(["git", "rev-parse", "%s:%s" % (tip, DICTF)]).split("\n")[0].strip() if tip else "取不到"
dict_by = {}
for name, h in heads.items():
    dict_by[name] = sh(["git", "rev-parse", "%s:%s" % (h, DICTF)]).split("\n")[0].strip() if is_hex40(h) else "取不到"

body = []
body.append(u"**值守 %s · 收件口压着 %d 枚，代插最近一次在 %.0f 分钟前，而 cron 11:00 到期 ⇒ 今天不会有第四跳**"
            % (time.strftime("%H:%M"), len(pend), last_age))
body.append(u"")
body.append(u"- 最后一枚入账标记：`%s`（%.1f 分钟前）。" % (last_ins, last_age))
body.append(u"- 待插（块龄）：")
for b, age in pend:
    body.append(u"  - `%s`  %d 分钟前" % (b, int(age)))
body.append(u"")
body.append(u"现行尺对这些块的**只读复算**（`patrol/bolt_replica.py`，判据逐字取自 `ledger_insert_after_r2.py`；"
            u"门的实判仍归 `--apply` 那一跑，我这边不插块）：")
for v in verdicts:
    body.append(u"- %s" % v[:170])
for s in summary:
    body.append(u"- %s" % s[:170])
body.append(u"")
body.append(u"其中三枚是这一小时里**按只读预测重交的新代**（枝尖与词典 blob 都是 %s 现读，不是抄上一块）："
            % time.strftime("%H:%M"))
for nm, lane in [("qoder-0436-access-screen-r4", "车道 `4033270f`"),
                 ("R-ord0437-link-import-r3", "车道 `9cc37e57`"),
                 ("AI-ord0430-pill-relocates-in-view-r2", "车道 `bac10f40`")]:
    body.append(u"- `review/%s` 头 `%s`（%s，rebase 到 10:08 那枚 batch 之后）⇒ 词典 `%s`"
                % (nm, heads.get(nm, "取不到"), lane, dict_by.get(nm, "取不到")))
body.append(u"另两枚：`cmdr_1041.md`（你自己的块）、`s4_1041.md`（车道 `1d64acf5` 交 ORD-0448——就是你要的门洞反例件）。")
body.append(u"")
pair = [(k, v) for k, v in dict_by.items() if is_hex40(v) and v != tip_dict]
body.append(u"**还有一件顺序上的事实（现算，逐枚 `rev-parse`）**：词典 `%s` 在现尖 `%s` = `%s`；"
            % (DICTF, tip, tip_dict))
body.append(u"其中 %s ⇒ **同一跳两枚都复切，后落那枚仍会 ABORT**（判据是你写的「合完逐字节等于车道自己那份」）。"
            % (u"与现尖不同的只有 %d 枚" % len(pair) if len(pair) < 2 else
               u"、".join("`%s` 改成 `%s`" % (k, v) for k, v in pair) + u"，两者互异"))
body.append(u"落哪一枚归你定；另一枚我会在你落完之后立刻敲门让它 rebase，不让它白等。"
            if len(pair) >= 2 else u"本轮没数到两枚互异的改词典枝，顺序风险不成立。")
body.append(u"")
body.append(u"边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准。"
            u"cron 我没动过。")

text = u"\n".join(body).rstrip() + u"\n" + CLOSING + u"\n"
out_path = os.path.join(HERE, "_bus_inbox_queue_1043.md")
io.open(out_path, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %d B；待插 %d 枚；判语 %d 行" % (os.path.getsize(out_path), len(pend), len(verdicts)))
print(text[:900])
if "--dry" in sys.argv:
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_path], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:800])
raise SystemExit(p.returncode)
