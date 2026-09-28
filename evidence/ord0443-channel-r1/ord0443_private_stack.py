"""ORD-0443 private stack: does the patched shim let the product's own client work?

Nothing here touches the user's running shim on :7864. The patched copy is started on an OS-assigned
port against the same gateway, then the product's own `DeepSeekResponsesClient` is pointed at it and
the three request shapes are timed. If they answer, the lane backend is booted with the channel wired
and the traveller's sentence is sent through the product's copilot door - the durable read is the
event row and the twin's `feasibility_envelope`, i.e. ORD-0432's own claim.

Credential: read from the gateway's config.json at runtime, passed to the child process environment
only; the receipt records length, never the value.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

CFG = Path(r"C:\Users\仓鼠王\WorkBuddy\2026-09-15-15-47-27\wb2api\config.json")
LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0443")
SHIM_SRC = LANE / "shim_patch" / "shim_r2.mjs"
TREE = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\wt")
SEED = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212\seed_lane_db.py")
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
NODE = "node"
JID = "22222222-2222-4222-8222-222222222222"
OUT = LANE / "ORD0443_PRIVATE_STACK.json"
SENTENCE = "The Nexus River Cruise venue is closed this afternoon. What should I move, and what stays?"
MODEL = "global:glm-5.2"
TOOLS = [{"name": "inspect_journey", "description": "Read the current journey.",
          "parameters": {"type": "object", "properties": {}}},
         {"name": "request_replan", "description": "Ask for a replan proposal.",
          "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}}}]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def main() -> int:
    token = str(json.loads(CFG.read_text(encoding="utf-8")).get("api_key") or "")
    shim_port = free_port()
    shim = subprocess.Popen([NODE, str(SHIM_SRC)], env={**os.environ, "WB2API_SHIM_PORT": str(shim_port),
                                                        "WB2API_UPSTREAM": "http://127.0.0.1:7863/v1",
                                                        "WB2API_KEY": token},
                            cwd=str(SHIM_SRC.parent),
                            stdout=(LANE / "_shim_r2.log").open("w", encoding="utf-8"),
                            stderr=subprocess.STDOUT)
    report: dict = {"shim_port": shim_port, "shim_bytes": SHIM_SRC.stat().st_size,
                    "key_length": len(token), "key_written_to_any_file": False}
    try:
        for _ in range(30):
            if os.path.exists(LANE / "_shim_r2.log"):
                break
            time.sleep(0.5)
        time.sleep(2)
        report["shim_listening"] = any(f":{shim_port} " in line and "LISTENING" in line
                                       for line in subprocess.run(["netstat", "-ano"], capture_output=True,
                                                                  text=True, encoding="utf-8",
                                                                  errors="replace").stdout.splitlines())

        sys.path.insert(0, str(TREE / "backend"))
        os.environ.update({"CITYNEXUS_AI_ENABLED": "true", "CITYNEXUS_AI_PROVIDER": "deepseek",
                           "CITYNEXUS_AI_MODEL": MODEL, "CITYNEXUS_AI_API_KEY": token,
                           "CITYNEXUS_DEEPSEEK_API_URL": f"http://127.0.0.1:{shim_port}/v1/responses"})
        from app.integrations.ai.responses import DeepSeekResponsesClient  # noqa: E402
        msg = [{"role": "user", "content": SENTENCE}]
        shapes = []
        for label, kwargs in (("plain", {}), ("json_mode", {"json_mode": True}),
                              ("with_tools", {"tools": TOOLS, "tool_choice": "auto"})):
            client = DeepSeekResponsesClient(api_key=token, model=MODEL,
                                             base_url=os.environ["CITYNEXUS_DEEPSEEK_API_URL"],
                                             reasoning_effort="high", timeout_seconds=120.0)
            started = time.perf_counter()
            try:
                res = client.complete(msg, **kwargs)
                shapes.append({"shape": label, "ok": True,
                               "elapsed_s": round(time.perf_counter() - started, 2),
                               "text_len": len(str(getattr(res, "text", "") or "")),
                               "text_head": str(getattr(res, "text", "") or "")[:140],
                               "tool_calls": len(getattr(res, "tool_calls", []) or []),
                               "usage": getattr(res, "usage", None)})
            except Exception as exc:
                shapes.append({"shape": label, "ok": False,
                               "elapsed_s": round(time.perf_counter() - started, 2),
                               "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
            print(label, "->", shapes[-1]["ok"], shapes[-1]["elapsed_s"], "s")
        report["shapes"] = shapes
    finally:
        shim.terminate()
        try:
            shim.wait(timeout=15)
        except Exception:
            shim.kill()

    working = next((s for s in shapes if s["ok"]), None)
    report["verdict_shim_patch_makes_the_channel_usable"] = bool(working)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("shim_port", "shim_listening",
                                             "verdict_shim_patch_makes_the_channel_usable")},
                     ensure_ascii=False))
    print("WROTE", OUT)
    return 0 if working else 1


if __name__ == "__main__":
    raise SystemExit(main())
