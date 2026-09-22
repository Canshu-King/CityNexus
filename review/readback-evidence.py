"""Read back a published evidence folder from GitHub and prove each blob byte-for-byte.

The publisher prints a blob sha1 per PUT; this checks the other side of the same claim: what the
repository actually answers for that path today. A name, a size and a sha1 that all agree is the
coordinate an external auditor can resolve without this machine.

Run:  D:/moodle/CityNexus/.venv/Scripts/python.exe review/readback-evidence.py evidence/ord0221
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_integration_20260919")
REPO = "Canshu-King/CityNexus"
BRANCH = "commander/control"


def token() -> str:
    out = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("password="):
            return line[len("password=") :]
    raise SystemExit("no github credential from the helper")


def get(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token()}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "qoder-e345b9d6-readback",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, {"raw": error.read().decode("utf-8", errors="replace")[:200]}


def blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def main() -> int:
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "evidence/ord0221"
    status, listing = get(f"https://api.github.com/repos/{REPO}/contents/{repo_path}?ref={BRANCH}")
    print(f"https://github.com/{REPO}/tree/{BRANCH}/{repo_path}  -> HTTP {status}")
    if status != 200 or not isinstance(listing, list):
        print(f"  answer: {str(listing)[:200]}")
        return 2
    remote = {entry["name"]: (int(entry["size"]), entry["sha"]) for entry in listing}
    bad = 0
    for name in sorted(remote):
        size, sha = remote[name]
        local = ROOT / "review/evidence" / repo_path.split("/")[-1] / name
        if not local.exists():
            print(f"  {name:38s} {size:>7d} B  blob {sha[:16]}  -> NOT-ON-DISK (remote only)")
            bad += 1
            continue
        local_sha = blob_sha1(local)
        local_size = local.stat().st_size
        agree = local_size == size and local_sha == sha
        if not agree:
            bad += 1
        print(
            f"  {name:38s} {size:>7d} B  blob {sha[:16]}  -> "
            f"{'BYTE-LEVEL MATCH' if agree else f'MISMATCH local={local_size}/{local_sha[:16]}'}"
        )
    extra = sorted({p.name for p in (ROOT / "review/evidence" / repo_path.split("/")[-1]).iterdir()} - set(remote))
    print(f"remote entries={len(remote)} disagreements={bad} on-disk-but-not-published={extra}")
    return 0 if bad == 0 and not extra else 3


if __name__ == "__main__":
    raise SystemExit(main())
