# -*- coding: utf-8 -*-
"""task_board.py — read-only board: every lane's TASK (latest dispatch) vs its LAST self-report.

For each project session JSONL under the Qoder project dir:
  * all ORD-/REQ- ids that ever appear in user messages (their orders)
  * the latest user message timestamp + first 120 chars (the dispatch they last got)
  * the latest assistant message timestamp + first 200 chars (what they last said)
  * idle minutes from file mtime, and a QUOTA flag
Nothing is written. Usage: python -X utf8 task_board.py [max_idle_minutes]
"""
import glob
import io
import json
import os
import re
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
ME = "42d1a6fa"
NON_PROJECT = {"a6b95d59"}
ID_RE = re.compile(r"(?:ORD-\d{4}|REQ-\d{4}|ORD-[A-Z]\b)")
CAP = "daily usage limit for Chat"


def text_of(msg):
    c = msg.get("content")
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text"))
    return c if isinstance(c, str) else ""


def scan(path):
    orders, last_user, last_asst = set(), None, None
    n_user = 0
    for rec in io.open(path, encoding="utf-8", errors="replace").read().split(chr(10)):
        rec = rec.strip()
        if not rec:
            continue
        try:
            d = json.loads(rec)
        except Exception:
            continue
        m = d.get("message") or {}
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        t = text_of(m)
        if not t.strip():
            continue
        ts = d.get("timestamp") or ""
        if role == "user":
            n_user += 1
            orders.update(ID_RE.findall(t))
            if t.lstrip().startswith(("#", "<system", "【", "[", "【CMDR", "**")) or True:
                last_user = (ts, t.replace(chr(10), " "))
        else:
            last_asst = (ts, t.replace(chr(10), " "))
    return orders, last_user, last_asst, n_user


def main():
    max_idle = float(sys.argv[1]) if len(sys.argv) > 1 else 1e9
    now = time.time()
    rows = []
    for p in sorted(glob.glob(os.path.join(BASE, "*.jsonl"))):
        key = os.path.basename(p)[:8]
        if key == ME or key in NON_PROJECT:
            continue
        idle = (now - os.stat(p).st_mtime) / 60.0
        if idle > max_idle:
            continue
        orders, lu, la, nu = scan(p)
        rows.append((key, idle, sorted(orders), lu, la, nu))
    rows.sort(key=lambda r: r[1])
    for key, idle, orders, lu, la, nu in rows:
        print("=== %s   idle %.0f 分钟   指令 %d 条   单子: %s" % (key, idle, nu, " ".join(orders) or "(流水里没出现过 ORD 号)"))
        if lu:
            print("  最后收到的指令 @%s: %s" % (lu[0][:19], lu[1][:170]))
        if la:
            cap = "  <== QUOTA" if CAP in la[1] else ""
            print("  最后一次自报 @%s%s: %s" % (la[0][:19], cap, la[1][:200]))
        else:
            print("  最后一次自报: (没有 assistant 正文)")
        print("")
    print("共 %d 条 (idle<=%.0f 分钟)" % (len(rows), max_idle))


main()
