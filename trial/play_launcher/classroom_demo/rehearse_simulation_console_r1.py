"""One command that stands up the isolated SimulationRun stage and walks it.

The classroom stack (backend 60391, frontend 14492, database
`citynexus_v3_demo_1025.db`) is never touched.  This script exports the Codex
backend from a named commit into `_codex_probe_1025`, copies the demo database,
starts a spare backend and a spare Vite on loopback, runs the presenter event
card probe against them, and then stops only the processes it started.

Usage:
  python rehearse_simulation_console_r1.py [--ref a8f9b8ed16...] [--keep]
                                          [--backend-port 60396] [--frontend-port 14493]

Exit 0 means the probe reported no page errors and reached the guardian pause.
"""

import argparse
import io
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tarfile
import time
import urllib.request

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
PROBE = ROOT + "/trial/human_walk/_classroom_presenter_event_card_r25.mjs"
DEMO_DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_demo_1025.db"
WORK = r"D:/moodle/_codex_probe_1025"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"C:/Program Files/nodejs/node.exe"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
SHIM = r"C:/Users/仓鼠王/WorkBuddy/2026-09-15-15-47-27/wb2api/codex-shim/shim.mjs"
MODEL = "cn:hy3"


def gateway_key() -> str:
    match = re.search(r"WB2API_KEY \|\| '([^']+)'", io.open(SHIM, encoding="utf-8").read())
    if not match:
        raise SystemExit("no local gateway key found")
    return match.group(1)

SIM_DDL = """
CREATE TABLE IF NOT EXISTS simulation_runs (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL UNIQUE REFERENCES journeys(id),
    actor_id TEXT NOT NULL REFERENCES travelers(id),
    city_code TEXT NOT NULL,
    seed INTEGER NOT NULL,
    timezone TEXT NOT NULL,
    virtual_now TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0 CHECK(sequence >= 0),
    status TEXT NOT NULL,
    state_json TEXT NOT NULL DEFAULT '{}',
    history_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS simulation_commands (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id),
    run_id TEXT NOT NULL REFERENCES simulation_runs(id),
    actor_id TEXT NOT NULL REFERENCES travelers(id),
    idempotency_key TEXT NOT NULL,
    request_sha256 TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(journey_id, actor_id, idempotency_key)
);
"""


def listening(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def healthy(port: int) -> bool:
    try:
        with OPENER.open("http://127.0.0.1:%d/api/v1/health" % port, timeout=3) as answer:
            return answer.status == 200
    except Exception:
        return False


def wait_for(predicate, seconds: float) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(1)
    return False


def export_backend(ref: str) -> str:
    backend = os.path.join(WORK, "backend")
    if os.path.isdir(backend):
        shutil.rmtree(backend)
    data = os.path.join(WORK, "data")
    if os.path.isdir(data):
        shutil.rmtree(data)
    os.makedirs(WORK, exist_ok=True)
    tar_path = os.path.join(WORK, "_backend.tar")
    with open(tar_path, "wb") as handle:
        # `data/` carries the replay fixtures the agent runtime reads relative to
        # the backend's parent; without it a real guardian run dies at replan.
        subprocess.run(["git", "-C", ROOT, "archive", ref, "backend", "data"], check=True, stdout=handle)
    with tarfile.open(tar_path) as tar:
        tar.extractall(WORK)
    os.remove(tar_path)
    return backend


def copy_database() -> str:
    target = os.path.join(WORK, "probe2_1025.db")
    if os.path.exists(target):
        os.remove(target)
    source = sqlite3.connect("file:" + DEMO_DB + "?mode=ro", uri=True)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
        destination.executescript(SIM_DDL)
        destination.commit()
    finally:
        destination.close()
        source.close()
    return target


def start_backend(backend: str, database: str, port: int, with_model: bool) -> subprocess.Popen:
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + database.replace("\\", "/"),
        "CITYNEXUS_TRAVELER_AUTH_SECRET": "probe-isolated-5f3a9c1e7b2d4a6089f1c3e5d7b9a0f2",
        "CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS": "43200",
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_DEMO_DATABASE_PATH": database.replace("\\", "/"),
        "CITYNEXUS_SIMULATION_ENABLED": "true",
        "PYTHONPATH": backend,
    })
    if with_model:
        # Same wiring the classroom launcher uses; the key stays in this process's
        # environment and is never printed or written by this script.
        key = gateway_key()
        env.update({
            "CITYNEXUS_AI_ENABLED": "true",
            "CITYNEXUS_AI_PROVIDER": "deepseek",
            "CITYNEXUS_AI_MODEL": MODEL,
            "CITYNEXUS_AI_API_KEY": key,
            "CITYNEXUS_DEEPSEEK_API_URL": "http://127.0.0.1:7864/v1/responses",
            "CITYNEXUS_DEEPSEEK_REASONING_EFFORT": "low",
            "CITYNEXUS_DEEPSEEK_WEB_SEARCH": "false",
            "CITYNEXUS_HERMES_API_URL": "http://127.0.0.1:7863/v1/chat/completions",
            "CITYNEXUS_HERMES_API_KEY": key,
            "CITYNEXUS_HERMES_MODEL": MODEL,
        })
    log = open(os.path.join(WORK, "rehearse_backend.log"), "wb")
    process = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--app-dir", backend],
        cwd=backend, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    return process


