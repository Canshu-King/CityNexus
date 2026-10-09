# -*- coding: utf-8 -*-
"""值守 10:11 · 「推了枝但没申报」探测器（只读）。

10:08 我手跑一次就抓到两枚：车道 `bac10f40` 的 `AI-ord0430-pill-relocates-in-view-r2`（10:07 推）与
车道 `9759f1ac` 的 `Q-ord0446-machine-speech-residue-r2`（09:07 推）——两枚的 40 位在账本里 **0 命中**。
号令者 09:52 那块（账本 :16658）的规矩是原话：「**账本里没有申报块 ⇒ 未申报＝未交付**，我没复切、没落地、
也没判它不合格」。所以这一格不是洁癖：车道白干一轮，而且到点也不会上线。

判据只一条：**近 N 小时内动过的 `review/*` 枝，其头 40 位是否逐字出现在账本里**。
两个已知的不算数：
  ① `cmdr-*` 前缀的枝（batch / recut / int）是号令者自己的中间物，他会在下一块里一起申报，不当车道欠交；
  ② 命中只认**逐字 40 位**，不认 12 位短形（账本里短形到处是，会造出假「已申报」）。
"""
import io
import os
import re
import subprocess
import sys
import time

REPO = r"D:/moodle/CityNexus"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0


def sh(args, t=600):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=t)
    return ((p.stdout or "") + (p.stderr or "")).strip()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ls = sh(["git", "ls-remote", "origin", "refs/heads/review/*"]).split("\n")
    pairs = []
    for line in ls:
        if "\t" in line:
            s, r = line.split("\t", 1)
            if re.match(r"^[0-9a-f]{40}$", s.strip()):
                pairs.append((s.strip(), r.strip()))
    ledger = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    now = time.time()
    fresh, cmdr, undeclared, nosuch = [], [], [], []
    for s, r in pairs:
        out = sh(["git", "show", "-s", "--format=%ct", s])
        name = r.replace("refs/heads/review/", "")
        ct = out.split("\n")[0].strip()
        if not ct.isdigit():
            # 对象不在本地（别人推的枝我没 fetch 到）——这不能读成「没动过」，要单独计数
            nosuch.append((name, s))
            continue
        ts = int(ct)
        if now - ts > HOURS * 3600:
            continue
        rec = (ts, name, s, (s in ledger))
        if name.startswith(("cmdr-", "CMDR-")):
            cmdr.append(rec)
        else:
            fresh.append(rec)
            if not rec[3]:
                undeclared.append(rec)
    print("近 %.1f 小时动过的车道枝 %d 枚（号令者自己的 cmdr-* 中间物 %d 枚另计，不算欠交；"
          "本地取不到对象的 %d 枚**不算读数**，只报数）" % (HOURS, len(fresh), len(cmdr), len(nosuch)))
    for ts, name, s, has in sorted(fresh, reverse=True):
        print("  %s %-56s %s  账本逐字 40 位命中=%s"
              % (time.strftime("%H:%M", time.localtime(ts)), name[:56], s[:12], "是" if has else "**否**"))
    print("结论：**推了枝但账本里没有申报块的车道枝 %d 枚**" % len(undeclared))
    # 13:52 修的一处过报：同一族的旧代（`-r1` 被 `-r2` 取代）不该算「漏申报」——
    # 车道换了代次、申报跟的是最新那一代，旧代名留在远端是正常的。
    FAM = re.compile(r"^(.*?)(?:-r(\d+)|-(\d+))?$")
    newest = {}
    for ts, name, s, has in fresh:
        m = FAM.match(name.replace("review/", ""))
        n = int(m.group(2) or m.group(3) or 1)
        key = m.group(1)
        if key not in newest or n > newest[key][0]:
            newest[key] = (n, name, s, has)
    newest_names = set(x[1] for x in newest.values())
    stale = [x for x in undeclared if x[1] not in newest_names]
    undeclared2 = [x for x in undeclared if x[1] in newest_names]
    if stale:
        print("（另有 %d 枚是**同族旧代**，最新一代已申报或不缺，不算漏报：%s）"
              % (len(stale), ", ".join(x[1][:34] for x in stale[:6])))
    print("按族只取最新一代之后，**真正漏申报的车道枝 %d 枚**" % len(undeclared2))
    for ts, name, s, _ in sorted(undeclared2, reverse=True):
        print("   !! %s  头 %s" % (name, s))
    print("边界：只读（ls-remote / show -s / 读账本），0 次写、0 次插块、0 次落地。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
