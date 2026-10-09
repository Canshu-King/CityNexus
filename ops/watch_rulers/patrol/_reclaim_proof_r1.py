# -*- coding: utf-8 -*-
"""给「清理候选」补上决定性的一格：这枚目录名里带的 sha，内容在 git 里取不取回来。

取回得来 ⇒ 删掉不丢证据（号令者 18:04 自己用的判据是「账本引用次数」，我这里补的是第二道：可复现性）。
只读：`git cat-file -t`、`git merge-base --is-ancestor`，全对**权威尖**取；不 fetch 写、不动任何人的文件。
"""
import io
import json
import os
import re
import subprocess
import sys
import time

ROOT = r"D:\moodle"
REPO = r"D:\moodle\CityNexus"
HERE = os.path.dirname(os.path.abspath(__file__))
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="", http_proxy="", https_proxy="")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def git(*a):
    p = subprocess.run(("git", "-C", REPO) + a, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=120)
    return p.returncode, (p.stdout or "").strip()


tip = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1")[1].split()[0]
assert len(tip) == 40, "取不到尖"
led = io.open(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md", encoding="utf-8", errors="replace").read()
now = time.time()

# 候选 = 账本 0 引用 且 >24 小时没动；按大小排（du 每枚硬超时 15 秒），只看前 12 枚
cands = []
for d in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, d)
    if not (d.startswith("_qoder_") and os.path.isdir(p)):
        continue
    if d in led:
        continue
    if (now - os.path.getmtime(p)) / 3600.0 <= 24.0:
        continue
    kb = None
    try:
        r = subprocess.run(["du", "-sk", p], capture_output=True, text=True, timeout=15,
                           encoding="utf-8", errors="replace", env=ENV)
        f = r.stdout.strip().split("\t")[0]
        kb = int(f) if f.isdigit() else None
    except Exception:
        kb = None
    cands.append((d, kb, (now - os.path.getmtime(p)) / 86400.0))
    if len(cands) >= 40:
        break

big = [c for c in cands if c[1] and c[1] / 1024.0 >= 50.0]
timeout = [c for c in cands if c[1] is None]
print("扫到候选 %d 枚（账本 0 引用且 >24 小时没动）；其中 ≥50 MiB 的 %d 枚；du 15 秒走不完 %d 枚" % (
    len(cands), len(big), len(timeout)))
print("尖 %s @ %s" % (tip[:12], time.strftime("%H:%M:%S")))
print()
rows = []
for d, kb, days in sorted(big, key=lambda x: -x[1]):
    toks = re.findall(r"\b[0-9a-f]{6,40}\b", d)
    proof = []
    for t in toks:
        if len(t) < 6:
            continue
        rc, obj = git("rev-parse", "--verify", "-q", "%s^{commit}" % t) if len(t) >= 7 else (1, "")
        if rc == 0:
            rc2, _ = git("merge-base", "--is-ancestor", t, tip)
            proof.append(u"`%s` %s（对象在库，%s尖的祖先）" % (t, obj[:7], u"是" if rc2 == 0 else u"**不是**"))
        else:
            rc3, t3 = git("cat-file", "-t", t)
            proof.append(u"`%s` %s" % (t, (t3 if rc3 == 0 else u"库内取不到这枚短位")))
    rows.append((d, kb / 1024.0, days, u"；".join(proof) if proof else u"目录名里没有可认的 sha"))
for d, mib, days, pr in rows:
    print("  %-42s %8.1f MiB｜%5.1f 天没动｜%s" % (d, mib, days, pr[:170]))
tot = sum(r[1] for r in rows)
print()
print("这 %d 枚 ≥50 MiB 的合计 %.1f MiB（≈%.2f GiB）" % (len(rows), tot, tot / 1024.0))
df = subprocess.run(["df", "-k", "/d"], capture_output=True, text=True, env=ENV).stdout
m = re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%", df)
print("盘现值 %.1f MiB @ %s" % (int(m.group(3)) / 1024.0, time.strftime("%H:%M:%S")))
print("边界：可复现 ≠ 该删——目录名里的短位 sha 可能与这枚树的实际内容有出入；真要删，由号令者或用户逐枚点名，我不碰任何人的目录。")
io.open(os.path.join(HERE, "_reclaim_proof.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps({"at": time.strftime("%m-%d %H:%M:%S"), "tip": tip, "cands": len(cands),
                "big": [[d, round(mib, 1), round(days, 1), pr] for d, mib, days, pr in rows],
                "du_timeout": [t[0] for t in timeout],
                "free_mib": round(int(m.group(3)) / 1024.0, 1)}, ensure_ascii=False, indent=1))
