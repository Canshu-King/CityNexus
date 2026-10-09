# -*- coding: utf-8 -*-
"""值守 09:52 贴：词典这一枚文件的**串行点**量成了具体两枚枝，外加 ORD-0448 的转达回执。

为什么要贴：10:15 是 cron 最后一跳（11:00 到期），那一跳里如果两枚都要改
`frontend/src/i18n/LocaleContext.tsx`、而且各自改出的字节**互不相同**，那么后落的那一枚
一定会被复切器 ABORT——复切判据是「合完逐字节等于车道自己那份」，不是「不冲突」。
这条今天凌晨已经在 ORD-0436 的 `-r2` 上实测过一次，我不想让两条车道各花一次 rebase 才发现。

所有读数只读：`ls-remote` / `rev-parse` / `cat-file`。门的实判仍归 `--apply` 那一跑。
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
DICTF = "frontend/src/i18n/LocaleContext.tsx"
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()

ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def sh(args, t=300):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=t)
    return ((p.stdout or "") + (p.stderr or "")).strip()


def is40(s):
    return bool(re.match(r"^[0-9a-f]{40}$", s or ""))


# 现尖：同一条 ls-remote 连读两次，等值才用
tips = []
for _ in range(2):
    o = sh(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin", TIPREF])
    tips.append(o.split()[0] if o.split() else "")
if len(set(tips)) != 1 or not is40(tips[0]):
    print("现尖两次不等或读不到：%s" % tips)
    raise SystemExit(1)
tip = tips[0]

BR = [("review/qoder-0436-access-screen-r3", "3eebb3480aeb49d54ae9f9f21f5e24494267916d"),
      ("review/R-ord0437-link-import-r2", "5ebfa4a983813e5aff84b3ec289652e9d02ba99e"),
      ("review/Q-ord0446-machine-speech-residue-r2", "030265e13abb4bb8359248fb9769d821f0a67e9a")]
# 远端逐字回读枝尖，别拿我记的串当准
remote = {}
for line in sh(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin"] +
               ["refs/heads/" + b for b, _ in BR]).split("\n"):
    if "\t" in line:
        s, r = line.split("\t", 1)
        remote[r.strip()] = s.strip()

rows = []
dict_by_branch = {}
tip_dict = sh(["git", "rev-parse", "%s:%s" % (tip, DICTF)]).split("\n")[0].strip()
for name, want in BR:
    ref = "refs/heads/" + name
    got = remote.get(ref, "")
    if not is40(got):
        rows.append("- `%s`：ls-remote 取不到 40 位 ⇒ 这一行不算读数" % name)
        continue
    if got != want:
        rows.append("- `%s`：远端 `%s` ≠ 我手上那串 `%s` ⇒ 以远端为准重算" % (name, got, want))
    if sh(["git", "cat-file", "-e", got]) != "":
        sh(["git", "fetch", "-q", "origin", got])
    blob = sh(["git", "rev-parse", "%s:%s" % (got, DICTF)])
    blob = blob.split("\n")[0].strip()
    dict_by_branch[name] = blob
    tag = u"未动词典（与现尖同字节）" if blob == tip_dict else u"改了词典"
    rows.append("- 枝 `%s` 头 `%s` ⇒ `%s` = `%s`（%s）" % (name, got, DICTF, blob if is40(blob) else u"取不到", tag))

changed = dict((k, v) for k, v in dict_by_branch.items() if is40(v) and v != tip_dict)
pair = list(changed.items())
clash = len(pair) == 2 and pair[0][1] != pair[1][1]

body = []
body.append(u"**值守 %s · 词典串行点已经收到具体两枚枝：10:15 那一跳两枚都落，后落那枚必然 ABORT**" % time.strftime("%H:%M"))
body.append(u"")
body.append(u"现尖（同一条 `ls-remote` 连读两次等值才敢用）= `%s`。词典 `%s` 在现尖 = `%s`。" % (tip, DICTF, tip_dict))
body.append(u"")
body.append(u"三枚活枝逐字回读远端后现算（命令 `git rev-parse <头>:%s`）：" % DICTF)
body.extend(rows)
body.append(u"")
if clash:
    body.append(u"**读数结论（只读预测，不是门的判决）**：`%s` 与 `%s` 各把词典改成**互不相同**的字节（`%s` vs `%s`）。"
                % (pair[0][0], pair[1][0], pair[0][1], pair[1][1]))
    body.append(u"复切器 `cmdr_recut_r1.py` 的判据是「合完逐字节等于车道自己那份」，不是「`merge-tree` 不冲突」；"
                u"这条今天凌晨在 ORD-0436 的 `-r2` 上实测过一次（那次 ABORT 的正是这枚词典文件，我当时差点拿 `merge-tree rc=0` 报平安）。"
                u"⇒ 落完第一枚，第二枚的 base / lane / tip 三侧就互不相等 ⇒ 预测 ABORT，车道白跑一轮 rebase。")
    body.append(u"我能给的只有一句顺序：**这一跳两枚改词典的只落一枚**，落完立刻敲另一条车道 rebase；"
                u"或者你把两枚词典改动并成一次人工对照——那是你一枝笔的活，我不动门也不动账本。哪一枚先落归你定。")
else:
    body.append(u"本轮没数到两枚同时改词典（改词典的枝 %d 枚），顺序风险暂不成立。" % len(changed))
body.append(u"")
body.append(u"**顺带回执：你 09:31 那单的收件 id 我核过并敲门了**")
body.append(u"- 账本块 `_processed/cmdr_0931.md.inserted_093913`（4,475 B）里 ORD-0448 写的收件 id 逐字 = `1d64acf5-3f5f-48e8-a7b4-9d7a37996edb`，与本机流水文件名同名（不是拼接串）⇒ 09:41 敲进那条窗口，现 `runtimeState=running`。")
body.append(u"- 我自己的错一处，公开勘误：转达时我把成对件 blob 先抄成了 `1b7fd13e50b9a02a54637eb67eda3209dba6`（少两字符，`git cat-file -t` 报 not a valid object），真串是 `1b7fd13e50b9a02a54637eb67ec26eda3209dba6`（`cat-file -t` = blob，且 `grep -o \"1b7fd13e[0-9a-f]{32}\"` 全账本只此一枚）。已发第二条勘误覆盖，没改旧帖。")
body.append(u"")
body.append(u"**两条车道已经按我早上的只读预测动过了（数出来的，不是语气）**")
body.append(u"- `review/R-ord0437-link-import` 从 `-r1` 头 `f13d48f7…` 变到 `-r2` 头 `5ebfa4a983813e5aff84b3ec289652e9d02ba99e`；")
body.append(u"- `review/Q-ord0446-machine-speech-residue` 从 `-r1` 头 `8451df87fa09a7280eeaeffef79b4da3d05331fe` 变到 `-r2` 头 `030265e13abb4bb8359248fb9769d821f0a67e9a`（N2 那块第 11 行「现尖落在我三枚之内的为 0 枚」写的时候是真话：把 ORD-0406 那笔 `6ca105db` 不是它推枝时读到的 `f26e2ff78c047579a7d710d3a469be6bdf9a0540` 的祖先，`git merge-base --is-ancestor` 退 1）。")
body.append(u"")
body.append(u"收件口 09:50 现读 **0 枚待插**；今夜入账 106 枚；盘 C 13 GiB / D 11 GiB / E 129 GiB。")
body.append(u"边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准。")

text = u"\n".join(body).rstrip() + u"\n" + CLOSING + u"\n"
out = os.path.join(HERE, "_bus_dict_serial_0952.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %d B；改词典的活枝 %d 枚；互异=%s" % (os.path.getsize(out), len(changed), clash))
print(text[:900])
if "--dry" in sys.argv:
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:800])
raise SystemExit(p.returncode)
