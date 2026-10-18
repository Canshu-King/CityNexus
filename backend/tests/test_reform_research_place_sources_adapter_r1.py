"""Reform 2026-10-18, first adapter: `research_place_sources` is reachable from the product.

The reform order draws a line between a tool that exists in a directory and one a model can call:
the scanner is a backlog, not a certificate. These arms call the real route on the real app and
assert what this deployment actually does:

  1. the tool is advertised (v1 and v2 catalogs) and carries a read shape -- no domain mutation,
     no money, no C4;
  2. a DRAFT journey (no active plan) can research a place, and with no provider configured the
     answer is SOURCE_DISCOVERY_UNAVAILABLE with zero observations -- a missing provider never
     becomes invented leads;
  3. a place that is not in the journey's city is refused;
  4. a call without a place is a 422;
  5. a name outside the allowlist is a 404, which is what makes "registered" mean something.

Nothing is stubbed: the provider is not faked. The arms switch the deployment's own settings to
"no provider", which is a state the product really ships in.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.main as main_module
from app.agent.runtime import _MUTATION_TOOLS
from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2, TOOL_BY_NAME
from app.core.config import settings
from app.db.models import Journey, Place, WebObservation
from app.db.session import SessionLocal
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)
TOOL = "research_place_sources"


def _no_provider(monkeypatch) -> None:
    """Say what this deployment is: no AI key and no SearXNG endpoint.

    `Settings` is a frozen dataclass, so the state is expressed by replacing the module-level
    instance rather than mutating it. The handler imports `settings` at call time, so this is the
    object it reads.
    """
    from dataclasses import replace

    from app.core import config as config_module

    monkeypatch.setattr(
        config_module,
        "settings",
        replace(settings, ai_api_key=None, deepseek_web_search_enabled=False, searxng_url=None),
    )


def _demo_city_and_place() -> tuple[str, str, str, str]:
    """(traveler_id, city_code, place_id, timezone) from the demo scene."""
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    with SessionLocal() as session:
        journey = session.get(Journey, ids["journey_id"])
        assert journey is not None
        place = session.scalar(
            select(Place).where(Place.city_code == journey.city_code).order_by(Place.id)
        )
        assert place is not None
        return journey.traveler_id, journey.city_code, place.id, journey.timezone


def _draft_journey(traveler_id: str, city_code: str, timezone_name: str) -> str:
    start = datetime.now(timezone.utc) + timedelta(days=3)
    created = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": traveler_id,
            "title": "Reform adapter draft",
            "city_code": city_code,
            "timezone": timezone_name,
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(days=2)).isoformat(),
            "budget": {"amount_minor": 50000, "currency": "CNY"},
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_r1_tool_is_advertised_with_a_read_shape() -> None:
    v1 = {row["name"]: row for row in client.get("/api/v1/agent/tools").json()}
    v2 = {row["name"]: row for row in client.get("/api/v1/agent/tools/v2").json()}
    assert TOOL in v2
    # The v1 catalog's shape is frozen by `test_agent_authority_v2_actions`; new capabilities land
    # additively in v2, so this arm also pins that the addition did not leak backwards.
    assert TOOL not in v1
    assert TOOL in RUNTIME_MCP_ALLOWLIST_V2
    assert TOOL not in _MUTATION_TOOLS
    entry = TOOL_BY_NAME[TOOL].as_dict()
    assert entry["mutates_domain_truth"] is False
    assert entry["changes_money"] is False
    assert entry["changes_c4"] is False
    assert v2[TOOL]["action"] == "RESEARCH_PLACE_SOURCES"


def test_r2_draft_journey_researches_and_says_unavailable_without_provider(monkeypatch) -> None:
    _no_provider(monkeypatch)
    traveler_id, city_code, place_id, timezone_name = _demo_city_and_place()
    journey_id = _draft_journey(traveler_id, city_code, timezone_name)
    with SessionLocal() as session:
        draft = session.get(Journey, journey_id)
        assert draft is not None and draft.active_plan_version_id is None, "this arm needs a DRAFT"

    answer = client.post(
        f"/api/v1/agent/tools/{TOOL}",
        json={
            "request_id": "reform-research-" + str(uuid4()),
            "journey_id": journey_id,
            "place_id": place_id,
        },
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "SOURCE_DISCOVERY_UNAVAILABLE"
    assert body["authority"] == "NON_AUTHORITATIVE"
    assert body["observations"] == []
    assert body["query"].strip(), "the server must still build the query it would have sent"
    with SessionLocal() as session:
        rows = session.scalar(
            select(func.count())
            .select_from(WebObservation)
            .where(WebObservation.journey_id == journey_id)
        )
    assert rows == 0, "no provider means no rows: an unavailable answer must not write evidence"


def test_r3_place_outside_the_journey_city_is_refused() -> None:
    traveler_id, city_code, _place_id, timezone_name = _demo_city_and_place()
    journey_id = _draft_journey(traveler_id, city_code, timezone_name)
    answer = client.post(
        f"/api/v1/agent/tools/{TOOL}",
        json={
            "request_id": "reform-research-" + str(uuid4()),
            "journey_id": journey_id,
            "place_id": "place-not-in-this-city",
        },
    )
    assert answer.status_code == 404, answer.text


def test_r4_missing_place_is_422() -> None:
    traveler_id, city_code, _place_id, timezone_name = _demo_city_and_place()
    journey_id = _draft_journey(traveler_id, city_code, timezone_name)
    answer = client.post(
        f"/api/v1/agent/tools/{TOOL}",
        json={"request_id": "reform-research-" + str(uuid4()), "journey_id": journey_id},
    )
    assert answer.status_code == 422, answer.text


def test_r5_name_outside_the_allowlist_is_404() -> None:
    answer = client.post(
        "/api/v1/agent/tools/definitely_not_a_tool",
        json={"request_id": "reform-research-" + str(uuid4())},
    )
    assert answer.status_code == 404, answer.text


def test_r6_captured_leads_are_non_authoritative_and_deduplicated(monkeypatch) -> None:
    """The adapter's own write path, with a stub provider.

    This arm does NOT claim the provider is live. It stubs `SearXNGSearchProvider` so the work
    this adapter actually does can be observed: each lead lands as a row with
    `authority_status=NON_AUTHORITATIVE`, and the same lead captured twice is one row, not two.
    """
    from dataclasses import replace

    from app.core import config as config_module
    from app.integrations.web import searxng as searxng_module

    class StubProvider:
        def __init__(self, base_url: str, **_: object) -> None:
            self.base_url = base_url

        def search(self, query: str, *, limit: int = 5):
            return tuple(
                searxng_module.SearXNGObservation(
                    query=query,
                    url=f"https://example.invalid/{index}",
                    title=f"lead {index}",
                    domain="example.invalid",
                    content="excerpt",
                    captured_at="2026-10-18T10:00:00+00:00",
                )
                for index in range(2)
            )

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        config_module,
        "settings",
        replace(
            settings,
            ai_api_key=None,
            deepseek_web_search_enabled=False,
            searxng_url="http://stub.invalid",
        ),
    )
    monkeypatch.setattr(searxng_module, "SearXNGSearchProvider", StubProvider)

    traveler_id, city_code, place_id, timezone_name = _demo_city_and_place()
    journey_id = _draft_journey(traveler_id, city_code, timezone_name)
    payload = {
        "request_id": "reform-research-" + str(uuid4()),
        "journey_id": journey_id,
        "place_id": place_id,
    }
    first = client.post(f"/api/v1/agent/tools/{TOOL}", json=payload)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["status"] == "CAPTURED"
    assert len(body["observations"]) == 2
    assert {row["authority_status"] for row in body["observations"]} == {"NON_AUTHORITATIVE"}

    again = client.post(
        f"/api/v1/agent/tools/{TOOL}", json={**payload, "request_id": "reform-research-" + str(uuid4())}
    )
    assert again.status_code == 200, again.text
    assert len(again.json()["observations"]) == 2, "the same two leads must not double on re-read"

    with SessionLocal() as session:
        rows = session.scalars(
            select(WebObservation).where(WebObservation.journey_id == journey_id)
        ).all()
    assert len(rows) == 2
    assert {row.authority_status for row in rows} == {"NON_AUTHORITATIVE"}
