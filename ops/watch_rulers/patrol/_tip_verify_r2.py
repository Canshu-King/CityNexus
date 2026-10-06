# -*- coding: utf-8 -*-
"""Only measure the authoritative tip, ASCII labels, no writes, no ref updates.

Reads the tip three ways so a stale statement in the ledger can be told from the
server truth:
  1) GitHub API /git/ref/heads/<branch>   (no local fetch, no FETCH_HEAD)
  2) git ls-remote origin <branch>         (server-side, read-only)
  3) local cat-file subject/author-date of that sha (if the object is present)
Also answers: is dcb90cc an ancestor of the tip? is aa2a08ce?
"""
import ast
import datetime
import io
import json
import os
import re
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
sys.path.insert(0, LC)
REPO = r"D:\moodle\CityNexus"
BRANCH = "mirror/integration-frontend-apple-pass1"
PROD = "Canshu-King/CityNexus"          # origin of REPO (git remote -v, read 12:09)
TOKFILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"

for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    v = os.environ.pop(k, None)
    if v:
        print("env proxy cleared in THIS process only: %s was %s" % (k, v))

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api(path):
    tok = io.open(TOKFILE, encoding="utf-8").read().strip()
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"Authorization": "token " + tok, "Accept": "application/vnd.github+json",
                 "User-Agent": "cmdr-readonly-tip-check", "X-GitHub-Api-Version": "2022-11-28"},
    )
    with opener.open(req, timeout=60) as f:
        return json.loads(f.read().decode("utf-8"))


def git(*args):
    p = subprocess.run(("git", "-C", REPO) + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip())


now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
print("local time: %s (+08)" % now.strftime("%Y-%m-%d %H:%M:%S"))

try:
    d = api("/repos/" + PROD + "/git/ref/heads/" + BRANCH)
except Exception as exc:
    print("API: FAILED %s: %s" % (exc.__class__.__name__, str(exc)[:200]))
    d = None

sha_api = None
if d:
    sha_api = d["object"]["sha"]
    print("API tip sha   : %s" % sha_api)

rc, out, err = git("ls-remote", "origin", "refs/heads/" + BRANCH)
sha_remote = out.split()[0] if rc == 0 and out else None
print("ls-remote sha : %s%s" % (sha_remote, "" if rc == 0 else "  (rc=%d %s)" % (rc, err[:120])))
if sha_api and sha_remote:
    print("API vs ls-remote: %s" % ("SAME" if sha_api == sha_remote else "DIFFERENT"))

if sha_api:
    c = api("/repos/" + PROD + "/git/commits/" + sha_api)
    # this gateway returns a FLATTENED commit object (keys author/committer/message/parents
    # at top level, no "commit" wrapper) -- read both shapes so a shape change cannot lie.
    src = c.get("commit") or c
    subj = (src.get("message") or "?").splitlines()[0]
    adate = (src.get("author") or {}).get("date") or "?"
    pars = [x.get("sha", "?") for x in (src.get("parents") or [])]
    print("tip subject   : %s" % subj[:160])
    print("tip authordate: %s  (UTC)" % adate)
    print("tip parents   : %d -> %s" % (len(pars), " ".join(x[:12] for x in pars)))
    try:
        dt = datetime.datetime.strptime(adate, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        print("tip age minutes: %.1f  (stationary since the tip commit)" % ((now - dt.astimezone(now.tzinfo)).total_seconds() / 60.0))
    except Exception as exc:
        print("tip age minutes: NOT PARSED (%s)" % exc.__class__.__name__)
    rc, obj, e = git("cat-file", "-t", sha_api)
    print("local object  : %s%s" % (obj, "" if rc == 0 else "  (NOT LOCAL: %s)" % e[:80]))

for cand in ("dcb90cccc68b81f2317b28db19051dedb9f06c80", "aa2a08ce164a37a83bd6ed225524053bb0fa0606"):
    rc, obj, e = git("cat-file", "-t", cand)
    line = "candidate %s : local %s" % (cand[:12], obj if rc == 0 else "NOT LOCAL")
    if rc == 0 and sha_api:
        r2, _, _ = git("merge-base", "--is-ancestor", cand, sha_api)
        line += " | ancestor-of-tip: %s" % ("YES" if r2 == 0 else "NO")
        r3, s3, _ = git("log", "-1", "--format=%ad %s", "--date=format:%H:%M", cand)
        line += " | %s" % (s3[:110] if s3 else "?")
    print(line)
