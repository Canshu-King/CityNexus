#!/usr/bin/env python
"""cmdr_auto_wake_r1.py - detached auto-waker for the night shift.

Every WAKE_INTERVAL minutes it:
  1. scans all Qoder session jsonl files (this project dir) and computes each lane's silence;
  2. flags lanes silent > SILENCE_MIN minutes that are NOT quota-walled;
  3. appends one wake line per flagged lane to WAKE_LOG (the commander's cron/next window reads it
     and sends the knock), and writes a machine-readable snapshot to STATE_FILE.

It does NOT send messages itself (the MCP channel lives in the interactive window); it only
records who needs a knock.  Also applies pending ledger inbox blocks if the apply tool is idle
and a batch hasn't run in APPLY_EVERY minutes - guarded to run only when no other instance
holds the lock file.

Usage:  python cmdr_auto_wake_r1.py --once   (single pass, for testing)
        python cmdr_auto_wake_r1.py          (loop until STOP file appears)
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import re
import sys
import time

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
SELF = "494abfd7-5a79-4cc1-8487-e873818a2db3"
OUT_DIR = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
WAKE_LOG = os.path.join(OUT_DIR, "_auto_wake_log.txt")
STATE_FILE = os.path.join(OUT_DIR, "_auto_wake_state.json")
STOP_FILE = os.path.join(OUT_DIR, "_auto_wake_stop")
LOCK_FILE = os.path.join(OUT_DIR, "_auto_wake.lock")
INBOX = r"D:\moodle\_qoder_ledger_inbox"
LIVE = OUT_DIR

WAKE_INTERVAL = 20      # minutes between passes
SILENCE_MIN = 30        # silence that counts as stalled (not quota)
APPLY_EVERY = 15        # minutes between inbox-apply passes
QUOTA_RE = re.compile(r"daily usage limit|reached your daily|Come back tomorrow", re.I)


def parse_ts(v):
    if not v:
        return None
    s = str(v).strip()
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
    except Exception:
        return None


def lane_state(path):
    """Read the tail of one session jsonl; return (last_activity, quota_wall)."""
    last = None
    quota = False
    size = os.path.getsize(path)
    with io.open(path, "rb") as fh:
        start = max(0, size - 400_000)
        fh.seek(start)
        blob = fh.read().decode("utf-8", "replace")
    for line in blob.splitlines():
        if '"type":"assistant"' not in line and '"type":"user"' not in line \
           and '"type": "assistant"' not in line and '"type": "user"' not in line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        ts = parse_ts(o.get("timestamp"))
        if ts:
            last = ts
        t = o.get("type")
        if t == "assistant":
            m = o.get("message") or {}
            c = m.get("content")
            txt = ""
            if isinstance(c, str):
                txt = c
            elif isinstance(c, list):
                txt = "".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
            if txt and QUOTA_RE.search(txt):
                quota = True
    return last, quota


def scan():
    now = dt.datetime.now()
    rows = []
    for name in os.listdir(PROJ):
        if not name.endswith(".jsonl"):
            continue
        sid = name[:-6]
        if sid == SELF:
            continue
        p = os.path.join(PROJ, name)
        st = os.stat(p)
        age_h = (now - dt.datetime.fromtimestamp(st.st_mtime)).total_seconds() / 3600.0
        if age_h > 12:
            continue  # not part of tonight's shift
        last, quota = lane_state(p)
        silent = (now - last).total_seconds() / 60.0 if last else None
        rows.append({"id": sid[:8], "file": name, "last": last.isoformat() if last else None,
                     "silent_min": round(silent, 1) if silent is not None else None,
                     "quota": quota, "mtime": st.st_mtime})
    return rows


def inbox_count():
    n = 0
    for name in os.listdir(INBOX):
        if re.match(r"^[0-9a-f]{8}_[0-9]{4}\.md$", name) or name.startswith("cmdr_"):
            if name.endswith(".md"):
                n += 1
    return n


def run_apply():
    import subprocess
    env = dict(os.environ)
    env.pop("HTTP_PROXY", None)
    env.pop("HTTPS_PROXY", None)
    env["NO_PROXY"] = "*"
    env["no_proxy"] = "*"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        r = subprocess.run([sys.executable, os.path.join(LIVE, "ledger_inbox_apply_r2.py"), "--apply"],
                           cwd=LIVE, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900, env=env)
        return r.returncode, (r.stdout or "")[-400:]
    except Exception as e:
        return -1, "%s: %s" % (type(e).__name__, str(e)[:200])


def main() -> int:
    once = "--once" in sys.argv
    if not once and os.path.exists(LOCK_FILE):
        print("another instance holds", LOCK_FILE)
        return 0
    if not once:
        io.open(LOCK_FILE, "w").write(str(os.getpid()))

    last_apply = 0.0
    try:
        while True:
            if os.path.exists(STOP_FILE):
                print("stop file seen")
                break
            now = dt.datetime.now()
            rows = scan()
            wakes = [r for r in rows if r["silent_min"] is not None
                     and r["silent_min"] > SILENCE_MIN and not r["quota"]]
            state = {"at": now.isoformat(), "lanes": rows, "wakes": [w["id"] for w in wakes]}
            io.open(STATE_FILE, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False, indent=1))
            if wakes:
                with io.open(WAKE_LOG, "a", encoding="utf-8") as fh:
                    for w in wakes:
                        fh.write("%s WAKE %s silent=%.0fmin quota=%s\n" % (now.strftime("%H:%M:%S"), w["id"], w["silent_min"], w["quota"]))
            pend = inbox_count()
            if time.time() - last_apply > APPLY_EVERY * 60 and pend > 0:
                rc, tail = run_apply()
                last_apply = time.time()
                with io.open(WAKE_LOG, "a", encoding="utf-8") as fh:
                    fh.write("%s APPLY rc=%s pend=%d tail=%s\n" % (now.strftime("%H:%M:%S"), rc, pend, tail.replace("\n", " | ")[-200:]))
            if once:
                break
            time.sleep(WAKE_INTERVAL * 60)
    finally:
        if not once and os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    print("done; state at", STATE_FILE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
