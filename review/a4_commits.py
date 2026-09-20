"""Name the commits between the void A4 tip and the current one.

The order says `a6cfaca` is void and `dddfd8b` is the target, so the delta between them is
what I have to re-read before running anything: two commits, claimed to be a config fix and
a docs update.
"""

import json
import subprocess
import sys
import urllib.parse
import urllib.request

REPO = "Canshu-King/CityNexus-Workspace"
FROM = sys.argv[1] if len(sys.argv) > 1 else "a6cfaca048c47d209cb93ad541ef7c6573d358ff"
TO = sys.argv[2] if len(sys.argv) > 2 else "dddfd8b936e1615897736cdc32b03dc7670b30ab"


def token() -> str:
    proc = subprocess.run(
        "git credential fill",
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        shell=True,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line[len("password=") :]
    raise SystemExit("no credential from `git credential fill`")


def get(url: str, secret: str):
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {secret}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "cnx-ui-lane",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


secret = token()
body = get(
    f"https://api.github.com/repos/{REPO}/compare/{FROM}...{TO}",
    secret,
)
print(f"status={body.get('status')} ahead_by={body.get('ahead_by')} behind_by={body.get('behind_by')}")
for commit in body.get("commits", []):
    print(f"  {commit['sha'][:9]} {commit['commit']['message'].splitlines()[0]}")
print("files changed between the two tips:")
for item in body.get("files", []):
    print(f"  {item['status']:8s} +{item['additions']}/-{item['deletions']}  {item['filename']}")
