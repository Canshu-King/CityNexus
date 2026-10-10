"""ORD-0513 · what the three doors actually answer, in their own words.

Nothing here touches a screen: this is the *original* side of the order -- the sentence the server
puts in `error.message` for each of the three named refusals, with the status, the reason token and
the keys the `details` face carries.  The order forbids changing the codes and the `details` shape,
so both are recorded before and after and compared by name, not by impression.

The store is a copy.  `D:/moodle/_qoder_preview_20260920/_preview.db` is opened read-only to be
copied and is never written; every row this file creates lands in a private file under `backend/`.
"""
import io
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
WT = r"D:/moodle/_qoder_newlane_ord0444_20260929/wt2"
BACKEND = os.path.join(WT, "backend")
SC = r"D:/moodle/_qoder_newlane_ord0444_20260929/scratch"
PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
PREVIEW_DB = r"D:/moodle/_qoder_preview_20260920/_preview.db"
OUT = os.path.join(SC, "ord0513_doors_%s.json" % sys.argv[1] if len(sys.argv) > 1
                   else "ord0513_doors_run.json")
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
ENV = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(k, None)

out = {"generated_at": time.strftime("%m-%d %H:%M:%S"),
       "head": subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True,
                               text=True, errors="replace").stdout.strip(),
       "preview_db_bytes_at_copy": os.path.getsize(PREVIEW_DB)}


def free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


DB = os.path.join(BACKEND, "ord0513_%s.db" % uuid.uuid4().hex[:8])
# The preview store is opened read-only to be measured, copied byte for byte, and then never handed
# to the server: every write below lands in the copy under `backend/`.
with sqlite3.connect("file:%s?mode=ro" % PREVIEW_DB.replace("\\", "/"), uri=True) as src:
    preview_pages = src.execute("PRAGMA page_count").fetchone()[0]
    preview_integrity = src.execute("PRAGMA integrity_check").fetchone()[0]
preview_stat0 = os.stat(PREVIEW_DB)
shutil.copyfile(PREVIEW_DB, DB)
out["private_db"] = os.path.basename(DB)
out["preview_store"] = {"page_count": preview_pages, "integrity": preview_integrity,
                        "bytes_before": preview_stat0.st_size,
                        "mtime_ns_before": preview_stat0.st_mtime_ns}

PORT = free_port()
env = dict(ENV, CITYNEXUS_DATABASE_URL="sqlite:///./" + os.path.basename(DB),
           CITYNEXUS_DEMO_MODE="true")
log = io.open(os.path.join(SC, "uvicorn_0513.log"), "wb")
kid = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(PORT)], cwd=BACKEND, env=env, stdout=log,
                       stderr=subprocess.STDOUT)
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for _ in range(180):
    try:
        with OP.open("http://127.0.0.1:%d/api/v1/health" % PORT, timeout=6) as r:
            if r.status == 200:
                break
    except Exception:
        time.sleep(1)
else:
    io.open(OUT, "w", encoding="utf-8").write(json.dumps({"fatal": "backend never came up"}))
    raise SystemExit("backend never came up")


def call(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=data, method=method)
    if data:
        req.add_header("content-type", "application/json")
    try:
        with OP.open(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"unparsed_head": raw[:160].decode("utf-8", "replace")}


def read_door(method, path, body, expect_reason):
    """One refusal, said in the server's own words, plus what the `details` face carries with it."""
    status, ans = call(method, path, body)
    err = (ans or {}).get("error") or {}
    details = err.get("details")
    msg = err.get("message")
    out["refusals"].append({
        "reason_code": err.get("reason_code"),
        "expected": expect_reason,
        "http_status": status,
        "message": msg,
        "message_has_uuid": bool(UUID_RE.search(msg or "")),
        "message_uuid_count": len(UUID_RE.findall(msg or "")),
        "message_contains_given_ids": sorted(
            name for name, value in sorted((body or {}).items())
            if isinstance(value, str) and value and value in (msg or "")),
        "message_key": err.get("message_key"),
        "code": err.get("code"),
        "details_keys": sorted((details or {}).keys()) if isinstance(details, dict) else None,
        "details_has_uuid": bool(re.search(r"[0-9a-f]{8}-", json.dumps(details or "", ensure_ascii=False), re.I)),
        "trace_id_present": bool(err.get("trace_id")),
        "error_receipt_id_present": bool(err.get("error_receipt_id")),
    })


