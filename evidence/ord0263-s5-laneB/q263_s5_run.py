"""ORD-0263 fifth state: reproduce it with my own processes, and judge A3 while I am here.

Order of operations matters and is recorded: the client first gets a REAL origin so it can enter a
journey and cache a snapshot (that is the state a traveller is actually in), then the origin on the same
port is swapped for one that answers the read with 200 + an HTML document while /api/v1/health still
answers 200 JSON. If the screen then blames the network, the fifth state is reproduced, not argued.

A3 is a separate profile with the same swapped origin: a write leg that never settles. The reader records
whether any sentence, door or attribution appears inside the window -- "the screen says nothing" and
"the screen says something false" are different findings.
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
BASE = pathlib.Path(r"D:\moodle\_qoder_b_ord0263_20260923")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
GENB = pathlib.Path(r"D:\moodle\_qoder_b_ord0268_20260923\genB\frontend")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
NODE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"  # unused, node resolved from PATH
BACKEND_PORT, PREVIEW_PORT = 8441, 4441
DB = BASE / "db" / "ord0263_s5_8441.db"
DETACHED = 0x00000008 | 0x00000200
ENV = {"CITYNEXUS_DATABASE_URL": f"sqlite:///{DB.as_posix()}", "CITYNEXUS_ENV": "dev",
       "CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_AI_ENABLED": "false",
       "CITYNEXUS_GUARDIAN_AUTORUN": "false", "DEEPSEEK_API_KEY": "", "CITYNEXUS_AI_API_KEY": "",
       "CITYNEXUS_ANYWHERE_RESOLVER": "off", "CITYNEXUS_PHOTON_BASE_URL": "http://127.0.0.1:9",
       "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}


def listeners(port):
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out) if int(m.group(1)) == port})


def get(url, timeout=6):
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:
            return r.status, r.headers.get_content_type(), r.read()[:60]
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__, b""


def spawn(cmd, cwd, log, env):
    with open(log, "a", encoding="utf-8") as fh:
        return subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=fh, stderr=subprocess.STDOUT,
                                creationflags=DETACHED)


def kill(pids):
    for pid in dict.fromkeys(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")


def wait_port_ready(port, predicate, tries=90):
    for _ in range(tries):
        if listeners(port) and predicate():
            return True
        time.sleep(1)
    return False


def read(profile: pathlib.Path, out: pathlib.Path, enter: bool, window: int, label: str):
    cmd = ["node", str(SPIKE / "q263_read_page.js"), "--url", f"http://127.0.0.1:{PREVIEW_PORT}/v8/hub",
           "--profile", str(profile), "--out", str(out), "--window", str(window), "--label", label]
    if enter:
        cmd.append("--enter")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=(window + 120) * 3)
    print("  " + (r.stdout or "").strip().splitlines()[-1] if (r.stdout or "").strip() else f"  {label} NO OUT rc={r.returncode}")
    return json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"missing": True, "err": r.stderr[-300:]}


def main() -> int:
    (BASE / "db").mkdir(parents=True, exist_ok=True)
    for p in (BACKEND_PORT, PREVIEW_PORT):
        if listeners(p):
            print(f"ABORT: :{p} already answers {listeners(p)}")
            return 2
    shutil.rmtree(BASE / "profile_s5", ignore_errors=True)
    shutil.rmtree(BASE / "profile_a3", ignore_errors=True)
    for f in (DB,):
        for suf in ("", "-wal", "-shm"):
            pathlib.Path(str(f) + suf).unlink(missing_ok=True)

    be = spawn([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
               GENB.parent / "backend", BASE / "s5_backend.log", dict(os.environ) | ENV)
    ok_real = wait_port_ready(BACKEND_PORT, lambda: get(f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health")[0] == 200)
    if not ok_real:
        print("ABORT: real backend never answered")
        return 3
    subprocess.run([PY, "-c", "import app.main as m; from app.db.session import SessionLocal, ensure_schema;"
                              "ensure_schema(); s=SessionLocal(); m.seed_demo(s); s.close()"],
                   cwd=str(GENB.parent / "backend"), env=dict(os.environ) | ENV, capture_output=True, timeout=300)
    pv = spawn(["node", "node_modules/vite/bin/vite.js", "preview", "--outDir", "dist_ord0268",
                "--port", str(PREVIEW_PORT), "--strictPort", "--host", "127.0.0.1"],
               GENB, BASE / "s5_preview.log",
               dict(os.environ) | ENV | {"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT)})
    wait_port_ready(PREVIEW_PORT, lambda: get(f"http://127.0.0.1:{PREVIEW_PORT}/")[0] == 200)
    print(f"surface up with a REAL origin: {get(f'http://127.0.0.1:{PREVIEW_PORT}/api/v1/health')[:2]}")

    profile_s5 = BASE / "profile_s5"
    step_enter = read(profile_s5, BASE / "s5_enter.json", True, 25, "S5_enter_with_real_origin")
    print("  snapshot after enter:", json.dumps((step_enter.get("snapshot") or {}))[:80])

    # swap: the same port now answers reads with 200 + an HTML document, health stays 200 JSON
    kill(listeners(BACKEND_PORT) + [be.pid])
    html = spawn([PY, str(SPIKE / "q263_html_origin.py"), "--port", str(BACKEND_PORT)],
                 SPIKE, BASE / "s5_html_origin.log", dict(os.environ))
    wait_port_ready(BACKEND_PORT, lambda: get(f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health")[0] == 200)
    direct = get(f"http://127.0.0.1:{BACKEND_PORT}/api/v1/journeys/22222222-2222-4222-8222-222222222222/experience")
    via_proxy = get(f"http://127.0.0.1:{PREVIEW_PORT}/api/v1/journeys/22222222-2222-4222-8222-222222222222/experience")
    print(f"  origin read answer: {direct[0]} {direct[1]} body starts {direct[2][:34]!r}")
    print(f"  via proxy:          {via_proxy[0]} {via_proxy[1]} body starts {via_proxy[2][:34]!r}")

    s5 = read(profile_s5, BASE / "s5_state.json", False, 25, "S5_origin_answered_html")
    a3 = read(BASE / "profile_a3", BASE / "a3_state.json", True, 35, "A3_write_leg_hangs")

    kill(listeners(BACKEND_PORT) + [html.pid] + listeners(PREVIEW_PORT) + [pv.pid])
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), "order": "ORD-0263 第五态复量 + A3 判定",
           "lane": "B c01d72a3",
           "surface": {"built_from": "landed tip 2b49e3ca (含 0263)，preview :4441 -> origin :8441",
                       "origin_swap": "real uvicorn -> my own 200-HTML origin on the SAME port",
                       "no_browser_mocks": True, "forbidden_ports_requested": [4781, 4782, 8693, 4185, 8713]},
           "origin_probe_measured": {"direct_read": {"status": direct[0], "content_type": direct[1],
                                                     "body_head": direct[2].decode("utf-8", "replace")[:34]},
                                     "via_proxy_read": {"status": via_proxy[0], "content_type": via_proxy[1],
                                                       "body_head": via_proxy[2].decode("utf-8", "replace")[:34]}},
           "S5": s5, "A3": a3}
    p = BASE / "q263_s5_reproduction.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print("\nS5 attribution:", json.dumps(s5.get("app_attribution"), ensure_ascii=False)[:300])
    print("S5 screen head :", repr((s5.get("rendered_text") or "").replace("\n", " ")[:150]))
    print("S5 nodes       :", json.dumps({k: v for k, v in (s5.get("classification_nodes") or {}).items() if v}))
    print("S5 snapshot    :", json.dumps(s5.get("snapshot"))[:110])
    print("A3 attribution :", json.dumps(a3.get("app_attribution"), ensure_ascii=False)[:220])
    print("A3 screen head :", repr((a3.get("rendered_text") or "").replace("\n", " ")[:150]))
    print("A3 settle/nodes:", a3.get("seconds_to_settle"), json.dumps(a3.get("classification_nodes")))
    print("A3 POSTs seen  :", json.dumps(a3.get("non_get_requests"), ensure_ascii=False)[:220])
    print("->", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
