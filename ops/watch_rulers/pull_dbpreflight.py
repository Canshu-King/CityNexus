import base64, hashlib, io, json, os, subprocess, urllib.request
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus-Workspace/contents/db_probe_preflight.py?ref=4f2fc3d0eff91ceb756d8b389cc0d7a413a2354e")
for k, v in {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "cmdr"}.items():
    req.add_header(k, v)
m = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
data = base64.b64decode(m["content"])
out = os.path.join(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks", "db_probe_preflight.py")
io.open(out, "wb").write(data)
print("preflight tool:", len(data), "B  byte-proof:", hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest() == m["sha"])
