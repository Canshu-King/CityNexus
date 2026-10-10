import base64, hashlib, io, json, os, urllib.request
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
OUT = r"D:\moodle\_qoder_cmdr_ref_20260921\workspace_docs"
req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus-Workspace/contents/docs/REVOLUTION_LAB_FIRST_SHIFT.md?ref=arbiter/revolution-lab")
for k, v in {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "cmdr"}.items():
    req.add_header(k, v)
m = json.loads(urllib.request.urlopen(req, timeout=90).read().decode())
data = base64.b64decode(m["content"])
io.open(os.path.join(OUT, "REVOLUTION_LAB_FIRST_SHIFT.md"), "wb").write(data)
ok = hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest() == m["sha"]
print("REVOLUTION_LAB_FIRST_SHIFT.md ->", len(data), "B  blob=", m["sha"][:10], " byte-proof=", ok)
print(data.decode("utf-8", "replace")[:600])
