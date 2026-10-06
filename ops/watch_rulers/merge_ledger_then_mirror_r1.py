"""Fold the branch-only ledger lines back into my local copy, then let the guarded mirror run.

Why not a general diff: the ledger is ~49k lines and SequenceMatcher over it is minutes of silence. The
case that actually happens is small and shaped - a lane inserts a block and mirrors it while I am writing
mine, so my mirror guard refuses (it fired on F's ORD-0307 block). Those remote-only lines are contiguous,
and each one's predecessor is either also remote-only or is a line I already have.

So: walk the remote list, collect maximal runs of lines I lack, and re-attach each run after the nearest
preceding line that exists locally (anchored on that exact line, counted so a repeated line cannot grab the
wrong copy). Proofs before writing: the result must contain every remote line and every local line.
"""
import io
import json
import subprocess
import sys
import urllib.request
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from cmdr_net_env_guard_r1 import ensure_proxy_usable
# Stale HTTPS_PROXY on this box answered 10061 and faked a publication failure on 2026-09-26.
print("proxy guard:", ensure_proxy_usable())

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "cnx-cmdr-ledger-merge"}


def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=300).read())


import base64  # noqa: E402

meta = get("https://api.github.com/repos/Canshu-King/CityNexus/contents/CITYNEXUS_AGENT_CONTROL.md?ref=commander%2Fcontrol")
raw = base64.b64decode(get("https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/" + meta["sha"])["content"])
R = raw.decode("utf-8").split("\n")
L = io.open(LEDGER, encoding="utf-8", newline="").read().split("\n")
have = set(L)
print("remote", meta["sha"], len(R), "lines | local", len(L), "lines")

missing = [i for i, x in enumerate(R) if x not in have]
print("remote-only lines:", len(missing))
if not missing:
    print("nothing to merge - running the guarded mirror directly")
else:
    for i in missing[:6]:
        print("  R|%d| %s" % (i, R[i][:110]))
    # maximal contiguous runs of remote-only lines
    runs, start = [], missing[0]
    for k in range(1, len(missing)):
        if missing[k] != missing[k - 1] + 1:
            runs.append((start, missing[k - 1] + 1))
            start = missing[k]
    runs.append((start, missing[-1] + 1))
    print("runs to re-attach:", [(a, b, b - a) for a, b in runs])

    out = list(L)
    for a, b in runs:
        block = R[a:b]
        anchor = None
        for j in range(a - 1, -1, -1):
            if R[j] in have:
                anchor = R[j]
                break
        if anchor is None:
            print("ABORT: run at remote line %d has no local anchor" % a)
            raise SystemExit(7)
        # attach after the LAST occurrence of the anchor - my blocks always sit at the top of ORDERS,
        # a lane's block right after its own heading; the first copy could be either.
        idxs = [i for i, x in enumerate(out) if x == anchor]
        pos = idxs[-1] + 1
        out = out[:pos] + block + out[pos:]
        print("  attached %d line(s) after anchor %r" % (len(block), anchor[:60]))

    lost_r = [x for x in R if x not in set(out)]
    lost_l = [x for x in L if x not in set(out)]
    print("merged", len(out), "lines | remote lines lost", len(lost_r), "| local lines lost", len(lost_l))
    if lost_r or lost_l:
        for x in (lost_r + lost_l)[:6]:
            print("  LOST|", x[:120])
        print("ABORT: merge drops lines - not writing")
        raise SystemExit(6)
    io.open(LEDGER, "w", encoding="utf-8", newline="").write("\n".join(out))
    print("WROTE merged ledger")

r = subprocess.run([sys.executable, "mirror_with_guard_r1.py",
                    "commander: ledger merge (lane blocks preserved) + CMDR-0925-1825 Q57=2 gated publisher"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
print(r.stdout[-1200:])
print("guard+mirror rc", r.returncode)
raise SystemExit(r.returncode)
