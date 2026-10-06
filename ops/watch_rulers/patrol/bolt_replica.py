"""Read-only replica of the writer's coordinate bolt (ledger_insert_after.py:43-112).

Reproduces EXACTLY the arms the writer uses, minus the fetch (which would write into D:/moodle/CityNexus) and
minus the ledger write:
  * a token resolves if `git cat-file -t` works in CityNexus, in the live integration store, or on origin via REST
    (origin stands in for "the writer fetches all branches first");
  * an unresolvable token is CARRIED only when its OWN line matches _NON_RETRIEVABLE_PAT and the PARAGRAPH it
    sits in also carries a token that does resolve;
  * any other unresolvable token => the writer prints ABORT and returns rc 9 for that block.
So a block can be Q43-GREEN and still be refused by this second arm.
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

INBOX = r"D:\moodle\_qoder_ledger_inbox"
HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
ROOTS = [("A", r"D:\moodle\CityNexus"), ("B", r"D:\moodle\_qoder_integration_20260919")]
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"


def _live_ruler():
    """Read the ruler name out of the door file that is actually wired (r2 first, then r1)."""
    lc = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
    for df in ("ledger_insert_after_r2.py", "ledger_insert_after.py"):
        p = os.path.join(lc, df)
        if not os.path.exists(p):
            continue
        for i, ln in enumerate(io.open(p, encoding="utf-8", errors="replace").read().splitlines(), 1):
            m = re.search(r'"(claim_coordinate_check_r[0-9a-z]*\.py)"', ln)
            if m:
                return os.path.join(lc, m.group(1)), "%s:%d" % (df, i)
    return os.path.join(lc, "claim_coordinate_check_r4e.py"), "FALLBACK"


RULER, RULER_SRC = _live_ruler()
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
HDR = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
       "User-Agent": "cnx-patrol-bolt-replica", "X-GitHub-Api-Version": "2022-11-28"}
# copied verbatim from ledger_insert_after.py:66-72
PAT = re.compile(
    u"sha1\\s*[\\(（]?\\s*(over|of)\\s+bytes"
    u"|文件\\s*sha1|本机\\s*sha1|内容\\s*sha1"
    u"|本地字节重算|字节重算的\\s*sha"
    u"|从未入\\s*git|未入\\s*git|不在对象库"
    u"|非\\s*blob|不是\\s*blob|不可\\s*cat-file|故意不可取回",
    re.I)
_cache = {}


def api(path):
    if path in _cache:
        return _cache[path]
    req = urllib.request.Request("https://api.github.com" + path)
    try:
        st, raw = ghnet.urlopen(req, timeout=45, headers=HDR)
    except Exception as e:
        st, raw = 0, str(e).encode()
    _cache[path] = st
    return st


def resolves(tok):
    for n, root in ROOTS:
        r = subprocess.run(["git", "-C", root, "cat-file", "-t", tok],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            return "local_" + n + ":" + (r.stdout or "").strip()
    if api("/repos/Canshu-King/CityNexus/git/commits/" + tok) == 200:
        return "origin:commit"
    if api("/repos/Canshu-King/CityNexus/git/blobs/" + tok) == 200:
        return "origin:blob"
    return None


def paragraph(lines, idx):
    lo = hi = idx
    while lo > 0 and lines[lo - 1].strip():
        lo -= 1
    while hi < len(lines) - 1 and lines[hi + 1].strip():
        hi += 1
    return "\n".join(lines[lo:hi + 1])


def control():
    """An already-inserted block must read with NO abort through the SAME arms, or this replica is not
    trustworthy.  `no abort` is the condition, not `no unresolvable token`: the door itself CARRIES a token
    whose own line declares it non-retrievable while its paragraph holds a fetchable coordinate, and a lane
    block accepted that way (qoder-0370 at 00:41) is precisely the case the replica must classify as carried
    rather than as an abort.  Requiring zero unresolvable tokens here would turn a legitimate carry into a
    dead control."""
    proc = os.path.join(INBOX, "_processed")
    cands = sorted([f for f in os.listdir(proc) if ".inserted_" in f],
                   key=lambda f: os.path.getmtime(os.path.join(proc, f)))
    for f in reversed(cands):
        p = os.path.join(proc, f)
        q43, aborts, carried, n_tokens = evaluate(p)
        if q43 != "GREEN":
            continue
        print("CONTROL inserted-block=%s q43=GREEN aborts=%d carried=%d tokens=%d %s"
              % (f, len(aborts), len(carried), n_tokens, carried[:2]))
        return len(aborts) == 0, f
    print("CONTROL: no GREEN already-inserted block found - replica cannot be trusted")
    return False, None


def evaluate(p):
    """Return (q43_verdict, aborts, carried, n_tokens) for one block file."""
    d = subprocess.run([PY, RULER, "--text", p, "--expect-clean"], capture_output=True, timeout=600)
    q43 = "GREEN" if d.returncode == 0 else "RED"
    lines = io.open(p, encoding="utf-8", newline="\n").read().splitlines()
    res = {}
    for t in sorted(set(HEX40.findall("\n".join(lines)))):
        res[t] = resolves(t)
    aborts = []
    carried = []
    for ln, text in enumerate(lines):
        for t in sorted(set(HEX40.findall(text))):
            if res.get(t):
                continue
            declared = bool(PAT.search(text))
            anchored = any(res.get(o) for o in HEX40.findall(paragraph(lines, ln)) if o != t)
            if declared and anchored:
                carried.append((ln + 1, t))
            else:
                aborts.append((ln + 1, t, declared, anchored))
    return q43, aborts, carried, len(res)


def main():
    ok, ctl = control()
    if not ok:
        print("ABORT: control block %s did not read clean, so a 'WOULD-ABORT' verdict means nothing this run." % ctl)
        return 1
    files = sorted(f for f in os.listdir(INBOX) if f.endswith(".md"))
    n_abort = n_carry = n_pass = 0
    per_block = {}
    for f in files:
        p = os.path.join(INBOX, f)
        try:
            raw = io.open(p, encoding="utf-8", newline="\n").read()
        except FileNotFoundError:
            # lanes are live: a block can be renamed into _processed or re-cut while this scan runs.
            print("%-22s VANISHED-MID-SCAN (lane renamed or re-cut it - not a defect)" % f)
            continue
        d = subprocess.run([PY, RULER, "--text", p, "--expect-clean"], capture_output=True, timeout=600)
        q43 = "GREEN" if d.returncode == 0 else "RED"
        lines = raw.splitlines()
        # resolve every token once
        res = {}
        for t in sorted(set(HEX40.findall("\n".join(lines)))):
            res[t] = resolves(t)
        aborts = []
        carried = []
        for ln, text in enumerate(lines):
            for t in sorted(set(HEX40.findall(text))):
                if res.get(t):
                    continue
                declared = bool(PAT.search(text))
                anchored = any(res.get(o) for o in HEX40.findall(paragraph(lines, ln)) if o != t)
                if declared and anchored:
                    carried.append((ln + 1, t))
                else:
                    aborts.append((ln + 1, t, declared, anchored))
        verdict = "WOULD-ABORT" if aborts else ("WOULD-LAND" if q43 == "GREEN" else "Q43-RED")
        per_block[f] = (q43, verdict, len(aborts), len(carried), len(res))
        if aborts:
            n_abort += 1
        elif q43 == "GREEN":
            n_pass += 1
        else:
            n_carry += 1
        print("%-22s q43=%-5s bolt=%-11s abort=%d carried=%d tokens=%d" % (f, q43, verdict, len(aborts), len(carried), len(res)))
        for ln, t, dec, anc in aborts:
            print("      L%-3d %s  declared=%s anchored=%s   %s" % (ln, t[:12], dec, anc, lines[ln - 1].strip()[:88]))
    print("\nSUMMARY blocks=%d  would-abort=%d  green-and-would-land=%d  q43-red=%d  at %s"
          % (len(files), n_abort, n_pass, n_carry, time.strftime("%H:%M:%S")))
    io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bolt_replica.json"), "w",
            encoding="utf-8").write(json.dumps(per_block, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
