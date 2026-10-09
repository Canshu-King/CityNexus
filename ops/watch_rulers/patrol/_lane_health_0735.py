import os, re, time, sys, json

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LANES = {
    "aad2d1f2": "aad2d1f2-4de9-406b-a5df-afa0e2bcea58",
    "d2305848": "d2305848-0281-4e92-9735-6ca66c065884",
    "c01d72a3": "c01d72a3-8bae-43d9-8491-5b300bd43797",
    "e345b9d6": "e345b9d6-c2a1-4ed2-8fd6-9c9099d57bd5",
    "8ccd71d8": "8ccd71d8-51d2-4f3f-a6b3-bfe7bc6a4510",
    "494abfd7": "494abfd7-5a79-4cc1-8487-e873818a2db3",
}
FAIL = '"status":"failed'
ASST = '"type":"assistant"'
ts_re = re.compile(r'"timestamp":"(2026-[^"]+)"')

out = []
for k, v in LANES.items():
    p = os.path.join(BASE, v + ".jsonl")
    st = os.stat(p)
    tail = min(st.st_size, 2_000_000)
    with open(p, "rb") as fh:
        fh.seek(max(0, st.st_size - tail))
        d = fh.read().decode("utf-8", "replace")
    lines = [l for l in d.split("\n") if ASST in l]
    last = lines[-1] if lines else ""
    m = ts_re.search(last)
    try:
        j = json.loads(d.rstrip().split("\n")[-1])
        lasttype = j.get("type")
        lastts = j.get("timestamp")
    except Exception:
        lasttype, lastts = "?", None
    out.append((k, st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)),
                d.count(FAIL), (m.group(1) if m else None), lasttype, lastts))
for r in out:
    sys.stdout.write(repr(r) + "\n")
