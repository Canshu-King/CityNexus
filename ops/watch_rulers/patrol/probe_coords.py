"""Read-only: for every door-GREEN inbox block, decide whether each 40-hex coordinate is real, and where.

The writer's second arm resolves a coordinate with `git cat-file -t` in D:/moodle/CityNexus AFTER fetching
every origin branch (ledger_insert_after.py:50-52). A plain local probe therefore over-reports "unresolvable"
for anything published in the last fetch interval. So each token is judged on three independent channels:

  local_A  git cat-file -t in D:/moodle/CityNexus        (writer's own store, unfetched)
  local_B  git cat-file -t in D:/moodle/_qoder_integration_20260919  (the live line)
  origin   GitHub REST: /git/commits/<sha> then /git/blobs/<sha>     (what a fetch WOULD bring)

Only a token that fails all three is a coordinate the writer cannot land even after fetching.
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ghnet  # dead-proxy -> direct retry

INBOX = r"D:\moodle\_qoder_ledger_inbox"
ROOTS = [("local_A", r"D:\moodle\CityNexus"),
         ("local_B", r"D:\moodle\_qoder_integration_20260919")]
HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
RULER = os.path.join(os.path.dirname(HERE), "claim_coordinate_check_r4e.py")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
REPO = "Canshu-King/CityNexus"
HDR = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
       "User-Agent": "cnx-patrol-readonly", "X-GitHub-Api-Version": "2022-11-28"}
_api_cache = {}


def cat_file(root, sha):
    r = subprocess.run(["git", "-C", root, "cat-file", "-t", sha],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "").strip() if r.returncode == 0 else None


def api(path):
    if path in _api_cache:
        return _api_cache[path]
    req = urllib.request.Request("https://api.github.com" + path)
    st, raw = ghnet.urlopen(req, timeout=45, headers=HDR)
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception:
        d = {}
    # NOTE (shape read at 19:19): /git/commits/<sha> replies 200 WITHOUT a "type" field - a probe keyed on
    # `type` calls every real commit missing and then reports the blob 404, which is how my first run produced
    # a fake "HTTP_404" for the live tip. Verdicts here are keyed on the HTTP status.
    _api_cache[path] = (st, d)
    return st, d


def on_origin(sha):
    st, _d = api("/repos/%s/git/commits/%s" % (REPO, sha))
    if st == 200:
        return "commit"
    st, d = api("/repos/%s/git/blobs/%s" % (REPO, sha))
    if st == 200 and d.get("type") == "blob":
        return "blob"
    return "HTTP_%d" % st


def main():
    # CONTROL, bolted in: the tip that `git ls-remote` reports right now must read back as a commit through the
    # same API channel used below. If it does not, the token/endpoint/links are broken and NO per-token verdict
    # in this run means anything - so the run refuses to produce verdicts.
    ref = "refs/heads/mirror/integration-frontend-apple-pass1"
    r = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", r"D:\moodle\CityNexus",
                        "ls-remote", "origin", ref], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    tip = (r.stdout or "").split()
    tip_sha = tip[0] if tip and re.match(r"^[0-9a-f]{40}$", tip[0]) else None
    ctl = on_origin(tip_sha) if tip_sha else "NO-TIP-READ"
    print("CONTROL ls-remote %s -> %s ; same-channel API read = %s" % (ref, (tip_sha or "")[:12], ctl))
    if ctl != "commit":
        print("ABORT: control failed, the origin channel is not trustworthy this run - reporting nothing.")
        return 1
    print("roots present:", [(n, os.path.isdir(p)) for n, p in ROOTS])
    lines = []
    green = []
    for f in sorted(os.listdir(INBOX)):
        if not f.endswith(".md"):
            continue
        p = os.path.join(INBOX, f)
        d = subprocess.run([PY, RULER, "--text", p, "--expect-clean"],
                           capture_output=True, timeout=600)
        if d.returncode == 0:
            green.append(f)
    print("door-GREEN blocks=%d -> %s" % (len(green), ", ".join(green)))
    tot_ok = tot_bad = 0
    for f in green:
        p = os.path.join(INBOX, f)
        body = io.open(p, encoding="utf-8", errors="replace").read()
        toks = sorted(set(HEX40.findall(body)))
        bad = []
        for t in toks:
            kinds = [(n, cat_file(rp, t)) for n, rp in ROOTS]
            on_any_local = [n for n, k in kinds if k]
            o = None
            if not on_any_local:
                o = on_origin(t)
            ok = bool(on_any_local) or o in ("commit", "blob")
            print("  %-16s %s localA=%s localB=%s origin=%s => %s" % (
                f, t[:12], kinds[0][1] or "MISS", kinds[1][1] or "MISS", o or "-",
                "REAL" if ok else "NOT-RETRIEVABLE"))
            if ok:
                tot_ok += 1
            else:
                tot_bad += 1
                bad.append(t)
        for t in bad:
            for i, ln in enumerate(body.splitlines(), 1):
                if t in ln:
                    print("    DEAD %s line %d: %s" % (t[:12], i, ln.strip()[:110]))
    print("TOTAL real=%d not-retrievable=%d  at %s" % (tot_ok, tot_bad, time.strftime("%H:%M:%S")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
