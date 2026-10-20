"""Reform 2026-10-18, alternative search: when the catalogue has nothing, the agent can still look.

This is the order's first priority -- "研究公开地点没结果后的备选搜索". The adapter wraps the
deployment's own provider path (`capture_real_city_candidates`), not an arbitrary HTTP client, and
the arms are about the budget and the honesty of the answer:

  - a replay call returns at most the requested number of rows, and appends a ProviderCall audit row;
  - a deployment with no captured snapshot answers zero candidates and says so -- it does not raise,
    and it does not invent a place;
  - the captured snapshot is refused for a city it does not belong to, by name;
  - the server's own caps are enforced by the request schema (radius 5 km, twenty rows).
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.main as main_module
from app.agent.runtime import _MUTATION_TOOLS
from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2, TOOL_BY_NAME
from app.db.models import Journey, ProviderCall
from app.db.session import SessionLocal
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)
TOOL = "discover_places"


def _journey(city_code: str | None = None) -> str:
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    if city_code is None:
        return ids["journey_id"]
    with SessionLocal() as session:
        journey = session.get(Journey, ids["journey_id"])
        assert journey is not None
        traveler_id = journey.traveler_id
        timezone_name = journey.timezone
    from datetime import datetime, timedelta, timezone

    start = datetime.now(timezone.utc) + timedelta(days=5)
    created = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": traveler_id,
            "title": "Reform discovery",
            "city_code": city_code,
            "timezone": timezone_name,
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(days=2)).isoformat(),
            "budget": {"amount_minor": 40000, "currency": "CNY"},
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _discover(journey_id: str, **fields: object):
    payload: dict[str, object] = {
        "request_id": "reform-discover-" + str(uuid4()),
        "journey_id": journey_id,
    }
    payload.update(fields)
    return client.post(f"/api/v1/agent/tools/{TOOL}", json=payload)


def _provider_calls() -> int:
    with SessionLocal() as session:
        return int(
            session.scalar(
                select(func.count())
                .select_from(ProviderCall)
                .where(ProviderCall.operation == "discover_city_services")
            )
            or 0
        )


def test_r1_tool_is_advertised_and_open_in_a_draft() -> None:
    v1 = {row["name"] for row in client.get("/api/v1/agent/tools").json()}
    v2 = {row["name"] for row in client.get("/api/v1/agent/tools/v2").json()}
    assert TOOL in v2
    assert TOOL not in v1, "new capabilities land in v2; the v1 catalog stays frozen"
    assert TOOL in RUNTIME_MCP_ALLOWLIST_V2
    assert TOOL not in _MUTATION_TOOLS, "discovery creates candidates, not plan truth"
    entry = TOOL_BY_NAME[TOOL].as_dict()
    assert entry["mutates_domain_truth"] is True
    assert entry["changes_money"] is False


def test_r2_replay_returns_bounded_rows_and_writes_an_audit_row() -> None:
    journey_id = _journey()
    before = _provider_calls()
    answer = _discover(journey_id, query="咖啡", mode="replay", limit=3, radius_m=2500)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["mode"] == "replay"
    assert body["count"] <= 3, body["count"]
    assert body["count"] == len(body["candidates"])
    assert body["counts_as_supply"] is bool(body["candidates"])
    assert body["provider_status"]["overpass"] == "REPLAY_NOT_CALLED"
    assert _provider_calls() == before + 1, "every discovery call must be auditable"


def test_r3_no_snapshot_answers_zero_instead_of_inventing(monkeypatch) -> None:
    from app.integrations.discovery import real_city as real_city_module

    monkeypatch.setattr(real_city_module, "_load_replay_snapshot", lambda: {})
    journey_id = _journey()
    answer = _discover(journey_id, query="夜市", mode="captured_replay")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["count"] == 0
    assert body["candidates"] == []
    assert body["counts_as_supply"] is False


def test_r4_a_snapshot_from_another_city_is_refused_by_name() -> None:
    journey_id = _journey(city_code="CN-BEIJING")
    answer = _discover(journey_id, query="咖啡", mode="captured_replay")
    assert answer.status_code == 409, answer.text
    assert "CAPTURED_REPLAY_CITY_MISMATCH" in answer.text


def test_r5_the_servers_own_caps_are_enforced() -> None:
    journey_id = _journey()
    too_wide = _discover(journey_id, query="咖啡", mode="replay", radius_m=6000)
    assert too_wide.status_code == 422, too_wide.text
    too_many = _discover(journey_id, query="咖啡", mode="replay", limit=25)
    assert too_many.status_code == 422, too_many.text
    no_query = _discover(journey_id, mode="replay")
    assert no_query.status_code == 422, no_query.text
