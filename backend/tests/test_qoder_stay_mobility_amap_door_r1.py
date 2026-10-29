"""The stay/mobility provider surface has to answer on the key the stack was actually booted with.

Why this file exists: `GET /api/v1/journeys/{id}/stay-mobility/providers` builds its `provider_mesh`
from `experience_payload`, and that block used to decide AMap's readiness by reading one bare name,
`os.getenv("AMAP_WEB_KEY")` (the line this replaces was at app/stay_mobility.py:2085).  The stacks these
walks run on are booted with `CITYNEXUS_AMAP_WEB_KEY` -- the name config.py defines -- so on a machine
where the Agent really was routing, this surface answered NOT_CONFIGURED.  A status that contradicts the
work happening underneath it is the same defect already fixed twice on other doors
(app/integrations/china/amap.py:48 reads both spellings; backend/tests/test_v9_real_trip_operations.py:277
pins that one), and this file bolts the rule to this third surface.

Each arm sets the environment rather than trusting it, so the file passes the same way on a machine that
happens to hold a key and on one that holds none.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.models import Traveler
from app.integrations.china import amap as amap_module
from app.main import app
from app.db.session import SessionLocal

client = TestClient(app)

SETTINGS_NAME = "settings-name-not-a-real-key-000111222333"
BARE_NAME = "bare-name-not-a-real-key-444555666777"


def _traveler() -> str:
    """A real Traveler row, because the journey door refuses an id it cannot find."""
    traveler_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.add(Traveler(id=traveler_id, display_name="AMAP door probe", email=None,
                             locale="zh-CN", timezone="Asia/Shanghai", created_at=now, updated_at=now))
        session.commit()
    return traveler_id


def _journey_id() -> str:
    created = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": _traveler(),
            "title": "AMAP DOOR",
            "city_code": "CN-BEIJING",
            "timezone": "Asia/Shanghai",
            "start_at": "2026-12-03T09:00:00+08:00",
            "end_at": "2026-12-04T20:00:00+08:00",
            "budget": {"amount_minor": 60000, "currency": "CNY"},
            "planning_mode": "balanced",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _amap_cell(monkeypatch, *, settings_key: str | None, bare_key: str | None) -> dict:
    """One read of the surface, with both spellings pinned to a known state."""
    monkeypatch.setattr(amap_module, "settings", SimpleNamespace(amap_web_key=settings_key))
    monkeypatch.delenv("AMAP_WEB_KEY", raising=False)
    if bare_key is not None:
        monkeypatch.setenv("AMAP_WEB_KEY", bare_key)
    journey_id = _journey_id()
    response = client.get(f"/api/v1/journeys/{journey_id}/stay-mobility/providers")
    assert response.status_code == 200, response.text
    cell = response.json()["mobility"]["amap"]
    assert isinstance(cell, dict), cell
    return cell


def test_the_name_the_stacks_are_booted_with_answers_ready_here(monkeypatch) -> None:
    """The regression: this used to be NOT_CONFIGURED while the Agent underneath was routing."""
    cell = _amap_cell(monkeypatch, settings_key=SETTINGS_NAME, bare_key=None)
    assert cell["status"] == "READY"


def test_a_deployment_that_still_uses_the_bare_name_keeps_answering_ready(monkeypatch) -> None:
    cell = _amap_cell(monkeypatch, settings_key=None, bare_key=BARE_NAME)
    assert cell["status"] == "READY"


def test_with_neither_name_present_the_surface_says_so_instead_of_guessing(monkeypatch) -> None:
    cell = _amap_cell(monkeypatch, settings_key=None, bare_key=None)
    assert cell["status"] == "NOT_CONFIGURED"


def test_no_arm_leaks_the_value_it_configured(monkeypatch) -> None:
    """The answer is a word about readiness; the secret never travels back out."""
    for kwargs in ({"settings_key": SETTINGS_NAME, "bare_key": None},
                   {"settings_key": None, "bare_key": BARE_NAME}):
        journey_id = _journey_id()
        monkeypatch.setattr(amap_module, "settings",
                            SimpleNamespace(amap_web_key=kwargs["settings_key"]))
        monkeypatch.delenv("AMAP_WEB_KEY", raising=False)
        if kwargs["bare_key"] is not None:
            monkeypatch.setenv("AMAP_WEB_KEY", kwargs["bare_key"])
        response = client.get(f"/api/v1/journeys/{journey_id}/stay-mobility/providers")
        assert response.status_code == 200, response.text
        assert SETTINGS_NAME not in response.text
        assert BARE_NAME not in response.text
