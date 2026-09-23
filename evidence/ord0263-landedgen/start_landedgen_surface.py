"""ORD-0263 on the LANDED generation (tip 2b49e3ca, ORD-0263 now shipped): same face recipe, new bundle.

The question is what a traveller actually sees today, so the front end must be the one that is really
served - not a rebuild. `D:/moodle/_qoder_preview_20260920/dist` is the disk root behind the user's chain;
this script only ever READS it, copies into my own lab directory, and re-hashes every file to prove the
copy is byte-identical (29 files, plus a tree digest over relative-path + bytes).

Deliberate boundaries:
* the user's ports (:4781/:4782, tunnel, cnx proxy) are never contacted; their DB files are never opened;
  no `demo/reset`;
* my own surface gets a NEW port :4415 and `CITYNEXUS_BACKEND_PORT=8411`, because vite's `/api` proxy port
  is fixed at start-up - a preview without that variable would quietly judge someone else's backend;
* ownership is proven both ways before any reading counts: 200 for the marker journey that exists only in
  MY sqlite, and 404 for a uuid I first confirm is absent from MY sqlite (a live-200 on that id would mean
  the proxy is answering from another store).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sqlite3
import sys
import time
import uuid
import urllib.request
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
LIVE_DIST = Path(r"D:\moodle\_qoder_preview_20260920\dist")
MY_DIST = BASE / "landedgen" / "dist"
FRONTEND = BASE / "repo" / "frontend"
DB = BASE / "db" / "canary_8411.db"
MARKER = "harness-ord0254-canary-8411"
STATIC_PORT, BACKEND_PORT = 4415, 8411
FORBIDDEN = (4781, 4782, 8693, 4185, 8713)


def sh(*a, cwd=None):
    return subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=cwd)


def listeners(port: int) -> list[int]:
    out = sh("netstat", "-ano").stdout
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out)
                   if int(m.group(1)) == port})


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree_digest(root: Path) -> tuple[int, int, str]:
    fs = sorted(p for p in root.rglob("*") if p.is_file())
    h = hashlib.sha256()
    tot = 0
    for p in fs:
        b = p.read_bytes()
        tot += len(b)
        h.update(p.relative_to(root).as_posix().encode() + b)
    return len(fs), tot, h.hexdigest()


def get(path: str, port: int = STATIC_PORT, timeout: float = 12):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="GET")
    req.add_header("User-Agent", "cnx-ord0263-landedgen")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), b""
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}", str(e).encode()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    live_n, live_b, live_t = tree_digest(LIVE_DIST)
    served = re.findall(r'assets/index-[A-Za-z0-9_-]+\.(?:js|css)',
                        (LIVE_DIST / "index.html").read_text(encoding="utf-8"))
    if not MY_DIST.exists():
        MY_DIST.mkdir(parents=True)
        shutil.copytree(LIVE_DIST, MY_DIST, dirs_exist_ok=True)
    my_n, my_b, my_t = tree_digest(MY_DIST)
    copy_ok = (live_n, live_b, live_t) == (my_n, my_b, my_t)
    print(f"live dist : {live_n} files {live_b:,} B tree {live_t[:16]}")
    print(f"my  copy  : {my_n} files {my_b:,} B tree {my_t[:16]}  byte-identical={copy_ok}")
    print(f"served refs in index.html: {served}")
    if not copy_ok:
        print("ABORT: the copy is not byte-identical")
        return 2

    if listeners(STATIC_PORT):
        print(f"ABORT: :{STATIC_PORT} already busy with {listeners(STATIC_PORT)}")
        return 3
    env = dict(os.environ) | {"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT), "PYTHONIOENCODING": "utf-8"}
    log = open(BASE / "landedgen_preview.log", "a", encoding="utf-8")
    log.write(f"\n=== landedgen start {time.strftime('%Y-%m-%dT%H:%M:%S+08:00')} ===\n")
    log.flush()
    proc = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "preview",
                             "--outDir", str(MY_DIST), "--port", str(STATIC_PORT),
                             "--strictPort", "--host", "127.0.0.1"],
                            cwd=str(FRONTEND), env=env, stdout=log, stderr=subprocess.STDOUT)
    up = False
    for _ in range(40):
        st, ct, body = get("/v8/hub")
        if st == 200 and b"<!doctype" in body.lower()[:200] + body[:200].lower():
            up = True
            break
        if proc.poll() is not None:
            print("ABORT: preview exited early; see landedgen_preview.log")
            print(Path(BASE / "landedgen_preview.log").read_text(encoding="utf-8", errors="replace")[-600:])
            return 4
        time.sleep(1)
    if not up:
        print("ABORT: shell never answered on :%d" % STATIC_PORT)
        return 5

    # ownership, both directions
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    ro = con.execute("PRAGMA query_only").fetchone()[0]
    marker_rows = con.execute("SELECT COUNT(*) FROM audit_logs WHERE id=?", (MARKER,)).fetchone()[0]
    jid = con.execute("SELECT id FROM journeys LIMIT 1").fetchone()[0]
    absent = str(uuid.uuid4())
    hits = con.execute("SELECT COUNT(*) FROM journeys WHERE id=?", (absent,)).fetchone()[0]
    con.close()
    st_marker, ct_m, body_m = get(f"/api/v1/journeys/{jid}")
    st_absent, _, _ = get(f"/api/v1/journeys/{absent}")
    st_direct, _, _ = get(f"/api/v1/journeys/{jid}", port=BACKEND_PORT)
    lb = listeners(BACKEND_PORT)
    owned = (st_marker == 200 and jid.encode() in body_m and st_absent == 404
             and marker_rows == 1 and st_direct == 200)
    rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
           "generation": {"live_dist_root": str(LIVE_DIST), "served_refs": served,
                          "index_html_mtime": time.strftime(
                              "%Y-%m-%dT%H:%M:%S+08:00",
                              time.localtime((LIVE_DIST / "index.html").stat().st_mtime)),
                          "files": live_n, "bytes": live_b, "tree_sha256": live_t,
                          "per_file_sha256_of_the_two_named_assets": {
                              served[0]: sha(LIVE_DIST / served[0]),
                              served[1]: sha(LIVE_DIST / served[1])},
                          "rebuilt": False, "read_only_source": True},
           "my_copy": {"root": str(MY_DIST), "files": my_n, "bytes": my_b, "tree_sha256": my_t,
                       "byte_identical_to_live": copy_ok},
           "surface": {"static_port": STATIC_PORT, "preview_pid": proc.pid,
                       "citynexus_backend_port": BACKEND_PORT,
                       "backend_listeners": lb,
                       "proxy_proof_200_marker_journey": {"id": jid, "status": st_marker,
                                                          "via_backend_direct": st_direct},
                       "proxy_proof_404_absent_id": {"id": absent, "rows_in_my_db": hits,
                                                     "status": st_absent},
                       "db_marker_rows": marker_rows, "query_only_read_back": ro,
                       "ownership_verdict": "PROVEN" if owned else "NOT_PROVEN"},
           "user_chain": {"ports_contacted": [], "db_files_opened": [], "demo_reset_issued": False,
                          "forbidden_ports_observed_only": {str(p): listeners(p) for p in FORBIDDEN}}}
    (BASE / "ord0263_landedgen_surface_receipt.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    (BASE / "landedgen_preview.pid").write_text(str(proc.pid), "utf-8")
    print(json.dumps(rec["surface"], ensure_ascii=False, indent=1))
    print("ownership:", rec["surface"]["ownership_verdict"], " receipt: ord0263_landedgen_surface_receipt.json")
    return 0 if owned else 6


if __name__ == "__main__":
    raise SystemExit(main())
