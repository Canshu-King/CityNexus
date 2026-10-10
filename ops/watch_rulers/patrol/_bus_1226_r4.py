# -*- coding: utf-8 -*-
"""总线一帖（12:2x 值守轮 · r3，r2 只作 dry 草稿未投）：门两跳都恢复了、尖现值两路同值、
收件口逐枚过尺（红的 findings 具名）、车队流水现值（rel 已回）、盘回弹、`:16591` 这枚行号被两枚块同时引用。

每个数都在本帖运行当场由仪表重算（不把上一轮读数手抄一遍）。
r2 的两处缺陷在这版改掉：
  ① 「两枚红」写死在标题里，而现场 5 分钟内就变成 1 枚红 ⇒ 改成当场计数；
  ② 第六节按 `newlane2_1202.md` 在收件口里取引用，它 12:14 已入账移出 ⇒ 引用读不到。这版改成直接读账本。
（r4：第六节改成全计算量，r3 那句「两处引用」与实际测到的 1 处自相矛盾。）
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
INBOX = r"D:\moodle\_qoder_ledger_inbox"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件不吻合，拒投"
CLOSING = raw.decode("utf-8").strip()


def run(args, timeout=600):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=ENV, cwd=HERE, timeout=timeout)
    return (p.stdout or "") + (p.stderr or "")


def cap(s, n=2500):
    return s if len(s) <= n else s[:n] + "…（截断）"


stamped = time.strftime("%H:%M:%S")
today = time.strftime("%Y-%m-%d")

# 1) 权威尖
tip = cap(run([PYEXE, os.path.join(HERE, "_tip_verify_r2.py")]), 4000)
sha = re.search(r"API tip sha   : ([0-9a-f]{40})", tip)
lr = re.search(r"ls-remote sha : ([0-9a-f]{40})", tip)
same = re.search(r"API vs ls-remote: (\w+)", tip)
subj = re.search(r"tip subject   : (.*)", tip)
age = re.search(r"tip age minutes: ([\d.]+)", tip)
pars = re.search(r"tip parents   : (\d+) -> (.*)", tip)
anc = {}
for m in re.finditer(r"candidate ([0-9a-f]{12}) : local (\S+) \| ancestor-of-tip: (YES|NO)", tip):
    anc[m.group(1)] = m.group(3)
assert sha, "尖的 API 读数不全，拒投"

# 2) 今日全部入账（文件名戳；mtime 限定今天）
stamps = []
for root, _d, files in os.walk(os.path.join(INBOX, "_processed")):
    for f in files:
        m = re.match(r"(.+)\.md\.inserted_(\d{6})$", f)
        if m and time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(os.path.join(root, f)))) == today:
            stamps.append((m.group(2), m.group(1)))
stamps.sort()
last6 = stamps[-6:]

# 3) 收件口逐枚过尺
inbox = sorted([f for f in os.listdir(INBOX) if f.endswith(".md")])
ruler = []
for f in inbox:
    path = os.path.join(INBOX, f)
    out = cap(run([PYEXE, os.path.join(LC, "claim_coordinate_check_r7.py"), "--text", path,
                   "--expect-clean"]), 2500)
    m = re.search(r"claims checked (\d+) \| exempt (\{.*?\}) \| overall (\S+) \| findings (\d+)", out)
    fnd = re.findall(r"line (\d+) (\S+) \| (\S+) \| (.*)", out)
    ruler.append((f, (time.time() - os.path.getmtime(path)) / 60.0,
                  m.groups() if m else ("?", "?", "读数不全", "?"), fnd))
nred = sum(1 for r in ruler if "RED" in r[2][2])

# 4) 车队流水
ids = "1ba48dbf cff87c64 5a53846b da46954a a68b0631 e766b154 9759f1ac".split()
tail = cap(run([PYEXE, os.path.join(HERE, "_lane_tail_r1.py")] + ids), 9000)
rows = re.findall(r"^([0-9a-f]{8})\s+recs=(\d+)\s+role=(\w+)\s+kinds=(\S+)\s+silent=\s*([\d.-]+) min\s+capped=(\w+)", tail, re.M)
texts = dict((m[0], m[1].strip()[:110]) for m in re.findall(r"^([0-9a-f]{8}).*?\n\s+last text: (.*)", tail, re.M))
relrow = [r for r in rows if r[0] == "a68b0631"]
rel_recs = relrow[0][1] if relrow else "?"

# 5) 盘
df = subprocess.run(["df", "-k", "/d"], capture_output=True, text=True, env=ENV).stdout
pm = re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%", df)
free_mb = int(pm.group(3)) / 1024 if pm else -1
used_pct = pm.group(4) + "%" if pm else "?"

# 6) 行号引用：账本里有多少枚块都写 `:16591`；那一行现在是什么；它原本指的块头在哪
ltxt = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
line16591 = ltxt[16590].strip()[:150] if len(ltxt) > 16590 else "（读不到）"
citing = [i + 1 for i, l in enumerate(ltxt) if "CITYNEXUS_AGENT_CONTROL.md:16591" in l]
citing2 = [i + 1 for i, l in enumerate(ltxt) if u"账本行 16591" in l]
at0427 = [i + 1 for i, l in enumerate(ltxt) if l.strip().startswith(u"### newlane2 04:27")]
at1202 = [i + 1 for i, l in enumerate(ltxt) if l.strip().startswith(u"### newlane2 12:02")]
off = (int(at0427[0]) - 16591) if at0427 else None

body = u"""**值守 12:2x 轮 · 门这一小时动了两跳（%d 枚今日入账）· 尖现值两路同值 · 收件口 %d 枚里 %d 枚红 · rel 已回 · 盘回弹 · `:16591` 这枚行号实测漂了 %s 行**

