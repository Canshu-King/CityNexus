"""Read-only branch-shape verification I must do myself before any fast-forward landing.

Why this exists: I landed ORD-0219/0261/0264 only after re-reading the tip myself, and tonight a lane's
receipt carried 21 carrier nodeids of which 4 had roots that did not match its own run cwd - a coordinate
problem that only shows up when you compare the object, not the prose.  So the shape questions are
answered from the API: where is the ref, who is the parent, what tree does it carry, and is the excluded
commit an ancestor?
"""
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
API = "https://api.github.com"
REPO = "Canshu-King/CityNexus"


def get(path):
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request(API + path, headers={
        "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
        "User-Agent": "commander-branch-shape-read", "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def compare(base, head):
    c = get(f"/repos/{REPO}/compare/{base}...{head}")
    return c.get("status"), c.get("ahead_by"), c.get("behind_by"), len(c.get("commits") or [])


def main():
    ref = sys.argv[1]
    tip_expected = sys.argv[2] if len(sys.argv) > 2 else None
    authoritative = sys.argv[3] if len(sys.argv) > 3 else "c79e2b4f4efe414dba22a071a7136ae10b5c84aa"
    excluded = sys.argv[4] if len(sys.argv) > 4 else "44b428da83e4"
    r = get(f"/repos/{REPO}/git/ref/heads/{urllib.parse.quote(ref, safe='')}")
    sha = r["object"]["sha"]
    print(f"ref {ref} -> {sha}   (ref exists on origin: YES)")
    if tip_expected:
        print(f"  declared tip {tip_expected}  ==  read tip ?  {'YES' if sha.startswith(tip_expected[:10]) else 'NO'}")
    c = get(f"/repos/{REPO}/git/commits/{sha}")
    print(f"  parents    {[p['sha'] for p in c['parents']]}")
    print(f"  tree       {c['tree']['sha']}")
    print(f"  commit msg {c['message'].splitlines()[0][:90]}")
    for label, other in (("authoritative tip", authoritative), ("excluded commit", excluded)):
        st, ahead, behind, n = compare(other, sha)
        print(f"  compare {other}...{sha}  = {st} ahead_by={ahead} behind_by={behind} commits={n}"
              f"   [{label}]")
    st, ahead, behind, n = compare(sha, excluded)
    print(f"  compare {sha}...{excluded}  = {st} ahead_by={ahead} behind_by={behind}   [direction check]")
    # what the branch actually changes against the authoritative tip
    c2 = get(f"/repos/{REPO}/compare/{authoritative}...{sha}")
    for f in c2.get("files") or []:
        print(f"  file {f['status']:<8} +{f['additions']}/-{f['deletions']}  {f['filename']}")


if __name__ == "__main__":
    import urllib.parse  # noqa: E402
    main()
