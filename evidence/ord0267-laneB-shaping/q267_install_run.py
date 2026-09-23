"""ORD-0267 install-reading run: bring my surface up, let the worker install, capture what it says.

Read-only on the product: same exported tree as the shaping pass. No mocks -- the only lever is my own
process being up while the probe runs.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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


def listeners(port: int) -> list[int]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out)
                   if int(m.group(1)) == port})


def ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=6) as r:
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
    busy = {str(p): listeners(p) for p in (PORT, PREVIEW_PORT)}
    if any(busy.values()):
        print(f"ABORT: my ports are not free: {busy}")
        return 2
    if not (TREE / "frontend" / "dist_ord0267" / "v10-sw.js").exists():
        print("ABORT: the exported tree has no build; run q267_shape.py first")
        return 2
    be = spawn([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
               TREE / "backend", BASE / "backend.log", dict(os.environ) | ENV)
    for _ in range(90):
        if ok(f"http://127.0.0.1:{PORT}/api/v1/health"):
            break
        time.sleep(1)
    pv = spawn(["node", "node_modules/vite/bin/vite.js", "preview", "--outDir", "dist_ord0267",
                "--port", str(PREVIEW_PORT), "--strictPort", "--host", "127.0.0.1"],
               TREE / "frontend", BASE / "preview.log",
               dict(os.environ) | ENV | {"CITYNEXUS_BACKEND_PORT": str(PORT)})
    for _ in range(45):
        if ok(f"http://127.0.0.1:{PREVIEW_PORT}/"):
            break
        time.sleep(1)
    print(f"surface up :{PREVIEW_PORT} / :{PORT} listeners {listeners(PREVIEW_PORT)} {listeners(PORT)}")

    r = subprocess.run(["node", str(SPIKE / "q267_install_probe.js"),
                        "--base", f"http://127.0.0.1:{PREVIEW_PORT}",
                        "--out", str(BASE / "q267_install_probe.json"), "--window", "20"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    (BASE / "q267_install_probe.stdout.log").write_text(
        (r.stdout or "") + "\n--- stderr ---\n" + (r.stderr or ""), encoding="utf-8", newline="\n")
    keep = [ln for ln in (r.stdout or "").splitlines()
            if any(k in ln for k in ("nav1:", "nav2", "caches ever seen", "CDP-LOG", "worker-shaped",
                                     "[service_worker]", "v10-sw", "workbox", "precache", "PROBE THREW"))]
    print("\n".join(keep[:60]) or (r.stdout or "").strip()[-1500:])
    if r.returncode != 0:
        print("rc=", r.returncode, (r.stderr or "")[-500:])
    kill(listeners(PREVIEW_PORT) + [pv.pid] + listeners(PORT) + [be.pid])
    print("released:", {str(p): listeners(p) for p in (PORT, PREVIEW_PORT)})
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
