"""Does the PRODUCT's own front drop the two operator headers, or did my lane's hand-rolled static
host drop them?  REQ-0521A was ruled on the reading my 0532 block gave, and that reading was taken
through `run_ord0502_stack_r1.py`'s StaticHandler, which builds its upstream request with
Content-Type only.  This arm takes the same request through `vite preview`, i.e. the front the
product actually ships behind, and reports both answers side by side.

Nothing shared is touched: own backend child on :4651, own `vite preview` on :4652, own fresh
sqlite.  The scene token exists only in this process's environment.  `demo/reset` is never called.
"""
from __future__ import annotations

import importlib.util
import json
import secrets
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

TREE = Path(r"D:/moodle/_qoder_frontdrop_20261003/wt")
WORK = Path("D:/moodle/_ord0502")
PY = sys.executable

spec = importlib.util.spec_from_file_location("runner", TREE / "review/ord0502/run_ord0502_stack_r1.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

run_id = "FRONTDROP-" + time.strftime("%H%M%S")
backend_port = runner.free_port(4651, "backend")
preview_port = runner.free_port(4652, "preview")
db = WORK / f"{run_id}.db"
token = secrets.token_urlsafe(24)
env = runner.env_base(run_id, db, backend_port)
env["CITYNEXUS_DEMO_MODE"] = "true"
env["CITYNEXUS_DEMO_SCENE_TOKEN"] = token
report = {"run_id": run_id, "backend_port": backend_port, "preview_port": preview_port, "db": str(db)}


def counts() -> dict[str, int]:
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        return {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                for t in ("journeys", "places", "activities", "plan_versions")}
    finally:
        conn.close()


def ensure(port: int, key: str, headers: dict[str, str]):
    hdrs = {"Content-Type": "application/json", **headers}
    if key:
        hdrs["Idempotency-Key"] = key
    request = urllib.request.Request(f"http://127.0.0.1:{port}/api/v1/demo/scene/ensure",
                                     data=json.dumps({}).encode(), headers=hdrs)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8", "replace") or "{}")
            return {"http_status": response.status, "state": body.get("state"),
                    "journey_id_named": bool(body.get("journey_id"))}
    except urllib.error.HTTPError as error:
        return {"http_status": error.code,
                "body": " ".join(error.read().decode("utf-8", "replace").split())[:170]}


print(f"[frontdrop] {run_id} backend=:{backend_port} preview=:{preview_port}", flush=True)
log = (WORK / f"uvicorn_{run_id}.log").open("w", encoding="utf-8")
child = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(backend_port)],
                         cwd=str(TREE / "backend"), env=env, stdout=log, stderr=subprocess.STDOUT)
ok, reading = runner.wait_http(f"http://127.0.0.1:{backend_port}/api/v1/health")
report["health"] = reading[:120]
if not ok:
    child.terminate()
    raise SystemExit("backend did not start")

npm = str(Path(r"C:/Program Files/nodejs/npx.cmd"))
prev_log = (WORK / f"vite_preview_{run_id}.log").open("w", encoding="utf-8")
preview = subprocess.Popen([npm, "vite", "preview", "--host", "127.0.0.1", "--port", str(preview_port), "--strictPort"],
                           cwd=str(TREE / "frontend"), env=env, stdout=prev_log, stderr=subprocess.STDOUT)
report["preview_up"] = runner.wait_http(f"http://127.0.0.1:{preview_port}/v8/hub", 90)[0]

if report["preview_up"]:
    report["A_via_product_preview"] = ensure(preview_port, "fd-" + secrets.token_hex(6),
                                             {"X-Demo-Scene-Token": token})
    report["rows_after_A"] = counts()
    report["B_via_lane_static_host"] = "see 0532 block: StaticHandler forwards Content-Type only"
    report["C_direct_to_backend_control"] = ensure(backend_port, "fd-" + secrets.token_hex(6),
                                                   {"X-Demo-Scene-Token": token})
    report["rows_after_C"] = counts()
else:
    report["preview_log_tail"] = (WORK / f"vite_preview_{run_id}.log").read_text(encoding="utf-8", errors="replace")[-500:]

preview.terminate()
child.terminate()
out = WORK / f"frontdrop_{run_id}.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("[frontdrop] receipt", out, flush=True)
for k in ("preview_up", "A_via_product_preview", "rows_after_A", "C_direct_to_backend_control", "rows_after_C"):
    print("[frontdrop]", k, json.dumps(report.get(k), ensure_ascii=False)[:240], flush=True)
