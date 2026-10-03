"""What does this lane's carrier answer when there is no origin at all?

`errUnnamed` and `errNoResponse` are the two refusal sentences the backend never emits (0 hits in
backend/app), so only glass can read them -- and which of the two the screen must say depends on WHO
answers.  Before writing that arm I measure the carrier's own shape with the origin gone, through the
same vite the browser uses, with curl: no browser, no page, nothing simulated.

  start vite on its own port, pointed at my backend port
  stop MY backend (the stack tool only kills the listener it owns on my port)
  ask the carrier for the parse door and the add door and record status / byte count / body head
  start the backend again and re-read the same two doors, so the difference is the origin and nothing else

Writes: none -- a POST to parse is a read door, and the add call is sent with an empty selection, which
the server refuses before it can touch a row.  That refusal is recorded, not assumed.

    D:/moodle/CityNexus/.venv/Scripts/python.exe -X utf8 review/ord0545/dead_origin_carrier_probe_r1.py
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "review/ord0545/readouts/dead_origin_carrier_probe_r1.json"
FRONTEND_PORT = int(os.environ.get("CITYNEXUS_ORD0545S5_FRONTEND_PORT", "4926"))
BACKEND_PORT = int(os.environ.get("CITYNEXUS_ORD0533_BACKEND_PORT", "4921"))
STACK_TAG = os.environ.get("CITYNEXUS_ORD0533_TAG", "s5probe")
CANARY_JOURNEY = "22222222-2222-4222-8222-222222222222"
PARSE = f"/api/v1/journeys/{CANARY_JOURNEY}/poi-import/parse"
ADD = f"/api/v1/journeys/{CANARY_JOURNEY}/poi-import/add"


def ask(port: int, path: str, body: dict | None, method: str = "POST") -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                                headers={"Content-Type": "application/json"})
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw, status = res.read(), res.status
    except urllib.error.HTTPError as exp:
        raw, status = exp.read(), exp.code
    except Exception as exp:
        return {"reachable": False, "kind": type(exp).__name__, "seconds": round(time.time() - started, 2)}
    text = raw.decode("utf-8", "replace")
    reason = None
    parsed = None
    try:
        parsed = json.loads(text) if raw else None
        if isinstance(parsed, dict) and isinstance(parsed.get("error"), dict):
            reason = parsed["error"].get("reason_code") or parsed["error"].get("code")
    except Exception:
        reason = "body is not JSON"
    return {"reachable": True, "status": status, "bytes": len(raw), "json_object": parsed is not None,
            "reason_code": reason, "content_type": None, "head": text[:160],
            "seconds": round(time.time() - started, 2)}


def stack(mode: str) -> dict:
    env = dict(os.environ)
    env.update({"CITYNEXUS_ORD0533_TAG": STACK_TAG, "CITYNEXUS_ORD0533_BACKEND_PORT": str(BACKEND_PORT)})
    proc = subprocess.run([sys.executable, "review/ord0533/lane_stack_r1.py", mode], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
                          env=env)
    out = proc.stdout + proc.stderr
    return {"rc": proc.returncode, "tail": out.strip().splitlines()[-2:]}


def listening(port: int) -> list[str]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace").stdout
    return sorted({ln.split()[-1] for ln in out.splitlines()
                   if len(ln.split()) >= 5 and ln.split()[0].upper() == "TCP"
                   and ln.split()[3].upper() == "LISTENING" and ln.split()[1].endswith(f":{port}")})


def main() -> int:
    result: dict[str, object] = {"measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                 "frontend_port": FRONTEND_PORT, "backend_port": BACKEND_PORT,
                                 "stack_tag": STACK_TAG}
    if listening(FRONTEND_PORT):
        raise SystemExit("ABORT: something already listens on the carrier port " + str(FRONTEND_PORT)
                         + ": " + ",".join(listening(FRONTEND_PORT)))
    vite_env = dict(os.environ)
    vite_env["CITYNEXUS_BACKEND_PORT"] = str(BACKEND_PORT)
    vite = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1",
                             "--port", str(FRONTEND_PORT), "--strictPort"], cwd=ROOT / "frontend",
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=vite_env)
    try:
        for _ in range(40):
            if listening(FRONTEND_PORT):
                break
            time.sleep(1)
        result["carrier_listening"] = bool(listening(FRONTEND_PORT))
        # baseline: origin alive, both doors answered through the carrier
        result["with_origin"] = {"parse": ask(FRONTEND_PORT, PARSE, {"text": "Central Food Hall"}),
                                 "add_empty_selection": ask(FRONTEND_PORT, ADD, {"place_ids": []})}
        result["backend_listening_before"] = listening(BACKEND_PORT)
        result["stop"] = stack("--stop")
        time.sleep(2)
        result["backend_listening_after_stop"] = listening(BACKEND_PORT)
        # the reading this probe exists for: who answers now, and in what shape
        result["without_origin"] = {"parse": ask(FRONTEND_PORT, PARSE, {"text": "Central Food Hall"}),
                                    "add_empty_selection": ask(FRONTEND_PORT, ADD, {"place_ids": []}),
                                    "plain_page": ask(FRONTEND_PORT, "/", None, method="GET")}
        result["restart"] = stack("--start")
        for _ in range(30):
            if listening(BACKEND_PORT):
                break
            time.sleep(1)
        result["backend_listening_after_restart"] = listening(BACKEND_PORT)
        result["with_origin_again"] = {"parse": ask(FRONTEND_PORT, PARSE, {"text": "Central Food Hall"})}

        w, o = result["with_origin"]["parse"], result["without_origin"]["parse"]
        result["conclusions"] = {
            # the carrier really answers for the origin -- that is what makes the screen say "unnamed"
            "carrier_answers_when_origin_is_gone": bool(
                w.get("status") == 200 and o.get("reachable") and o.get("status") and o["status"] >= 500),
            "the_answer_carries_no_json_object": bool(o.get("json_object") is False),
            "nothing_was_written_by_the_probes": bool(
                result["with_origin"]["add_empty_selection"].get("status") != 201
                and result["without_origin"]["add_empty_selection"].get("status") != 201),
            "the_origin_was_really_the_only_variable": bool(
                w.get("status") == result["with_origin_again"]["parse"].get("status")
                and result["backend_listening_before"] and not result["backend_listening_after_stop"]
                and result["backend_listening_after_restart"]),
        }
    finally:
        vite.kill()
        time.sleep(1)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({"with_origin_parse": w.get("status"), "without_origin": o.get("status"),
                      "without_origin_bytes": o.get("bytes"), "json_object": o.get("json_object"),
                      "plain_page": result["without_origin"]["plain_page"].get("status"),
                      "conclusions": result["conclusions"]}, ensure_ascii=False))
    print("wrote", OUT.as_posix(), OUT.stat().st_size, "B")
    return 0 if all(result["conclusions"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
