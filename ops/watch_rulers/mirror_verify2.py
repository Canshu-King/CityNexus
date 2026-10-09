"""Blob readback with retries: the big-file response link-resets mid-body (seen before)."""
import base64, hashlib, io, json, time, urllib.request
TOKEN = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
def get(url, accept):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "citynexus-commander")
    with urllib.request.urlopen(req, timeout=240) as r:
        return r.read()
local = io.open(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md", "rb").read()
meta = json.loads(get("https://api.github.com/repos/Canshu-King/CityNexus/contents/CITYNEXUS_AGENT_CONTROL.md?ref=commander/control",
                      "application/vnd.github+json"))
best = None
for attempt in range(1, 6):
    try:
        data = get("https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/" + meta["sha"],
                   "application/vnd.github.raw")
    except Exception as e:  # noqa: BLE001
        print("attempt", attempt, type(e).__name__, getattr(e, "partial", None) and "partial" or "")
        time.sleep(2)
        continue
    print("attempt", attempt, "got bytes", len(data))
    if len(data) == len(local):
        best = data
        break
    time.sleep(2)
if best is None:
    print("readback incomplete after retries; remote size field =", meta.get("size"), "local =", len(local))
    raise SystemExit(1)
print("local  sha256", hashlib.sha256(local).hexdigest()[:16])
print("remote sha256", hashlib.sha256(best).hexdigest()[:16])
print("BYTE-IDENTICAL:", best == local)
