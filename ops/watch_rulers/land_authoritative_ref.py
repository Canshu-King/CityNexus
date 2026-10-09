"""Land a candidate on the authoritative branch by ATOMIC, non-force ref update - commander's hand only.

Why the API instead of a local `git push`: SSH port 22 is dead on this network (measured: connect timeout),
and a local merge + push has a window in which another writer could move the tip.  `force:false` makes
GitHub itself refuse the update unless the candidate is a descendant of the current tip, which is exactly
the fast-forward-only rule, checked server-side at the moment of the write.

Read back before and after; the token is never printed.
"""
import json
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
API = "https://api.github.com"
REPO = "Canshu-King/CityNexus"
# Measured 2026-09-25 02:1x: there is NO branch named `integration/frontend-apple-pass1` on GitHub - the
# readable mirror of the commander's authoritative line is `mirror/integration-frontend-apple-pass1`
# (that is the EXTERNALLY_READABLE_EVIDENCE arrangement we settled on).  Pass the ref explicitly; never
# assume a local branch name exists on the remote, and never trust a 404 as "not landed" without reading
# the ref list - my first attempt today fail-closed on exactly that difference and wrote nothing.
BRANCH = "mirror/integration-frontend-apple-pass1"


def call(method, path, payload=None):
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
        "User-Agent": "commander-landing-hand", "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:  # noqa: BLE001
            return e.code, {"raw": "unparseable"}


def main():
    want = sys.argv[1]
    expect_base = sys.argv[2] if len(sys.argv) > 2 else None
    quoted = urllib.parse.quote(BRANCH, safe="")
    st, before = call("GET", f"/repos/{REPO}/git/ref/heads/{quoted}")
    tip = (before.get("object") or {}).get("sha")
    print(f"branch {BRANCH}\n  read-back tip before: {tip}  (http {st})")
    if expect_base and tip != expect_base:
        print(f"REFUSE: tip is not the expected base {expect_base} - someone else moved it. 0 writes.")
        return 5
    st2, res = call("PATCH", f"/repos/{REPO}/git/refs/heads/{quoted}", {"sha": want, "force": False})
    print(f"  PATCH force=false -> http {st2}  url={res.get('url', '')[:70]}")
    if st2 not in (200, 201):
        print("  refused by GitHub - nothing moved. body:", json.dumps(res)[:300])
        return 6
    st3, after = call("GET", f"/repos/{REPO}/git/ref/heads/{quoted}")
    tip2 = (after.get("object") or {}).get("sha")
    print(f"  read-back tip after : {tip2}  (http {st3})")
    ok = tip2 == want
    print("LANDED" if ok else "MISMATCH_AFTER_LAND - do not claim the landing")
    c = call("GET", f"/repos/{REPO}/git/commits/{want}")[1]
    print(f"  landed commit: parents={[p['sha'][:12] for p in c.get('parents') or []]} tree={c['tree']['sha'][:12]}"
          f" msg={c['message'].splitlines()[0][:70]}")
    return 0 if ok else 7


if __name__ == "__main__":
    import urllib.parse  # noqa: E402
    main()
