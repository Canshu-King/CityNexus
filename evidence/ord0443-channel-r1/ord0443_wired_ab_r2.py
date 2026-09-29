"""ORD-0443 wiring proof, take two: same door, same sentence, channel off vs channel on.

The first A/B could only show that the product's bytes changed; the channel it used was the shipped
shim, which silently dropped the traveller's text, so "it changed" was not yet "the model answered".
This run points the product at my patched shim copy (own OS-assigned port; the user's running
:7864 is untouched) and with the borrowed 10-second knob raised to a minute and a half, then
compares the two copilot bodies field by field on the fields that carry words - so the judge is
content, not a trace id.

Credential: read from the gateway config at runtime, into a child environment only.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import time
from pathlib import Path

import httpx

CFG = Path(r"C:\Users\仓鼠王\WorkBuddy\2026-09-15-15-47-27\wb2api\config.json")
LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0443")
TREE = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\wt")
SEED = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212\seed_lane_db.py")
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
JID = "22222222-2222-4222-8222-222222222222"
SENTENCE = "The river cruise stop is closed this afternoon. What should I move, and what stays untouched?"
OUT = LANE / "ORD0443_WIRED_AB_R2.json"
WORDS_KEYS = ("reply", "message", "summary", "assistant_text", "answer", "explanation", "text")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def boot_shim(token: str) -> tuple[subprocess.Popen, int]:
    port = free_port()
    proc = subprocess.Popen(["node", str(LANE / "shim_patch" / "shim_r2.mjs")],
                            env={**os.environ, "WB2API_SHIM_PORT": str(port),
                                 "WB2API_UPSTREAM": "http://127.0.0.1:7863/v1", "WB2API_KEY": token},
                            cwd=str(LANE / "shim_patch"),
                            stdout=(LANE / "_shim_ab_r2.log").open("w", encoding="utf-8"),
                            stderr=subprocess.STDOUT)
    time.sleep(3)
    return proc, port


def boot_lane(token: str, db: Path, shim_port: int | None) -> tuple[subprocess.Popen, int]:
    port = free_port()
    env = {**os.environ, "PYTHONPATH": ".", "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
           "CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_IMPACT_TIMEOUT_SECONDS": "90"}
    if shim_port:
        env.update({"CITYNEXUS_AI_ENABLED": "true", "CITYNEXUS_AI_PROVIDER": "deepseek",
                    "CITYNEXUS_AI_MODEL": "global:glm-5.2", "CITYNEXUS_AI_API_KEY": token,
                    "DEEPSEEK_API_KEY": token,
                    "CITYNEXUS_DEEPSEEK_API_URL": f"http://127.0.0.1:{shim_port}/v1/responses"})
    proc = subprocess.Popen([str(PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                             "--port", str(port)], cwd=str(TREE / "backend"), env=env,
                            stdout=(LANE / f"_lane_ab_{'on' if shim_port else 'off'}.log").open(
                                "w", encoding="utf-8"), stderr=subprocess.STDOUT)
    return proc, port


def words(node, found=None):
    found = {} if found is None else found
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and k in WORDS_KEYS and v.strip():
                found.setdefault(k, v[:200])
            else:
                words(v, found)
    elif isinstance(node, list):
        for item in node:
            words(item, found)
    return found


def arm(label: str, token: str, shim_port: int | None) -> dict:
    db = LANE / f"_ab_{label}.db"
    for suffix in ("", "-wal", "-shm"):
        Path(str(db) + suffix).unlink(missing_ok=True)
    subprocess.run([str(PY), str(SEED)], check=True, capture_output=True, text=True,
                   env={**os.environ, "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
                        "LANE_BACKEND_ROOT": str(TREE / "backend")})
    proc, port = boot_lane(token, db, shim_port)
    out: dict = {"arm": label, "port": port, "lane_db": str(db)}
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=240, trust_env=False) as c:
            for _ in range(120):
                try:
                    if c.get("/api/v1/health", timeout=4).status_code == 200:
                        break
                except Exception:
                    pass
                time.sleep(1)
            out["health"] = c.get("/api/v1/health").json()
            gen = c.post(f"/api/v1/journeys/{JID}/plans/generate", json={})
            if gen.status_code == 201 and gen.json():
                c.post(f"/api/v1/journeys/{JID}/plans/{gen.json()[0]['id']}/select")
                c.post(f"/api/v1/journeys/{JID}/start")
            started = time.perf_counter()
            r = c.post(f"/api/v1/journeys/{JID}/agent/commands", json={"command": SENTENCE},
                       headers={"Idempotency-Key": f"ord0443-ab2-{label}"})
            body = r.json() if r.status_code < 500 else {}
            out["copilot"] = {"http": r.status_code, "bytes": len(r.content),
                              "elapsed_s": round(time.perf_counter() - started, 2),
                              "body_sha1": hashlib.sha1(r.content).hexdigest()[:16],
                              "words": words(body),
                              "mission_status": (body.get("mission") or {}).get("status"),
                              "failure_reason": (body.get("mission") or {}).get("failure_reason"),
                              "ai_state": (body.get("mission") or {}).get("ai_state")}
            out["events_after"] = [{"type": e.get("event_type"), "severity": e.get("severity"),
                                    "status": e.get("status"), "provenance": e.get("provenance")}
                                   for e in c.get(f"/api/v1/journeys/{JID}/events").json()]
            env_block = c.get(f"/api/v1/journeys/{JID}/twin").json()["context"]["feasibility_envelope"]
            out["envelope_after"] = {"robust": env_block["robust"],
                                     "risk_reason_codes": env_block["risk_reason_codes"]}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=25)
        except Exception:
            proc.kill()
    return out


def main() -> int:
    token = str(json.loads(CFG.read_text(encoding="utf-8")).get("api_key") or "")
    shim, shim_port = boot_shim(token)
    try:
        off = arm("off", token, None)
        on = arm("on", token, shim_port)
    finally:
        shim.terminate()
        try:
            shim.wait(timeout=15)
        except Exception:
            shim.kill()
    report = {"sentence": SENTENCE, "shim": "patched copy, own port, user's :7864 untouched",
              "key_length": len(token), "key_written_to_any_file": False,
              "off": off, "on": on,
              "diff": {"bodies_equal": off["copilot"]["body_sha1"] == on["copilot"]["body_sha1"],
                       "off_words": off["copilot"]["words"], "on_words": on["copilot"]["words"]},
              "verdict_model_words_reach_product_reply": bool(
                  on["copilot"]["words"] and on["copilot"]["body_sha1"] != off["copilot"]["body_sha1"])}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    for a in (off, on):
        print(a["arm"], "http", a["copilot"]["http"], "bytes", a["copilot"]["bytes"],
              "s", a["copilot"]["elapsed_s"], "| mission", a["copilot"]["mission_status"],
              a["copilot"]["failure_reason"] or "", "| words",
              json.dumps(a["copilot"]["words"], ensure_ascii=False)[:220])
        print("   ai_state", a["copilot"]["ai_state"], "| events", a["events_after"],
              "| envelope", a["envelope_after"])
    print("verdict", report["verdict_model_words_reach_product_reply"], "| WROTE", OUT)
    return 0 if report["verdict_model_words_reach_product_reply"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
