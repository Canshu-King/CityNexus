from __future__ import annotations

import json
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
    # WB2api is an OpenAI-compatible endpoint, not the native MCP transport.
    # It remains subject to the persisted traveler policy and deterministic
    # gateway facts, but must not inherit the native MCP proposal-only fence.
    agent_id = "hermes-compat"
    _initial_max_tokens = 1200
    _empty_message_retry_max_tokens = 2400

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
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
        )
        self._owns_client = client is None

    def _complete(self, messages: list[dict]) -> dict:
        last_error: Exception | None = None
        errors: list[str] = []
        while self._model_index < len(self._model_chain):
            model = self._model_chain[self._model_index]
            try:
                payload = {
                    "model": model,
                    "temperature": 0,
                    "max_tokens": self._initial_max_tokens,
                    "messages": messages,
                    "tools": __import__(
                        "app.agent.runtime", fromlist=["citynexus_tool_definitions"]
                    ).citynexus_tool_definitions(),
                    "tool_choice": "auto",
                    "stream": True,
                }
                with self._client.stream(
                    "POST",
                    settings.hermes_api_url,
                    headers={"Authorization": f"Bearer {settings.hermes_api_key}"},
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "")
                    stream_response = "application/json" not in content_type
                    if not stream_response:
                        response.read()
                        choice = response.json()["choices"][0]
                        message = choice["message"]
                        finish_reason = choice.get("finish_reason")
                    else:
                        message = self._merge_sse(response.iter_lines())
                        finish_reason = None
                if not isinstance(message, dict):
                    raise TypeError("Hermes response message is invalid")
                if not str(message.get("content") or "").strip() and not message.get("tool_calls"):
                    # A reasoning model can spend the initial output budget on reasoning and
                    # finish with no visible assistant content.  WB2api reports this as an
                    # empty message with finish_reason=length (or as a streamed reasoning-only
                    # turn).  Retry the same model with a larger non-stream budget before
                    # consuming the next domestic fallback; this is a budget correction, not
                    # a model switch.
                    retryable_budget_exhaustion = (
                        stream_response
                        or finish_reason == "length"
                        or bool(message.get("reasoning_content"))
                    )
                    if retryable_budget_exhaustion:
                        retry_payload = {
                            **payload,
                            "stream": False,
                            "max_tokens": self._empty_message_retry_max_tokens,
                        }
                        retry = self._client.post(
                            settings.hermes_api_url,
                            headers={"Authorization": f"Bearer {settings.hermes_api_key}"},
                            json=retry_payload,
                        )
                        retry.raise_for_status()
                        retry_choice = retry.json()["choices"][0]
                        message = retry_choice["message"]
                    if (
                        not isinstance(message, dict)
                        or (
                            not str(message.get("content") or "").strip()
                            and not message.get("tool_calls")
                        )
                    ):
                        raise ValueError("Hermes response message is empty")
                self.model_key = model
                return message
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
                last_error = exc
                detail = str(exc).replace("\n", " ")[:240]
                errors.append(f"{model}:{type(exc).__name__}:{detail}")
                self._model_index += 1
        suffix = f"; attempts={'; '.join(errors)}" if errors else ""
        raise AgentRuntimeUnavailable(
            "Hermes Agent completion failed for configured model chain" + suffix
        ) from last_error

    @staticmethod
    def _merge_sse(lines) -> dict:
        content: list[str] = []
        reasoning: list[str] = []
        calls: dict[int, dict] = {}
        for line in lines:
            if not line or not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if raw == "[DONE]":
                break
            chunk = json.loads(raw)
            delta = ((chunk.get("choices") or [{}])[0].get("delta") or {})
            if delta.get("content"):
                content.append(str(delta["content"]))
            if delta.get("reasoning_content"):
                reasoning.append(str(delta["reasoning_content"]))
            for item in delta.get("tool_calls") or []:
                index = int(item.get("index", 0))
                call = calls.setdefault(
                    index,
                    {
                        "id": item.get("id") or f"tool-call-{index}",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    },
                )
                if item.get("id"):
                    call["id"] = item["id"]
                function = item.get("function") or {}
                if function.get("name"):
                    call["function"]["name"] = function["name"]
                if function.get("arguments"):
                    call["function"]["arguments"] += str(function["arguments"])
        message = {"role": "assistant", "content": "".join(content), "tool_calls": [calls[i] for i in sorted(calls)]}
        if reasoning:
            message["reasoning_content"] = "".join(reasoning)
        return message


def configured_journey_agent(
    *, native_factory: Callable[[], JourneyAgentRuntime] = DeepSeekJourneyAgent
) -> JourneyAgentRuntime:
    """Prefer configured Hermes and otherwise use the native DeepSeek loop."""

    if settings.hermes_api_url and settings.hermes_api_key:
        return HermesJourneyAgent()
    return native_factory()
