"""One-shot shift check: is anyone stopped, and does the ledger point at someone who is not moving?

Prints, all computed live:
  * session census (quota_now's predicate): capped / producing / resting, with each resting lane's idle minutes;
  * the newest patrol round lines (door ruler, backlog classes, tip movement, candidate count);
  * whether a lane's transcript ends on an unanswered tool_use (the permission-prompt signature that stalled map
    for 50 minutes) - that is a different failure from being at rest, and it needs a human, not a knock;
  * genuine wake candidates (census/table blocks are suppressed by wake_from_commits' dispatch-marker guard).
"""
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ID8 = {"494abfd7": "号令者", "e4f3490f": "道0370", "4033270f": "道0383", "a68b0631": "rel",
       "3b65af59": "map", "904a042d": "Q", "8e5245f0": "道0369", "49fe0d7b": "N3",
       "9759f1ac": "N2", "1d64acf5": "S4", "be19052c": "道tokens", "bac10f40": "AI",
       "2d2d7428": "0388/0389"}


def dangling_tool(id8):
    g = sorted(glob.glob(os.path.join(BASE, id8 + "*.jsonl")), key=os.path.getmtime)
    if not g:
        return None
    p = g[-1]
    recs = []
    with io.open(p, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                recs.append(json.loads(s))
            except Exception:
                pass
    last_use = None
    for r in recs:
        m = r.get("message") or {}
        c = m.get("content")
        if m.get("role") == "assistant" and isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "tool_use":
                    last_use = {"name": x.get("name"), "input": x.get("input"), "ts": r.get("timestamp")}
        if m.get("role") == "user" and isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "tool_result" and last_use:
                    last_use = None
    if not last_use:
        return None
    age = (time.time() - os.path.getmtime(p)) / 60.0
    return {"tool": last_use["name"], "idle_min": round(age, 1),
            "input": json.dumps(last_use["input"], ensure_ascii=False)[:220]}


def main():
    q = subprocess.run([PY, os.path.join(HERE, "quota_now.py")], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=900)
    lines = (q.stdout or "").splitlines()
    m = re.search(r"掐着 (\d+) / 共 (\d+) 条会话", "\n".join(lines))
    print("[%s] census: 掐着=%s / 共=%s" % (time.strftime("%H:%M:%S"), m.group(1), m.group(2)))
    resting = []
    for l in lines:
        mm = re.match(r"\s+可动\s+(\S+)\s+([0-9a-f]{8})\s+idle\s+([0-9.]+) 分", l)
        if mm and float(mm.group(3)) >= 8:
            resting.append((mm.group(1), mm.group(2), float(mm.group(3))))
    print("  静待 >=8 分：%s" % (", ".join("%s(%s) %.0fm" % r for r in resting) or "无"))
    print("  静待 >=60 分：%s" % (", ".join("%s(%s) %.0fm" % r for r in resting if r[2] >= 60) or "无"))
    for nm, id8, mins in resting:
        d = dangling_tool(id8)
        if d:
            print("  !! %s(%s) 停在未应答的 tool_use=%s（%.1f 分无新记录）⇒ 这是等人点弹窗，不是等人敲门：cmd=%s"
                  % (nm, id8, d["tool"], d["idle_min"], d["input"][:140]))
    # 权限弹窗可以在车道还"很活跃"的时候出现（道0383 21:24 就是这样，才 13 分就被弹窗卡住），
    # 所以这道检查不能只跑在"静待 >=8 分"的名单上。逐条查全部会话，便宜到可以每轮都跑。
    for id8, nm in ID8.items():
        if nm in ("号令者",):
            continue
        if any(id8 == r[1] for r in resting):
            continue
        d = dangling_tool(id8)
        if d and d["idle_min"] >= 5:
            print("  !! %s(%s) 虽在静待名单之外，也停在未应答的 tool_use=%s（%.1f 分）：cmd=%s"
                  % (nm, id8, d["tool"], d["idle_min"], d["input"][:140]))
    rl = io.open(os.path.join(HERE, "round_watch.log"), encoding="utf-8", errors="replace").read()
    last = [s for s in rl.split("=====") if s.strip()][-1]
    keep = [l.strip() for l in last.splitlines()
            if re.search(r"尺=|积压分类|tip=|candidates=|_processed", l)]
    print("  最近一轮：" + " | ".join(keep[:6]))
    print("  轮数=%d  最新 tip=%s" % (len([s for s in rl.split("=====") if s.strip()]),
                                     (re.findall(r"tip=([0-9a-f]{12})", rl) or ["-"])[-1]))
    w = subprocess.run([PY, os.path.join(HERE, "wake_from_commits.py")], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=1800)
    cand = re.findall(r"candidates=(\d+)", w.stdout or "")
    print("  wake candidates=%s" % (cand[-1] if cand else "?"))
    d = json.loads(io.open(os.path.join(HERE, "wake_candidates.json"), encoding="utf-8").read())
    for c in d.get("candidates", []):
        print("    → %s(%s) idle %.1f 分  块头「%s」" % (c["lane"], c["id8"], c["idle_min"], c["head"][:70]))
    inbox = sorted(os.path.basename(x) for x in glob.glob(os.path.join(r"D:\moodle\_qoder_ledger_inbox", "*.md")))
    print("  收件根目录 %d 枚：%s" % (len(inbox), ", ".join(inbox)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
