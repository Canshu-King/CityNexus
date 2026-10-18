"""Reform 2026-10-18, Scout: research can start before a canonical Place exists.

`research_place_sources(place_id)` is correct but cannot be called when Photon,
Nominatim and the city catalogue all answer zero: there is no Place to name.
These arms prove the new first step is real and bounded:

  1. advertised in v2, granted to a PLAN_ONLY mission, and still read-shaped
     (no domain truth, no money, no C4);
  2. with zero canonical Places, a public region + topic returns non-authoritative
     leads, writes WebObservation/ProviderCall rows, and creates no Place;
  3. with no configured provider the answer is SOURCE_DISCOVERY_UNAVAILABLE,
     not invented leads;
  4. a Journey whose public region is unknown is REGION_PENDING and sends no query;
  5. an internal id smuggled into the topic is a named 422;
  6. the old query builder never forwards `CN-RV-...` or a private title.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.main as main_module
from app.agent.mission_plan import build_mission_plan
from app.agent.runtime import _MUTATION_TOOLS
from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2, TOOL_BY_NAME
from app.db.models import Journey, Place, ProviderCall, Traveler, WebObservation
from app.db.session import SessionLocal
from app.integrations.web import source_discovery
from app.integrations.web.public_region import REGION_PENDING
from app.integrations.web.research_service import build_source_query

client = TestClient(main_module.app)
TOOL = "discover_source_leads"


@pytest.fixture(scope="module", autouse=True)
def _schema_present() -> None:
    from app.db.session import ensure_schema

    ensure_schema()


def _journey(city_code: str = "CN-XIAMEN", title: str = "Reform scout") -> str:
    now = datetime.now(timezone.utc)
    traveler_id, journey_id = str(uuid4()), str(uuid4())
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="scout arm",
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
                title=title,
                city_code=city_code,
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
    return journey_id


def _call(journey_id: str, topic: str, **extra):
    payload = {
        "request_id": "reform-scout-" + str(uuid4()),
        "journey_id": journey_id,
        "topic": topic,
    }
    payload.update(extra)
    return client.post(f"/api/v1/agent/tools/v2/{TOOL}", json=payload)


def _leads(drafts):
    return [
        SimpleNamespace(
            query="server-built",
            url=draft["url"],
            title=draft["title"],
            domain=draft["domain"],
            provider_key="stub-web",
            captured_at="2026-10-18T15:30:00+00:00",
            source_class="OPEN_WEB",
            content=draft["content"],
        )
        for draft in drafts
    ]


def test_r1_tool_is_advertised_granted_and_read_shaped() -> None:
    v1 = {row["name"] for row in client.get("/api/v1/agent/tools").json()}
    v2 = {row["name"] for row in client.get("/api/v1/agent/tools/v2").json()}
    assert TOOL in v2
    assert TOOL not in v1, "new capabilities land in v2; the v1 catalog stays frozen"
    assert TOOL in RUNTIME_MCP_ALLOWLIST_V2
    assert TOOL not in _MUTATION_TOOLS, "a source lead is not a domain mutation"
    entry = TOOL_BY_NAME[TOOL].as_dict()
    assert entry["mutates_domain_truth"] is False
    assert entry["changes_money"] is False
    assert entry["changes_c4"] is False
    plan_only = build_mission_plan(autonomy="PLAN_ONLY")
    assert TOOL in set(plan_only.allowed_tools)


def test_r2_zero_places_still_researches_and_never_creates_a_place(monkeypatch) -> None:
    journey_id = _journey()
    with SessionLocal() as session:
        before = session.scalar(
            select(func.count()).select_from(Place).where(Place.city_code == "CN-XIAMEN")
        )
    monkeypatch.setattr(
        source_discovery,
        "provider_availability",
        lambda: {"web": True, "searxng": False},
    )
    monkeypatch.setattr(
        source_discovery,
        "run_web_search",
        lambda query, *, provider, limit=5: (
            _leads(
                [
                    {
                        "url": "https://example.gov.cn/gucun",
                        "title": "古村落官方介绍",
                        "domain": "example.gov.cn",
                        "content": "官方页面，开放时间待核实",
                    },
                    {
                        "url": "https://example.org/food",
                        "title": "当地小吃来源",
                        "domain": "example.org",
                        "content": "来源线索，未核实",
                    },
                ]
            ),
            "CAPTURED",
            None,
        ),
    )

    answer = _call(journey_id, "古村落")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "CAPTURED", body
    assert body["authority"] == "NON_AUTHORITATIVE"
    assert body["region"]["label"] == "XIAMEN", body
    assert len(body["leads"]) == 2
    for lead in body["leads"]:
        assert lead["authority_status"] == "NON_AUTHORITATIVE"
        assert lead["identity_status"] == "UNVERIFIED"
        assert lead["can_promote_to_place"] is False
        assert lead["url"].startswith("https://")

    with SessionLocal() as session:
        rows = session.scalars(
            select(WebObservation).where(WebObservation.journey_id == journey_id)
        ).all()
        calls = session.scalars(
            select(ProviderCall).where(ProviderCall.operation == "source_lead_discovery")
        ).all()
        after = session.scalar(
            select(func.count()).select_from(Place).where(Place.city_code == "CN-XIAMEN")
        )
    assert len(rows) == 2
    assert all(row.authority_status == "NON_AUTHORITATIVE" for row in rows)
    assert len(calls) >= 1
    assert after == before, "a source lead must not create a canonical Place"


def test_r3_no_provider_is_a_named_unavailable_not_invented_leads(monkeypatch) -> None:
    journey_id = _journey()
    monkeypatch.setattr(
        source_discovery,
        "provider_availability",
        lambda: {"web": False, "searxng": False},
    )
    answer = _call(journey_id, "古村落")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "SOURCE_DISCOVERY_UNAVAILABLE"
    assert body["reason_code"] == "NO_WEB_PROVIDER"
    assert body["leads"] == []
    assert body["next_legal_path"]
    with SessionLocal() as session:
        rows = session.scalar(
            select(func.count())
            .select_from(WebObservation)
            .where(WebObservation.journey_id == journey_id)
        )
    assert rows == 0


def test_r4_unknown_public_region_sends_no_query(monkeypatch) -> None:
    journey_id = _journey(city_code="CN-RV-random", title="周末随便走走")

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("a query was sent without a confirmed public region")

    monkeypatch.setattr(source_discovery, "run_web_search", must_not_run)
    answer = _call(journey_id, "古村落")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == REGION_PENDING
    assert body["region"]["confirmed"] is False
    assert body["leads"] == []
    assert "region" in body["next_legal_path"].lower()


def test_r5_internal_id_in_the_topic_is_a_named_422(monkeypatch) -> None:
    journey_id = _journey()
    monkeypatch.setattr(
        source_discovery,
        "provider_availability",
        lambda: {"web": True, "searxng": False},
    )
    answer = _call(journey_id, "研究 CN-RV-123456 的古村落")
    assert answer.status_code == 422, answer.text
    assert "PUBLIC_TOPIC_CARRIES_INTERNAL_ID" in answer.text


def test_r6_the_old_query_builder_never_forwards_an_internal_code() -> None:
    place = SimpleNamespace(name="鼓浪屿", external_id="overpass:node/123")
    firstlook = SimpleNamespace(city_code="CN-RV-random", title="厦门 · 2日行程")
    query = build_source_query(place, firstlook)
    assert "厦门" in query
    assert "CN-RV" not in query
    assert "CN RV" not in query

    private = SimpleNamespace(city_code="CN-RV-random", title="我的私人周末")
    with pytest.raises(ValueError) as refused:
        build_source_query(place, private)
    assert REGION_PENDING in str(refused.value)
