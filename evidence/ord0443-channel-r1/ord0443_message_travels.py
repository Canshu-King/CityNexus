"""ORD-0443: does the traveller's own sentence reach the model through the patched shim?

Two questions with checkable answers, sent with the product's own Responses client against the
patched shim on an OS-assigned port. `input_tokens` is recorded per question on purpose: an
identical count for two different sentences is the signature of content being dropped, which is
what the shipped shim did. Nothing here touches the user's running shim on :7864.
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
TREE = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\wt")
OUT = LANE / "ORD0443_MESSAGE_TRAVELS.json"
CASES = [("What is 21 times 4? Reply with the number only.", "84"),
         ("Name the single activity I should move: the Nexus River Cruise is closed this afternoon.", "cruise")]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def main() -> int:
    token = str(json.loads(CFG.read_text(encoding="utf-8")).get("api_key") or "")
    port = free_port()
    shim = subprocess.Popen(["node", str(LANE / "shim_patch" / "shim_r2.mjs")],
                            env={**os.environ, "WB2API_SHIM_PORT": str(port),
                                 "WB2API_UPSTREAM": "http://127.0.0.1:7863/v1", "WB2API_KEY": token},
                            stdout=(LANE / "_shim_probe.log").open("w", encoding="utf-8"),
                            stderr=subprocess.STDOUT)
    sys.path.insert(0, str(TREE / "backend"))
    from app.integrations.ai.responses import DeepSeekResponsesClient
    rows: list[dict] = []
    try:
        time.sleep(3)
        for question, expect in CASES:
            client = DeepSeekResponsesClient(api_key=token, model="global:glm-5.2",
                                             base_url=f"http://127.0.0.1:{port}/v1/responses",
                                             reasoning_effort="high", timeout_seconds=120.0)
            started = time.perf_counter()
            try:
                res = client.complete([{"role": "user", "content": question}])
                text = str(getattr(res, "text", "") or "")
                usage = getattr(res, "usage", None) or {}
                rows.append({"asked": question[:60], "expected_substring": expect,
                             "answer_head": text[:140],
                             "contains_expected": expect.lower() in text.lower(),
                             "elapsed_s": round(time.perf_counter() - started, 2),
                             "input_tokens": usage.get("input_tokens"),
                             "output_tokens": usage.get("output_tokens")})
            except Exception as exc:
                rows.append({"asked": question[:60], "expected_substring": expect,
                             "error": f"{type(exc).__name__}: {str(exc)[:180]}"})
            print(json.dumps(rows[-1], ensure_ascii=False))
    finally:
        shim.terminate()
        try:
            shim.wait(timeout=12)
        except Exception:
            shim.kill()
    counts = [r.get("input_tokens") for r in rows if r.get("input_tokens") is not None]
    report = {"rows": rows,
              "input_tokens_distinct": len(set(counts)) == len(counts) and len(counts) == len(CASES),
              "verdict_message_travels": all(r.get("contains_expected") for r in rows) and len(rows) == len(CASES)}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print("verdict_message_travels", report["verdict_message_travels"],
          "| input_tokens distinct:", report["input_tokens_distinct"])
    print("WROTE", OUT)
    return 0 if report["verdict_message_travels"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
