"""ORD-0443 attribution: how long does a product-shaped request through the shim really take?

The lane mission came back `PROVIDER_REFUSED` while the gateway answered my direct completions in
about two seconds, so the refusal was not the channel being dead. `backend/app/agent/runtime.py:282`
builds the agent's model client with `timeout_seconds=settings.impact_timeout_seconds`, whose default
is ten seconds (an unrelated door's knob), so this replays the product's OWN client with a wide
budget and times each shape: plain, with reasoning, and with tools.

The credential is read from config.json at runtime and never written down.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

CFG = Path(r"C:\Users\仓鼠王\WorkBuddy\2026-09-15-15-47-27\wb2api\config.json")
TREE = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\wt")
OUT = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0443\ORD0443_SHAPES.json")
SHIM = "http://127.0.0.1:7864/v1/responses"

token = str(json.loads(CFG.read_text(encoding="utf-8")).get("api_key") or "")
os.environ.update({"CITYNEXUS_AI_ENABLED": "true", "CITYNEXUS_AI_PROVIDER": "deepseek",
                   "CITYNEXUS_AI_MODEL": "global:glm-5.2", "CITYNEXUS_AI_API_KEY": token,
                   "DEEPSEEK_API_KEY": token, "CITYNEXUS_DEEPSEEK_API_URL": SHIM})
import sys
sys.path.insert(0, str(TREE / "backend"))
from app.integrations.ai.responses import DeepSeekResponsesClient  # noqa: E402
from app.core.config import settings  # noqa: E402

MSG = [{"role": "user", "content": "The Nexus River Cruise venue is closed this afternoon. "
                                   "Which activity should I move to, and what stays untouched?"}]
TOOLS = [{"name": "inspect_journey", "description": "Read the current journey.",
          "parameters": {"type": "object", "properties": {}}},
         {"name": "request_replan", "description": "Ask for a replan proposal.",
          "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}}}]


def one(label: str, **kwargs) -> dict:
    client = DeepSeekResponsesClient(api_key=settings.ai_api_key, model=settings.ai_model,
                                     base_url=settings.deepseek_api_url, reasoning_effort="high",
                                     timeout_seconds=kwargs.pop("timeout", 180.0))
    started = time.perf_counter()
    out = {"shape": label, "timeout_budget_s": client.timeout_seconds}
    try:
        result = client.complete(MSG, **kwargs)
        text = getattr(result, "text", None) or ""
        out.update(ok=True, elapsed_s=round(time.perf_counter() - started, 2),
                   text_head=str(text)[:120], text_len=len(str(text)),
                   tool_calls=len(getattr(result, "tool_calls", []) or []),
                   usage=getattr(result, "usage", None))
    except Exception as exc:
        out.update(ok=False, elapsed_s=round(time.perf_counter() - started, 2),
                   error=f"{type(exc).__name__}: {str(exc)[:220]}")
    print(label, "->", "ok" if out.get("ok") else "FAIL", out.get("elapsed_s"), "s",
          out.get("text_head") or out.get("error") or "")
    return out


def main() -> int:
    report = {"model": settings.ai_model, "base_url": settings.deepseek_api_url,
              "impact_timeout_seconds_default": settings.impact_timeout_seconds,
              "agent_client_timeout_source": "backend/app/agent/runtime.py:282",
              "shapes": [one("plain"), one("json_mode", json_mode=True),
                         one("with_tools", tools=TOOLS, tool_choice="auto")]}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print("product default timeout for the agent loop:", settings.impact_timeout_seconds, "s")
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
