# -*- coding: utf-8 -*-
"""交付脉搏：`refs/heads/review/*` 里最近 N 分钟新增/动过的枝，按枝名里出现的 ORD 号聚合。

只读远端（`ls-remote` + 本地 `for-each-ref`，先 fetch review 命名空间），0 次写、0 次 push。
用途：夜里每一条「车道在不在干活」都要有可回查的证据，而不是看进程或端口。
"""
import os
import re
import subprocess
import sys
import time

REPO = r"D:\moodle\CityNexus"
GIT = ["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy="]


def main():
    win = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    if "--no-fetch" not in sys.argv:
        subprocess.run(GIT + ["fetch", "--quiet", "origin",
                              "+refs/heads/review/*:refs/remotes/origin/review/*"],
                       capture_output=True, timeout=600)
    r = subprocess.run(GIT + ["for-each-ref", "--sort=-committerdate",
                              "--format=%(committerdate:unix)\t%(refname:short)\t%(objectname:short)\t%(subject)",
                              "refs/remotes/origin/review/*"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    now = time.time()
    rows = []
    for line in (r.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        try:
            ts = float(parts[0])
        except ValueError:
            continue
        if (now - ts) / 60.0 <= win:
            rows.append((time.strftime("%H:%M", time.localtime(ts)), parts[1], parts[2], parts[3][:70]))
    orders = []
    for _t, ref, _s, subj in rows:
        for m in re.findall(r"ord-?0?(\d{3})", ref.lower() + " " + subj.lower()):
            o = "ORD-0" + m
            if o not in orders:
                orders.append(o)
    print("PULSE %s 窗口 %s 分：新动过的 review 枝 %d 条，涉及单号 %s（共 %d 张）"
          % (time.strftime("%H:%M"), int(win), len(rows), "、".join(sorted(orders)) or "无", len(orders)))
    for t, ref, sha, subj in rows[:10]:
        print("   %s  %-52s %s  %s" % (t, ref.replace("origin/review/", ""), sha, subj))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
