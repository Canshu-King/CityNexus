"""ORD-0512 lane 8ac89982: prove which generation the :4783 static port serves (day23).

Two proofs only, both read-only:
  1. the entry asset name is taken from THIS dist's own index.html (not from memory)
  2. the bytes served over 127.0.0.1:4783 equal the bytes on disk in THIS dist (sha1)
Plus the ownership note: the PID behind :4783 has --dist naming this same tree in its
CommandLine (read separately by PowerShell, copied into the json below).
"""
import hashlib
import io
import json
import os
import re
import sys
import urllib.request
from urllib.request import ProxyHandler, build_opener

DIST = sys.argv[1]
BASE = "http://127.0.0.1:4783"
OUT = sys.argv[2]

opener = build_opener(ProxyHandler({}))


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"Pragma": "no-cache"})
    with opener.open(req, timeout=20) as resp:
        return resp.status, resp.read()


def sha1(b):
    return hashlib.sha1(b).hexdigest()


def disk(rel):
    p = os.path.join(DIST, rel.replace("/", os.sep))
    if not os.path.exists(p):
        return None
    with io.open(p, "rb") as fh:
        return fh.read()


report = {"dist": DIST}

status, html = fetch("/")
report["root_status"] = status
report["root_bytes"] = len(html)
m = re.search(r'src="(/?assets/index-[^"]+\.js)"', html.decode("utf-8", "replace"))
entry = m.group(1).lstrip("/") if m else None
report["dist_index_entry"] = entry
cm = re.search(r'href="(/?assets/index-[^"]+\.css)"', html.decode("utf-8", "replace"))
report["dist_index_css"] = cm.group(1).lstrip("/") if cm else None

LABEL_MARK = b"v8-map-stop-label"
for rel in [n for n in (entry, report["dist_index_css"]) if n]:
    s, body = fetch("/" + rel)
    d = disk(rel)
    report[rel] = {
        "status": s,
        "served_bytes": len(body),
        "served_sha1": sha1(body),
        "on_disk": d is not None,
        "disk_bytes": None if d is None else len(d),
        "disk_sha1": None if d is None else sha1(d),
        "served_equals_disk": (d is not None) and (sha1(body) == sha1(d)),
        "label_hits_served": body.count(LABEL_MARK),
        "label_hits_disk": None if d is None else d.count(LABEL_MARK),
    }

with io.open(OUT, "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)
print(json.dumps(report, ensure_ascii=False, indent=1))
