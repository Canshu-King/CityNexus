"""Prove the ORD-0310 delivery by reading every file back with its own GET.

The publisher prints a proof per PUT; that is the same process that wrote, so it does not count as
independent verification. Here each published path gets its own `GET /contents/<path>`, the base64
body is decoded and compared byte for byte against the local artifact, and the git blob sha1 is
recomputed on both sides. The directory listing is a separate call, so the count of files is read
from the server rather than from my own list.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
PUB = ROOT / "_scratch_0310" / "pub"
OUT = ROOT / "_scratch_0310" / (sys.argv[1] if len(sys.argv) > 1 else "ord0310-readback-r1.json")
DIR = "evidence/ord0288-keyless-deadline"
API = "https://api.github.com/repos/Canshu-King/CityNexus/contents"
REF = "commander/control"


def token() -> str:
    out = subprocess_credentials()
    for line in out.splitlines():
        if line.startswith("password="):
            return line[len("password="):]
    raise SystemExit("no github credential from the helper")


def subprocess_credentials() -> str:
    import subprocess
    return subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                          capture_output=True, text=True, check=True).stdout


def get(url: str, attempts: int = 4):
    last = None
    for i in range(attempts):
        request = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token()}", "Accept": "application/vnd.github+json",
            "User-Agent": "qoder-e345b9d6-ord0310-readback"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            return error.code, {"raw": error.read().decode("utf-8", errors="replace")[:200]}
        except Exception as error:  # transient link resets on this uplink; retry, then report
            last = error
            time.sleep(2 + 2 * i)
    return 0, {"raw": f"transport failure after {attempts} attempts: {type(last).__name__}: {last}"}


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main() -> int:
    status, listing = get(f"{API}/{DIR}?ref={REF}")
    if status != 200 or not isinstance(listing, list):
        print(f"ABORT: the directory listing did not answer 200 with an array (status {status})")
        return 2
    on_server = sorted(e["name"] for e in listing if e["type"] == "file")
    local = sorted(p.name for p in PUB.iterdir() if p.is_file())
    rows = {}
    for name in on_server:
        st, body = get(f"{API}/{DIR}/{urllib.request.quote(name)}?ref={REF}")
        if st != 200 or "content" not in body:
            rows[name] = {"remote_status": st, "verdict": "READ_FAILED",
                          "raw": str(body.get("raw", ""))[:160]}
            continue
        remote = base64.b64decode(body["content"])
        mine = (PUB / name).read_bytes() if (PUB / name).exists() else None
        rows[name] = {
            "remote_bytes": len(remote), "remote_blob": body["sha"],
            "remote_blob_recomputed_from_decoded_bytes": blob(remote),
            "local_bytes": None if mine is None else len(mine),
            "local_blob": None if mine is None else blob(mine),
            "byte_level_equal_to_local": None if mine is None else remote == mine,
            "verdict": ("BYTE_LEVEL_MATCH" if mine is not None and remote == mine
                        and body["sha"] == blob(remote) else "MISMATCH"),
            "one_independent_get": f"GET {API}/{DIR}/{name}?ref={REF} -> HTTP {st}",
        }
    payload = {
        "order": "ORD-0310", "lane": "D e345b9d6",
        "directory": DIR, "ref": REF,
        "directory_get": {"status": status, "entries_on_server": len(on_server),
                          "names_on_server": on_server},
        "names_local": local,
        "only_on_server": sorted(set(on_server) - set(local)),
        "only_local": sorted(set(local) - set(on_server)),
        "requestedAndChecked": len(on_server),
        "byteLevelMatches": sum(1 for r in rows.values() if r["verdict"] == "BYTE_LEVEL_MATCH"),
        "notMatching": sorted(n for n, r in rows.items() if r["verdict"] != "BYTE_LEVEL_MATCH"),
        "rows": rows,
        "method": "one GET per published path; base64 decoded and compared byte for byte; "
                  "git blob sha1 recomputed on both the decoded remote bytes and the local file",
        "self_reference": "this JSON cannot certify itself; it is closed by one further single GET "
                          "printed in the bus post, and that line is written only if the two blobs agree",
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                   newline="\n")
    print(f"wrote {OUT} {OUT.stat().st_size} B blob={blob(OUT.read_bytes())}")
    print(f"entries={payload['directory_get']['entries_on_server']} matches={payload['byteLevelMatches']} "
          f"notMatching={payload['notMatching']} only_on_server={payload['only_on_server']} "
          f"only_local={payload['only_local']}")
    return 0 if not payload["notMatching"] and not payload["only_local"] else 3


raise SystemExit(main())
