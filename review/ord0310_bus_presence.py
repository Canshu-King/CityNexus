"""Ask the bus, before retrying, whether a comment with this body already exists.

An SSL truncation during a POST says nothing about whether the server stored the comment, and a
retry that creates a second copy of a delivery is a defect I have shipped before.
"""
from __future__ import annotations

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
BODY = ROOT / "_scratch_0310" / (sys.argv[1] if len(sys.argv) > 1 else "ord0310-post-body-r3.md")
NEEDLE = sys.argv[2] if len(sys.argv) > 2 else "落成的那一代 + 一处自我勘误"
API = "https://api.github.com/repos/Canshu-King/CityNexus-Workspace/issues/1"


def secret() -> str:
    out = subprocess.run(["git", "credential", "fill"],
                         input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True, check=True).stdout
    value = ""
    for line in out.splitlines():
        if line.startswith("password="):
            value = line[len("password="):]
    return value


def get(url: str):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + secret(),
                                              "Accept": "application/vnd.github+json",
                                              "User-Agent": "qoder-e345b9d6-bus-presence-check"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


body_bytes = BODY.read_bytes()
mine = blob(body_bytes)
issue = get(API)
total = issue["comments"]
per = 20
page = (total // per) + 1
rows = get(f"{API}/comments?per_page={per}&page={page}")
print(f"total_comments={total} page={page} rows_on_page={len(rows)}")
print(f"my_body_bytes={len(body_bytes)} my_body_blob={mine}")
same_blob = [c["id"] for c in rows if blob(c["body"].encode("utf-8")) == mine]
head_hit = [c["id"] for c in rows if NEEDLE in c["body"]]
print("comments_with_my_exact_blob:", same_blob)
print("comments_holding_my_heading:", head_hit)
for c in rows[-4:]:
    b = c["body"].encode("utf-8")
    print(f"  tail {c['id']} {c['created_at']} {len(b)} B blob {blob(b)[:12]} :: "
          f"{b.decode('utf-8', errors='replace')[:52]}".replace("\n", " "))
print("VERDICT:", "ALREADY_POSTED" if (same_blob or head_hit) else "NOT_POSTED_YET")
