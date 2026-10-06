# -*- coding: utf-8 -*-
"""值守 13:12 · 落地顺序表（只读）：已申报未落地的候选里，哪两枚**改同一枚文件且结果不同**。

为什么现在要这张表：cron 11:00 到期后落地全靠号令者自己想起来跑，而每一跳的时间窗有限；
复切判据是「合完逐字节等于车道自己那份」，所以同一批里两枚改同一枚文件且各自结果不同时，
**后落的那枚必然 ABORT**（今天已实测过多次）。他 11:47 那批就是靠这张表排的顺序。

算法：对每枚候选取 `merge-base(现尖, 头)`，用 `git ls-tree -r` 各拉一份 path→blob 表（每枚 rev 只拉一次并缓存），
两两比较：`f` 同时在两枚候选的 diff 里、且两侧各自的新 blob 不同 ⇒ 记一对冲突。
边界：只读预测，门的实判归 `--apply` / `--land`。
"""
import glob
import io
import os
import re
import subprocess
import sys
import time

REPO = r"D:\moodle\CityNexus"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
REF = re.compile(r"refs/heads/(review/[A-Za-z0-9._-]+)")
HEX = re.compile(r"\b([0-9a-f]{40})\b")
CACHE = {}


def sh(args, t=900):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=t)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def tree_map(rev):
    if rev in CACHE:
        return CACHE[rev]
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
    CACHE[rev] = m
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
        print("现尖取不到")
        return 1
    tt = tree_map(tip)

    # 远端逐字回读：枝名以远端头为准，块里那枚只当「车道自报」的对照（不一致要写出来，别默默用一边）
    rc, ro = sh(["git", "ls-remote", "origin", "refs/heads/review/*"])
    remote = {}
    for line in ro.split("\n"):
        if "\t" in line:
            s, r = line.split("\t", 1)
            remote[r.strip().replace("refs/heads/", "")] = s.strip()
    cands = {}
    mism = []
    files = []
    for f in glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*")) + glob.glob(os.path.join(INBOX, "*.md")):
        if now - os.path.getmtime(f) > 150 * 60:
            continue
        files.append(f)
    lost = []
    for f in files:
        try:
            t = io.open(f, encoding="utf-8", errors="replace").read()
        except (FileNotFoundError, PermissionError):
            # 10-05 16:2x 现场：这一支死过一次。收件口是共享的，列完文件之后代插腿会把刚插完的块
            # 搬进 `_processed/<名>.inserted_<钟点>`——搬家不等于消失，那枚申报已经进账本了，
            # 照样得算进分母。所以跟着搬后的件重读；仍找不到就具名记一笔并继续，
            # 绝不让整张表因为一次竞态而崩掉，也绝不静悄悄把分母算小。
            alt = glob.glob(os.path.join(INBOX, "_processed", os.path.basename(f) + u".inserted_*"))
            if not alt:
                lost.append(os.path.basename(f))
                continue
            t = io.open(alt[0], encoding="utf-8", errors="replace").read()
        for m in REF.finditer(t):
            name = m.group(1)
            if name.startswith("review/cmdr-"):
                continue
            near = t[max(0, m.start() - 80):m.end() + 200]
            declared = ""
            for h in HEX.findall(near):
                if sh(["git", "cat-file", "-e", h + "^{commit}"])[0] == 0:
                    declared = h
                    break
            head = remote.get(name, "") or declared
            if not head:
                continue
            if declared and head != declared:
                mism.append((name, declared, head))
            if sh(["git", "merge-base", "--is-ancestor", head, tip])[0] != 0:
                cands.setdefault(name, (head, os.path.basename(f)))
    print("现尖 `%s`；最近 150 分钟块里**申报了但未落地**的车道枝 %d 枚（枝尖以远端 `ls-remote` 为准）"
          % (tip[:12], len(cands)))
    if lost:
        # 读不到的块具名打出来：分母少了什么，看表的人必须能知道，不能让他以为「就这么些」
        print("  !! 有 %d 枚块既不在收件口也不在 _processed（%s）⇒ 上面的分母偏小，不是全量"
              % (len(lost), ", ".join(lost)))
    if mism:
        # 枝名与两枚头都不截断：这张表是给号令者点单用的，`review/cff87c64-ord0568-route-` 这种半截名
        # 他既不能点也不能核对；要列几枚就列几枚，超过十二枚才具名写「本页只打前十二」。
        print("  !! 块里自报的头与远端头不一致 %d 枚（可能车道又推了一代）：%s"
              % (len(mism), "; ".join("%s 块报 %s / 远端 %s" % (n, a, b) for n, a, b in mism[:12])))
        if len(mism) > 12:
            print("     （其余 %d 枚未打，全量在这支尺的 mism 里）" % (len(mism) - 12))
    # 13:14 修的一处自报缺陷：同一族（去掉尾巴 -rN）的旧代不该当候选列——
    # 第一版把 `R-ord0437` 的 -r3/-r5/-r6 三代与 `qoder-0436-access-screen-r3`（已被 -r4 取代并落地）
    # 都列成独立候选，读起来像「有 9 枚要落」，其实每族只有最新那一代是活的。
    fams = {}
    FAM = re.compile(r"^(.*?)(?:-r(\d+)|-(\d+))?$")
    for name, val in cands.items():
        mm = FAM.match(name)
        fam, n = mm.group(1), int(mm.group(2) or 1)
        if fam not in fams or n > fams[fam][0]:
            fams[fam] = (n, name, val)
    dropped = len(cands) - len(fams)
    cands = dict((v[1], v[2]) for v in fams.values())
    # 远端头可能不在本地对象库里：先补 fetch，取不到就不能当候选（否则会误报「未落地」）
    usable = {}
    for k, v in cands.items():
        head = v[0]
        if sh(["git", "cat-file", "-e", head + "^{commit}"])[0] != 0:
            sh(["git", "fetch", "-q", "origin", head])
        if sh(["git", "cat-file", "-e", head + "^{commit}"])[0] != 0:
            print("  （%s 的头 %s 本地取不到对象 ⇒ 不算读数）" % (k[:40], head[:12]))
            continue
        usable[k] = v
    cands = usable
    # 13:15 再修一处：一族里如果**任何一代**已经在现尖上（例如 0436 的 -r4 落了，而扫描窗口里只看得见 -r3），
    # 这一族就不该再当「待落候选」——那是同一份活的两副名字，会把候选数虚报成好几枚。
    fam_remote = {}
    for rname, rsha in remote.items():
        mm = FAM.match(rname)
        if not mm:
            continue
        fam_remote.setdefault(mm.group(1), []).append((int(mm.group(2) or mm.group(3) or 1), rsha))
    landed_fams = set()
    for fam, lst in fam_remote.items():
        for n, sha in sorted(lst, reverse=True):
            if sh(["git", "cat-file", "-e", sha + "^{commit}"])[0] != 0:
                sh(["git", "fetch", "-q", "origin", sha])
            if sh(["git", "cat-file", "-e", sha + "^{commit}"])[0] == 0 and \
               sh(["git", "merge-base", "--is-ancestor", sha, tip])[0] == 0:
                landed_fams.add(fam)
                break
    before = len(cands)
    cands = dict((k, v) for k, v in cands.items()
                 if FAM.match(k).group(1) not in landed_fams)
    print("剔除「同族已有代次在线上」的 %d 枚（这些族的工作已在线，只是块里留的是旧代名）" % (before - len(cands)))
    # 最新一代也重测一次「是否已在现尖上」，刚落的族要自动退出候选
    cands = dict((k, v) for k, v in cands.items()
                 if sh(["git", "merge-base", "--is-ancestor", v[0], tip])[0] != 0)
    print("最终候选 %d 枚（同族折叠后）" % len(cands))
    # 13:33 修：`merge-base --is-ancestor` 会把已落地的读成未落地——复切落地时把枝重挂成新提交
    # （`cmdr-recut-*`），车道原头因此不在现尖祖先链上，但它那份字节已经在线上。
    # 按复切器自己的口径量：该枝改过的每枚文件，字节是否已等于现尖那一份。
    still, onlined = {}, []
    for k, (head, blk) in cands.items():
        rcx, mb = sh(["git", "merge-base", tip, head])
        rcy, fl = sh(["git", "diff", "--name-only", "%s..%s" % (mb, head)])
        fs = [x for x in fl.split("\n") if x.strip()]
        hm, tm2 = tree_map(head), tree_map(tip)
        d = [f for f in fs if hm.get(f, "") != tm2.get(f, "")]
        if d:
            still[k] = (head, blk, len(fs), len(d))
        else:
            onlined.append((k, head[:12], len(fs)))
    if onlined:
        print("按字节复算**其实已经在线上**的 %d 枚（祖先判据会把它们误报成候选，我不这么报）：%s"
              % (len(onlined), ", ".join("%s(%s,%d枚全等)" % (x[0][:28], x[1], x[2]) for x in onlined[:8])))
    cands = dict((k, (v[0], v[1])) for k, v in still.items())
    deltas = dict((k, (v[2], v[3])) for k, v in still.items())
    print("按字节确有未落地差的候选 %d 枚" % len(cands))
    print("同族只取最新一代、补 fetch 并重测落地状态后剩 %d 枚（折叠旧代 %d 枚）" % (len(cands), dropped))

    info = {}
    for name, (head, blk) in cands.items():
        rc2, mb = sh(["git", "merge-base", tip, head])
        if rc2:
            continue
        rc3, fl = sh(["git", "diff", "--name-only", "%s..%s" % (mb, head)])
        bm, lm = tree_map(mb), tree_map(head)
        changed = {}
        for f in [x for x in fl.split("\n") if x.strip()]:
            b, l = bm.get(f, ""), lm.get(f, "")
            if l != b:
                changed[f] = l
        info[name] = (head, blk, changed)
        # 名字不许截断打印：10-05 16:2x 这块表被拿去给号令者点单，截断的枝名等于没给——
        # 他按截断名点就落错枝。列宽是好看，名单是可点，后者赢。
        print("  %s 头 %s 自报改动 %2d 枚" % (name, head[:12], len(changed)))

    pairs = []
    names = sorted(info)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            hits = []
            for f in set(info[a][2]) & set(info[b][2]):
                if info[a][2][f] != info[b][2][f]:
                    hits.append(f)
            if hits:
                pairs.append((a, b, hits))
    print("\n两两互斥（同一跳只能落一枚，另一枚必须再 rebase）：%d 对" % len(pairs))
    ordered = sorted(pairs, key=lambda x: -len(x[2]))
    for a, b, hits in ordered[:24]:
        # 枝名与撞的文件都不截断，也不指向一个本尺没有的 `--json` 形（那样打出来就是一句假路标）
        print("  %s × %s 共 %d 枚：%s" % (a, b, len(hits), ", ".join(sorted(hits))))
    if len(pairs) > 24:
        print("  !! 互斥对共 %d 对，这里只打前 24 对 ⇒ 这一页不是全量，别按它下结论" % len(pairs))
    if not pairs:
        print("  （没有互斥对 ⇒ 这一批可以同跳全落）")
    lonely = [n for n in names if not any(n in (p[0], p[1]) for p in pairs)]
    print("与谁都不同改的枝 %d 枚：%s" % (len(lonely), ", ".join(lonely)))
    print("边界：只读（ls-remote / merge-base / ls-tree / diff），0 次写、0 次落地、0 次动权威线。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
