import base64, hashlib, io, json, os, urllib.request
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
OUT = r"D:\moodle\_qoder_cmdr_ref_20260921\workspace_docs"
def get(path):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "cmdr"}.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=90) as x:
            return x.status, json.loads(x.read().decode())
    except Exception as e:
        return type(e).__name__, str(e)[:140]
os.makedirs(OUT, exist_ok=True)
st, b = get("/repos/Canshu-King/CityNexus-Workspace/branches/arbiter/revolution-lab")
print("Workspace branch arbiter/revolution-lab ->", st, (b["commit"]["sha"][:9] if st == 200 else b))
for f in ("docs/REVOLUTION_LAB_CHARTER.md", "docs/REVOLUTION_LAB_AUTONOMY_PROFILE.md"):
    st, m = get("/repos/Canshu-King/CityNexus-Workspace/contents/" + f + "?ref=arbiter/revolution-lab")
    if st != 200:
        print("  ", f, "->", st, str(m)[:80]); continue
    data = base64.b64decode(m["content"])
    name = f.split("/")[-1]
    io.open(os.path.join(OUT, name), "wb").write(data)
    ok = hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest() == m["sha"]
    print("  ", name, "->", len(data), "B  blob=", m["sha"][:10], " byte-proof=", ok)
