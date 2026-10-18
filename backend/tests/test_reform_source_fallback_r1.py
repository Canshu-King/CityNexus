"""Issue #37's acceptance line, made real: a first source answering zero does not stop the Agent.

Before this slice both research tools asked exactly one provider. `NO_RESULTS` or
`FAILED_EXTERNAL` from that provider came back as the whole answer, and the traveler was
told to try something else -- the "把困难退回给旅行者" pattern the reform order names. Both
tools now walk a bounded chain of the providers this deployment actually configured: at most
two attempts, stopping as soon as one returns leads, and every leg is audited.

The arms are about the chain, not about the network:

  r1  first provider answers zero, second is captured -> `CAPTURED`, `fallback_used=true`,
      two `ProviderCall` rows carrying their attempt number;
  r2  one provider, and it fails -> one attempt, no invented observation, no fallback claim;
  r3  classroom mode earns its estimate only after both legs answered empty;
  r4  the Place-rooted tool shares the same runner, so both tools keep the same promise;
  r5  an explicit provider preference is still a preference: it goes first, the other one is
      the bounded second step.

No live provider is called anywhere in this file, so nothing here is `LIVE_VERIFIED`.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.core.config as config_module
import app.main as main_module
from app.db.models import Journey, Place, ProviderCall, Traveler, WebObservation
from app.db.session import SessionLocal
from app.integrations.web import source_discovery

client = TestClient(main_module.app)


@pytest.fixture(scope="module", autouse=True)
def _schema_present() -> None:
    from app.db.session import ensure_schema

    ensure_schema()


def _journey(topic_tag: str) -> tuple[str, str]:
    """A DRAFT Journey in a city with a public label, plus this arm's unique topic."""

    now = datetime.now(timezone.utc)
    traveler_id, journey_id = str(uuid4()), str(uuid4())
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="fallback arm " + topic_tag,
                email=None,
                locale="zh-CN",
                timezone="Asia/Shanghai",
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )
        )
        session.flush()
        session.add(
            Journey(
                id=journey_id,
                traveler_id=traveler_id,
                title="厦门 · 2日行程",
                city_code="CN-XIAMEN",
                timezone="Asia/Shanghai",
                start_at=now.isoformat(),
                end_at=(now + timedelta(days=2)).isoformat(),
                budget_currency="CNY",
                budget_amount_minor=90000,
                planning_mode="balanced",
                status="DRAFT",
                active_plan_version_id=None,
                current_activity_id=None,
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )
        )
        session.commit()
    return journey_id, "鼓浪屿" + topic_tag


