"""Read-only fetch of one file from Canshu-King/CityNexus @ commander/control, printed as text.

Used to read another lane's published evidence without touching my working tree.  Prints the blob sha
GitHub reports plus the decoded body (truncated to --max, default 6000 chars).  Never prints credentials.
"""
import base64
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
        "User-Agent": "commander-evidence-read",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    path = sys.argv[1]
    mx = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
    meta = get(f"{API}/repos/{REPO}/contents/{path}?ref={BRANCH}")
    if isinstance(meta, list):
        print("DIRECTORY:", path)
        for e in meta:
            print(f"  {e['sha']}  {e.get('size')} B  {e['path']}")
        return
    raw = base64.b64decode(meta.get("content", ""))
    print(f"path {path}\nblob {meta.get('sha')}  size {meta.get('size')} B  decoded {len(raw)} B")
    txt = raw.decode("utf-8", "replace")
    print(txt if len(txt) <= mx else txt[:mx] + f"\n...[truncated {len(txt) - mx} chars]")


if __name__ == "__main__":
    main()
