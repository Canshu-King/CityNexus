"""Post this lane's ORD-0310 comment on the coordination bus and read it back from its own URL.

Posting is not delivering: the read-back is what says the bytes landed, and the tail check is what
says the commander's closing line survived the trip (it is copied out of CLOSING_LINE.txt, never typed).
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
BODY = ROOT / "_scratch_0310" / "ord0310-post-body.md"
CLOSING = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt")
API = "https://api.github.com/repos/Canshu-King/CityNexus-Workspace/issues/1/comments"
OUT = ROOT / "_scratch_0310" / "ord0310-bus-post.json"


def secret() -> str:
    out = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True, check=True).stdout
    return next((l[len("password="):] for l in out.splitlines() if l.startswith("password=")), "")


def call(url: str, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET", headers={
        "Authorization": f"Bearer {secret()}", "Accept": "application/vnd.github+json",
        "User-Agent": "qoder-e345b9d6-ord0310"})
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    body = BODY.read_text(encoding="utf-8")
    closing = CLOSING.read_text(encoding="utf-8").strip()
    made = call(API, {"body": body})
    cid = made["id"]
    got = call(f"https://api.github.com/repos/Canshu-King/CityNexus-Workspace/issues/comments/{cid}")
    same = got["body"] == body
    tail = got["body"].rstrip().endswith(closing)
    note = {"comment_id": cid, "permalink": got["html_url"],
            "created_at": got["created_at"],
            "how_read": f"GET /repos/Canshu-King/CityNexus-Workspace/issues/comments/{cid}",
            "body_bytes_sent": len(body.encode("utf-8")), "body_bytes_read": len(got["body"].encode("utf-8")),
            "readback_equals_sent_byte_for_byte": same,
            "closing_line_verbatim_from_file": tail,
            "closing_line_bytes": len(closing.encode("utf-8")),
            "closing_line_blob": hashlib.sha1(b"blob %d\0" % len(closing.encode("utf-8"))
                                              + closing.encode("utf-8")).hexdigest(),
            "post_body_blob": hashlib.sha1(b"blob %d\0" % len(body.encode("utf-8"))
                                           + body.encode("utf-8")).hexdigest()}
    OUT.write_text(json.dumps(note, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                   newline="\n")
    print(json.dumps(note, ensure_ascii=False, indent=1))
    return 0 if same and tail else 3


raise SystemExit(main())
