# -*- coding: utf-8 -*-
"""Print the last few records of a session transcript: role, kind, time, snippet."""
import io, json, os, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
for sid in sys.argv[1:]:
    g = [f for f in os.listdir(PROJ) if f.startswith(sid) and f.endswith(".jsonl")]
    if not g:
        print("== %s : no transcript" % sid); continue
    p = os.path.join(PROJ, sorted(g)[0])
    recs = []
    with io.open(p, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: recs.append(json.loads(line))
            except Exception: pass
    print("== %s  记录 %d 枚  mtime %s" % (sid, len(recs), time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(p)))))
    for r in recs[-4:]:
        role = r.get("role") or r.get("type")
        kinds = []
        txt = ""
        c = r.get("content")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict):
                    kinds.append(b.get("type"))
                    if b.get("type") == "text": txt += (b.get("text") or "")
        elif isinstance(c, str):
            kinds.append("str"); txt = c
        ts = r.get("timestamp") or r.get("created_at") or ""
        print("   - %s | %s | %s | %s" % (str(ts)[:19], role, ",".join(kinds), txt[:220].replace("\n", " ")))
