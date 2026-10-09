# -*- coding: utf-8 -*-
"""值守 07:12 现场汇总：睡到下一轮之后一次性把六件读数打出来（只读，不发消息、不写账本、不删）。

用法：python _watch_dump_0712.py [秒数]
"""
import io
import os
import json
import glob
import time
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = sys.executable
INBOX = r"D:/moodle/_qoder_ledger_inbox"
LEDGER = r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
PROJ = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"
GATE = "^[A-Za-z0-9._-]+_[0-9]{4}\\.md$"
CL = io.open(os.path.join(LC, "CLOSING_LINE.txt"), encoding="utf-8").read().strip()


def sh(args, timeout=600, cwd=None):
    env = dict(os.environ)
    env["HTTPS_PROXY"] = ""
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, cwd=(cwd or HERE), env=env)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return "ERR %s: %s\n" % (type(e).__name__, e)


def main():
    wait = int(sys.argv[1]) if len(sys.argv) > 1 else 330
    time.sleep(wait)
    print("=== 值守现场 %s（睡了 %d 秒）===" % (time.strftime("%H:%M:%S"), wait))

    print("\n[1] 自动轮 last 14")
    for l in io.open(os.path.join(HERE, "autumn_watch.log"), encoding="utf-8",
                     errors="replace").read().rstrip().split("\n")[-14:]:
        print("   " + l[:200])

    print("\n[2] 两道闸的只读复算")
    print(sh([PY, os.path.join(HERE, "bolt_replica.py")])[-900:])

    print("\n[3] 收件箱（按命名门 %s）" % GATE)
    now = time.time()
    for p in sorted(glob.glob(os.path.join(INBOX, "*.md"))):
        print("   %-28s %7d B  %.1f min" % (os.path.basename(p), os.path.getsize(p),
                                            (now - os.path.getmtime(p)) / 60.0))

    print("\n[4] 账本")
    print("   %d B  mtime=%s（%.1f 分钟前）" % (os.path.getsize(LEDGER),
           time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(LEDGER))),
           (time.time() - os.path.getmtime(LEDGER)) / 60.0))
    t = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    for k in ("ai_0652", "map_0716", "newlane_0637", "dt_0705", "dt_07"):
        print("   字样 %-14s 命中 %d 次" % (k, t.count(k)))

    print("\n[5] 权威线（只读 ls-remote）")
    print(sh(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin",
              "refs/heads/mirror/integration-frontend-apple-pass1"], 180,
             cwd=r"D:/moodle/CityNexus").strip())

    print("\n[6] 我敲过的三条车道最后在说什么")
    for sid in ("1ba48dbf", "1d64acf5", "be19052c"):
        p = glob.glob(os.path.join(PROJ, sid + "*.jsonl"))
        if not p:
            print("   %s 流水读不到" % sid)
            continue
        last = None
        for line in io.open(p[0], encoding="utf-8", errors="replace"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            m = r.get("message") or {}
            if m.get("role") != "assistant":
                continue
            c = m.get("content")
            if isinstance(c, list):
                txt = " ".join(b.get("text", "") for b in c
                               if isinstance(b, dict) and b.get("type") == "text")
            else:
                txt = c if isinstance(c, str) else ""
            if txt.strip():
                last = txt
        print("   %s: %s" % (sid, (last or "(还没有助手文本)").replace("\n", " ")[:300]))

    print("\n[7] 盘")
    print(sh(["df", "-B", "1G", "C:", "D:", "E:"])[:400])


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    raise SystemExit(main())
