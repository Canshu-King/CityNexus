"""Who put a Q43-RED block into the ledger at 19:24, and is it really there?

Three readings, all read-only:
  1) the ruler's own verdict on the two rel blocks that moved to _processed at 19:24;
  2) whether their exact headings occur in the local ledger file, and at which line;
  3) the authoritative branch tip and its last commits (author/date/subject) read from origin via REST,
     because the local branch ref can lag and a bare sha pins nothing.
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
import ghnet

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
PROC = r"D:\moodle\_qoder_ledger_inbox\_processed"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
HDR = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
       "User-Agent": "cnx-patrol-readonly", "X-GitHub-Api-Version": "2022-11-28"}


def ruler(path):
    r = subprocess.run([PY, "claim_coordinate_check_r4e.py", "--text", path, "--expect-clean"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=LC, timeout=600)
    out = (r.stdout or "").strip().splitlines()
    findings = [l for l in out if l.strip().startswith("line ")]
    m = re.search(r"overall (\S+)", " ".join(out))
    return r.returncode, (m.group(1) if m else "?"), findings, out


def api(path):
    req = urllib.request.Request("https://api.github.com" + path)
    st, raw = ghnet.urlopen(req, timeout=45, headers=HDR)
    return st, json.loads(raw.decode("utf-8"))


for n in ("rel_0338.md.inserted_192412", "rel_0437.md.inserted_192417", "Q_1935.md.inserted_192346"):
    p = os.path.join(PROC, n)
    if not os.path.exists(p):
        print("MISSING", n)
        continue
    rc, overall, findings, out = ruler(p)
    print("%-32s rc=%d overall=%s findings=%d  mtime=%s" % (
        n, rc, overall, len(findings), time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(p)))))
    for l in findings[:4]:
        print("      %s" % l.strip()[:140])

led = io.open(LEDGER, encoding="utf-8", errors="replace").read()
lines = led.splitlines()
print("\nlocal ledger: %d B  mtime=%s  lines=%d" % (
    os.path.getsize(LEDGER), time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(LEDGER))), len(lines)))
for n in ("rel_0338.md.inserted_192412", "rel_0437.md.inserted_192417"):
    head = io.open(os.path.join(PROC, n), encoding="utf-8").read().splitlines()[0]
    hits = [i + 1 for i, l in enumerate(lines) if l.strip() == head.strip()]
    print("  heading %-64s occurrences_in_local_ledger=%d %s" % (head[:60], len(hits), hits[:4]))

st, tip = api("/repos/Canshu-King/CityNexus/git/ref/heads/commander/control")
sha = None
if st == 200:
    sha = tip["object"]["sha"]
    st, c = api("/repos/Canshu-King/CityNexus/git/commits/" + sha)
    print("\norigin commander/control tip=%s  %s | %s" % (
        sha[:12], c["author"]["date"], c["message"].splitlines()[0][:80]))
    st, hist = api("/repos/Canshu-King/CityNexus/commits?sha=%s&per_page=6" % sha)
    for cc in (hist.get("items", []) if st == 200 else []):
        print("   %s  %-18s %s  %s" % (cc["sha"][:10], (cc.get("author") or {}).get("login") or "-",
                                       cc["commit"]["author"]["date"], cc["commit"]["message"].splitlines()[0][:64]))
else:
    print("origin ref read failed st=%d (local-only evidence below)" % st)
print("at %s" % time.strftime("%H:%M:%S"))