out["refusals"] = []
with sqlite3.connect(DB) as con:
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    traveler = con.execute("SELECT id FROM travelers ORDER BY id LIMIT 1").fetchone()[0]
    places = [r[0] for r in con.execute("SELECT id FROM places ORDER BY id LIMIT 3")]
    journey = None
    if "journeys" in tables:
        row = con.execute("SELECT id FROM journeys LIMIT 1").fetchone()
        journey = row[0] if row else None
out["store"] = {"tables_present": len(tables), "traveler": traveler[:8] + "…",
                "places": len(places), "journey": (journey or "")[:8] + "…"}

# -- MEMBER_TRAVELER_UNKNOWN: name an owner no row carries.
read_door("POST", "/api/v1/collections",
          {"name": "ORD-0513 反例架", "owner_traveler_id": str(uuid.uuid4())},
          "MEMBER_TRAVELER_UNKNOWN")

# -- a real shelf, so the two place refusals have a folder that exists.
status, shelf = call("POST", "/api/v1/collections",
                     {"name": "ORD-0513 架子", "owner_traveler_id": traveler})
out["shelf_created"] = {"http_status": status, "id_present": bool((shelf or {}).get("id"))}
folder_id = (shelf or {}).get("id")

# -- PLACE_NOT_FOUND: a place id this server does not hold.
read_door("POST", "/api/v1/collections/%s/items" % folder_id,
          {"place_id": str(uuid.uuid4())}, "PLACE_NOT_FOUND")

# -- PLACE_ALREADY_IN_COLLECTION: the same place on the same shelf, twice.
first = call("POST", "/api/v1/collections/%s/items" % folder_id, {"place_id": places[0]})
out["first_add"] = {"http_status": first[0]}
read_door("POST", "/api/v1/collections/%s/items" % folder_id,
          {"place_id": places[0]}, "PLACE_ALREADY_IN_COLLECTION")

# -- and the membership door's own copy of the third sentence, which the contract says uses the
#    same words; measured separately because "the same words" is a claim, not a fact.
if journey:
    read_door("POST", "/api/v1/journeys/%s/members" % journey,
              {"traveler_id": str(uuid.uuid4()), "role": "COLLABORATOR", "invited_by": traveler},
              "MEMBER_TRAVELER_UNKNOWN")

out["reason_codes_seen"] = sorted({str(r["reason_code"]) for r in out["refusals"]})
out["expected_vs_seen_mismatch"] = [r["expected"] for r in out["refusals"]
                                 if r["reason_code"] != r["expected"]]
preview_stat1 = os.stat(PREVIEW_DB)
out["preview_store_untouched"] = {
    "bytes_equal": preview_stat0.st_size == preview_stat1.st_size,
    "mtime_ns_equal": preview_stat0.st_mtime_ns == preview_stat1.st_mtime_ns,
    "bytes_after": preview_stat1.st_size}
subprocess.run(["taskkill", "/PID", str(kid.pid), "/T", "/F"], capture_output=True)
time.sleep(4)
for suffix in ("", "-wal", "-shm"):
    try:
        if os.path.exists(DB + suffix):
            os.remove(DB + suffix)
    except PermissionError:
        print("LEFTOVER_DB", DB + suffix)
log.close()
io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("WROTE", OUT, os.path.getsize(OUT), "bytes")
for r in out["refusals"]:
    print("  %-28s http_status=%s uuid_in_message=%s details_keys=%s" % (
        r["reason_code"], r["http_status"], r["message_has_uuid"], r["details_keys"]))
    print("      message: %s" % (r["message"] or "")[:120])
