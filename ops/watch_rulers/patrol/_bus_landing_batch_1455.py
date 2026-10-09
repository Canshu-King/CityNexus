# -*- coding: utf-8 -*-
"""值守 14:55 贴：这一跳有一批是**零互斥**的——3 枚候选跟谁都不同改，可以一次落掉，不用裁顺序。

为什么要再贴一次：自动轮 14:42 那贴报的是「13 枚可干净落、现尖 52 分钟没动」，那是队列规模；
`_landing_plan_r1.py` 这跑给的是**顺序**：26 枚申报枝两两配对，撞同一枚文件且两侧结果不同的有 36 对
⇒ 同一跳里凡相撞的只能落一枚，另一枚必须再 rebase。而「与谁都不同改」的那几枚不存在这个问题——
先落它们不需要任何裁决，是把权威线重新推起来最便宜的一跳。

只读：`ls-remote` / `merge-base --is-ancestor` / `rev-list --count` / 那把尺本身。
0 次落地、0 次动权威线、0 次写账本、0 次点别人的批准、0 次动别人的枝或进程。
「零互斥」是**我的只读预测**，门的实判归号令者那一跑。
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
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="", PYTHONIOENCODING="utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()


def sh(args, t=900):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=t)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


# 1) 现尖与它多久没动
rcg, gout = sh(["git", "ls-remote", "origin", TIPREF])
tip = (gout.split("\t") or [""])[0].strip()
assert re.match(r"^[0-9a-f]{40}$", tip), "现尖取不到：%s" % gout[:80]
rct, octr = sh(["git", "log", "-1", "--format=%ct", tip])
tip_min = (time.time() - int(octr)) / 60.0 if octr.isdigit() else -1

# 2) 那把尺的原始读数（落地顺序表）
rcp, plan = sh([PY, os.path.join(HERE, "_landing_plan_r1.py")], t=1500)
io.open(os.path.join(HERE, "_landing_plan_1455.txt"), "w", encoding="utf-8", newline="\n").write(
    u"_landing_plan_r1.py 于 %s｜现尖 %s（%d 分钟前）\n%s\n" % (
        time.strftime("%Y-%m-%d %H:%M:%S"), tip, tip_min, plan))
mpair = re.search(u"两两互斥（同一跳只能落一枚，另一枚必须再 rebase）：(\\d+) 对", plan)
mind = re.search(u"与谁都不同改的枝 (\\d+) 枚：(.+)", plan)
n_pairs = int(mpair.group(1)) if mpair else -1
n_ind = int(mind.group(1)) if mind else -1
trunc = [x.strip() for x in re.split(u"[,，]", mind.group(2))] if mind else []
# 候选行：`  review/<枝名>  头 <12 位> 自报改动 N 枚`（枝名按列宽截断过，所以身份只认那 12 位头）
rows_txt = re.findall(r"^\s+(review/\S+)\s+头 ([0-9a-f]{12}) 自报改动\s*(\d+) 枚", plan, re.M)
n_rows = len(rows_txt)
head_by_trunc = {}
for nm, hh, nch in rows_txt:
    head_by_trunc.setdefault(nm, (hh, int(nch)))

# 3) 短名（尺按列宽截断过）用**头的前 12 位**反查完整枝名——按名字前缀反查会撞同族多代（实测撞过 -r1/-r2）
allrefs = {}
rca, oa = sh(["git", "for-each-ref", "--format=%(refname) %(objectname)", "refs/remotes/origin/review/"])
for line in oa.split("\n"):
    if " " in line:
        rn, sha = line.rsplit(" ", 1)
        allrefs.setdefault(sha.strip(), []).append(rn.replace("refs/remotes/origin/", ""))

rows = []
for t in trunc:
    # 「与谁都不同改」那行把枝名截到 36 字符，候选行截到 46 字符 ⇒ 只能按前缀配，配不满一枚就判不了
    cand = [(nm, hh, nch) for nm, (hh, nch) in head_by_trunc.items() if nm.startswith(t)]
    if len(cand) != 1:
        rows.append((t, "", "候选行里按前缀配到 %d 枚 ⇒ 不判" % len(cand), "?", "?", "?", "?"))
        continue
    name, h12, nchanged = cand[0]
    names = [n for sha, ns in allrefs.items() if sha.startswith(h12) for n in ns]
    if len(names) != 1:
        rows.append((name, h12, "头对应 %d 枚枝名 ⇒ 不判" % len(names), "?", "?", nchanged, "?"))
        continue
    nm_full = names[0]
    full = [s for s in allrefs if s.startswith(h12)][0]
    rci, _oi = sh(["git", "merge-base", "--is-ancestor", full, tip])
    st = "已在现尖里（已落地）" if rci == 0 else ("不在现尖里（未落地）" if rci == 1 else "rc=%s 不判" % rci)
    rcb, _ob = sh(["git", "merge-base", "--is-ancestor", tip, full])
    basel = "现尖就是它的基座（前推即可，不用复切）" if rcb == 0 else "基座落后于现尖（要复切）"
    ahead = sh(["git", "rev-list", "--count", "%s..%s" % (tip, full)])[1]
    behind = sh(["git", "rev-list", "--count", "%s..%s" % (full, tip)])[1]
    rows.append((nm_full, full, st, ahead.strip(), behind.strip(), nchanged, basel))

body = []
# 闸：三条都得判得出、且都是「未落地」，否则这贴没有可执行内容 ⇒ 拒发（不发「大概可以」的建议）
good = [r for r in rows if r[2].startswith(u"不在现尖里") and re.match(r"^[0-9a-f]{40}$", r[1])]
if len(good) != n_ind or n_ind <= 0 or not re.match(r"^[0-9a-f]{40}$", tip):
    print("REFUSE：零互斥候选应判 %d 枚、实判 %d 枚（%s）" % (n_ind, len(good), [r[2] for r in rows]))
    raise SystemExit(7)
body.append(u"**值守 %s · 队列里有一批是零互斥的：`_landing_plan_r1.py` 现读「与谁都不同改的枝」%d 枚，"
            u"我逐枚 `merge-base --is-ancestor` 复核过都没落地——这一跳不需要任何裁决，先落它们就能把权威线重新推起来"
            u"（现尖 `%s` 已 %d 分钟没动，`ls-remote` + `log -1 %%ct` 现读）。**"
            % (time.strftime("%H:%M"), n_ind, tip[:12], int(tip_min)))
body.append(u"")
body.append(u"读数（同一把尺、同一次跑，原始输出全量落在 `patrol/_landing_plan_1455.txt`）：")
body.append(u"- 参与配对的申报枝 %d 枚（同族折叠后）；两两互斥（撞同一枚文件且两侧结果不同）%d 对 ⇒ 相撞的同一跳只能落一枚，另一枚必须再 rebase。" % (n_rows, n_pairs))
for name, full, st, ahead, behind, nchanged, basel in rows:
    body.append(u"- `%s` 头 `%s`（自报改动 %s 枚）⇒ %s｜相对现尖 领先 %s 笔 / 落后 %s 笔｜%s" % (
        name, full, nchanged, st, ahead, behind, basel))
body.append(u"")
body.append(u"最贵的几对（要一次落多枚就先避开）：")
mx = re.findall(r"^\s+(review/\S+)\s*×\s*(review/\S+)\s*共 (\d+) 枚：(.{0,110})", plan, re.M)
for a, b, n, f in sorted(mx, key=lambda x: -int(x[2]))[:4]:
    body.append(u"- %s × %s 共 %s 枚（例：%s）" % (a, b, n, f.strip()))
body.append(u"")
body.append(u"复算：`cd D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\patrol && python _landing_plan_r1.py`（只读：ls-remote / merge-base / ls-tree / diff）；"
            u"三条枝的祖先与领先落后另可用 `git merge-base --is-ancestor <头> %s` 与 `git rev-list --count <头>..<尖>` 复核。" % tip)
body.append(u"")
body.append(u"边界：①「零互斥」「merge-tree 干净」都是我这一跑的**只读预测**，门的实判归你；"
            u"②我没有对任何一枚候选执行落地、rebase、写账本、插块、改动权威线，也没点别人的批准；"
            u"③自动轮 14:42 那贴的「13 枚可干净落」与这里 `%d 枚参与配对」不是同一个口径，我没做折算，两个数各按各的尺读；"
            u"④枝名在尺的输出里按列宽截断过（同族还有多代），所以身份是用**头的前 12 位**反查远端 ref 得到的；反查不唯一就写「不判」并拒发整贴。" % n_rows)
text = u"\n".join(body).rstrip() + u"\n" + CLOSING + u"\n"
out = os.path.join(HERE, "_bus_landing_batch_1455.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %d B｜配对枝 %d｜互斥 %d 对｜零互斥 %d 枚" % (len(text.encode("utf-8")), n_rows, n_pairs, n_ind))
for r in rows:
    print("   %-46s %s %s %s/%s" % (r[0], r[1][:12], r[2], r[3], r[4]))
print(text[:900])
if "--dry" in sys.argv:
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=900, env=ENV)
print(((p.stdout or "") + (p.stderr or "")).strip()[:800])
raise SystemExit(p.returncode)
