"""Pre-mirror guard r2: same refusal semantics as r1, but the remote ledger is fetched in a way that
survives its own size.

Why r2 exists: r1 read the remote ledger through the git blobs route, which answers the whole file as
one base64 string inside a JSON body.  At 5.7 MB that already returned an empty body once (r1's own
docstring records it); at 11 MB the body now truncates mid-stream three times in a row
(`IncompleteRead`), so the guard cannot read the remote at all and the mirror step never runs.  A
guard that cannot read is not a safe guard - it is a stopped pipeline, and lanes' blocks then sit in
the inbox with nobody mirroring them.

r2 fetches the raw file over raw.githubusercontent.com in chunks, and *proves* the read is complete
by comparing the sha1 of the assembled bytes against the blob sha the contents route reports for the
same ref.  A truncated read therefore fails closed (ABORT), never silently: mirroring over a ledger
we only half-read is exactly the failure mode r1 was written to prevent.

Usage: python mirror_with_guard_r2.py [--dry] [commit message]
  --dry   fetch and compare only; do not mirror.
"""
import hashlib
import io
import json
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
API = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
       "User-Agent": "cmdr-premirror-guard-r2"}
D = "Canshu-King/CityNexus"
REF = "commander/control"
PATH = "CITYNEXUS_AGENT_CONTROL.md"
LOCAL = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
RAW = "https://api.github.com/repos/%s/git/blobs/{sha}" % D
CHUNK = 1 << 20


def api_get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=API), timeout=240).read())


def blob_sha_of_remote():
    """The sha the contents route reports for the file at this ref - the value the raw bytes must hash to."""
    m = api_get("https://api.github.com/repos/%s/contents/%s?ref=%s" % (D, PATH, REF.replace("/", "%2F")))
    return m["sha"], m.get("size")


def fetch_raw_chunked(sha, attempts=6):
    """Stream the blob body with the raw media type (no base64 envelope) in 1 MiB chunks, one fresh
    connection per attempt.  raw.githubusercontent.com is not usable here: the ref itself contains a
    slash (`commander/control`), so that URL cannot tell ref from path and answers 404."""
    hdr = dict(API)
    hdr["Accept"] = "application/vnd.github.raw"
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(RAW.format(sha=sha), headers=hdr)
            with urllib.request.urlopen(req, timeout=900) as r:
                buf = bytearray()
                while True:
                    part = r.read(CHUNK)
                    if not part:
                        break
                    buf += part
                return bytes(buf), i + 1
        except Exception as e:  # noqa: BLE001 - any transport failure is retryable here
            last = "%s: %s" % (type(e).__name__, str(e)[:160])
            time.sleep(2 + i * 2)
    raise SystemExit("RAW_FETCH_FAILED after %d attempts; last=%s | ABORT: cannot mirror over a ledger we cannot read"
                     % (attempts, last))


def main():
    dry = "--dry" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--dry"]
    want_sha, want_size = blob_sha_of_remote()
    raw, used = fetch_raw_chunked(want_sha)
    got = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
    print("remote blob sha (contents route) %s | size route %s" % (want_sha, want_size))
    print("raw fetched %d B in %d attempt(s) | git-blob sha1(raw) %s | complete=%s"
          % (len(raw), used, got, got == want_sha))
    if got != want_sha:
        print("ABORT: the raw read does not hash to the reported blob - truncated or ref moved mid-read")
        raise SystemExit(6)
    loc = io.open(LOCAL, "rb").read()
    loc_sha = hashlib.sha1(b"blob %d\x00" % len(loc) + loc).hexdigest()
    print("local %d B | local blob sha1 %s" % (len(loc), loc_sha))
    R = set(raw.decode("utf-8", "replace").splitlines())
    L = set(loc.decode("utf-8", "replace").splitlines())
    only_r = [x for x in raw.decode("utf-8", "replace").splitlines() if x not in L]
    only_l = [x for x in loc.decode("utf-8", "replace").splitlines() if x not in R]
    print("remote-only lines: %d | local-only lines: %d" % (len(only_r), len(only_l)))
    for x in only_r[:10]:
        print("  R|", x[:160])
    if only_r:
        print("ABORT: remote carries lines this file does not - merge first, never mirror over them")
        raise SystemExit(5)
    if dry:
        print("DRY: guard passed, remote read complete, no mirror performed")
        return 0
    msg = args[0] if args else "commander: ledger mirror (guard r2, chunked remote read)"
    p = subprocess.run([sys.executable, "mirror_ledger_r2.py", msg], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    print(p.stdout[-2200:])
    if p.returncode:
        print("MIRROR RC", p.returncode, p.stderr[-400:])
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
