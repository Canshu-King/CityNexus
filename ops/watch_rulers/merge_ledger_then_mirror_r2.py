"""Fold branch-only ledger lines back into the local copy, then run the guarded mirror - r2.

Identical merge semantics to r1 (contiguous runs of remote-only lines re-attached after their nearest
local anchor, with "no line may be lost" proved before writing).  The one change is how the remote
ledger is READ, and why:

r1 read it as `git/blobs/<sha>` with the default JSON media type, i.e. the whole 8 MB file base64'd
inside one JSON body.  That route already returned an empty body once at 5.7 MB, and at 8.1 MB it now
truncates mid-stream (`IncompleteRead`) often enough that the read-back step of every mirror run
degraded to "CONTENTS_BODY_UNUSABLE_BLOB_CONFIRMED" - a state in which the remote bytes were never
actually compared to the local ones.  r2 streams the same blob with `Accept: application/vnd.github.raw`
in 1 MiB chunks and then proves completeness by hashing the assembled bytes as a git blob
(`sha1("blob <len>\\0" + body)`) and requiring it to equal the sha the contents route reports.  A
truncated read therefore fails closed with a non-zero exit instead of quietly merging half a ledger.

Also: r2 calls `mirror_with_guard_r2.py`, which does the same completeness proof before it PUTs.
"""
import hashlib
import io
import json
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from cmdr_net_env_guard_r2 import ensure_proxy_usable
# Stale HTTPS_PROXY on this box answered 10061 and faked a publication failure on 2026-09-26.
print("proxy guard:", ensure_proxy_usable())

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "cnx-cmdr-ledger-merge-r2"}
REPO = "Canshu-King/CityNexus"
REF = "commander%2Fcontrol"
CHUNK = 1 << 20


def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=300).read())


def fetch_blob_raw(sha, attempts=6):
    """Stream a blob's bytes (no base64 envelope).  raw.githubusercontent.com cannot be used: the ref
    itself contains a slash, so that URL cannot separate ref from path and answers 404."""
    hdr = dict(H)
    hdr["Accept"] = "application/vnd.github.raw"
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request("https://api.github.com/repos/%s/git/blobs/%s" % (REPO, sha), headers=hdr)
            with urllib.request.urlopen(req, timeout=900) as r:
                buf = bytearray()
                while True:
                    part = r.read(CHUNK)
                    if not part:
                        break
                    buf += part
                return bytes(buf), i + 1
        except Exception as e:  # noqa: BLE001 - transport failures are retryable
            last = "%s: %s" % (type(e).__name__, str(e)[:160])
            time.sleep(2 + i * 2)
    raise SystemExit("REMOTE_LEDGER_READ_FAILED after %d attempts; last=%s | ABORT: will not merge or mirror "
                     "against a ledger we could not read completely" % (attempts, last))


meta = get("https://api.github.com/repos/%s/contents/CITYNEXUS_AGENT_CONTROL.md?ref=%s" % (REPO, REF))
raw, used = fetch_blob_raw(meta["sha"])
got = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
print("remote blob %s | size route %s | fetched %d B in %d attempt(s) | git-blob sha1 %s | complete=%s"
      % (meta["sha"], meta.get("size"), len(raw), used, got, got == meta["sha"]))
if got != meta["sha"]:
    print("ABORT: fetched bytes do not hash to the reported blob - truncated read, refusing to merge")
    raise SystemExit(8)
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

r = subprocess.run([sys.executable, "mirror_with_guard_r2.py",
                    "commander: ledger merge (lane blocks preserved) + guarded mirror r2 (complete remote read)"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
print(r.stdout[-1500:])
print("guard+mirror rc", r.returncode)
raise SystemExit(r.returncode)
