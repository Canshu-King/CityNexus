import json
import sys
import urllib.request
sys.path.insert(0, r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
import ghnet

TOK = open(r"D:\moodle\_qoder_recovery_20260920\.api_tok_20260920", encoding="utf-8").read().strip() if False else \
    open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
     "User-Agent": "cnx-patrol-readonly", "X-GitHub-Api-Version": "2022-11-28"}


def get(path):
    req = urllib.request.Request("https://api.github.com" + path)
    st, raw = ghnet.urlopen(req, timeout=45, headers=H)
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception:
        d = {"_nonjson": raw[:120].decode("utf-8", "replace")}
    return st, d


st, d = get("/rate_limit")
print("rate_limit", st, json.dumps(d)[:200])
st, d = get("/repos/Canshu-King/CityNexus")
print("repo", st, d.get("private"), d.get("default_branch"), str(d.get("message"))[:60])
import subprocess
r = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", r"D:\moodle\CityNexus",
                    "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                   capture_output=True, text=True)
tip = (r.stdout or "").split()
print("ls-remote rc", r.returncode, tip[:1], (r.stderr or "")[:80])
if tip:
    st, d = get("/repos/Canshu-King/CityNexus/git/commits/" + tip[0])
    print("commit-endpoint", st, d.get("type"), str(d.get("message"))[:60])
    st, d = get("/repos/Canshu-King/CityNexus/git/tags/" + tip[0])
    print("tags-endpoint", st, d.get("type"), str(d.get("message"))[:60])
    st, d = get("/repos/Canshu-King/CityNexus/commits/" + tip[0])
    print("commits-short", st, d.get("type") or (d.get("commit") or {}).get("message", "")[:40], str(d.get("message"))[:60])
