"""Secure wb2api -> CityNexus Hermes-compatible Agent bridge.

This is CONFIGURATION of the existing real Agent runtime, not a chat demo.
NEVER place a key in this repository, browser JS, URL, or runtime logs.
The key must come from WB2API_KEY or be entered locally via getpass.
"""
from __future__ import annotations

import getpass
import json
import os
import re
from pathlib import Path
import urllib.error
import urllib.request

FREE_ROUTER_BASE = "http://127.0.0.1:7865/v1"
DIRECT_BASE = "http://127.0.0.1:7863/v1"
FREE_ROUTER_MODEL = "auto:cheapest"


def read_key_file(path: Path) -> str:
    """Read an explicitly supplied key or Markdown API Key table, never execute it."""
    try:
        if path.stat().st_size > 65536:
            raise ValueError("WB2API key document is too large")
        text = path.read_text(encoding="utf-8-sig").strip()
    except OSError:
        raise ValueError("WB2API key file is not readable") from None
    match = re.search(r"\*\*API Key\*\*\s*\|\s*`([^`]+)`", text)
    key = match.group(1).strip() if match else text
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{8,512}", key):
        raise ValueError("WB2API key file must contain one key or an API Key table entry")
    return key


def agent_settings(*, direct_model: str | None = None, key_file: Path | None = None) -> tuple[dict[str, str], str]:
    """Construct environment consumed by app.agent.orchestrator.HermesJourneyAgent.

    The original application requires the *complete chat completions URL*,
    not merely the /v1 base URL from the general wb2api tutorial.
    """
    if direct_model is not None:
        if not re.fullmatch(r"(?:global|cn):[a-zA-Z0-9._-]{1,100}", direct_model):
            raise ValueError("Direct model must be a valid global:<model> or cn:<model> identifier")
        base, model, label = DIRECT_BASE, direct_model, "wb2api-direct"
    else:
        base, model, label = FREE_ROUTER_BASE, FREE_ROUTER_MODEL, "wb2api-free-router"

    key = read_key_file(key_file) if key_file is not None else (os.environ.get("WB2API_KEY") or "").strip()
    if not key:
        key = getpass.getpass("Enter local WB2API_KEY (hidden, never committed): ").strip()
    if not key:
        raise ValueError("WB2API_KEY missing; AI Agent is not configured")
    if any(ch in key for ch in "\r\n"):
        raise ValueError("WB2API_KEY must be one line")

    settings = {
        "CITYNEXUS_AI_ENABLED": "true",
        # Reuse the checked-in real Hermes-compatible tool-use loop, not the
        # DeepSeek /responses adapter (wb2api speaks /chat/completions).
        "CITYNEXUS_HERMES_API_URL": base + "/chat/completions",
        "CITYNEXUS_HERMES_API_KEY": key,
        "CITYNEXUS_HERMES_MODEL": model,
        # The 7865 router IGNOREs requested concrete model names; sending
        # domestic default fallbacks would only repeat the same routed request.
        "CITYNEXUS_HERMES_MODEL_FALLBACKS": "",
        # A bounded external request timeout, not an implicit 10s cutoff for
        # real tool-rich model turns. No infinite retries on model failures.
        "CITYNEXUS_IMPACT_TIMEOUT_SECONDS": "120",
        # Native Hermes and native DeepSeek are separate protocols. Keep them
        # unset to avoid promoting a chat gateway to the wrong runtime.
        "CITYNEXUS_HERMES_NATIVE_API_URL": "",
        "CITYNEXUS_HERMES_API_SERVER_KEY": "",
        "CITYNEXUS_AI_API_KEY": "",
        "CITYNEXUS_DEEPSEEK_WEB_SEARCH": "false",
        # Preserve the original protective default: model decisions do not
        # silently trigger background Guardian or payment transactions.
        "CITYNEXUS_GUARDIAN_AUTORUN": "false",
        "CITYNEXUS_BOOKING_PROVIDER": "mock-booking",
        "CITYNEXUS_PAYMENT_PROVIDER": "mock-payment",
        "NO_PROXY": "127.0.0.1,localhost,::1",
        "no_proxy": "127.0.0.1,localhost,::1",
    }
    return settings, label


def router_health(timeout: float = 3.0) -> tuple[bool, str]:
    """Free-router metadata only. No credentials, model billing, or tool calls."""
    req = urllib.request.Request("http://127.0.0.1:7865/router/status")
    try:
        # Loopback health must never be redirected through a system HTTP proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=timeout) as response:
            if response.status != 200:
                return False, f"ROUTER_HTTP_{response.status}"
            data = json.load(response)
        if isinstance(data, dict) and data.get("healthy") is False:
            return False, "ROUTER_UNHEALTHY"
        return True, "ROUTER_ENDPOINT_REACHABLE"
    except (TimeoutError, urllib.error.URLError, OSError, ValueError) as exc:
        # Avoid serializing URLs that can include operator-specific paths.
        return False, type(exc).__name__
