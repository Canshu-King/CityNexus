# -*- coding: utf-8 -*-
"""盘的清理池「够做决定」版：把候选目录一枚枚量大小 + 分「删得回不来不来」，落 JSON 与排名表。

为什么现在做（13:46）：值守自己给的盘读数是——近 2/4/6 小时斜率 1.04~1.47 GiB/小时，按斜率外推 2 GiB 档
落在 17:49—23:42 之间，正好压在今晚 23:00 那一档上。到时候再找人清就是临阵救灾；现在把
「哪些能清、多大、删了能不能拿回来」量清楚，交号令者一句话就能动手。

判据（三条，全只读）：
  ① 12 小时以上没动过 且 账本正文 0 引用  ⇒ 候选（沿用 `_reclaim_scan_r1.py` 的单遍正则口径）；
  ② 目录里有 `.git` 且出现在 `git worktree list` ⇒ 登记在册的工作树，**不能 rm**（会坏别人的线）；
  ③ 目录名里那枚 40 位/12 位 sha 能在 `D:/moodle/CityNexus` 里 `git cat-file -t` 得到 ⇒ 内容在 git 里，
     删了可用 `git archive <sha>` 原地重建（这是号令者 09-30 自己用过的路数）。
每条读数都带「怎么复算」；量不到大小的（du 超时）单列，不外推、不混进合计。
"""
import io
import json
import os
import re
import subprocess
import sys
import time

ROOT = r"D:\moodle"
LEDGER = os.path.join(ROOT, "CITYNEXUS_AGENT_CONTROL.md")
REPO = os.path.join(ROOT, "CityNexus")
HERE = os.path.dirname(os.path.abspath(__file__))
IDLE_H = float(os.environ.get("IDLE_H", "12"))
BUDGET = float(os.environ.get("BUDGET", "900"))
DU_TO = int(os.environ.get("DU_TO", "15"))
OUT_JSON = os.path.join(HERE, "_reclaim_sizes_latest.json")
OUT_TXT = os.path.join(HERE, "_reclaim_sizes_latest.txt")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="", http_proxy="", https_proxy="")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def log(s):
    io.open(OUT_TXT, "a", encoding="utf-8", newline="\n").write(
        time.strftime("[%H:%M:%S] ") + s + "\n")
    print(s)


