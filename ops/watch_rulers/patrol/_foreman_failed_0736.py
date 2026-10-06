import os, re, time, sys, json

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
P = os.path.join(BASE, "494abfd7-5a79-4cc1-8487-e873818a2db3.jsonl")
st = os.stat(P)
now = time.time()
print("size", st.st_size, "mtime", time.strftime("%H:%M:%S", time.localtime(st.st_mtime)),
      "age_s", round(now - st.st_mtime, 1), "local_now", time.strftime("%H:%M:%S", time.localtime(now)))

tail = min(st.st_size, 6_000_000)
with open(P, "rb") as fh:
    fh.seek(max(0, st.st_size - tail))
    d = fh.read().decode("utf-8", "replace")

ts_re = re.compile(r'"timestamp":"(2026-[^"]+)"')
for i, l in enumerate(d.split("\n")):
    if '"status":"failed' not in l:
        continue
    try:
        j = json.loads(l)
    except Exception:
        print("unparsable line with failed, len", len(l)); continue
    t = j.get("type")
    msg = j.get("message") or {}
    content = msg.get("content") if isinstance(msg, dict) else None
    kinds = []
    txtlen = 0
    if isinstance(content, list):
        for c in content:
            kinds.append(c.get("type"))
            if c.get("type") == "text":
                txtlen += len(c.get("text") or "")
            if c.get("type") == "tool_result":
                s = json.dumps(c.get("content"), ensure_ascii=False)
                idx = s.find('"status":"failed')
                kinds.append("tr:" + (s[max(0, idx-90):idx+60] if idx >= 0 else "nofail"))
    sys.stdout.write(repr((j.get("timestamp"), t, kinds[:4], txtlen)) + "\n")
