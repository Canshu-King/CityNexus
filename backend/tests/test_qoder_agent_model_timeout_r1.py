"""The Agent's model turn must carry its own clock, not the impact probe's.

Why this file exists: on the rescue line, a traveller who typed one wish and pressed 发送 got
nothing back. The goal-task loop's first model turn was recorded as `MODEL_TIMEOUT` with zero steps
written (canary database `citynexus_v3_agent_1022.db`, run `87ecbd2b`, 2026-10-22), because
`HermesJourneyAgent` built its HTTP client with `settings.impact_timeout_seconds` -- ten seconds,
which is the budget of a provider impact probe, while a tool-loop turn carries the journey context
and the whole tool schema.

These arms pin the door itself: the number the client is built with must come from the Agent's own
setting, turning the impact knob down must not be able to mute the assistant, and a too-small
setting must still leave a usable floor.
"""
from __future__ import annotations

from types import SimpleNamespace

import httpx

from app.agent import orchestrator as module


def _settings(**overrides):
    base = {
        "hermes_api_url": "http://127.0.0.1:9/v1/chat/completions",
        "hermes_api_key": "loopback-test-key",
        "hermes_model": "test-model",
        "hermes_model_fallbacks": (),
        "agent_model_timeout_seconds": 90.0,
        "impact_timeout_seconds": 10.0,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _built_client(monkeypatch, settings):
    monkeypatch.setattr(module, "settings", settings)
    agent = module.HermesJourneyAgent()
    client = agent._client
    try:
        return client
    finally:
        client.close()


def test_the_model_turn_clock_comes_from_the_agents_own_setting(monkeypatch):
    client = _built_client(monkeypatch, _settings(agent_model_timeout_seconds=77.0))
    assert client.timeout.read == 77.0
    assert client.timeout.write == 10.0
    assert client.timeout.connect == 10.0


def test_turning_the_impact_probe_down_cannot_mute_the_assistant(monkeypatch):
    """The negative control: the old coupling would make this read 5.0 instead of 90.0."""
    client = _built_client(monkeypatch, _settings(impact_timeout_seconds=1.0))
    assert client.timeout.read == 90.0


def test_a_steamroller_small_agent_setting_still_leaves_a_floor(monkeypatch):
    """Five seconds is the floor the door has always kept; the connect/write legs sit under it too."""
    client = _built_client(monkeypatch, _settings(agent_model_timeout_seconds=0.1))
    assert client.timeout.read == 5.0
    assert client.timeout.connect == 5.0
    assert client.timeout.write == 5.0
