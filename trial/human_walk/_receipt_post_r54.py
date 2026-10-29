"""Publish a receipt block to Issue #42 and PR #43, behind a gate that lives in the same door.

The gate is not a suggestion: every `path:line` coordinate in the block must resolve in the rescue tree (file
exists AND has at least that many lines) or the POST is refused.  A receipt whose coordinates are dead is worse
than no receipt, because the next shift will cite it.  The closing line is read from the reference tree, never
typed, and after each POST the comment is read back by its own id to confirm the tail.
"""
from __future__ import annotations

import io
import json
import os
import re
import urllib.request

REPO = r"D:\moodle\_cmdr_rescue_v3_1022"
BLOCK = os.environ.get("RECEIPT_BLOCK") or r"D:\moodle\_cmdr_v3_port_1022\_receipt_54_block.md"
TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
CLOSING_FILE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\CLOSING_LINE.txt"
ENDPOINTS = (("issue-42", "/repos/Canshu-King/CityNexus/issues/42/comments"),
             ("pr-43", "/repos/Canshu-King/CityNexus/issues/43/comments"))
SEARCH_DIRS = ("", "trial/human_walk", "trial/results", "trial/results/20261022_v3_human_chrome", "frontend", "backend")

COOR = re.compile(r"`([\w./\\-]+\.(?:ts|tsx|py|mjs|ps1|md|txt|png|json|css)):(\d+)`")
LINE_CACHE: dict[str, int] = {}


def line_count(path):
    if path not in LINE_CACHE:
        with io.open(path, "r", encoding="utf-8", errors="replace") as handle:
            LINE_CACHE[path] = sum(1 for _ in handle)
    return LINE_CACHE[path]


def resolve(name):
    for prefix in SEARCH_DIRS:
        candidate = os.path.join(REPO, prefix, name.replace("/", os.sep)) if prefix else os.path.join(REPO, name.replace("/", os.sep))
        if os.path.isfile(candidate):
            return candidate
    return None


body = io.open(BLOCK, "r", encoding="utf-8").read().rstrip()
citations = COOR.findall(body)
dead = []
for name, line in citations:
    path = resolve(name)
    if path is None:
        dead.append((name, line, "no such file"))
    elif line_count(path) < int(line):
        dead.append((name, line, "file has %d lines" % line_count(path)))
print("COORDINATES checked=%d distinct=%d dead=%d" % (len(citations), len(set(citations)), len(dead)))
for item in dead:
    print("  DEAD", item)

amap = (os.environ.get("CITYNEXUS_AMAP_WEB_KEY") or "").strip()
leaks = sum(1 for marker in (amap, "Authorization") if marker and marker in body)
print("CREDENTIAL_SCAN key_len=%d hits=%d" % (len(amap), leaks))

if dead or leaks:
    raise SystemExit("REFUSED: gate red (dead=%d credential_hits=%d) -- nothing was posted" % (len(dead), leaks))

if os.environ.get("RECEIPT_DRY") == "1":
    raise SystemExit("DRY_RUN: gate green, nothing posted")

closing = io.open(CLOSING_FILE, "r", encoding="utf-8").read().strip()
payload = body + "\n\n" + closing + "\n"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
token = io.open(TOKEN_FILE, "r", encoding="utf-8").read().strip()


def call(path, method, data=None):
    req = urllib.request.Request("https://api.github.com" + path, method=method)
    if data is not None:
        req.data = json.dumps(data).encode("utf-8")
    req.add_header("Authorization", "token " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "cmdr-receipt-poster")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with opener.open(req, timeout=180) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


for label, path in ENDPOINTS:
    status, created = call(path, "POST", {"body": payload})
    comment_id = created.get("id")
    print("POST %s http_status=%s id=%s created=%s" % (label, status, comment_id, created.get("created_at")))
    read_status, readback = call("/repos/Canshu-King/CityNexus/issues/comments/%s" % comment_id, "GET")
    rb = (readback.get("body") or "").strip()
    print("READBACK %s http_status=%s bytes=%d tail_matches=%s head_matches=%s"
          % (label, read_status, len(rb.encode("utf-8")), rb.endswith(closing),
             rb.startswith(body.splitlines()[0])))
    if not rb.endswith(closing):
        print("  WARN the posted comment does not end with the closing line")
