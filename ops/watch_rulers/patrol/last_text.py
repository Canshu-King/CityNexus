import json, os, sys, collections

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LANES = {"494abfd7": "包工头", "8ccd71d8": "F", "aad2d1f2": "HJ-P3",
         "e345b9d6": "D", "c01d72a3": "C", "d2305848": "E"}


def files(sid):
    out = []
    for fn in os.listdir(BASE):
        if fn.startswith(sid) and fn.endswith(".jsonl"):
            out.append(os.path.join(BASE, fn))
    return out


def rows(path, limit=400):
    data = open(path, "rb").read()
    lines = data.split(b"\n")
    lines = [l for l in lines if l.strip()]
    tail = lines[-limit:]
    res = []
    for l in tail:
        try:
            res.append(json.loads(l.decode("utf-8", "replace")))
        except Exception:
            pass
    return res


def text_of(r):
    m = r.get("message") or {}
    c = m.get("content")
    parts = []
    if isinstance(c, str):
        parts.append(c)
    elif isinstance(c, list):
        for b in c:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text":
                parts.append(b.get("text", ""))
            elif b.get("type") == "tool_use":
                parts.append("[tool_use " + str(b.get("name")) + "]")
            elif b.get("type") == "tool_result":
                parts.append("[tool_result]")
    return " ".join(parts).strip()


want = sys.argv[1:] or list(LANES)
for sid in want:
    name = LANES.get(sid, sid)
    fs = files(sid)
    if not fs:
        print("=== %s (%s) NO FILE" % (name, sid))
        continue
    path = max(fs, key=os.path.getmtime)
    rs = rows(path)
    a = [r for r in rs if (r.get("message") or {}).get("role") == "assistant" and text_of(r)]
    u = [r for r in rs if (r.get("message") or {}).get("role") == "user" and text_of(r)]
    print("=== %s (%s) turns=%d" % (name, sid[:8], len(rs)))
    if u:
        print("  last USER : " + text_of(u[-1])[:300].replace("\n", " / "))
    if a:
        print("  last ASSIST: " + text_of(a[-1])[:700].replace("\n", " / "))
    print()
