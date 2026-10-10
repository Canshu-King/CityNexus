# -*- coding: utf-8 -*-
"""盘的「补集」清点：一次跑完、一次读数、帖里每个数都出自这同一遍（09-30 18:13 我发过一条把两遍读数混在一起的帖，这条是它的更正原件）。

只读：账本单遍正则计数 + 目录 mtime + 对候选逐枚 du（每枚硬超时 12 秒）。
不删、不改名。定义写死在这里，免得下次又混：
  在用的      = 12 小时内动过
  0 引用      = 目录名在账本正文里一次都没出现
  候选        = 0 引用 且 超过 24 小时没动过
"""
import io
import json
import os
import re
import subprocess
import sys
import time

ROOT = r"D:\moodle"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_reclaim_last.json")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

names = [d for d in os.listdir(ROOT) if d.startswith("_qoder_") and os.path.isdir(os.path.join(ROOT, d))]
led = io.open(LEDGER, encoding="utf-8", errors="replace").read()
pat = re.compile("|".join(re.escape(n) for n in names))
cit = {}
for m in pat.finditer(led):
    cit[m.group(0)] = cit.get(m.group(0), 0) + 1
now = time.time()
rows = [(n, (now - os.path.getmtime(os.path.join(ROOT, n))) / 3600.0, cit.get(n, 0)) for n in names]
res = {
    "at": time.strftime("%m-%d %H:%M:%S"),
    "dirs": len(rows),
    "in_use_12h": len([r for r in rows if r[1] <= 12.0]),
    "uncited_all": len([r for r in rows if r[2] == 0]),
    "candidates_24h": len([r for r in rows if r[2] == 0 and r[1] > 24.0]),
    "sample_n": 0, "sample_mib": 0.0, "sample_list": [], "du_timeout": [],
}
for n, h, c in sorted([r for r in rows if r[2] == 0 and r[1] > 24.0], key=lambda x: -x[1])[:10]:
    kb = None
    try:
        r = subprocess.run(["du", "-sk", os.path.join(ROOT, n)], capture_output=True, text=True,
                           timeout=12, encoding="utf-8", errors="replace")
        f = r.stdout.strip().split("\t")[0]
        kb = int(f) if f.isdigit() else None
    except Exception:
        kb = None
    if kb is None:
        res["du_timeout"].append(n)
    else:
        res["sample_n"] += 1
        res["sample_mib"] += kb / 1024.0
        res["sample_list"].append([n, round(kb / 1024.0, 1), round(h / 24.0, 1)])
df = subprocess.run(["df", "-k", "/d"], capture_output=True, text=True).stdout
res["free_mib"] = round(int(re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%", df).group(3)) / 1024.0, 1)
io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps(res, ensure_ascii=False))
