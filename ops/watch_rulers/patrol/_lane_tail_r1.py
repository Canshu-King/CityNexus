# -*- coding: utf-8 -*-
"""Tail liveness for the id prefixes given on argv: last record shape + minutes silent.

Reads only the transcript jsonl files (no processes, no ports). Prints the last
assistant text verbatim (truncated) so 'stopped mid-tool' can be told from
'stopped after a sentence' -- the first is worth a knock, the second usually
means the lane is waiting on a ruling it does not have yet.
"""
import glob
import io
import json
import os
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
now = time.time()
for pre in sys.argv[1:]:
    hits = sorted(glob.glob(os.path.join(BASE, pre + "*.jsonl")))
    if not hits:
        print("%-9s NO TRANSCRIPT FILE (name it from the jsonl list, not a title)" % pre)
        continue
    f = max(hits, key=os.path.getmtime)
    last_role = last_kind = None
    texts = []
    n = 0
    with io.open(f, encoding="utf-8", errors="replace") as h:
        for line in h:
            try:
                r = json.loads(line)
            except Exception:
                continue
            n += 1
            m = r.get("message") or {}
            role = m.get("role") or r.get("role")
            if role:
                last_role = role
            c = m.get("content")
            kinds = []
            if isinstance(c, str):
                kinds = ["text"]
                texts = [c]
            elif isinstance(c, list):
                for b in c:
                    if isinstance(b, dict):
                        kinds.append(b.get("type"))
                        if b.get("type") == "text":
                            texts = [b.get("text", "")]
            if kinds:
                last_kind = ",".join([k for k in kinds if k] or ["?"])
    age = (now - os.path.getmtime(f)) / 60.0
    cap = bool(texts) and "daily usage limit" in texts[-1].lower()
    print("%-9s recs=%-5d role=%-9s kinds=%-18s silent=%5.1f min  capped=%s" % (
        pre, n, last_role, (last_kind or "?")[:18], age, "YES" if cap else "no"))
    if texts:
        print("           last text: %s" % texts[-1].strip().replace("\n", " ")[:230])
