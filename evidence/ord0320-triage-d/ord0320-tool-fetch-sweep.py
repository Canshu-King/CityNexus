"""Fetch the two Q64-sweep artefacts and print what they actually contain.

I am asked to bucket 16 cells, so the first measurement is what the sweep JSON holds: which rule,
which tree, which hits, and the per-cell `cite`. Counting from the order text would be counting
someone else's summary.
"""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
OUT = ROOT / "_scratch_0320"
OUT.mkdir(exist_ok=True)
REPO = "Canshu-King/CityNexus"
REF = "commander/control"
WANTED = {
    "sweep_r1.json": ("evidence/q64-sweep-S1/sweep_r1.json",
                      "f783b12eea629d52dbe8ff00f45716d50b99e30c"),
    "verify_r1.json": ("evidence/cmdr-s1-verify-0306/verify_r1.json",
                       "2799ec3d3be2b058edde839bfeba96c947e6332d"),
}


def secret() -> str:
    out = subprocess.run(["git", "credential", "fill"],
                         input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True, check=True).stdout
    value = ""
    for line in out.splitlines():
        if line.startswith("password="):
            value = line[len("password="):]
    return value


def get(path: str) -> bytes:
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={REF}"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + secret(),
                                              "Accept": "application/vnd.github+json",
                                              "User-Agent": "qoder-e345b9d6-ord0320"})
    with urllib.request.urlopen(req, timeout=180) as r:
        payload = json.loads(r.read())
    body = base64.b64decode(payload["content"])
    if hashlib.sha1(b"blob %d\0" % len(body) + body).hexdigest() != payload["sha"]:
        raise SystemExit(f"ABORT: {path} decoded to a different blob than the server claims")
    return body


for local, (path, claimed) in WANTED.items():
    body = get(path)
    got = hashlib.sha1(b"blob %d\0" % len(body) + body).hexdigest()
    (OUT / local).write_bytes(body)
    print(f"{path}\n  -> {OUT / local} {len(body):,} B blob {got} "
          f"{'== claimed' if got == claimed else 'DIFFERENT FROM THE ORDER TEXT (' + claimed + ')'}")
    doc = json.loads(body)
    print("  top-level keys:", list(doc)[:14])
    text = json.dumps(doc, ensure_ascii=False)
    for key in ("generation", "tree", "rule", "ruler", "files_scanned", "files_with_hits",
                "hits", "total_hits", "buckets", "classes"):
        if key in doc:
            v = doc[key]
            print(f"  {key} = {json.dumps(v, ensure_ascii=False)[:220]}")
    print(f"  bytes of JSON text: {len(text):,}")
