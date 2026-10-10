import base64, hashlib, io, json, os, urllib.request
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus-Workspace/contents/ledger_write_preflight.py?ref=620c8e6057d3f35e92da60efa87638f54edf9520")
for k, v in {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "cmdr"}.items():
    req.add_header(k, v)
m = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
data = base64.b64decode(m["content"])
out = os.path.join(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks", "ledger_write_preflight.py")
io.open(out, "wb").write(data)
ok = hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest() == m["sha"]
print("pulled", len(data), "B  byte-proof:", ok)
import re
print("public functions:", re.findall(r"^def (\w+)", data.decode("utf-8", "replace"), re.M))
