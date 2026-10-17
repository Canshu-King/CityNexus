from __future__ import annotations

import json
import logging
import re
from types import SimpleNamespace

import httpx
import pytest
from starlette.requests import Request

import trial.agent_preview_app as preview


_JOURNEY_ID = "journey-private-id-marker"
_TRAVELER_ID = "traveler-private-id-marker"
_PROMPT = "private-prompt-marker"
_API_KEY = "private-api-key-marker"
_AUTHORIZATION = f"Bearer {_API_KEY}"
_URL_QUERY = "private-url-query-marker"
_UPSTREAM_BODY = "private-upstream-body-marker"
_UPSTREAM_URL = "http://127.0.0.1:7865/v1/chat/completions"


class _PreviewSession:
    def __enter__(self) -> _PreviewSession:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def get(self, _model: type, _journey_id: str) -> SimpleNamespace:
        return SimpleNamespace(
            deleted_at=None,
            status="DRAFT",
            active_plan_version_id=None,
            traveler_id=_TRAVELER_ID,
            title="Fixture city · Revolution Explore",
        )


class _ReplyClient:
    def __init__(self, outcome: object, calls: list[tuple[tuple, dict]]) -> None:
        self._outcome = outcome
        self._calls = calls

    async def __aenter__(self) -> _ReplyClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def post(self, *args: object, **kwargs: object) -> object:
        self._calls.append((args, kwargs))
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self._outcome


def _request(journey_id: str) -> Request:
    path = f"/api/v1/journeys/{journey_id}/trial-ai-discovery"
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [(b"host", b"127.0.0.1:14173")],
            "server": ("127.0.0.1", 14173),
            "client": ("127.0.0.1", 43210),
            "root_path": "",
        }
    )


def _install_preview_fakes(
    monkeypatch: pytest.MonkeyPatch,
    outcome: object,
) -> list[tuple[tuple, dict]]:
    calls: list[tuple[tuple, dict]] = []
    monkeypatch.setattr(preview, "_check_local_agent", lambda: None)
    monkeypatch.setattr(preview, "_admit_model_request", lambda _traveler_id: None)
    monkeypatch.setattr(preview, "SessionLocal", _PreviewSession)
    monkeypatch.setattr(
        preview,
        "resolve_journey_member_principal",
        lambda *_args, **_kwargs: (SimpleNamespace(traveler_id=_TRAVELER_ID), None),
    )
    monkeypatch.setattr(
        preview,
        "settings",
        SimpleNamespace(
            hermes_api_url=f"{_UPSTREAM_URL}?{_URL_QUERY}",
            hermes_api_key=_API_KEY,
            hermes_model="fixture-model",
        ),
    )
    monkeypatch.setattr(
        preview.httpx,
        "AsyncClient",
        lambda **_kwargs: _ReplyClient(outcome, calls),
    )
    return calls


def _provider_outcome(kind: str) -> object:
    request = httpx.Request("POST", f"{_UPSTREAM_URL}?{_URL_QUERY}")
    if kind == "http_status":
        return httpx.Response(502, text=_UPSTREAM_BODY, request=request)
    if kind == "connection":
        return httpx.ConnectError(_UPSTREAM_BODY, request=request)
    if kind == "protocol":
        return httpx.RemoteProtocolError(_UPSTREAM_BODY, request=request)
    if kind == "timeout":
        return httpx.ReadTimeout(_UPSTREAM_BODY, request=request)
    if kind == "json":
        return httpx.Response(200, content=_UPSTREAM_BODY.encode(), request=request)
    if kind == "structure":
        return httpx.Response(
            200,
            json={"choices": _UPSTREAM_BODY},
            request=request,
        )
    if kind == "tool_arguments":
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "propose_public_discovery",
                                        "arguments": _UPSTREAM_BODY,
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
            request=request,
        )
    raise AssertionError(f"unrecognized fake outcome: {kind}")


@pytest.mark.parametrize(
    ("kind", "failure_code", "status_code", "diagnostic"),
    [
        ("http_status", "UPSTREAM_HTTP_ERROR", 502, "upstream_status=502"),
        ("connection", "UPSTREAM_CONNECTION_ERROR", 502, "exception_class=ConnectError"),
        ("protocol", "UPSTREAM_PROTOCOL_ERROR", 502, "exception_class=RemoteProtocolError"),
        ("timeout", "UPSTREAM_TIMEOUT", 504, "exception_class=ReadTimeout"),
        ("json", "UPSTREAM_JSON_INVALID", 502, "exception_class=JSONDecodeError"),
        ("structure", "UPSTREAM_RESPONSE_INVALID", 502, "upstream_status=200"),
        ("tool_arguments", "UPSTREAM_JSON_INVALID", 502, "exception_class=JSONDecodeError"),
    ],
)
@pytest.mark.asyncio
async def test_provider_failures_return_bounded_diagnostics_without_sensitive_data(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    kind: str,
    failure_code: str,
    status_code: int,
    diagnostic: str,
):
    calls = _install_preview_fakes(monkeypatch, _provider_outcome(kind))
    caplog.set_level(logging.WARNING, logger=preview.__name__)

    result = await preview.propose_public_discovery(
        _JOURNEY_ID,
        preview.DiscoveryGoal(goal=_PROMPT),
        _request(_JOURNEY_ID),
    )

    assert isinstance(result, preview.JSONResponse)
    assert result.status_code == status_code
    body = json.loads(result.body)
    error = body["error"]
    assert set(error) == {
        "code",
        "message",
        "message_key",
        "trace_id",
        "details",
        "failure_code",
        "correlation_id",
    }
    assert error["message"] == "AI 网关未完成请求；可以直接搜索公开地点继续。"
    assert error["failure_code"] == failure_code
    assert re.fullmatch(r"[0-9a-f]{32}", error["correlation_id"])
    assert error["trace_id"] == error["correlation_id"]
    assert error["details"] is None
    assert len(calls) == 1

    records = "\n".join(
        record.getMessage() for record in caplog.records if record.name == preview.__name__
    )
    assert "adapter=wb2api_hermes_compatible" in records
    assert "port=7865" in records
    assert "elapsed_ms=" in records
    assert "failure_code=" not in records
    assert diagnostic in records
    assert f"correlation_id={error['correlation_id']}" in records

    output = records + json.dumps(body, ensure_ascii=False)
    sensitive_values = (
        _JOURNEY_ID,
        _TRAVELER_ID,
        _PROMPT,
        _API_KEY,
        _AUTHORIZATION,
        "Authorization",
        _URL_QUERY,
        _UPSTREAM_BODY,
    )
    for sensitive in sensitive_values:
        assert sensitive not in output
