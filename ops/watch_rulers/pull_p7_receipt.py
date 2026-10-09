import base64, hashlib, io, json, urllib.request
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus-Workspace/contents/P7_RESOLVER_BEHAVIOR_RECEIPT.md?ref=aea25cc85669aef82325635ebba93f8093174a53")
for k, v in {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "cmdr"}.items():
    req.add_header(k, v)
m = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
data = base64.b64decode(m["content"])
io.open(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\P7_RESOLVER_BEHAVIOR_RECEIPT.md", "wb").write(data)
print("P7 receipt template:", len(data), "B  byte-proof:", hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest() == m["sha"])
print(data.decode("utf-8", "replace")[:700])
