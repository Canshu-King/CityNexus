"""Optional one-call *read-only tool-call protocol* probe for local wb2api.

Run from repo root: py -3.13 trial/probe_wb2api_agent.py
With a precise direct model: ... --direct-model global:deepseek-v4.1-flash

This DOES make one external model request and MAY SPEND credits even on 7865.
No Journey data or credentials are printed/saved, and this script never
executes any model tool call. A pass proves only protocol compatibility,
not that an end-to-end CityNexus AgentRun has succeeded.
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request

from wb2api_agent import agent_settings, router_health


def run_probe(direct_model: str | None) -> int:
    if direct_model is None:
        online, reason = router_health()
        print("Free router: " + reason)
        if not online:
            print("NOT READY. Start FreeRouter/WorkBuddy2API locally before continuing.")
            return 2

    settings, label = agent_settings(direct_model=direct_model)
    print("Selected route:", label)
    print("Model request:", settings["CITYNEXUS_HERMES_MODEL"])
    print("Calling the model ONCE. 7865 is free-first but its last fallback can charge credits.")
    # Intentionally dummy UUID. This is only a wire-compatibility handshake:
    # no backend /journeys operation is invoked by this script.
    payload = {
        "model": settings["CITYNEXUS_HERMES_MODEL"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are testing OpenAI-compatible tool_call framing. "
                    "You cannot execute tools yourself. Return exactly one inspect_journey "
                    "function call for the given dummy journey ID; do not invent a result."
                ),
            },
            {
                "role": "user",
                "content": "Invoke inspect_journey for 00000000-0000-4000-8000-000000000000.",
            },
        ],
        "tools": [{
            "type": "function",
            "function": {
                "name": "inspect_journey",
                "description": "Read-only inspection request; it is NOT executed in this probe.",
                "parameters": {
                    "type": "object",
                    "properties": {"journey_id": {"type": "string"}},
                    "required": ["journey_id"],
                    "additionalProperties": False,
                },
            },
        }],
        "tool_choice": "auto",
        "stream": False,
        "max_tokens": 1600,
    }

    req = urllib.request.Request(
        settings["CITYNEXUS_HERMES_API_URL"],
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + settings["CITYNEXUS_HERMES_API_KEY"],
        },
        method="POST",
    )
    try:
        # Local wb2api should not traverse HTTP_PROXY, and a proxy must never
        # receive the user's wb2api Authorization header.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=135) as response:
            output = json.load(response)
            used_model = response.headers.get("x-free-router-model") or output.get("model") or "UNREPORTED"
    except urllib.error.HTTPError as exc:
        # Do not print the server response body: it can echo private input or tokens.
        print(f"MODEL_REQUEST_HTTP_{exc.code}")
        if exc.code == 503:
            print("The free chain may be cooling. Check /router/status and retry later.")
        return 3
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
        print("MODEL_REQUEST_FAILED:", type(exc).__name__)
        return 3

    msg = (((output.get("choices") or [{}])[0]).get("message") or {})
    calls = msg.get("tool_calls") or []
    tool_names = [
        call.get("function", {}).get("name")
        for call in calls
        if isinstance(call, dict) and isinstance(call.get("function"), dict)
    ]
    usage = output.get("usage") or {}
    print("Actual upstream model:", str(used_model)[:100])
    print("Usage credit:", usage.get("credit", "NOT_REPORTED"))
    if "inspect_journey" in tool_names:
        print("TOOL_FRAME_PASS: provider returned inspect_journey; no tool was executed.")
        print("This is NOT an end-to-end signed Journey AgentRun acceptance.")
        return 0
    print("CHAT_ONLY_OR_UNVERIFIED: model replied without inspect_journey tool_calls.")
    print("Do NOT claim autonomous tool use until one signed AgentRun completes.")
    return 4


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="One-bounded-request wb2api function call probe.")
    parser.add_argument("--direct-model", default=None,
                        help="Optional 7863 direct model, e.g. global:deepseek-v4.1-flash.")
    args = parser.parse_args()
    try:
        raise SystemExit(run_probe(args.direct_model))
    except ValueError as exc:
        print("Agent configuration unavailable:", str(exc))
        raise SystemExit(2)