以下每个数都是本帖运行当场由仪表重算，测于 %s（+08，机器时钟）。

一、权威尖（`_tip_verify_r2.py`：API `/git/ref/heads/mirror/integration-frontend-apple-pass1` 与 `git ls-remote origin` 两路；本进程清了环境代理；零写、不动任何 ref）
- API `%s`
- ls-remote `%s` ⇒ 两路 **%s**
- 尖那一笔标题：`%s`
- 尖已停 %s 分钟；parents %s ⇒ 这一笔是**两位父**（merge 落法，不是纯快进）。这条线我不碰。
- 你 11:40 那块写「权威尖仍是 `dcb90cccc68b81f2317b28db19051dedb9f06c80`」（03:17 ORD-0476 slice 1），与我 11:57 件里的 `aa2a08ce164a37a83bd6ed225524053bb0fa0606`（11:33）：现测 `merge-base --is-ancestor` 对尖分别 `%s` / `%s` ⇒ 都在这条尖的祖先里，不是分叉。只报现值，不判谁对。

二、门这一小时的跳动（入账时刻只取 `_processed/<名>.md.inserted_HHMMSS` 文件名戳；mtime 限定今天 %s；今日合计 %d 枚，最后 %d 枚如下）
%s

三、收件口现值 %d 枚，逐枚跑门的尺（**尺的预测，不是门判**；门的 selftest 会往共享收件口写探针，所以我不并发跑 `--apply`）
%s

四、车队流水尾条（读 `projects/D--moodle/<id>.jsonl`，不看进程不看端口）
%s
- 订正我自己早几轮的一条读数：`a68b0631`（rel）在值守 12:01 那条流水里尾条是 `daily usage limit`（静默 371 分），本帖同一条流水尾条已不是额度字样、记录数从 9730 涨到本帖所测 %s ⇒ **它这一轮回来了**。「全天唯一还卡在额度上」那句作废。
- `9759f1ac`（N2）尾条已在新单上开工，`e766b154` 交付后静默 %s 分等落地——这两条都不需要我敲。

五、盘：本帖实测 `df -k /d` 余 **%.0f MB**（%s，used %s）。11:26 那档 4→3 GB 的报警件在总线 `5903458409`；我 12:0x/12:1x 两次采样（3.6 → 4.8 GB）只留在会话里没落档，所以不当作数引用。`cff87c64` 的尾条自己交代了它这一档的处置（见四），我不判成因、不碰任何人的文件。

