#!/usr/bin/env python
"""Read-only lane scanner.

For every Qoder session jsonl in the project dir, report:
  last_user_ts, last_assistant_ts, silent_minutes, cwd (lane identity), tail text.

No writes anywhere.  Usage:
    python _cmdr_lane_scan_r2.py [--top N] [--json out.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import sys

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
SELF_ID = "494abfd7-5a79-4cc1-8487-e873818a2db3"

QUOTA_RE = re.compile(r"daily usage limit|reached your daily|Come back tomorrow", re.I)


def parse_ts(v):
    if not v:
        return None
    if isinstance(v, (int, float)):
        try:
            return dt.datetime.fromtimestamp(float(v) / 1000.0)
        except Exception:
            return None
    s = str(v).strip()
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
    except Exception:
        return None


def text_of(msg):
    if not isinstance(msg, dict):
        return ""
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for it in c:
            if isinstance(it, dict) and it.get("type") == "text":
                parts.append(it.get("text") or "")
        return "\n".join(parts)
    return ""


def scan(path):
    last_u = last_a = None
    cwd = ""
    tail_a = ""
    quota = False
    n_assist = 0
    try:
        with io.open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"type": "assistant"' not in line and '"type": "user"' not in line and '"cwd"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                t = o.get("type")
                if t == "assistant":
                    ts = parse_ts(o.get("timestamp"))
                    if ts:
                        last_a = ts
                        n_assist += 1
                    txt = text_of(o.get("message"))
                    if txt:
                        tail_a = txt
                        if QUOTA_RE.search(txt):
                            quota = True
                elif t == "user":
                    ts = parse_ts(o.get("timestamp"))
                    if ts:
                        last_u = ts
                    if not cwd and o.get("cwd"):
                        cwd = o["cwd"]
                elif o.get("cwd") and not cwd:
                    cwd = o["cwd"]
    except OSError as e:
        return {"id": os.path.basename(path), "error": str(e)}
    return {
        "id": os.path.basename(path).replace(".jsonl", ""),
        "last_user": last_u,
        "last_assistant": last_a,
        "cwd": cwd,
        "assist_turns": n_assist,
        "quota_hit": quota,
        "tail": tail_a[-400:],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--json")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    now = dt.datetime.now()
    rows = []
    for name in os.listdir(PROJ):
        if not name.endswith(".jsonl"):
            continue
        p = os.path.join(PROJ, name)
        st = os.stat(p)
        age_min = (now - dt.datetime.fromtimestamp(st.st_mtime)).total_seconds() / 60.0
        if not args.all and age_min > 24 * 60:
            continue
        r = scan(p)
        r["mtime"] = dt.datetime.fromtimestamp(st.st_mtime)
        r["size"] = st.st_size
        rows.append(r)

    rows.sort(key=lambda r: r.get("mtime") or dt.datetime.min, reverse=True)
    out = []
    for r in rows[: args.top]:
        lu = r.get("last_user")
        la = r.get("last_assistant")
        sil = ""
        if la:
            sil = f"{(now - la).total_seconds() / 60.0:.0f}m"
        cwd = (r.get("cwd") or "")[-58:]
        selfmark = " <SELF>" if r["id"] == SELF_ID else ""
        print(f"{r['id'][:8]} mtime={r['mtime']:%H:%M} size={r['size']//1024}K u={lu:%H:%M:%S} a={la:%H:%M:%S} silent={sil} quota={r.get('quota_hit')}{selfmark}")
        print(f"    cwd={cwd}")
        print(f"    tail={r.get('tail','').replace(chr(10),' | ')[:300]}")
        out.append(r)

    if args.json:
        with io.open(args.json, "w", encoding="utf-8") as fh:
            json.dump(
                [
                    {
                        **{k: (v.isoformat() if isinstance(v, dt.datetime) else v) for k, v in r.items()},
                    }
                    for r in out
                ],
                fh,
                ensure_ascii=False,
                indent=1,
            )
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
