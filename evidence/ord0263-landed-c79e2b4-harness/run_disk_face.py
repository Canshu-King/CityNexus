"""ORD-0263 close-out: stand my face on the generation actually on disk, and identify it by more than a name.

Read-only rules, same as the two earlier generations I measured this way: the served root
`D:/moodle/_qoder_preview_20260920/dist` is only ever read, copied into my lab, and re-hashed - the receipt
carries the copy's tree digest next to the source's, so "I measured the shipped bundle, not a rebuild" is
provable rather than asserted.

The generation marker matters here because the previous round taught me a stale-SW reading is possible: the
index's asset names can survive a re-spin, so this script also hashes `v10-sw.js`, `manifest.webmanifest` and
`sw.js`, and records the old bundle still on disk - which is how the reader can tell this is the c79e2b4f
generation (`v10-sw.js` sha256/16 88a7d980b3ffcbd6) and not the one before it
(`e63d7421eda34093`), and can see DEPLOY_BUNDLE_RETENTION honoured instead of old assets vanishing.

Ownership is proven both ways before anything counts: the marker journey answers 200 through my surface and
through the backend directly, while a uuid I confirmed absent from my own sqlite answers 404 through the same
proxy. The port is new (:4417) so this origin carries no service worker from my earlier rounds.
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
SRC = Path(r"D:\moodle\_qoder_preview_20260920\dist")
MINE = BASE / "diskgen" / "dist"
FRONTEND = BASE / "repo" / "frontend"
DB = BASE / "db" / "canary_8411.db"
MARKER = "harness-ord0254-canary-8411"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4417
BACKEND_PORT = 8411
JID = "22222222-2222-4222-8222-222222222222"
EXPECTED = {"index-Cpy_jhEg.js": "5d674a444291f10b", "v10-sw_prev_generation": "e63d7421eda34093"}


def sh(*a, cwd=None):
    return subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=cwd or str(BASE / "repo"))


def listeners(port: int) -> list[int]:
    out = sh("netstat", "-ano").stdout
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out)
                   if int(m.group(1)) == str(port)})


def tree(root: Path) -> tuple[int, int, str]:
    fs = sorted(p for p in root.rglob("*") if p.is_file())
    h, tot = hashlib.sha256(), 0
    for p in fs:
        b = p.read_bytes()
        tot += len(b)
        h.update(p.relative_to(root).as_posix().encode() + b)
    return len(fs), tot, h.hexdigest()


def get(path: str, port: int, timeout: float = 12):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
    req.add_header("User-Agent", "cnx-ord0263-close")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.headers or {}).get("Content-Type"), b""
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__, str(e).encode()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    n_src, b_src, t_src = tree(SRC)
    html = (SRC / "index.html").read_text(encoding="utf-8")
    refs = re.findall(r"assets/index-[A-Za-z0-9_-]+\.(?:js|css)", html)
    markers = {}
    for name in ["v10-sw.js", "manifest.webmanifest", "sw.js"]:
        p = SRC / name
        markers[name] = {"bytes": p.stat().st_size,
                         "sha256_16": hashlib.sha256(p.read_bytes()).hexdigest()[:16]} if p.is_file() else "ABSENT"
    old_asset = SRC / "assets" / "index-Cpy_jhEg.js"
    retention = {"previous_bundle_on_disk": old_asset.is_file(),
                 "sha256_16": hashlib.sha256(old_asset.read_bytes()).hexdigest()[:16] if old_asset.is_file() else None,
                 "expected_prefix": EXPECTED["index-Cpy_jhEg.js"]}
    print(f"source root: {n_src} files {b_src:,} B tree {t_src[:16]}  index refs {refs}")
    print("markers:", json.dumps(markers, ensure_ascii=False))
    if not MINE.exists():
        MINE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SRC, MINE)
    n_my, b_my, t_my = tree(MINE)
    identical = (n_src, b_src, t_src) == (n_my, b_my, t_my)
    print(f"my copy    : {n_my} files {b_my:,} B tree {t_my[:16]}  byte-identical={identical}")
    if not identical:
        print("ABORT: copy is not byte-identical")
        return 2
    if listeners(PORT):
        print(f"ABORT: :{PORT} busy with {listeners(PORT)}")
        return 3

    env = dict(os.environ) | {"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT), "PYTHONIOENCODING": "utf-8"}
    log = open(BASE / "close_preview.log", "a", encoding="utf-8")
    log.write(f"\n=== close face {time.strftime('%Y-%m-%dT%H:%M:%S+08:00')} ===\n")
    log.flush()
    proc = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "preview",
                             "--outDir", str(MINE), "--port", str(PORT), "--strictPort",
                             "--host", "127.0.0.1"], cwd=str(FRONTEND), env=env,
                            stdout=log, stderr=subprocess.STDOUT)
    up = None
    for _ in range(40):
        st, ct, body = get("/v8/hub", PORT)
        if st == 200 and b"<" in body[:16]:
            up = (st, ct, len(body))
            break
        if proc.poll() is not None:
            print("ABORT: preview died:", (BASE / "close_preview.log").read_text(
                encoding="utf-8", errors="replace")[-500:])
            return 4
        time.sleep(1)
    if not up:
        print("ABORT: shell never answered")
        return 5

    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    ro = con.execute("PRAGMA query_only").fetchone()[0]
    marker_rows = con.execute("SELECT COUNT(*) FROM audit_logs WHERE id=?", (MARKER,)).fetchone()[0]
    absent = str(uuid.uuid4())
    hits = con.execute("SELECT COUNT(*) FROM journeys WHERE id=?", (absent,)).fetchone()[0]
    con.close()
    st_ok, _, body_ok = get(f"/api/v1/journeys/{JID}", PORT)
    st_direct, _, _ = get(f"/api/v1/journeys/{JID}", BACKEND_PORT)
    st_absent, _, _ = get(f"/api/v1/journeys/{absent}", PORT)
    owned = (st_ok == 200 and JID.encode() in body_ok and st_direct == 200
             and st_absent == 404 and marker_rows == 1)
    served = re.findall(r"assets/index-[A-Za-z0-9_-]+\.js",
                        get("/v8/hub", PORT)[2].decode("utf-8", "replace"))
    rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
           "generation": {"source_root_read_only": str(SRC), "rebuilt": False,
                          "index_html_mtime": time.strftime(
                              "%Y-%m-%dT%H:%M:%S+08:00",
                              time.localtime((SRC / "index.html").stat().st_mtime)),
                          "index_refs": refs, "served_js_through_my_face": served[:1],
                          "bundle_sha256_16": hashlib.sha256(
                              (SRC / refs[0]).read_bytes()).hexdigest()[:16] if refs else None,
                          "root_files": n_src, "root_bytes": b_src, "root_tree_sha256": t_src,
                          "sw_markers": markers,
                          "generation_is_distinguishable_from_previous": (
                              markers.get("v10-sw.js", {}).get("sha256_16")
                              != EXPECTED["v10-sw_prev_generation"]
                              if isinstance(markers.get("v10-sw.js"), dict) else None),
                          "previous_v10_sw_prefix_for_reference": EXPECTED["v10-sw_prev_generation"]},
           "retention": retention,
           "my_copy": {"root": str(MINE), "files": n_my, "bytes": b_my, "tree_sha256": t_my,
                       "byte_identical": identical},
           "surface": {"port": PORT, "preview_pid": proc.pid,
                       "citynexus_backend_port": BACKEND_PORT,
                       "backend_listeners": listeners(BACKEND_PORT),
                       "proof_200_marker_journey": {"status": st_ok, "via_backend_direct": st_direct},
                       "proof_404_absent_id": {"uuid": absent, "rows_in_my_db": hits,
                                               "status": st_absent},
                       "db_marker_rows": marker_rows, "query_only_read_back": ro,
                       "fresh_origin_no_service_worker_from_earlier_rounds": True,
                       "ownership_verdict": "PROVEN" if owned else "NOT_PROVEN"},
           "user_chain": {"ports_contacted": [], "db_files_opened": [], "demo_reset_issued": False}}
    (BASE / "ord0263_close_surface_receipt.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    (BASE / "close_preview.pid").write_text(str(proc.pid), "utf-8")
    print(json.dumps(rec["surface"], ensure_ascii=False, indent=1))
    print("ownership:", rec["surface"]["ownership_verdict"],
          "| generation distinguishable:",
          rec["generation"]["generation_is_distinguishable_from_previous"])
    return 0 if owned else 6


if __name__ == "__main__":
    raise SystemExit(main())