def start_frontend(port: int, backend_port: int) -> subprocess.Popen:
    env = dict(os.environ)
    env["CITYNEXUS_BACKEND_PORT"] = str(backend_port)
    log = open(os.path.join(WORK, "rehearse_frontend.log"), "wb")
    return subprocess.Popen(
        [NODE, "node_modules/vite/bin/vite.js", "--port", str(port), "--strictPort", "--host", "127.0.0.1"],
        cwd=os.path.join(ROOT, "frontend"), env=env, stdout=log, stderr=subprocess.STDOUT,
    )


def stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    subprocess.run(["taskkill", "/PID", str(process.pid), "/F"], capture_output=True)
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="a8f9b8ed16f2f9f91798ea400a8c3be1975a2505")
    parser.add_argument("--backend-port", type=int, default=60396)
    parser.add_argument("--frontend-port", type=int, default=14493)
    parser.add_argument("--keep", action="store_true", help="leave the isolated stack running")
    parser.add_argument("--with-model", action="store_true", help="wire the local model gateway into the isolated backend")
    parser.add_argument("--model-walk", action="store_true", help="walk the guardian path with the model instead of the UI probe")
    parser.add_argument("--reuse-backend", action="store_true", help="use the existing exported backend directory as-is")
    parser.add_argument("--stack-only", action="store_true", help="start the isolated stack and return without probing")
    args = parser.parse_args()

    for port in (args.backend_port, args.frontend_port):
        if listening(port):
            print("PORT_IN_USE %d -- pick another port; nothing was started." % port)
            return 2

    backend = os.path.join(WORK, "backend") if args.reuse_backend else export_backend(args.ref)
    if args.reuse_backend and not os.path.isdir(backend):
        print("BACKEND_DIR_MISSING %s" % backend)
        return 2
    database = copy_database()
    backend_process = start_backend(backend, database, args.backend_port, args.with_model)
    frontend_process = start_frontend(args.frontend_port, args.backend_port)
    try:
        if not wait_for(lambda: healthy(args.backend_port), 90):
            print("BACKEND_NOT_HEALTHY -- see rehearse_backend.log")
            return 3
        if not wait_for(lambda: listening(args.frontend_port), 90):
            print("FRONTEND_NOT_UP -- see rehearse_frontend.log")
            return 4

        if args.stack_only:
            print("SIM_STACK_READY backend=%d frontend=%d db=%s" % (args.backend_port, args.frontend_port, database))
            return 0

        if args.model_walk:
            probe = subprocess.run(
                [sys.executable, ROOT + "/trial/human_walk/_simulation_guardian_model_r1.py",
                 "--base", "http://127.0.0.1:%d" % args.backend_port, "--db", database, "--timeout", "480"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
            )
            evidence = (probe.stdout or "") + (probe.stderr or "")
            with open(ROOT + "/trial/results/20261022_v3_human_chrome/guardian-model-walk-1.txt", "w", encoding="utf-8") as handle:
                handle.write(evidence)
            print(evidence.strip())
            if probe.returncode != 0 or "GUARDIAN_HTTP http=200" not in evidence:
                print("MODEL_WALK_FAILED rc=%d" % probe.returncode)
                return 7
            print("SIM_GUARDIAN_MODEL_WALK_OK backend=%d ref=%s" % (args.backend_port, args.ref[:12]))
            return 0

        env = dict(os.environ)
        env["SIM_BASE"] = "http://127.0.0.1:%d" % args.frontend_port
        probe = subprocess.run([NODE, PROBE], env=env, capture_output=True, text=True, timeout=300)
        print(probe.stdout.strip())
        if probe.returncode != 0:
            print("PROBE_FAILED rc=%d" % probe.returncode)
            print(probe.stderr[-800:])
            return 5

        evidence = open(
            ROOT + "/trial/results/20261022_v3_human_chrome/classroom-presenter-event-card-25.txt",
            encoding="utf-8",
        ).read()
        if "ERRORS []" not in evidence or "现场模型不可用" not in evidence:
            print("PROBE_READING_MISSING -- the evidence has no clean guardian pause.")
            return 6
        print("SIM_CONSOLE_REHEARSAL_OK backend=%d frontend=%d ref=%s" % (args.backend_port, args.frontend_port, args.ref[:12]))
        return 0
    finally:
        if not args.keep:
            stop(frontend_process)
            stop(backend_process)


if __name__ == "__main__":
    sys.exit(main())
