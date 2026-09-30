from __future__ import annotations

from typing import Callable, Protocol

import httpx

from app.agent.runtime import AgentRuntimeUnavailable, DeepSeekJourneyAgent
from app.agent.runtime_identity import HERMES_COMPAT_ENDPOINT
from app.core.config import settings


class JourneyAgentRuntime(Protocol):
    provider_key: str
    model_key: str

    def run(self, session, *, journey, mission, max_steps: int = 12) -> dict: ...


class HermesJourneyAgent(DeepSeekJourneyAgent):
    """Hermes primary-runtime adapter over an OpenAI-compatible tool endpoint."""

    provider_key = "hermes"
    runtime_identity = HERMES_COMPAT_ENDPOINT

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        model_chain: tuple[str, ...] | None = None,
    ):
        if not settings.hermes_api_url or not settings.hermes_api_key:
            raise AgentRuntimeUnavailable("Hermes runtime endpoint is not configured")
        configured_chain = model_chain or (settings.hermes_model, *settings.hermes_model_fallbacks)
        self._model_chain = tuple(dict.fromkeys(item.strip() for item in configured_chain if item.strip()))
        if not self._model_chain:
            raise AgentRuntimeUnavailable("Hermes runtime model chain is empty")
        self._model_index = 0
        self.model_key = self._model_chain[0]
        self._client = client or httpx.Client(timeout=settings.impact_timeout_seconds)
        self._owns_client = client is None

    def _complete(self, messages: list[dict]) -> dict:
        last_error: Exception | None = None
        while self._model_index < len(self._model_chain):
            model = self._model_chain[self._model_index]
            try:
                response = self._client.post(
                    settings.hermes_api_url,
                    headers={"Authorization": f"Bearer {settings.hermes_api_key}"},
                    json={
                        "model": model,
                        "temperature": 0,
                        "max_tokens": 1200,
                        "messages": messages,
                        "tools": __import__(
                            "app.agent.runtime", fromlist=["citynexus_tool_definitions"]
                        ).citynexus_tool_definitions(),
                        "tool_choice": "auto",
                    },
                )
                response.raise_for_status()
                message = response.json()["choices"][0]["message"]
                if not isinstance(message, dict):
                    raise TypeError("Hermes response message is invalid")
                self.model_key = model
                return message
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
                last_error = exc
                self._model_index += 1
        raise AgentRuntimeUnavailable("Hermes Agent completion failed for configured model chain") from last_error


def configured_journey_agent(
    *, native_factory: Callable[[], JourneyAgentRuntime] = DeepSeekJourneyAgent
) -> JourneyAgentRuntime:
    """Prefer configured Hermes and otherwise use the native DeepSeek loop."""

    if settings.hermes_api_url and settings.hermes_api_key:
        return HermesJourneyAgent()
    return native_factory()