def _place(journey_id: str, tag: str) -> str:
    """A canonical Place in the Journey's own city, with every required column filled."""

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        place_id = str(uuid4())
        session.add(
            Place(
                id=place_id,
                provider_key="reform-fallback-stub",
                external_id=f"scout:{uuid4()}",
                city_code=journey.city_code,
                name="鼓浪屿" + tag,
                category="attraction",
                latitude=24.445,
                longitude=118.066,
                opening_hours_json="{}",
                tags_json="[]",
                metadata_json="{}",
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        session.commit()
        return place_id


def _lead(url: str, title: str):
    return SimpleNamespace(
        query="server-built",
        url=url,
        title=title,
        domain=url.split("/")[2],
        provider_key="stub",
        captured_at="2026-10-19T02:00:00+00:00",
        source_class="OPEN_WEB",
        content="excerpt",
    )


def _stub_providers(monkeypatch, behaviour: dict[str, tuple[list, str, str | None]]) -> list[str]:
    """Patch availability and the one provider call, recording the order it was asked in."""

    order: list[str] = []
    monkeypatch.setattr(
        source_discovery,
        "provider_availability",
        lambda: {"web": "web" in behaviour, "searxng": "searxng" in behaviour},
    )

    def run(query: str, *, provider: str, limit: int = 5):
        order.append(provider)
        drafts, status, reason = behaviour[provider]
        return drafts, status, reason

    monkeypatch.setattr(source_discovery, "run_web_search", run)
    return order


def _leads_call(journey_id: str, topic: str, **extra):
    payload = {
        "request_id": "fallback-leads-" + str(uuid4()),
        "journey_id": journey_id,
        "topic": topic,
    }
    payload.update(extra)
    response = client.post("/api/v1/agent/tools/v2/discover_source_leads", json=payload)
    return response.status_code, response.json()


def _calls(operation: str, needle: str) -> list[ProviderCall]:
    """Provider rows for one operation, narrowed by a per-arm unique string.

    The audit table is shared by every arm in this session, so counting a whole operation
    would read another arm's rows as this one's. Each arm searches with a token no other arm
    uses, and the rows are matched on it.
    """

    with SessionLocal() as session:
        rows = session.scalars(
            select(ProviderCall).where(
                ProviderCall.operation == operation,
                ProviderCall.request_json.like(f"%{needle}%"),
            )
        ).all()
    return list(rows)


def _observations(journey_id: str) -> int:
    with SessionLocal() as session:
        return session.scalar(
            select(func.count())
            .select_from(WebObservation)
            .where(WebObservation.journey_id == journey_id)
        )


def test_r1_zero_from_the_first_source_is_answered_by_the_second(monkeypatch) -> None:
    tag = uuid4().hex[:6]
    order = _stub_providers(
        monkeypatch,
        {
            "web": ([], "NO_RESULTS", None),
            "searxng": (
                [_lead("https://example.gov.cn/gulangyu", "鼓浪屿官方页面")],
                "CAPTURED",
                None,
            ),
        },
    )
    journey_id, topic = _journey(tag)
    status, body = _leads_call(journey_id, topic)
    assert status == 200, body
    assert order == ["web", "searxng"], order
    assert body["status"] == "CAPTURED"
    assert body["fallback_used"] is True
    assert [row["provider"] for row in body["attempts"]] == ["web", "searxng"]
    assert body["attempts"][0]["count"] == 0 and body["attempts"][1]["count"] == 1
    assert len(body["leads"]) == 1
    assert body["leads"][0]["authority_status"] == "NON_AUTHORITATIVE"

    rows = _calls("source_lead_discovery", topic)
    assert len(rows) == 2, "both the empty answer and the capture are auditable"
    attempts = sorted(json.loads(row.request_json).get("attempt") for row in rows)
    assert attempts == [1, 2], attempts
    assert _observations(journey_id) == 1


def test_r2_a_single_failing_provider_is_one_attempt_and_no_invented_lead(monkeypatch) -> None:
    tag = uuid4().hex[:6]
    order = _stub_providers(monkeypatch, {"searxng": ([], "FAILED_EXTERNAL", "SEARXNG_FAILED")})
    journey_id, topic = _journey(tag)
    status, body = _leads_call(journey_id, topic)
    assert status == 200, body
    assert order == ["searxng"], order
    assert body["status"] == "FAILED_EXTERNAL"
    assert body["reason_code"] == "SEARXNG_FAILED"
    assert body["fallback_used"] is False
    assert len(body["attempts"]) == 1
    assert body["leads"] == []
    assert "estimate" not in body, "classroom mode is off, so nothing is estimated"
    assert body["next_legal_path"]
    assert _observations(journey_id) == 0
    assert len(_calls("source_lead_discovery", topic)) == 1


def test_r3_classroom_estimates_only_after_the_whole_chain_came_back_empty(monkeypatch) -> None:
    tag = uuid4().hex[:6]
    order = _stub_providers(
        monkeypatch,
        {"web": ([], "NO_RESULTS", None), "searxng": ([], "NO_RESULTS", None)},
    )
    monkeypatch.setattr(
        config_module, "settings", replace(config_module.settings, classroom_mode=True)
    )
    journey_id, topic = _journey(tag)
    status, body = _leads_call(journey_id, topic)
    assert status == 200, body
    assert order == ["web", "searxng"], "the estimate is only earned after both legs answered"
    assert body["status"] == "NO_RESULTS"
    assert body["fallback_used"] is True
    assert body["authority"] == "NON_AUTHORITATIVE"
    assert body["leads"] == []
    assert body["estimate"]["kind"] == "source_angles"
    assert body["estimate"]["authority_eligible"] is False
    assert "http" not in json.dumps(body["estimate"], ensure_ascii=False).lower()
    assert _observations(journey_id) == 0


def test_r4_the_place_rooted_tool_walks_the_same_chain(monkeypatch) -> None:
    tag = uuid4().hex[:6]
    order = _stub_providers(
        monkeypatch,
        {
            "web": ([], "NO_RESULTS", None),
            "searxng": ([_lead("https://example.org/hours", "开放时间")], "CAPTURED", None),
        },
    )
    journey_id, _topic = _journey(tag)
    place_id = _place(journey_id, tag)
    response = client.post(
        "/api/v1/agent/tools/v2/research_place_sources",
        json={
            "request_id": "fallback-place-" + str(uuid4()),
            "journey_id": journey_id,
            "place_id": place_id,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert order == ["web", "searxng"], order
    assert body["status"] == "CAPTURED"
    assert body["fallback_used"] is True
    assert len(body["attempts"]) == 2
    assert len(body["observations"]) == 1
    assert len(_calls("place_source_research", "鼓浪屿" + tag)) == 2


def test_r5_an_explicit_preference_goes_first_but_is_not_a_dead_end(monkeypatch) -> None:
    tag = uuid4().hex[:6]
    order = _stub_providers(
        monkeypatch,
        {
            "web": ([_lead("https://example.com/a", "lead")], "CAPTURED", None),
            "searxng": ([], "NO_RESULTS", None),
        },
    )
    journey_id, topic = _journey(tag)
    status, body = _leads_call(journey_id, topic, provider="searxng")
    assert status == 200, body
    assert order == ["searxng", "web"], order
    assert body["provider"] == "web"
    assert body["fallback_used"] is True
    assert len(body["leads"]) == 1
