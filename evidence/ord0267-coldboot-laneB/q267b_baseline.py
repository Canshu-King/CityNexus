"""ORD-0267 re-shaping, step 1: take the baseline again on the CURRENT generation.

The previous shaping was measured on `d2665e2`, where the origin's CacheStorage stayed empty for every
client. ORD-0268 then landed (the duplicate hand-written `v10-shell` precache entry removed), and the
commander says the phone chain now runs a newer generation. So the fact my old shape rested on may no
longer hold, and a shaping document built on a stale baseline is worthless.

Nothing here implements anything: it builds the current tip into its own outDir, serves it on my ports,
lets one profile install normally, then kills the site and asks the two questions that matter --
  installed client, site gone          -> does the shell answer, and from where?
  client that never visited, site gone -> same question for a cold device
-- reading the worker's own registrations, CacheStorage keys, controller and fromServiceWorker from
inside the browser.
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
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0267_20260923")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
BACKEND = pathlib.Path(r"D:\moodle\_qoder_b_ord0268_20260923\genB\backend")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
OUT = WORK / "genB_baseline"
PREVIEW_PORT, BACKEND_PORT = 4445, 8445
DETACHED = 0x00000008 | 0x00000200
DB = WORK / "db" / "ord0267b_8445.db"
ENV = {"CITYNEXUS_DATABASE_URL": f"sqlite:///{DB.as_posix()}", "CITYNEXUS_ENV": "dev",
       "CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_AI_ENABLED": "false",
       "CITYNEXUS_GUARDIAN_AUTORUN": "false", "DEEPSEEK_API_KEY": "", "CITYNEXUS_AI_API_KEY": "",
       "CITYNEXUS_ANYWHERE_RESOLVER": "off", "CITYNEXUS_PHOTON_BASE_URL": "http://127.0.0.1:9",
       "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}


def g(args):
    return subprocess.run(["git", "-C", str(LANE), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def listeners(port):
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return sorted({m.group(1) for m in
                   re.finditer(rf"TCP\s+127\.0\.0\.1:{port}\s+\S+\s+LISTENING\s+(\d+)", out)})


def kill(pids):
    for pid in dict.fromkeys(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")


def spawn(cmd, cwd, log, env):
    with open(log, "a", encoding="utf-8") as fh:
        return subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=fh, stderr=subprocess.STDOUT,
                                creationflags=DETACHED)


def get(url, timeout=8):
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:
            return r.status, r.read()[:40]
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__.encode()


def probe(phase: str, out_file: pathlib.Path):
    out_file.unlink(missing_ok=True)
    r = subprocess.run(["node", str(SPIKE / "q267_probe.js"),
                        "--base", f"http://127.0.0.1:{PREVIEW_PORT}",
                        "--out", str(out_file), "--phase", phase,
                        "--p1", str(WORK / "profile_install_b"), "--p2", str(WORK / "profile_cold_b")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=420)
    line = ((r.stdout or "").strip().splitlines() or [f"NO OUTPUT rc={r.returncode} {(r.stderr or '')[-200:]}"])[-1]
    print(f"  {phase:5s} {line[:190]}")
    return json.loads(out_file.read_text(encoding="utf-8")) if out_file.exists() else {"missing": True,
                                                                                       "stderr": (r.stderr or "")[-300:]}


def main() -> int:
    TIP = g(["rev-parse", "HEAD"]).strip()
    SUBJ = g(["log", "-1", "--format=%ad %s", "--date=iso"]).strip()
    print(f"tip {TIP}  {SUBJ}")
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(WORK / "profile_install_b", ignore_errors=True)
    shutil.rmtree(WORK / "profile_cold_b", ignore_errors=True)
    (WORK / "db").mkdir(exist_ok=True)
    for suf in ("", "-wal", "-shm"):
        pathlib.Path(str(DB) + suf).unlink(missing_ok=True)
    for p in (PREVIEW_PORT, BACKEND_PORT):
        if listeners(p):
            print(f"ABORT: :{p} already answers {listeners(p)}")
            return 2

    b = subprocess.run(["node", "node_modules/vite/bin/vite.js", "build", "--outDir", "dist_ord0267b"],
                       cwd=str(LANE / "frontend"), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    precache = next((l.strip() for l in (b.stdout or "").splitlines() if "precache" in l), None)
    print(f"build rc={b.returncode}  {precache}")
    if b.returncode != 0:
        print((b.stdout or b.stderr)[-500:])
        return 3
    sw = (LANE / "frontend" / "dist_ord0267b" / "v10-sw.js").read_text(encoding="utf-8", errors="replace")
    manifest = re.findall(r"precacheAndRoute\(\[(.*?)\]\)", sw, re.S)
    entries = re.findall(r'\{"url":"([^"]+)","revision":([^,}]+)', manifest[0]) if manifest else []
    print(f"  worker precache entries: {len(entries)}; url=/index.html rows: "
          f"{[e for e in entries if e[0] == '/index.html']}")

    be = spawn([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
               BACKEND, OUT / "backend.log", dict(os.environ) | ENV)
    for _ in range(90):
        if listeners(BACKEND_PORT) and get(f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health")[0] == 200:
            break
        time.sleep(1)
    subprocess.run([PY, "-c", "import app.main as m; from app.db.session import SessionLocal, ensure_schema;"
                              "ensure_schema(); s=SessionLocal(); m.seed_demo(s); s.close()"],
                   cwd=str(BACKEND), env=dict(os.environ) | ENV, capture_output=True, timeout=400)
    pv = spawn(["node", "node_modules/vite/bin/vite.js", "preview", "--outDir", "dist_ord0267b",
                "--port", str(PREVIEW_PORT), "--strictPort", "--host", "127.0.0.1"],
               LANE / "frontend", OUT / "preview.log",
               dict(os.environ) | ENV | {"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT)})
    for _ in range(60):
        if listeners(PREVIEW_PORT) and get(f"http://127.0.0.1:{PREVIEW_PORT}/v8/hub")[0] == 200:
            break
        time.sleep(1)

    up = probe("up", OUT / "probe_up.json")
    print("  killing the site (my own processes only)")
    kill(listeners(PREVIEW_PORT) + [pv.pid] + listeners(BACKEND_PORT) + [be.pid])
    time.sleep(2)
    down = probe("down", OUT / "probe_down.json")

    receipt = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
               "order": "ORD-0267 定形重取 · 第 1 步：当前代基线",
               "lane": "B c01d72a3", "mode": "READ-ONLY; no product byte changed",
               "generation": {"tip": TIP, "subject": SUBJ,
                              "contains": "ORD-0263 fifth state (c79e2b4f) + ORD-0268 precache fix",
                              "previous_shaping_was_measured_on": "d2665e25855aeb265329266831983de42321697d",
                              "build": {"outDir": "dist_ord0267b", "precache_line": precache,
                                        "worker_precache_entries": len(entries),
                                        "index_html_rows": [e for e in entries if e[0] == "/index.html"]}},
               "surface": {"preview": PREVIEW_PORT, "backend": BACKEND_PORT,
                           "profiles": ["profile_install_b (installs while the site is up)",
                                        "profile_cold_b (never visited)"],
                           "loopback_only": True,
                           "never_touched_or_opened": [":4781", ":4782", ":8693", "tunnel", "cnx proxy",
                                                       "_live.db", "_preview.db"],
                           "demo_reset": 0, "provider_egress": "off"},
               "up_phase": up, "down_phase": down}
    p = OUT / "ord0267b_baseline.json"
    p.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    cells = (down.get("cases") or down)
    print("\n  --- while up:", json.dumps(up, ensure_ascii=False)[:400])
    print("\n  --- while down:", json.dumps(cells, ensure_ascii=False)[:900])
    print("->", p.relative_to(WORK))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
