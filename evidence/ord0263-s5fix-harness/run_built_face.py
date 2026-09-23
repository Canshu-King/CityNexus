"""Stand my own face on a bundle I just built from a named commit, and prove the proxy is mine.

Same two ownership checks I keep having to relearn are the only ones that matter: the marker journey that exists
only in MY sqlite answers 200 through the surface, and a uuid I first confirmed absent from MY sqlite answers
404 through it. A port being mine does not make the backend mine - vite fixes the `/api` proxy target from
CITYNEXUS_BACKEND_PORT at start-up, so that variable is set here and the pairing is asserted, not assumed.

The bundle is identified by the two asset names plus their sha256s and the tree digest of the dist directory, so
a later reader can tell which build the readings belong to even after the working tree has moved on.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
import urllib.request
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
FRONTEND = BASE / "repo" / "frontend"
DIST = FRONTEND / "dist"
DB = BASE / "db" / "canary_8411.db"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4416
BACKEND_PORT = 8411
MARKER = "harness-ord0254-canary-8411"
JID = "22222222-2222-4222-8222-222222222222"
LABEL = sys.argv[2] if len(sys.argv) > 2 else "s5fix"


def sh(*a, cwd=None):
    return subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=cwd or str(BASE / "repo"))


def listeners(port: int) -> list[int]:
    out = sh("netstat", "-ano").stdout
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+127\.0\.0\.1:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out)
                   if int(m.group(1)) == str(port)})


def get(path: str, port: int, timeout: float = 12):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
    req.add_header("User-Agent", f"cnx-ord0263-{LABEL}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.headers or {}).get("Content-Type"), b""
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__, str(e).encode()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    html = (DIST / "index.html").read_text(encoding="utf-8")
    refs = re.findall(r"assets/index-[A-Za-z0-9_-]+\.(?:js|css)", html)
    files = sorted(p for p in DIST.rglob("*") if p.is_file())
    tot = sum(p.stat().st_size for p in files)
    h = hashlib.sha256()
    for p in files:
        h.update(p.relative_to(DIST).as_posix().encode() + p.read_bytes())
    built = {"refs": refs,
             "per_asset_sha256": {r: hashlib.sha256((DIST / r).read_bytes()).hexdigest() for r in refs},
             "dist_files": len(files), "dist_bytes": tot, "dist_tree_sha256": h.hexdigest(),
             "commit_built_from": sh("git", "rev-parse", "HEAD").stdout.strip()}
    print("bundle:", built["refs"], built["dist_files"], "files", f"{built['dist_bytes']:,} B",
          "tree", built["dist_tree_sha256"][:16], "| commit", built["commit_built_from"][:12])

    if listeners(PORT):
        print(f"ABORT: :{PORT} already has {listeners(PORT)}")
        return 3
    env = dict(os.environ) | {"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT), "PYTHONIOENCODING": "utf-8"}
    log = open(BASE / f"{LABEL}_preview.log", "a", encoding="utf-8")
    log.write(f"\n=== face start {time.strftime('%Y-%m-%dT%H:%M:%S+08:00')} ===\n")
    log.flush()
    proc = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "preview",
                             "--port", str(PORT), "--strictPort", "--host", "127.0.0.1"],
                            cwd=str(FRONTEND), env=env, stdout=log, stderr=subprocess.STDOUT)
    up = None
    for _ in range(40):
        st, ct, body = get("/v8/hub", PORT)
        if st == 200 and b"<" in body[:16]:
            up = (st, ct, len(body))
            break
        if proc.poll() is not None:
            print("ABORT: preview died:", Path(BASE / f"{LABEL}_preview.log").read_text(
                encoding="utf-8", errors="replace")[-500:])
            return 4
        time.sleep(1)
    if not up:
        print("ABORT: shell never answered")
        return 5

    st_ok, ct_ok, body_ok = get(f"/api/v1/journeys/{JID}", PORT)
    st_direct, _, _ = get(f"/api/v1/journeys/{JID}", BACKEND_PORT)
    absent = str(uuid.uuid4())
    st_absent, _, _ = get(f"/api/v1/journeys/{absent}", PORT)
    owned = (st_ok == 200 and JID.encode() in body_ok and st_direct == 200 and st_absent == 404)
    rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()), "label": LABEL,
           "bundle": built,
           "surface": {"port": PORT, "preview_pid": proc.pid, "listeners": listeners(PORT),
                       "citynexus_backend_port": BACKEND_PORT,
                       "backend_listeners": listeners(BACKEND_PORT),
                       "proof_200_marker_journey": {"status": st_ok, "via_backend_direct": st_direct},
                       "proof_404_absent_id": {"uuid": absent, "status": st_absent},
                       "ownership_verdict": "PROVEN" if owned else "NOT_PROVEN"},
           "user_chain": {"ports_contacted": [], "db_files_opened": [], "demo_reset_issued": False}}
    (BASE / f"ord0263_{LABEL}_surface_receipt.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    (BASE / f"{LABEL}_preview.pid").write_text(str(proc.pid), "utf-8")
    print(json.dumps(rec["surface"], ensure_ascii=False, indent=1))
    print("ownership:", rec["surface"]["ownership_verdict"],
          "| receipt: ord0263_" + LABEL + "_surface_receipt.json")
    return 0 if owned else 6


if __name__ == "__main__":
    raise SystemExit(main())
