"""ORD-0267 shaping run (READ-ONLY on the product: nothing here edits source, nothing is committed).

What it produces is a baseline reading for the ruling "which layer has to catch a cold offline deep
link": the shell is served from a tree exported at the authoritative tip (`git archive d2665e2…`), the
SW facts are read out of the browser, and the two client states are kept apart --

  A  a client that installs the shell while the site is up            (profile_install)
  B  that same client after the WHOLE site is down, on /v8/hub, /, /v8/discover
  C  a device that never visited, offline from the start              (profile_cold)

Ports are my own (:4441 preview, :8441 backend); forbidden ports get zero requests; no demo/reset;
the DB is a new file, not a copy.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TIP = "d2665e25855aeb265329266831983de42321697d"
REPO = pathlib.Path(r"D:\moodle\_qoder_integration_20260919")
BASE = pathlib.Path(r"D:\moodle\_qoder_b_ord0267_20260923")
TREE = BASE / "tree"
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
PORT, PREVIEW_PORT = 8441, 4441
DB = BASE / "db" / "ord0267_8441.db"
ENV = {"CITYNEXUS_DATABASE_URL": f"sqlite:///{DB.as_posix()}", "CITYNEXUS_ENV": "dev",
       "CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_AI_ENABLED": "false",
       "CITYNEXUS_GUARDIAN_AUTORUN": "false", "DEEPSEEK_API_KEY": "", "CITYNEXUS_AI_API_KEY": "",
       "CITYNEXUS_ANYWHERE_RESOLVER": "off", "CITYNEXUS_PHOTON_BASE_URL": "http://127.0.0.1:9",
       "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
DETACHED = 0x00000008 | 0x00000200
NM_SRC = pathlib.Path(r"D:\moodle\_qoder_integration_20260919\frontend\node_modules")


def listeners(port: int) -> list[int]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out)
                   if int(m.group(1)) == port})


def ok(url: str, timeout: int = 6) -> bool:
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def spawn(cmd, cwd, log, env):
    with open(log, "a", encoding="utf-8") as fh:
        return subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=fh, stderr=subprocess.STDOUT,
                                creationflags=DETACHED)


def kill(pids):
    for pid in dict.fromkeys(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")


def main() -> int:
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "db").mkdir(parents=True, exist_ok=True)
    busy = {str(p): listeners(p) for p in (PORT, PREVIEW_PORT)}
    if any(busy.values()):
        print(f"ABORT: my ports are not free: {busy}")
        return 2

    # 1) export the authoritative tree (git archive, not a checkout, not a patch apply)
    if not (TREE / "frontend" / "package.json").exists():
        TREE.mkdir(parents=True, exist_ok=True)
        p = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", TIP,
                            "frontend", "backend", "data", "contracts"], capture_output=True)
        assert p.returncode == 0, p.stderr[:200]
        subprocess.run(["tar", "-x", "-C", str(TREE)], input=p.stdout, check=True)
        print(f"exported {TIP[:12]} -> {TREE}")
    else:
        print(f"reusing the export at {TREE}")
    exported_head = json.dumps({"tip": TIP,
                                "frontend_files": sum(1 for _ in (TREE / "frontend" / "src").rglob("*"))})
    print("export check:", exported_head)

    # 2) node_modules: a junction, read-only from vite's point of view
    link = TREE / "frontend" / "node_modules"
    if not link.exists():
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"New-Item -ItemType Junction -Path '{link}' -Target '{NM_SRC}'"],
                       capture_output=True, text=True)
    assert (link / "vite").exists(), "junction did not resolve"

    dist = "dist_ord0267"
    b = subprocess.run(["node", "node_modules/vite/bin/vite.js", "build", "--outDir", dist],
                       cwd=str(TREE / "frontend"), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    print("build rc=", b.returncode, (b.stdout or "").strip().splitlines()[-3:])
    if b.returncode != 0:
        return 3

    # 3) the surface: my backend + my preview
    be = spawn([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
               TREE / "backend", BASE / "backend.log", dict(os.environ) | ENV)
    for _ in range(90):
        if ok(f"http://127.0.0.1:{PORT}/api/v1/health"):
            break
        time.sleep(1)
    else:
        raise SystemExit("ABORT: backend never answered")
    subprocess.run([PY, "-c", "import app.main as m; from app.db.session import SessionLocal, ensure_schema;"
                              "ensure_schema(); s=SessionLocal(); m.seed_demo(s); s.close()"],
                   cwd=str(TREE / "backend"), env=dict(os.environ) | ENV, capture_output=True, timeout=300)
    pv = spawn(["node", "node_modules/vite/bin/vite.js", "preview", "--outDir", dist,
                "--port", str(PREVIEW_PORT), "--strictPort", "--host", "127.0.0.1"],
               TREE / "frontend", BASE / "preview.log",
               dict(os.environ) | ENV | {"CITYNEXUS_BACKEND_PORT": str(PORT)})
    for _ in range(45):
        if ok(f"http://127.0.0.1:{PREVIEW_PORT}/"):
            break
        time.sleep(1)
    else:
        raise SystemExit("ABORT: preview never answered")
    print(f"surface up: preview :{PREVIEW_PORT} (backend :{PORT} pid {listeners(PORT)})")

    run1 = subprocess.run(["node", str(SPIKE / "q267_probe.js"), "--phase", "up",
                           "--base", f"http://127.0.0.1:{PREVIEW_PORT}", "--out",
                           str(BASE / "q267_probe.json")],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=420)
    print(run1.stdout.strip())

    # 4) the whole site down: both of MY processes, then re-visit with the same profiles
    kill(listeners(PREVIEW_PORT) + [pv.pid] + listeners(PORT) + [be.pid])
    for _ in range(30):
        if not listeners(PORT) and not listeners(PREVIEW_PORT):
            break
        time.sleep(0.5)
    print(f"sites down: :{PREVIEW_PORT} {listeners(PREVIEW_PORT)} :{PORT} {listeners(PORT)}")
    run2 = subprocess.run(["node", str(SPIKE / "q267_probe.js"), "--phase", "down",
                           "--base", f"http://127.0.0.1:{PREVIEW_PORT}", "--out",
                           str(BASE / "q267_probe.json")],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=420)
    print(run2.stdout.strip())
    kill(listeners(PREVIEW_PORT) + listeners(PORT))
    print("released:", {str(p): listeners(p) for p in (PORT, PREVIEW_PORT)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
