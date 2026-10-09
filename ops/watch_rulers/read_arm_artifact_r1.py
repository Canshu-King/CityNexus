"""Read-only: pull F's strict-boot arm artifact by its 40-hex blob and print the REAL key names.

Why: I was about to write a field name into the ledger that I did not reproduce from the artifact.
The Q43 gate refused it, which is exactly the job that gate has. This script exists so the citation
comes out of the bytes rather than out of my memory.

It prints: top-level keys, the arm array's own key names, and per-arm the fields I intend to quote.
Nothing here writes anything anywhere.
"""
import base64
import hashlib
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
HDRS = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
        "User-Agent": "cnx-cmdr-reader", "X-GitHub-Api-Version": "2022-11-28"}

def mask(s):
    """Never print a credential value, even if a lane's artifact accidentally holds one.

    Anything that looks like a long high-entropy run (>=16 of [A-Za-z0-9_\\-.]) is replaced by its
    length + sha1 fingerprint, which is the same shape the gate itself is required to report.
    """
    import re
    return re.sub(r"[A-Za-z0-9_\-]{16,}",
                  lambda m: "MASKED(len=%d fp=%s)" % (len(m.group()), hashlib.sha1(m.group().encode()).hexdigest()[:10]),
                  s)


def show(v, lim=160):
    s = json.dumps(v, ensure_ascii=False)
    s = mask(s)
    return s if len(s) <= lim else s[:lim - 3] + "..."


WANT = sys.argv[1] if len(sys.argv) > 1 else "13272a0639d58b47a35e75739e738338ffeaed8b"
PATH = sys.argv[2] if len(sys.argv) > 2 else "evidence/ord0307-credential-literals-f/ord0307_strict_boot_arm_r1.json"

req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/" + WANT)
for k, v in HDRS.items():
    req.add_header(k, v)
with urllib.request.urlopen(req, timeout=180) as r:
    obj = json.loads(r.read().decode())
raw = base64.b64decode(obj["content"])
got = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
print("path=%s" % PATH)
print("bytes=%d requested_sha=%s recomputed=%s MATCH=%s" % (len(raw), WANT, got, got == WANT))
d = json.loads(raw.decode("utf-8"))
print("\n--- top-level keys (%d) ---" % len(d))
for k in d:
    v = d[k]
    t = type(v).__name__
    print("  %-42s %-6s %s" % (k, t, show(v, 200)))
arms = d.get("arms")
if isinstance(arms, list) and arms:
    keys = []
    for a in arms:
        for k in a:
            if k not in keys:
                keys.append(k)
    print("\n--- arms[*] key union (%d) ---" % len(keys))
    print("  " + ", ".join(keys))
    print("\n--- arms, quoted field by field ---")
    for a in arms:
        print("  arm=%r" % a.get("arm"))
        for k, v in a.items():
            if k == "arm":
                continue
            print("     %-34s %s" % (k, show(v, 240)))
