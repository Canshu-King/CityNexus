# -*- coding: utf-8 -*-
"""tail_report.py — print the last assistant message of selected lane sessions.

Read-only. Usage:
  python -X utf8 tail_report.py            # all discovered lanes
  python -X utf8 tail_report.py N2 S4      # only whose display name contains these
"""
import glob
import io
import json
import os
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
import recover_watch as rw


def texts(msg):
    c = msg.get("content")
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text"))
    return c if isinstance(c, str) else ""


def main():
    want = [a for a in sys.argv[1:] if not a.startswith("-")]
    names = rw.discover(max_age_h=24.0)
    now = time.time()
    rows = []
    for p in sorted(glob.glob(os.path.join(BASE, "*.jsonl"))):
        key = os.path.basename(p)[:8]
        if key == rw.ME or key in rw.NON_PROJECT:
            continue
        nm = names.get(key, key)
        if want and not any(w.lower() in (nm + " " + key).lower() for w in want):
            continue
        idle = (now - os.stat(p).st_mtime) / 60.0
        last_role, last_txt, cap = None, "", False
        try:
            recs = io.open(p, encoding="utf-8", errors="replace").read().split(chr(10))
        except Exception as e:
            rows.append((nm, key, idle, "ERR " + str(e), cap))
            continue
        for rec in reversed(recs):
            rec = rec.strip()
            if not rec:
                continue
            try:
                d = json.loads(rec)
            except Exception:
                continue
            m = d.get("message") or {}
            role = m.get("role")
            if role not in ("assistant", "user"):
                continue
            t = texts(m)
            if role == "assistant" and not t.strip():
                continue
            last_role, last_txt = role, t
            break
        cap = "daily usage limit for Chat" in last_txt
        if last_role is None:
            shown = "(流水里没有 assistant/user 正文)"
        else:
            shown = "%s: %s" % (last_role, last_txt.replace(chr(10), " "))
        rows.append((nm, key, idle, shown[:264], cap))
    rows.sort(key=lambda r: -r[2])
    for nm, key, idle, t, cap in rows:
        print("[%s] %.0fm%s  %s" % (nm, idle, "  <== QUOTA" if cap else "", t))
        print("")
    print("共 %d 条会话" % len(rows))


main()
