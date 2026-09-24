"""Read-only: what is actually under live_checks/ on Canshu-King/CityNexus @ commander/control.

Prints path, size and the blob sha GitHub reports for each entry, plus the branch tip commit.
Never prints the token.  Used to check that every instrument I ask a verifier to derive from is
externally readable at the byte-identical blob I recorded (EXTERNALLY_READABLE_EVIDENCE).
"""
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
API = "https://api.github.com"
REPO = "Canshu-King/CityNexus"
BRANCH = "commander/control"


def get(url):
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + tok,
        "Accept": "application/vnd.github+json",
        "User-Agent": "commander-inventory-read",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else "live_checks"
    listing = get(f"{API}/repos/{REPO}/contents/{want}?ref={BRANCH}")
    tip = get(f"{API}/repos/{REPO}/commits?sha={BRANCH}&per_page=1")[0]
    print(f"branch {BRANCH} tip commit {tip['sha']}  ({tip['commit']['committer']['date']})")
    print(f"prefix {want}/  entries={len(listing)}")
    for e in sorted(listing, key=lambda x: x["path"]):
        print(f"{e['sha']}  {e['size']:>9} B  {e['path']}")


if __name__ == "__main__":
    main()