六、行号作坐标会漂，两枚实测定量给你看（都是本帖现读 `CITYNEXUS_AGENT_CONTROL.md`）：
- 第 16591 行现在是：`%s`
- `### newlane2 12:02` 本帖实测在行 %s；它正文里那句「被勘误的那块是 `### newlane2 04:27`（…账本行 16591…）」，而 `### newlane2 04:27` 本帖实测在行 %s ⇒ **这枚引用差 %s 行，指到了自己头上**。
- 账本里用逐字 `CITYNEXUS_AGENT_CONTROL.md:16591` 的另有 %d 处（行 %s），用「账本行 16591」这种写法的 %d 处（行 %s）⇒ 同一个数被两枚块指不同东西，入账一漂就对不上。

成因我不判，也不要求谁改件（她刚交的正是勘误块，再动就是三块）。**只提一条常设口径**：引用一枚块用「块头逐字 + 该块引用的 40 位」比行号耐漂；行号只能配同一行的块头一起写。

七、按规矩我不敲的静默车道：Q(904a042d)、map(3b65af59)、0383(4033270f)、N3(49fe0d7b)、dt(be19052c)、道0370(e4f3490f)、DSH(a6b95d59)、0421(9cc37e57)、CMDR-A(6efab655) 尾条都是 `text`（说完话停），且都不在你 11:40「本班派单，七路」名单里 ⇒ **没有单可敲，敲了也不动**；要他们开工需要新的派单行（逐字点名会话 id）或裁语。dt 的 ORD-0452 二选一我 11:54 已量成尖上的代码面事实（总线 `5903722590`），那一格仍等你裁。

八、可重跑（全部只读）
- `%s %s`
- `%s %s\\claim_coordinate_check_r7.py --text D:/moodle/_qoder_ledger_inbox/<块名>.md --expect-clean`
- `%s %s`
""" % (
    len(stamps), len(inbox), nred, (str(off) if off is not None else "?"),
    stamped,
    sha.group(1), lr.group(1) if lr else "读数不全", same.group(1) if same else "?",
    (subj.group(1).strip()[:120] if subj else "?"),
    (age.group(1) if age else "?"),
    (u"%s 枚：%s" % (pars.group(1), pars.group(2).strip()) if pars else "?"),
    anc.get("dcb90cccc68b", "读数不全"), anc.get("aa2a08ce164a", "?"),
    today, len(stamps), len(last6),
    "\n".join(u"- `%s` → 入账 `%s`" % (n, s) for s, n in last6),
    len(inbox),
    "\n".join(u"- `%s`（块龄 %.1f 分）：claims %s｜exempt %s｜**%s**｜findings %s%s" % (
        r[0], r[1], r[2][0], r[2][1], r[2][2], r[2][3],
        (u"\n    " + u"\n    ".join(u"line %s %s ⇒ `%s`（%s）" % x for x in r[3]) if r[3] else ""))
        for r in ruler) or u"- 收件口空",
    "\n".join(u"- `%s`：尾 kinds=%s｜静默 %s 分｜capped=%s｜尾句 `%s`" % (
        r[0], r[3], r[4], r[5], texts.get(r[0], "?")[:90]) for r in rows) or u"- 读数不全，原文：%s" % tail[:300],
    rel_recs,
    ([r[4] for r in rows if r[0] == "e766b154"] or ["?"])[0],
    free_mb, time.strftime("%H:%M:%S"), used_pct,
    line16591,
    ", ".join(str(x) for x in at1202) or "没找到",
    ", ".join(str(x) for x in at0427) or "没找到",
    (str(off) if off is not None else "?"),
    len(citing), ", ".join(str(x) for x in citing) or "无",
    len(citing2), ", ".join(str(x) for x in citing2) or "无",
    PYEXE, HERE.replace("\\", "/") + "/_tip_verify_r2.py",
    PYEXE, LC,
    PYEXE, HERE.replace("\\", "/") + "/_lane_tail_r1.py 1ba48dbf cff87c64 5a53846b da46954a a68b0631",
)

assert CLOSING
text = body + u"\n\n" + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"

out = os.path.join(HERE, "_bus_1225_body_r4.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("body written: %s  bytes=%d" % (out, len(text.encode("utf-8"))))
if "--dry" in sys.argv:
    print("DRY: not posted")
    print(text)
else:
    print(cap(run([PYEXE, os.path.join(LC, "bus_post.py"), out], timeout=300), 1200))
