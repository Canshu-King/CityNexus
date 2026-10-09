import base64, hashlib, io, json, os, urllib.request
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus-Workspace/contents/ORD_0192_REPRODUCTION_PROTOCOL.md?ref=cab91a255e98d202e7bb34bc01eb651c21ba35d5")
for k, v in {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "cmdr"}.items():
    req.add_header(k, v)
m = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
data = base64.b64decode(m["content"])
out = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\ORD_0192_REPRODUCTION_PROTOCOL.md"
io.open(out, "wb").write(data)
print("protocol:", len(data), "B  byte-proof:", hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest() == m["sha"])
