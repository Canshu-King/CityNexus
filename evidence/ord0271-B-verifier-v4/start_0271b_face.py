"""ORD-0271-B: put a named build of MY OWN clone behind my own face on :4418, and prove which bytes answer.

Why this exists: `run_disk_face.py` copied the *user's served root* and was only ever meant to read it.
For 0271-B the thing under test is my own single-variable mutant of candidate c79e2b4f, so the root has to
be a copy of my build directory, and swapping control <-> mutant must be provable rather than remembered.

What each run records, all of it measured:
* the previous listener on the port is killed only after its command line is read back and shown to be a
  `vite.js preview` of a root inside my own lab directory - another lane's process on a number I happen to
  want is not mine to signal;
* every file copied src -> dest is re-hashed on both sides, and the tree digest over (relative path + bytes)
  must be equal before the server is started;
* `index.html` as served by the face is parsed for the asset it names, and that asset's sha256 is taken from
  the bytes the face actually answers over HTTP, not from disk;
* ownership both ways: the marker journey answers 200 through my face and through my backend directly, and a
  uuid first confirmed absent from my own sqlite answers 404 through the same proxy.

Boundaries, same as every earlier round: the user's ports (:4781/:4782/tunnel/proxy) are never contacted,
their DB files are never opened, `demo/reset` is never issued, and `CITYNEXUS_BACKEND_PORT=8411` is set
because vite's proxy port is fixed at start-up - without it this face would quietly judge someone else's
backend.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
FRONTEND = BASE / "repo" / "frontend"
DEST = BASE / "diskgen" / "dist"
DB = BASE / "db" / "canary_8411.db"
MARKER = "harness-ord0254-canary-8411"
JID = "22222222-2222-4222-8222-222222222222"
PORT = 4418
BACKEND_PORT = 8411


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())


def ps(pid: int) -> str:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    return out.strip()


def listeners(port: int) -> list[int]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    if out.count("\n") < 200:
        raise SystemExit(f"ABORT: netstat returned {out.count(chr(10))} lines; that is not a free port")
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out)
                   if int(m.group(1)) == int(port)})   # int==str here reads every port as free


def tree(root: Path) -> tuple[int, int, str]:
    fs = sorted(p for p in root.rglob("*") if p.is_file())
    h, tot = hashlib.sha256(), 0
    for p in fs:
        b = p.read_bytes()
        tot += len(b)
        h.update(p.relative_to(root).as_posix().encode() + b)
    return len(fs), tot, h.hexdigest()


def per_asset(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): {"bytes": p.stat().st_size,
                                             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(root.rglob("*")) if p.is_file()}


def get(path: str, port: int, timeout: float = 12):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
    req.add_header("User-Agent", "cnx-ord0271b-face")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.headers or {}).get("Content-Type"), b""
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__, str(e).encode()


def free_port(label: str) -> dict:
    """Signal only what I can prove is mine: a vite preview of a root inside my own lab directory."""
    note = {"port": PORT, "found": [], "killed": [], "free_after": None}
    for _ in range(6):
        pids = listeners(PORT)
        if not pids:
            note["free_after"] = True
            return note
        for pid in pids:
            cl = ps(pid)
            mine = ("vite.js" in cl and "preview" in cl and str(BASE) in cl)
            note["found"].append({"pid": pid, "mine": mine, "command_line": cl[:260]})
            if not mine:
                print(f"ABORT: :{PORT} pid {pid} is not mine to signal: {cl[:200]}")
                note["free_after"] = False
                return note
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
            note["killed"].append(pid)
        time.sleep(1.5)
    note["free_after"] = not listeners(PORT)
    return note


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="build directory whose dist/ goes behind the face")
    ap.add_argument("--gen", required=True, help="control | mutant-<n>, recorded in the receipt name")
    a = ap.parse_args()
    SRC = BASE / a.src / "dist"
    if not SRC.is_dir():
        print(f"ABORT: no such build: {SRC}")
        return 2

    n_s, b_s, t_s = tree(SRC)
    assets_src = per_asset(SRC)
    print(f"[{a.gen}] source build {SRC}: {n_s} files {b_s:,} B tree {t_s[:16]}")

    free = free_port(a.gen)
    print("port:", json.dumps(free, ensure_ascii=False)[:400])
    if not free["free_after"]:
        return 3

    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SRC, DEST)
    n_d, b_d, t_d = tree(DEST)
    assets_dst = per_asset(DEST)
    identical = (n_s, b_s, t_s) == (n_d, b_d, t_d) and assets_src == assets_dst
    print(f"copied to {DEST}: {n_d} files {b_d:,} B tree {t_d[:16]} byte-identical={identical}")
    if not identical:
        return 4

    env = dict(os.environ) | {"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT), "PYTHONIOENCODING": "utf-8"}
    log = open(BASE / "0271b_preview.log", "a", encoding="utf-8")
    log.write(f"\n=== 0271-B face gen={a.gen} src={SRC} {now()} ===\n")
    log.flush()
    proc = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "preview",
                             "--outDir", str(DEST), "--port", str(PORT), "--strictPort",
                             "--host", "127.0.0.1"], cwd=str(FRONTEND), env=env,
                            stdout=log, stderr=subprocess.STDOUT)
    up = None
    for _ in range(45):
        st, ct, body = get("/v8/hub", PORT)
        if st == 200 and b"<" in body[:16]:
            up = {"status": st, "content_type": ct, "bytes": len(body)}
            break
        if proc.poll() is not None:
            print("ABORT: preview died:", (BASE / "0271b_preview.log").read_text(
                encoding="utf-8", errors="replace")[-600:])
            return 5
        time.sleep(1)
    if not up:
        print("ABORT: shell never answered 200 on :%d" % PORT)
        return 6

    # what the face actually answers, hashed off the wire
    st_html, _, body_html = get("/v8/hub", PORT)
    named = re.findall(r"assets/index-[A-Za-z0-9_-]+\.js", body_html.decode("utf-8", "replace"))
    wire = {}
    for rel in sorted(set(named + re.findall(r"assets/index-[A-Za-z0-9_-]+\.css",
                                             body_html.decode("utf-8", "replace")))):
        st_a, ct_a, body_a = get("/" + rel, PORT)
        wire[rel] = {"status": st_a, "content_type": ct_a, "bytes": len(body_a),
                     "sha256": hashlib.sha256(body_a).hexdigest(),
                     "equals_source_build_file": assets_src.get(rel, {}).get("sha256")
                     == hashlib.sha256(body_a).hexdigest()}

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
    owned = bool(st_ok == 200 and JID.encode() in body_ok and st_direct == 200
                 and st_absent == 404 and marker_rows == 1)

    rec = {"at": now(), "gen": a.gen, "build_source": str(SRC),
           "source_build": {"files": n_s, "bytes": b_s, "tree_sha256": t_s, "assets": assets_src},
           "served_root": {"path": str(DEST), "files": n_d, "bytes": b_d, "tree_sha256": t_d,
                           "copy_byte_identical": identical},
           "shell": {"status": st_html, "names_asset": named[:1], "answered_over_http": wire},
           "previous_listener": free,
           "surface": {"port": PORT, "preview_pid": proc.pid,
                       "actual_listener_pids_after_start": listeners(PORT),
                       "spawned_pid_is_the_listener": listeners(PORT) == [proc.pid],
                       "listener_command_lines": [ps(p)[:200] for p in listeners(PORT)],
                       "citynexus_backend_port": BACKEND_PORT,
                       "backend_listeners": listeners(BACKEND_PORT),
                       "proof_200_marker_journey": {"status": st_ok, "via_backend_direct": st_direct},
                       "proof_404_absent_id": {"uuid": absent, "rows_in_my_db": hits, "status": st_absent},
                       "db_marker_rows": marker_rows, "query_only_read_back": ro,
                       "ownership_verdict": "PROVEN" if owned else "NOT_PROVEN"},
           "user_chain": {"ports_contacted": [], "db_files_opened": [], "demo_reset_issued": False}}
    out = BASE / f"ord0271B_face_{a.gen}.json"
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    (BASE / "0271b_preview.pid").write_text(str(proc.pid), "utf-8")
    print("face pid", proc.pid, "| ownership", rec["surface"]["ownership_verdict"],
          "| shell names", named[:1], "| wire==build",
          {k: v["equals_source_build_file"] for k, v in wire.items()})
    print("receipt:", out.name, f"{out.stat().st_size:,} B")
    return 0 if owned and identical else 7


if __name__ == "__main__":
    raise SystemExit(main())