def main():
    if os.path.exists(OUT_TXT):
        os.remove(OUT_TXT)
    now = time.time()
    led = io.open(LEDGER, encoding="utf-8", errors="replace", newline="").read()
    p = subprocess.run(("git", "-C", REPO, "worktree", "list"), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=120)
    wt = set()
    for l in (p.stdout or "").splitlines():
        d = l.split()[0] if l.split() else ""
        if d:
            wt.add(os.path.normpath(d).lower())
    tip = subprocess.run(("git", "-C", REPO, "ls-remote", "origin",
                          "refs/heads/mirror/integration-frontend-apple-pass1"),
                         capture_output=True, text=True, encoding="utf-8", errors="replace",
                         env=ENV, timeout=180).stdout.split()
    tipsha = tip[0] if tip and len(tip[0]) == 40 else ""

    dirs = [d for d in os.listdir(ROOT) if d.startswith("_qoder_") and os.path.isdir(os.path.join(ROOT, d))]
    cand = []
    for d in dirs:
        full = os.path.join(ROOT, d)
        if d == "_qoder_ledger_inbox" or d == "_qoder_cmdr_ref_20260921":
            continue                                    # 收件口与仪表树本身不算
        idle_h = (now - max(os.path.getmtime(full), os.path.getctime(full))) / 3600.0
        if idle_h < IDLE_H:
            continue
        if d in led:
            continue
        cand.append((d, idle_h))
    cand.sort(key=lambda x: -x[1])
    log("顶层 _qoder_* 共 %d 枚；闲置 >%.0f 小时且账本 0 引用 ⇒ 候选 %d 枚（worktree 登记 %d 条在册）" % (
        len(dirs), IDLE_H, len(cand), len(wt)))

    rows = []
    t0 = time.time()
    for i, (d, idle_h) in enumerate(cand):
        if time.time() - t0 > BUDGET:
            log("预算 %d 秒用完，还剩 %d 枚没量到（不外推、不猜）" % (BUDGET, len(cand) - i))
            break
        full = os.path.join(ROOT, d)
        has_git = os.path.exists(os.path.join(full, ".git"))
        registered = os.path.normpath(full.replace("\\", "/")).lower() in wt or \
            os.path.normpath(full).lower() in wt
        m = re.search(r"([0-9a-f]{40})", d) or re.search(r"([0-9a-f]{12})", d)
        sha = m.group(1) if m else ""
        blob = ""
        if sha:
            try:
                q = subprocess.run(("git", "-C", REPO, "cat-file", "-t", sha), capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", env=ENV, timeout=60)
                blob = (q.stdout or "").strip() if q.returncode == 0 else "取不到"
            except Exception:
                blob = "取不到"
        try:
            r = subprocess.run(["du", "-sk", full], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=DU_TO)
            mib = float(r.stdout.split()[0]) / 1024.0 if r.stdout and r.stdout.split() else None
        except Exception:
            mib = None
        if mib is None:
            verdict = "未量到（du 超时/读不到）"
        elif has_git and registered:
            verdict = "工作树登记在册 ⇒ 不能 rm"
        elif has_git:
            verdict = "自带 .git ⇒ 先问归属再动"
        elif blob and blob != "取不到":
            verdict = "可重建（名里 sha 在仓里取得到：%s）" % blob
        else:
            verdict = "未证明可重建 ⇒ 别自动清"
        rows.append({"dir": d, "idle_h": round(idle_h, 1), "mib": (round(mib, 1) if mib else None),
                     "has_git": has_git, "worktree": registered, "sha_in_name": sha, "cat_file": blob,
                     "verdict": verdict})
        if (i + 1) % 10 == 0:
            log("  进度 %d/%d，已用 %.0f 秒" % (i + 1, len(cand), time.time() - t0))

    tot = sum(r["mib"] for r in rows if r["mib"])
    ok = [r for r in rows if r["mib"] and r["verdict"].startswith(u"可重建")]
    reg = [r for r in rows if r["verdict"].endswith(u"不能 rm")]
    unk = [r for r in rows if r["mib"] and not r["verdict"].startswith(u"可重建") and u"不能 rm" not in r["verdict"]]
    tim = [r for r in rows if not r["mib"]]
    log("量到 %d 枚，合计 %.1f MiB；其中可重建 %d 枚 = %.1f MiB｜登记在册 %d 枚｜未证明可重建 %d 枚 = %.1f MiB｜未量到 %d 枚" % (
        len(rows) - len(tim), tot, len(ok), sum(r["mib"] for r in ok), len(reg), len(unk),
        sum(r["mib"] for r in unk), len(tim)))
    log("盘现值：余 %.1f MiB；尖 %s（worktree 判据取自它）" % (
        __import__("shutil").disk_usage("D:\\").free / 2 ** 20, tipsha or "取不到"))
    io.open(OUT_JSON, "w", encoding="utf-8", newline="\n").write(json.dumps(
        {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "idle_h_gt": IDLE_H, "tip": tipsha,
         "n_candidates": len(cand), "n_measured": len(rows) - len(tim),
         "rebuildable_mib": round(sum(r["mib"] for r in ok), 1),
         "unproven_mib": round(sum(r["mib"] for r in unk), 1),
         "timeout_n": len(tim), "rows": sorted(rows, key=lambda x: -(x["mib"] or 0))[:60]},
        ensure_ascii=False, indent=1))
    log("最大 12 枚：")
    for r in sorted([x for x in rows if x["mib"]], key=lambda x: -x["mib"])[:12]:
        log("   %-40s %8.1f MiB  闲置 %5.1f h  %s" % (r["dir"][:40], r["mib"], r["idle_h"], r["verdict"]))
    log("复算：python _reclaim_size_r1.py（IDLE_H/BUDGET/DU_TO 可用环境变量改）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
