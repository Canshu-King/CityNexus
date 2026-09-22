"""ORD-0221 ① -- read back the evidence surface the commander published, from GitHub itself.

The arbitration's reason for not signing was that `50b35e0` is 422 on GitHub: a working-tip SHA in
the ledger is not an audit coordinate.  This script does not re-publish anything; it asks the
service what is actually there at `Canshu-King/CityNexus @ commander/control / evidence/ord0216`,
prints name/size/blob-sha for every entry, and compares each one against the sha16 the order
quotes.  The token is read from the git credential helper and never printed.

Run:  D:/moodle/CityNexus/.venv/Scripts/python.exe review/verify-ord0221-evidence-surface.py
"""
from __future__ import annotations

import json
import subprocess
import urllib.request

OWNER_REPO = "Canshu-King/CityNexus"
REF = "commander/control"
PATH = "evidence/ord0216"

# What ORD-0221 quotes, copied from the ledger entry.
QUOTED = {
    "50b35e0__50b35e0.patch": ("8343", "d6b5caa03c34adda"),
    "3e259bd__3e259bd.patch": ("27113", "dfb25bda4e2784e9"),
    "522c414__522c414.patch": ("1590", "74b2270ea3d29043"),
    "50b35e0__50b35e0.files.txt": ("202", "41eac4f6df89156e"),
}


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


def main() -> int:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{OWNER_REPO}/contents/{PATH}?ref={REF}",
        headers={
            "Authorization": f"Bearer {token()}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "qoder-e345b9d6-verify",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        entries = json.loads(response.read().decode("utf-8"))

    print(f"https://github.com/{OWNER_REPO}/tree/{REF}/{PATH}")
    if isinstance(entries, dict):
        print(f"API answered: {entries.get('message')}")
        return 2
    on_repo = {entry["name"]: (str(entry["size"]), entry["sha"][:16]) for entry in entries}
    for name in sorted(on_repo):
        size, sha16 = on_repo[name]
        quoted = QUOTED.get(name)
        if quoted is None:
            verdict = "NOT-IN-THE-ORDER"
        else:
            verdict = "MATCHES" if quoted == (size, sha16) else f"MISMATCH order={quoted}"
        print(f"  {name:34s} {size:>7s} B  blob {sha16}  -> {verdict}")
    missing = sorted(set(QUOTED) - set(on_repo))
    extra = sorted(set(on_repo) - set(QUOTED))
    print(f"quoted-but-absent={missing} present-but-unquoted={extra}")
    return 0 if not missing and not extra else 3


if __name__ == "__main__":
    raise SystemExit(main())
