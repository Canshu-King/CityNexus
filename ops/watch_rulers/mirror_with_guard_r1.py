"""Pre-mirror guard: refuse to overwrite the shared ledger unless the remote holds nothing I lack.

Why: mirror_ledger.py PUTs the whole local file. That is only safe while local is a strict superset of
remote.  A lane can write between my last read and the PUT, and then a mirror silently destroys their
block - the single worst failure mode available to me on this project.  So the check and the mirror run
back to back in one process, and the check is done through the git blobs route (the contents route
returns an empty body at 5.7 MB, which once produced a false "the ledger has no ORD-0310" reading).
"""
import base64
import hashlib
import io
import json
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "cmdr-premirror-guard"}
D = "Canshu-King/CityNexus"
LOCAL = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"


def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=240).read())


m = get("https://api.github.com/repos/%s/contents/CITYNEXUS_AGENT_CONTROL.md?ref=commander%%2Fcontrol" % D)
raw = base64.b64decode(get("https://api.github.com/repos/%s/git/blobs/%s" % (D, m["sha"]))["content"])
loc = io.open(LOCAL, "rb").read()
R = set(raw.decode("utf-8", "replace").splitlines())
L = set(loc.decode("utf-8", "replace").splitlines())
only_r = [x for x in raw.decode("utf-8", "replace").splitlines() if x not in L]
print("remote blob", m["sha"], len(raw), "B | local blob",
      hashlib.sha1(b"blob %d\x00" % len(loc) + loc).hexdigest(), len(loc), "B")
print("remote-only lines:", len(only_r), "| local-only lines:", len([x for x in loc.decode('utf-8','replace').splitlines() if x not in R]))
for x in only_r[:10]:
    print("  R|", x[:160])
if only_r:
    print("ABORT: remote carries lines this file does not - merge first, never mirror over them")
    raise SystemExit(5)
msg = sys.argv[1] if len(sys.argv) > 1 else "commander: ledger mirror (CMDR-0925-1758 + ORD-0312)"
p = subprocess.run([sys.executable, "mirror_ledger.py", msg], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(p.stdout[-2200:])
if p.returncode:
    print("MIRROR RC", p.returncode, p.stderr[-400:])
raise SystemExit(p.returncode)
