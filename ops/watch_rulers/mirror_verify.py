"""Verify the ledger mirror by the blob API (the contents API omits `content` above ~1 MB)."""
import base64, hashlib, io, json, urllib.request
TOKEN = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
HDRS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
        "User-Agent": "citynexus-commander"}
def get(path, raw=False):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in HDRS.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read() if raw else json.loads(r.read().decode())
local = io.open(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md", "rb").read()
meta = get("/repos/Canshu-King/CityNexus/contents/CITYNEXUS_AGENT_CONTROL.md?ref=commander/control")
print("remote size field:", meta.get("size"), "| content inlined:", bool(meta.get("content")))
blob = get("/repos/Canshu-King/CityNexus/git/blobs/" + meta["sha"])
data = base64.b64decode(blob["content"]) if blob.get("content") else b""
print("blob bytes", len(data), "encoding", blob.get("encoding"))
print("local  bytes", len(local), "sha256", hashlib.sha256(local).hexdigest()[:12])
print("remote sha256", hashlib.sha256(data).hexdigest()[:12])
print("BYTE-IDENTICAL:", data == local)
