# -*- coding: utf-8 -*-
"""值守 13:00 · 「已申报但还没落地」清单尺（只读）。

为什么要这一把：12:20 之后现尖一直停在 `57ff5d1c2f85…`，而车道还在照单交货、门也还在代插
（12:54–12:55 那一趟收了 4 块）。也就是说**候选在排队，线在等笔**。
夜里靠 cron 每小时一跳来清这批队列；今天 11:00 cron 到期之后，清队列这件事只能靠号令者自己想起来跑。
这把尺就把队列具名列出来：哪一枚枝已在账本里逐字申报（40 位命中）、但还不是现尖的祖先（= 没落地），
并附我对它的一次只读落地预测（`merge-tree` 退码与冲突行计数）。

边界：全程只读，不落地、不插块、不写账本。判据是「合完逐字节等于车道自己那份」的**预测**，门的实判归 `--apply`/`--land`。
"""
import glob
import io
import os
import re
import subprocess
import sys
import time

REPO = r"D:\moodle\CityNexus"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")
SINCE_MIN = float(sys.argv[1]) if len(sys.argv) > 1 else 120.0
REF = re.compile(r"refs/heads/(review/[A-Za-z0-9._-]+)")
HEX = re.compile(r"\b([0-9a-f]{40})\b")
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"


def sh(args, t=600):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=t)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def tree_blobs(rev):
    """rev -> {path: blob40}（一次 `ls-tree -r`，只读）。"""
    rc, out = sh(["git", "ls-tree", "-r", rev])
    m = {}
    if rc == 0:
        for line in out.split("\n"):
            if "\t" not in line:
                continue
            meta, path = line.split("\t", 1)
            parts = meta.split()
            if len(parts) == 3 and parts[1] == "blob" and re.match(r"^[0-9a-f]{40}$", parts[2]):
                m[path.strip()] = parts[2]
    return m


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    now = time.time()
    rc, o = sh(["git", "ls-remote", "origin", TIPREF])
    tip = (o.split() or [""])[0]
    if not re.match(r"^[0-9a-f]{40}$", tip):
        print("现尖取不到：%s" % o[:120])
        return 1
    rc, last = sh(["git", "log", "-1", "--format=%ct", tip])
    tip_age = (now - int(last.split("\n")[0])) / 60.0 if last.isdigit() else -1
    print("现尖 `%s`（提交时间 %.1f 分前）" % (tip, tip_age))

    # 最近 SINCE_MIN 分钟内落盘的块里，找「枝名 + 同一块里的 40 位申报」
    blocks = []
    for f in glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*")) + glob.glob(os.path.join(INBOX, "*.md")):
        if now - os.path.getmtime(f) > SINCE_MIN * 60:
            continue
        blocks.append(f)
    ledger = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    cands = {}
    for f in blocks:
        t = io.open(f, encoding="utf-8", errors="replace").read()
        for m in REF.finditer(t):
            name = m.group(1)
            if name.startswith("review/cmdr-"):
                continue
            # 申报头：取该块里与枝名同行或相隔 <=80 字的 40 位
            near = t[max(0, m.start() - 80):m.end() + 200]
            heads = HEX.findall(near)
            head = ""
            for h in heads:
                if sh(["git", "cat-file", "-e", h + "^{commit}"])[0] == 0:
                    head = h
                    break
            if head:
                cands.setdefault(name, (head, os.path.basename(f)))
    print("最近 %.0f 分钟的块里数到车道枝 %d 枚（去重后）" % (SINCE_MIN, len(cands)))
    # 13:36 修的判据缺陷：`merge-base --is-ancestor 车道头 现尖` 会把**已落地**的读成未落地——
    # 落地时是把枝重挂成新提交（`review/cmdr-recut-*`），车道原来那枚头因此不在祖先链上，但它那份字节已经在线上。
    # 现在按复切器的口径量：同族取最新一代，再把该枝改过的每枚文件与现尖同路径逐枚比 blob。
    FAM = re.compile(r"^(.*?)(?:-r(\d+)|-(\d+))?$")
    fams = {}
    for name, val in cands.items():
        mm = FAM.match(name.replace("review/", ""))
        n = int(mm.group(2) or mm.group(3) or 1)
        if mm.group(1) not in fams or n > fams[mm.group(1)][0]:
            fams[mm.group(1)] = (n, name, val)
    folded = len(cands) - len(fams)
    tc = tree_blobs(tip)
    ready, landed, empty = [], 0, 0
    for fam, (n, name, (head, blk)) in sorted(fams.items()):
        if sh(["git", "cat-file", "-e", head + "^{commit}"])[0] != 0:
            sh(["git", "fetch", "-q", "origin", head])
        if sh(["git", "cat-file", "-e", head + "^{commit}"])[0] != 0:
            empty += 1
            continue
        rc2, mb = sh(["git", "merge-base", tip, head])
        rc3, fl = sh(["git", "diff", "--name-only", "%s..%s" % (mb, head)])
        fs = [x for x in fl.split("\n") if x.strip()]
        hc = tree_blobs(head)
        diff = [f for f in fs if hc.get(f, "") != tc.get(f, "")]
        if not fs or not diff:
            landed += 1
            continue
        declared = head in ledger
        rc4, mt = sh(["git", "merge-tree", "--write-tree", tip, head])
        conf = len([l for l in mt.split("\n") if "CONFLICT" in l])
        ready.append((name, head, blk, declared, rc4, conf, len(diff), len(fs)))
    print("同族折叠 %d 枚；按字节复算**已在线上 %d 枚**、**确有未落地差 %d 枚**（本地取不到对象 %d 枚不算读数）"
          % (folded, landed, len(ready), empty))
    for name, head, blk, declared, rc4, conf, ndiff, nall in ready:
        verdict = "merge-tree 干净" if rc4 == 0 else ("冲突 %d 行" % conf if conf else "merge-tree 退 %d" % rc4)
        print("  %-52s 头 %s  块 %s  账本逐字命中=%s  与现尖差 %d/%d 枚  只读预测=%s"
              % (name[:52], head[:12], blk[:26], "是" if declared else "否", ndiff, nall, verdict))
    clean = [x for x in ready if x[4] == 0]
    print("小结：可干净落的候选 %d 枚；若现尖 %.0f 分钟没动而队列非空 ⇒ 队列在等那一笔落地（只有号令者能移动权威线，我不落）。"
          % (len(clean), tip_age))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
