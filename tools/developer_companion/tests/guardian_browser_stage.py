"""Isolated deterministic Guardian browser case; real HTTP/SQLite, fixture mobility."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from tools.developer_companion.process_scope import ProcessScope


PAIRS = {
    ("place-city-park", "place-riverside-museum"): 17,
    ("place-design-library", "place-riverside-museum"): 15,
}


def api(port, path, *, method="GET", body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(f"http://127.0.0.1:{port}/api/v1{path}", data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        value = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Fixture API {method} {path} returned {exc.code}: {value[:350]}") from None


def run_server(args):
    secret = json.loads((args.state / "local-test-secrets.json").read_text(encoding="utf-8"))
    os.environ.update({"CITYNEXUS_DATABASE_URL": "sqlite:///" + str(args.state / "guardian-case.db").replace("\\", "/"), "CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_TRAVELER_AUTH_SECRET": secret["auth"], "CITYNEXUS_DEMO_RESET_TOKEN": secret["reset"]})
    sys.path[:0] = [str(args.checkout / "backend"), str(args.checkout / "backend" / "tests")]
    from _qoder_explicit_demo_mobility import seed_module_mobility
    from pytest import MonkeyPatch
    patch = MonkeyPatch()
    seed_module_mobility(patch, PAIRS)
    import uvicorn
    from app.main import app
    uvicorn.run(app, host="127.0.0.1", port=args.backend_port, access_log=False, log_level="warning")


def seed(args):
    marker = args.state / "case.json"
    if marker.exists():
        raise RuntimeError("This fixture stage is already seeded; preserve it")
    secret = json.loads((args.state / "local-test-secrets.json").read_text(encoding="utf-8"))
    _, ids = api(args.backend_port, "/demo/reset", method="POST", headers={"X-Demo-Reset-Token": secret["reset"]})
    journey = ids["journey_id"]
    _, identity = api(args.backend_port, "/demo/session")
    headers = {"Authorization": "Bearer " + identity["access_token"]}
    _, plans = api(args.backend_port, f"/journeys/{journey}/plans/generate", method="POST", body={"candidate_count": 1}, headers=headers)
    plan = plans[0]
    api(args.backend_port, f"/journeys/{journey}/plans/{plan['id']}/select", method="POST", headers=headers)
    api(args.backend_port, f"/journeys/{journey}/start", method="POST", headers=headers)
    target = next(activity for activity in plan["activities"] if activity["place_id"] == "place-tech-art")
    for activity in plan["activities"]:
        if activity["id"] == target["id"]:
            break
        api(args.backend_port, f"/journeys/{journey}/activities/{activity['id']}/complete", method="POST", headers=headers)
    _, event = api(args.backend_port, f"/journeys/{journey}/events", method="POST", headers=headers, body={"event_type": "CLOSURE", "severity": "MAJOR", "affected_activity_id": target["id"], "occurred_at": "2026-10-10T13:25:00+08:00", "payload": {"reason": "ISOLATED_TEST_FIXTURE issue51 accepted replan"}})
    api(args.backend_port, f"/journeys/{journey}/replans", method="POST", headers={**headers, "Idempotency-Key": "issue51-browser-" + event["id"]}, body={"trigger_event_id": event["id"], "candidate_count": 3})
    _, proposals = api(args.backend_port, f"/journeys/{journey}/replans", headers=headers)
    proposal = next(p for p in proposals if p["status"] == "PRESENTED" and p["trigger_event_id"] == event["id"])
    public = {"evidence": "ISOLATED_TEST_FIXTURE_REAL_HTTP_SQLITE", "journey_id": journey, "event_id": event["id"], "proposal_id": proposal["id"], "base_plan_id": plan["id"], "frontend_url": f"http://127.0.0.1:{args.frontend_port}/revolution", "database": str(args.state / "guardian-case.db")}
    marker.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(public, ensure_ascii=False))


def launch(args):
    args.state.mkdir(parents=True, exist_ok=True)
    secret_path = args.state / "local-test-secrets.json"
    if not secret_path.exists():
        if (args.state / "guardian-case.db").exists():
            raise RuntimeError("Refuse an existing database without this fixture stage's identity")
        with secret_path.open("x", encoding="utf-8") as stream:
            json.dump({"auth": secrets.token_urlsafe(32), "reset": secrets.token_urlsafe(32)}, stream)
        secret_path.chmod(0o600)
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LOCALAPPDATA", "APPDATA", "USERPROFILE", "COMSPEC", "PATHEXT"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update({"PYTHONUTF8": "1", "PYTHONPATH": str(Path(__file__).resolve().parents[3]), "CITYNEXUS_BACKEND_PORT": str(args.backend_port)})
    children = []
    logs = []
    def start(command, name, cwd):
        log = (args.state / f"{name}.log").open("ab")
        logs.append(log)
        options = {"cwd": cwd, "env": env, "stdin": subprocess.DEVNULL, "stdout": log, "stderr": subprocess.STDOUT}
        options["creationflags" if os.name == "nt" else "start_new_session"] = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else True
        process = subprocess.Popen(command, **options)
        scope = ProcessScope(process)
        children.append((process, scope))
        return process, scope
    command = [shutil.which("py") or sys.executable, "-3.13", "-m", "tools.developer_companion.tests.guardian_browser_stage", "server", "--checkout", str(args.checkout), "--state", str(args.state), "--backend-port", str(args.backend_port), "--frontend-port", str(args.frontend_port)]
    backend = start(command, "backend", args.checkout / "backend")
    vite = args.checkout / "frontend/node_modules/vite/bin/vite.js"
    try:
        start([shutil.which("node"), str(vite), "--host", "127.0.0.1", "--port", str(args.frontend_port), "--strictPort"], "frontend", args.checkout / "frontend")
        print(json.dumps({"stage": "ISOLATED_TEST_FIXTURE", "backend_port": args.backend_port, "frontend_port": args.frontend_port, "database": str(args.state / "guardian-case.db"), "commands": ["restart", "stop"]}), flush=True)
        for line in sys.stdin:
            if line.strip() == "restart":
                backend[1].close()
                backend[0].wait(timeout=5)
                backend = start(command, "backend", args.checkout / "backend")
                print('backend_restarted_same_fixture_database', flush=True)
            elif line.strip() in {"stop", ""}:
                break
    finally:
        for process, scope in reversed(children):
            scope.close()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        for log in logs:
            log.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["launch", "server", "seed"])
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--backend-port", type=int, default=18651)
    parser.add_argument("--frontend-port", type=int, default=14651)
    args = parser.parse_args()
    args.checkout, args.state = args.checkout.resolve(), args.state.resolve()
    if args.state.is_relative_to(args.checkout):
        raise RuntimeError("Fixture database and secrets must stay outside the source checkout")
    {"launch": launch, "server": run_server, "seed": seed}[args.action](args)


if __name__ == "__main__":
    main()
