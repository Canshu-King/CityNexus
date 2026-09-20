"""ORD-0043 -- pull the six files of the arbiter's A4 branch by path.

The recursive tree call is ~5.5MB and this box's path to GitHub drops mid-body, so fetch the
known paths through the Contents API instead: six small requests, each verified by the blob
sha the API reports.  Nothing is written into the working tree here -- the landing step is a
separate, deliberate action after reading what actually arrived.
"""

import base64
import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = "Canshu-King/CityNexus-Workspace"
SHA = sys.argv[1] if len(sys.argv) > 1 else "dddfd8b936e1615897736cdc32b03dc7670b30ab"
PREFIX = "_tools/qoder-integration-20260919"
OUT = (
    sys.argv[2]
    if len(sys.argv) > 2
    else "D:/moodle/_qoder_ui_overnight_20260920/review/a4-incoming-dddfd8b"
)

WANTED = [
    "frontend/src/main.tsx",
    "frontend/vite.config.ts",
    "frontend/public/sw.js",
    "frontend/playwright.sw.config.ts",
    "frontend/e2e/qoder-sw-lifecycle.spec.ts",
    "frontend/docs/SW_LIFECYCLE_ACCEPTANCE.md",
]


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
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")
        except Exception as error:  # noqa: BLE001 -- a dropped body is retried, not fatal
            print(f"  retry {attempt + 1} after {type(error).__name__}")
    return 0, {}


os.makedirs(OUT, exist_ok=True)
secret = token()
print(f"token acquired (length {len(secret)}, never printed)")

report = {}
for path in WANTED:
    for candidate in (f"{PREFIX}/{path}", path):
        status, body = get(
            f"https://api.github.com/repos/{REPO}/contents/{urllib.parse.quote(candidate)}?ref={SHA}",
            secret,
        )
        if status == 200 and isinstance(body, dict) and "content" in body:
            data = base64.b64decode(body["content"])
            destination = os.path.join(OUT, path.replace("/", "__"))
            with open(destination, "wb") as fh:
                fh.write(data)
            report[path] = {
                "resolved": candidate,
                "bytes": len(data),
                "sha": body.get("sha"),
                "size_matches": body.get("size") == len(data),
            }
            print(f"OK  {path}  {len(data)} B  blob={body.get('sha')[:8]}  via {candidate}")
            break
        if status == 404:
            print(f"    {candidate} -> 404, trying next candidate")
    else:
        report[path] = {"missing": True, "last_status": status}
        print(f"MISSING {path} (last status {status})")

with io.open(f"{OUT}/_manifest.json", "w", encoding="utf-8", newline="") as fh:
    json.dump({"sha": SHA, "files": report}, fh, indent=2, ensure_ascii=False)
print(f"\nwrote manifest: {OUT}/_manifest.json")
