"""Trial-only, signed, read-only AI discovery guide on the real CityNexus API.

Run ONLY through trial/try_revolution.py. This imports the production FastAPI
application untouched and attaches one narrow, authenticated guidance route.
It does not create a Journey Mission, AgentRun, provider fact, POI, PlanVersion,
or tool-gateway action. Its one legitimate model tool call proposes an interest
category; real OSM queries remain separately user-initiated.

This is a genuine Hermes-compatible external MODEL TOOL CALL in the onboarding
experience. It is NOT the full autonomous Journey Operator, which only operates
on an actual ACTIVE Journey through its own persisted authorization pipeline.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from uuid import uuid4
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from app.main import app
from app.core.config import settings
from app.db.models import Journey
from app.db.session import SessionLocal
from app.traveler_principal import resolve_journey_member_principal


# Keep the public model-facing contract intentionally small and strictly typed.
_ALLOWED_CATEGORIES = frozenset({"park/garden", "museum/gallery", "cafe", "library"})
_SAFE_UPSTREAM_FAILURE_CODES = frozenset(
    {
        "UPSTREAM_HTTP_ERROR",
        "UPSTREAM_CONNECTION_ERROR",
        "UPSTREAM_PROTOCOL_ERROR",
        "UPSTREAM_TRANSPORT_ERROR",
        "UPSTREAM_TIMEOUT",
        "UPSTREAM_JSON_INVALID",
        "UPSTREAM_RESPONSE_INVALID",
    }
)
_logger = logging.getLogger(__name__)
_lock = threading.Lock()
_recent_model_requests: dict[str, list[float]] = {}


class DiscoveryGoal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str = Field(min_length=4, max_length=360)


def _check_local_agent() -> None:
    if not settings.ai_enabled or not settings.hermes_api_url or not settings.hermes_api_key:
        raise HTTPException(503, "本机 Hermes 模型尚未启用。可以继续手动探索。")
    # Intentionally reject non-loopback credentials and unexpected paths in
    # this local-only bridge; never turn it into an arbitrary SSRF endpoint.
    parsed = urlsplit(settings.hermes_api_url)
    if (
        parsed.scheme != "http" or
        parsed.hostname not in {"127.0.0.1", "localhost"} or
        parsed.port not in {7863, 7865} or
        parsed.path != "/v1/chat/completions" or
        parsed.username or parsed.password or parsed.query or parsed.fragment
    ):
        raise HTTPException(503, "本地 AI 网关地址不符合试用版的安全配置。")


def _admit_model_request(traveler_id: str) -> None:
    # At most one attempt per 15 seconds and five per 30 minutes per signed
    # member. This is local, single-process cost protection, not a billing cap.
    now = time.monotonic()
    with _lock:
        valid = [timestamp for timestamp in _recent_model_requests.get(traveler_id, [])
                 if now - timestamp < 1800]
        if valid and now - valid[-1] < 15:
            raise HTTPException(429, "刚刚已经请求过 AI，请稍后再试，不需要重复点击。")
        if len(valid) >= 5:
            raise HTTPException(429, "这半小时的 AI 体验次数已用完，避免意外消耗模型积分。")
        valid.append(now)
        _recent_model_requests[traveler_id] = valid


def _upstream_failure(
    *,
    failure_code: str,
    started_at: float,
    status_code: int = 502,
    upstream_status: int | None = None,
    exception_class: str | None = None,
) -> JSONResponse:
    safe_code = (
        failure_code
        if failure_code in _SAFE_UPSTREAM_FAILURE_CODES
        else "UPSTREAM_TRANSPORT_ERROR"
    )
    try:
        port = urlsplit(settings.hermes_api_url).port
    except ValueError:
        port = None
    elapsed_ms = max(0, round((time.monotonic() - started_at) * 1000))
    diagnostic = (
        f"upstream_status={upstream_status}"
        if upstream_status is not None
        else f"exception_class={exception_class or 'ResponseStructureError'}"
    )
    correlation_id = uuid4().hex
    _logger.warning(
        "adapter=wb2api_hermes_compatible port=%s elapsed_ms=%s %s correlation_id=%s",
        port,
        elapsed_ms,
        diagnostic,
        correlation_id,
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": "TRIAL_AI_UPSTREAM_FAILURE",
                "message": "AI 网关未完成请求；可以直接搜索公开地点继续。",
                "message_key": "error.trial_ai_upstream_failure",
                "trace_id": correlation_id,
                "details": None,
                "failure_code": safe_code,
                "correlation_id": correlation_id,
            }
        },
    )


def _invalid_upstream_response(*, started_at: float, upstream_status: int) -> JSONResponse:
    return _upstream_failure(
        failure_code="UPSTREAM_RESPONSE_INVALID",
        started_at=started_at,
        upstream_status=upstream_status,
    )


@app.post("/api/v1/journeys/{journey_id}/trial-ai-discovery", tags=["Revolution Local Trial"])
async def propose_public_discovery(
    journey_id: str,
    payload: DiscoveryGoal,
    request: Request,
) -> dict:
    """ONE user-requested, no-retry, signed read-only Hermes tool suggestion."""
    _check_local_agent()
    if not request.url.hostname in {"127.0.0.1", "localhost"}:
        raise HTTPException(403, "只允许本机独立试玩环境发起这个 AI 请求。")
    with SessionLocal() as session:
        principal, member = resolve_journey_member_principal(
            request, session, journey_id=journey_id
        )
        journey = session.get(Journey, journey_id)
        if journey is None or journey.deleted_at:
            raise HTTPException(404, "找不到当前行程。")
        if journey.status != "DRAFT" or journey.active_plan_version_id is not None:
            raise HTTPException(409, "该 AI 引导只服务未启动的探索草稿。")
        if journey.traveler_id != principal.traveler_id:
            raise HTTPException(403, "此入口只供草稿的签名创建者使用。")
        city_hint = journey.title.split(" · Revolution Explore", 1)[0][:60]
        signed_traveler = principal.traveler_id

    _admit_model_request(signed_traveler)
    tool_schema = {
        "type": "function",
        "function": {
            "name": "propose_public_discovery",
            "description": (
                "Propose a public POI search CATEGORY from a Chinese travel goal. "
                "Read-only; cannot look up actual venues, request a map service, "
                "execute an itinerary or assert that a place is open."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": sorted(_ALLOWED_CATEGORIES),
                        "description": "Exactly one public POI category supported by CityNexus",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Plain Chinese one or two sentence suggestion, <= 100 chars",
                    },
                },
                "required": ["category", "reason"],
                "additionalProperties": False,
            },
        },
    }
    body = {
        "model": settings.hermes_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are CityNexus Revolution's Chinese travel discovery guide. "
                    "Call propose_public_discovery exactly once with one allowed public "
                    "search category. Use the traveler-entered city label and travel idea "
                    "to suggest a category. For venue details, direct the traveler to the "
                    "public-place search flow. This screen collects an area label and "
                    "travel interests."
                ),
            },
            {
                "role": "user",
                "content": "用户填写的地区：" + city_hint +
                           "\n用户旅行想法：" + payload.goal,
            },
        ],
        "tools": [tool_schema],
        "tool_choice": {
            "type": "function", "function": {"name": "propose_public_discovery"}
        },
        "stream": False,
        "max_tokens": 1500,
        "temperature": 0,
    }
    started_at = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=55.0, write=5.0, pool=5.0),
            trust_env=False, follow_redirects=False,
        ) as client:
            response = await client.post(
                settings.hermes_api_url,
                headers={"Authorization": "Bearer " + settings.hermes_api_key},
                json=body,
            )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        return _upstream_failure(
            failure_code="UPSTREAM_TIMEOUT",
            status_code=504,
            started_at=started_at,
            exception_class=type(exc).__name__,
        )
    except httpx.HTTPStatusError as exc:
        return _upstream_failure(
            failure_code="UPSTREAM_HTTP_ERROR",
            started_at=started_at,
            upstream_status=exc.response.status_code,
        )
    except (httpx.ProtocolError, httpx.DecodingError) as exc:
        return _upstream_failure(
            failure_code="UPSTREAM_PROTOCOL_ERROR",
            started_at=started_at,
            exception_class=type(exc).__name__,
        )
    except httpx.ConnectError as exc:
        return _upstream_failure(
            failure_code="UPSTREAM_CONNECTION_ERROR",
            started_at=started_at,
            exception_class=type(exc).__name__,
        )
    except httpx.NetworkError as exc:
        return _upstream_failure(
            failure_code="UPSTREAM_CONNECTION_ERROR",
            started_at=started_at,
            exception_class=type(exc).__name__,
        )
    except httpx.HTTPError as exc:
        return _upstream_failure(
            failure_code="UPSTREAM_TRANSPORT_ERROR",
            started_at=started_at,
            exception_class=type(exc).__name__,
        )

    try:
        data = response.json()
    except httpx.DecodingError as exc:
        return _upstream_failure(
            failure_code="UPSTREAM_PROTOCOL_ERROR",
            started_at=started_at,
            exception_class=type(exc).__name__,
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return _upstream_failure(
            failure_code="UPSTREAM_JSON_INVALID",
            started_at=started_at,
            exception_class=type(exc).__name__,
        )

    if not isinstance(data, dict):
        return _invalid_upstream_response(
            started_at=started_at,
            upstream_status=response.status_code,
        )
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return _invalid_upstream_response(
            started_at=started_at,
            upstream_status=response.status_code,
        )
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return _invalid_upstream_response(
            started_at=started_at,
            upstream_status=response.status_code,
        )
    calls = message.get("tool_calls")
    if calls is None or calls == []:
        return {
            "status": "MODEL_NO_TOOL_CALL",
            "reason": "模型没有给出可验证的工具建议。你可以直接搜索城市和公开地点。",
            "provider_calls": 0,
            "agent_run_created": False,
        }
    if not isinstance(calls, list) or len(calls) != 1 or not isinstance(calls[0], dict):
        return _invalid_upstream_response(
            started_at=started_at,
            upstream_status=response.status_code,
        )
    function = calls[0].get("function")
    if not isinstance(function, dict) or not isinstance(function.get("name"), str):
        return _invalid_upstream_response(
            started_at=started_at,
            upstream_status=response.status_code,
        )
    if function["name"] != "propose_public_discovery":
        return {
            "status": "MODEL_NO_TOOL_CALL",
            "reason": "模型没有给出可验证的工具建议。你可以直接搜索城市和公开地点。",
            "provider_calls": 0,
            "agent_run_created": False,
        }
    raw_arguments = function.get("arguments")
    if not isinstance(raw_arguments, str):
        return _invalid_upstream_response(
            started_at=started_at,
            upstream_status=response.status_code,
        )
    try:
        args = json.loads(raw_arguments)
    except (json.JSONDecodeError, TypeError) as exc:
        return _upstream_failure(
            failure_code="UPSTREAM_JSON_INVALID",
            started_at=started_at,
            exception_class=type(exc).__name__,
        )
    if not isinstance(args, dict) or set(args) != {"category", "reason"}:
        return _invalid_upstream_response(
            started_at=started_at,
            upstream_status=response.status_code,
        )
    category, reason = args.get("category"), args.get("reason")
    if (
        not isinstance(category, str)
        or category not in _ALLOWED_CATEGORIES
        or not isinstance(reason, str)
        or not reason.strip()
    ):
        return _invalid_upstream_response(
            started_at=started_at,
            upstream_status=response.status_code,
        )
    return {
        "status": "MODEL_TOOL_SUGGESTION",
        "category": category,
        "reason": reason.strip()[:110],
        # The preview response is returned here; authenticated AgentRun persistence belongs to the Journey flow.
        "evidence": "HERMES_COMPAT_READ_ONLY_TOOL_RESPONSE",
        "provider_calls": 0,
        "agent_run_created": False,
    }
