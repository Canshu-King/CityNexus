"""ORD-0443: wire the wb2api channel into the product and prove a product-visible difference.

Two boots of the same lane backend, same lane sqlite, one variable apart (AI off vs the channel
wired), because a 200 from the provider proves only that the provider answered. The judge is
whether the product's own copilot door answers differently for the same command.

Credential discipline: the key is read from the gateway's config.json at runtime and passed only
through the child process environment. Nothing here writes it - the receipt records presence and
length, never the value.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
import urllib.request
from pathlib import Path

import httpx

CFG = Path(r"C:\Users\仓鼠王\WorkBuddy\2026-09-15-15-47-27\wb2api\config.json")
LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0443")
TREE = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\wt")
SEED = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212\seed_lane_db.py")
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
JID = "22222222-2222-4222-8222-222222222222"
SHIM = "http://127.0.0.1:7864/v1/responses"
GATEWAY = "http://127.0.0.1:7863"
OUT = LANE / "ORD0443_WIRE_A_B.json"


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def boot(db: Path, extra_env: dict, log: Path) -> tuple[subprocess.Popen, int]:
    port = free_port()
    env = {**os.environ, "PYTHONPATH": ".", "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
           "CITYNEXUS_DEMO_MODE": "true", **extra_env}
    proc = subprocess.Popen([str(PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                             "--port", str(port)], cwd=str(TREE / "backend"), env=env,
                            stdout=log.open("w", encoding="utf-8"), stderr=subprocess.STDOUT)
    return proc, port


def wait(port: int, rounds=90) -> bool:
    for _ in range(rounds):
        try:
            if httpx.get(f"http://127.0.0.1:{port}/api/v1/health", timeout=4, trust_env=False).status_code == 200:
                return True
        except Exception:
            time.sleep(1)
    return False


def redact(node):
    import re
    secret_key = re.compile(r"key|token|secret|cookie|password|authorization|credential", re.I)
    if isinstance(node, dict):
        return {k: ("MASKED(len=%d)" % len(str(v))) if secret_key.search(str(k)) else redact(v)
                for k, v in node.items()}
    if isinstance(node, list):
        return [redact(v) for v in node[:20]]
    return node


def read_ai(port: int) -> dict:
    out = {}
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=60, trust_env=False) as c:
        for name, path in (("health", "/api/v1/health"),
                           ("runtime_status", "/api/v1/agent/runtime-status")):
            started = time.perf_counter()
            try:
                r = c.get(path)
                body = r.json() if "json" in (r.headers.get("content-type") or "") else {}
                scanned = json.dumps(redact(body), ensure_ascii=False)
                found = sorted({v for v in ("CONFIGURED_UNVERIFIED", "NOT_CONFIGURED",
                                            "DISABLED_BY_OPS", "PROVIDER_REFUSED") if v in scanned})
                out[name] = {"http": r.status_code, "bytes": len(r.content),
                             "elapsed_s": round(time.perf_counter() - started, 2),
                             "ai_words_found": found,
                             "body": json.loads(scanned) if found else {"keys": sorted(body)[:14]}}
            except Exception as exc:
                out[name] = {"http": "NO_RESPONSE", "error": f"{type(exc).__name__}: {exc}"[:120]}
    return out


def copilot(port: int, command: str, idem: str) -> dict:
    started = time.perf_counter()
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=120, trust_env=False) as c:
        r = c.post(f"/api/v1/journeys/{JID}/agent/commands",
                   json={"command": command}, headers={"Idempotency-Key": idem})
        try:
            body = r.json()
        except Exception:
            body = {}
    text = json.dumps(body, ensure_ascii=False, sort_keys=True)
    return {"http": r.status_code, "bytes": len(r.content),
            "elapsed_s": round(time.perf_counter() - started, 2),
            "response_sha1": __import__("hashlib").sha1(text.encode()).hexdigest()[:16],
            "intent": body.get("intent") or (body.get("interpretation") or {}).get("intent"),
            "reply_head": str(body.get("reply") or body.get("message") or "")[:120],
            "top_keys": sorted(body.keys())[:12]}


def setup_journey(port: int) -> dict:
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=90, trust_env=False) as c:
        for _ in range(60):
            if c.get("/api/v1/health").status_code == 200:
                break
            time.sleep(1)
        gen = c.post(f"/api/v1/journeys/{JID}/plans/generate", json={})
        if gen.status_code == 201 and gen.json():
            c.post(f"/api/v1/journeys/{JID}/plans/{gen.json()[0]['id']}/select")
            c.post(f"/api/v1/journeys/{JID}/start")
        conn = sqlite3.connect(str(LANE / "_wire.db"))
        acts = conn.execute("select a.id from activities a join plan_versions p "
                            "on a.plan_version_id=p.id where p.status='ACTIVE' order by a.start_at").fetchall()
        conn.close()
        return {"generate_http": gen.status_code, "active_activities": len(acts)}


def main() -> int:
    LANE.mkdir(parents=True, exist_ok=True)
    token = str(json.loads(CFG.read_text(encoding="utf-8")).get("api_key") or "")
    models = json.loads(urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
        urllib.request.Request(GATEWAY + "/v1/models",
                               headers={"Authorization": "Bearer " + token}), timeout=30).read())["data"]
    report: dict = {"shim_url": SHIM, "key_field_name": "api_key", "key_length": len(token),
                    "key_written_to_any_file": False}
    ids = [item["id"] for item in models]
    report["gateway_models_count"] = len(ids)
    report["gateway_has_deepseek"] = sorted(i for i in ids if "deepseek" in i)
    report["gateway_has_glm"] = sorted(i for i in ids if "glm" in i)

    db = LANE / "_wire.db"
    for suffix in ("", "-wal", "-shm"):
        Path(str(db) + suffix).unlink(missing_ok=True)
    subprocess.run([str(PY), str(SEED)], check=True, capture_output=True, text=True,
                   env={**os.environ, "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
                        "LANE_BACKEND_ROOT": str(TREE / "backend")})

    model = "global:glm-5.2" if "global:glm-5.2" in ids else sorted(i for i in ids if "glm" in i)[0]
    cmd = "The river cruise venue just closed this afternoon, tell me what to do next"

    off_proc, off_port = boot(db, {}, LANE / "_wire_off.log")
    try:
        assert wait(off_port), "AI-off lane never answered"
        setup = setup_journey(off_port)
        report["off"] = {"port": off_port, "setup": setup, "ai": read_ai(off_port),
                         "copilot": copilot(off_port, cmd, "ord0443-off-1")}
    finally:
        off_proc.terminate()
        try:
            off_proc.wait(timeout=20)
        except Exception:
            off_proc.kill()

    on_proc, on_port = boot(db, {"CITYNEXUS_AI_ENABLED": "true", "CITYNEXUS_AI_PROVIDER": "deepseek",
                                 "CITYNEXUS_AI_MODEL": model, "CITYNEXUS_AI_API_KEY": token,
                                 "DEEPSEEK_API_KEY": token,
                                 "CITYNEXUS_DEEPSEEK_API_URL": SHIM}, LANE / "_wire_on.log")
    try:
        assert wait(on_port), "channel-wired lane never answered"
        setup_journey(on_port)
        report["on"] = {"port": on_port, "model": model, "ai": read_ai(on_port),
                        "copilot": copilot(on_port, cmd, "ord0443-on-1")}
    finally:
        on_proc.terminate()
        try:
            on_proc.wait(timeout=20)
        except Exception:
            on_proc.kill()

    report["verdict_channel_reaches_product_state"] = bool(
        report["on"]["copilot"]["http"] == 200
        and report["on"]["copilot"]["response_sha1"] != report["off"]["copilot"]["response_sha1"])
    report["difference"] = {"off_intent": report["off"]["copilot"].get("intent"),
                            "on_intent": report["on"]["copilot"].get("intent"),
                            "off_reply_head": report["off"]["copilot"].get("reply_head"),
                            "on_reply_head": report["on"]["copilot"].get("reply_head"),
                            "off_elapsed_s": report["off"]["copilot"].get("elapsed_s"),
                            "on_elapsed_s": report["on"]["copilot"].get("elapsed_s")}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("gateway_models_count", "gateway_has_deepseek",
                                             "gateway_has_glm", "verdict_channel_reaches_product_state",
                                             "difference")}, ensure_ascii=False, indent=1)[:1400])
    print("off ai:", report["off"]["ai"])
    print("on  ai:", report["on"]["ai"])
    print("WROTE", OUT)
    return 0 if report["verdict_channel_reaches_product_state"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
