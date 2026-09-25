"""Close this lane's bus post with its own receipt: one GET of the comment id, byte for byte.

A POST that dies on TLS tells me nothing about whether the server stored it, so the presence check
runs first and this file only ever records a comment I can read back. The tail check is what says the
commander's closing line survived the trip; it is compared against the bytes of CLOSING_LINE.txt, not
against a string I retyped.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
SC = ROOT / "_scratch_0310"
BODY = SC / (sys.argv[1] if len(sys.argv) > 1 else "ord0310-post-body-r3.md")
CID = (sys.argv[2] if len(sys.argv) > 2 else "5834964517")
OUT = SC / (sys.argv[3] if len(sys.argv) > 3 else "ord0310-bus-post-r3.json")
CLOSING = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt")
IDS = SC / "ord0310-bus-ids.json"


def secret() -> str:
    out = subprocess.run(["git", "credential", "fill"],
                         input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True, check=True).stdout
    value = ""
    for line in out.splitlines():
        if line.startswith("password="):
            value = line[len("password="):]
    return value


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


req = urllib.request.Request(
    f"https://api.github.com/repos/Canshu-King/CityNexus-Workspace/issues/comments/{CID}",
    headers={"Authorization": "Bearer " + secret(), "Accept": "application/vnd.github+json",
             "User-Agent": "qoder-e345b9d6-ord0310-delivery-proof"})
got = json.loads(urllib.request.urlopen(req, timeout=120).read())
sent = BODY.read_bytes()
read_back = got["body"].encode("utf-8")
closing = CLOSING.read_bytes().rstrip(b"\r\n")
note = {
    "order": "ORD-0310", "lane": "D e345b9d6", "kind": "BUS_DELIVERY_PROOF",
    "written_at": datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%:z"),
    "comment_id": got["id"], "permalink": got["html_url"], "created_at": got["created_at"],
    "read_by": f"GET /repos/Canshu-King/CityNexus-Workspace/issues/comments/{got['id']}",
    "body_file": BODY.name,
    "body_bytes_sent": len(sent), "body_bytes_read_back": len(read_back),
    "body_blob_sent": blob(sent), "body_blob_read_back": blob(read_back),
    "read_back_equals_sent_byte_for_byte": read_back == sent,
    "tail_is_the_closing_line_from_its_own_file": read_back.rstrip().endswith(closing),
    "closing_line_bytes": len(closing), "closing_line_blob": blob(closing),
    "transport_note": "the POST raised SSL UNEXPECTED_EOF_WHILE_READING on the response; a presence "
                      "check (review/ord0310_bus_presence.py) read the exact body blob back off the "
                      "bus before any retry was considered, so no second comment was created",
}
OUT.write_bytes((json.dumps(note, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
seen = json.loads(IDS.read_text(encoding="utf-8")) if IDS.exists() else {}
seen[blob(sent)] = {"comment_id": got["id"], "permalink": got["html_url"],
                    "posted_at": got["created_at"], "body_file": BODY.name}
IDS.write_bytes((json.dumps(seen, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
print(json.dumps(note, ensure_ascii=False, indent=1))
ok = note["read_back_equals_sent_byte_for_byte"] and note["tail_is_the_closing_line_from_its_own_file"]
print(f"OUT={OUT} blob={blob(OUT.read_bytes())} verdict={'DELIVERED' if ok else 'NOT_CONFIRMED'}")
raise SystemExit(0 if ok else 3)
