from __future__ import annotations

from typing import Callable, Protocol

import httpx

from app.agent.ai_availability import record_provider_answer, record_provider_refusal
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

    def __init__(self, *, client: httpx.Client | None = None):
        if not settings.hermes_api_url or not settings.hermes_api_key:
            raise AgentRuntimeUnavailable("Hermes runtime endpoint is not configured")
        self.model_key = settings.hermes_model
        self._client = client or httpx.Client(timeout=settings.impact_timeout_seconds)
        self._owns_client = client is None

    def _complete(self, messages: list[dict]) -> dict:
        try:
            response = self._client.post(
                settings.hermes_api_url,
                headers={"Authorization": f"Bearer {settings.hermes_api_key}"},
                json={
                    "model": self.model_key,
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
            # ORD-0697: the compat endpoint is the door the product actually uses when
            # `CITYNEXUS_HERMES_API_URL` is set, so it is the arm that has to witness the answer.
            record_provider_answer(
                provider_key=self.provider_key,
                model_key=self.model_key,
                status_code=response.status_code,
            )
            return message
        except httpx.HTTPStatusError as exc:
            # Split out ahead of the broad arm below, which also catches this one: a status the
            # provider actually sent is a refusal, and only a refusal.
            record_provider_refusal(
                provider_key=self.provider_key,
                model_key=self.model_key,
                status_code=exc.response.status_code,
            )
            raise AgentRuntimeUnavailable("Hermes Agent completion failed") from exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise AgentRuntimeUnavailable("Hermes Agent completion failed") from exc


def configured_journey_agent(
    *, native_factory: Callable[[], JourneyAgentRuntime] = DeepSeekJourneyAgent
) -> JourneyAgentRuntime:
    """Prefer configured Hermes and otherwise use the native DeepSeek loop."""

    if settings.hermes_api_url and settings.hermes_api_key:
        return HermesJourneyAgent()
    return native_factory()
