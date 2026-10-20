"""The Guardian's status answer must carry what it actually saw, with its source and its moment.

V3 item 3 asks for sourced, timestamped risk observations. `guardian_status` already reported the
runs (decision, evidence, the plan it moved from and to); it did not report the observation rows the
server holds, so a screen could not say "the 地铁停运 note came from provider X at 07:12 and expired".
These arms cover that addition and nothing else.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent import guardian
from app.db.models import (
    Base,
    Journey,
    ProviderObservation,
    Traveler,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ago(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _ahead(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


@pytest.fixture()
def seeded():
    """Two journeys, each with observations; one journey also holds an expired and a sourceless row."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ids: dict[str, str] = {}
    with factory() as session:
        traveler = str(uuid.uuid4())
        session.add(Traveler(id=traveler, display_name="owner", email=None, locale="zh-CN",
                             timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
        ids["traveler"] = traveler
        for key in ("mine", "theirs"):
            journey = str(uuid.uuid4())
            session.add(Journey(id=journey, traveler_id=traveler, title=key, city_code="350200",
                                timezone="Asia/Shanghai", start_at=_ahead(60), end_at=_ahead(600),
                                budget_currency="CNY", budget_amount_minor=500_00,
                                status="ACTIVE", created_at=_now(), updated_at=_now()))
            ids[key] = journey

        def observe(journey_id: str, *, provider: str, kind: str, state: str, captured: str,
                    expires: str | None, provenance: str) -> str:
            ident = str(uuid.uuid4())
            session.add(ProviderObservation(
                id=ident, journey_id=journey_id, provider_key=provider, observation_type=kind,
                state=state, incident_fingerprint="inc-" + ident[:8], provenance=provenance,
                captured_at=captured, expires_at=expires, payload_json="{}", created_at=captured))
            return ident

        ids["older"] = observe(ids["mine"], provider="weather_api", kind="STORM_WARNING",
                               state="SEVERE", captured=_ago(120), expires=_ago(5),
                               provenance="REPLAY")
        ids["live"] = observe(ids["mine"], provider="transit_feed", kind="LINE_SUSPENDED",
                              state="SUSPENDED", captured=_ago(10), expires=_ahead(50),
                              provenance="LIVE")
        ids["no_expiry"] = observe(ids["mine"], provider="official_web", kind="OPENING_CHANGE",
                                   state="CHANGED", captured=_ago(30), expires=None,
                                   provenance="MANUAL_FIXTURE")
        ids["theirs"] = observe(ids["theirs"], provider="weather_api", kind="TYPHOON",
                                state="WATCH", captured=_ago(1), expires=_ahead(600),
                                provenance="LIVE")
        session.commit()
    return SimpleNamespace(factory=factory, ids=ids)


def _status(seeded) -> dict:
    from app.agent.guardian import guardian_status

    with seeded.factory() as session:
        journey = session.get(Journey, seeded.ids["mine"])
        return guardian_status(session, journey)


def test_the_status_answer_still_carries_everything_it_carried_before(seeded):
    answer = _status(seeded)
    assert answer["journey_id"] == seeded.ids["mine"]
    for key in ("standing_mission", "current_active_plan_version_id", "latest", "runs"):
        assert key in answer, key
    assert answer["latest"] is None and answer["runs"] == []


def test_each_observation_names_its_source_and_the_moment_it_was_taken(seeded):
    rows = {row["id"]: row for row in _status(seeded)["observations"]}
    live = rows[seeded.ids["live"]]
    assert live["provider_key"] == "transit_feed"
    assert live["observation_type"] == "LINE_SUSPENDED"
    assert live["state"] == "SUSPENDED"
    assert live["provenance"] == "LIVE"
    assert live["expires_at"] is not None
    with seeded.factory() as session:
        stored = session.get(ProviderObservation, seeded.ids["live"])
    # The door copies the stored moment; it does not re-stamp the row with the time of the read.
    assert live["captured_at"] == stored.captured_at
    assert datetime.fromisoformat(live["captured_at"]) <= datetime.now(timezone.utc)


def test_an_observation_that_never_stated_an_expiry_reports_none_not_a_stamp(seeded):
    rows = {row["id"]: row for row in _status(seeded)["observations"]}
    assert rows[seeded.ids["no_expiry"]]["expires_at"] is None
    # An expired observation stays visible with its own times: the window does not hide history.
    assert rows[seeded.ids["older"]]["expires_at"] is not None
    assert datetime.fromisoformat(rows[seeded.ids["older"]]["expires_at"]) < (
        datetime.now(timezone.utc))
    for row in rows.values():
        assert row["provider_key"] and row["captured_at"] and row["provenance"], row


def test_the_list_is_bounded_to_this_journey_and_ordered_newest_first(seeded):
    listed = [row["id"] for row in _status(seeded)["observations"]]
    assert seeded.ids["theirs"] not in listed
    assert listed == [seeded.ids["live"], seeded.ids["no_expiry"], seeded.ids["older"]]
    captured = [row["captured_at"] for row in _status(seeded)["observations"]]
    assert captured == sorted(captured, reverse=True)


def test_a_read_of_observations_writes_nothing(seeded):
    with seeded.factory() as session:
        observed_before = len(session.scalars(select(ProviderObservation)).all())
        runs_before = len(session.scalars(select(guardian.GuardianRun)).all())
    first = _status(seeded)
    again = _status(seeded)
    assert first["observations"] == again["observations"]
    with seeded.factory() as session:
        assert len(session.scalars(select(ProviderObservation)).all()) == observed_before
        assert len(session.scalars(select(guardian.GuardianRun)).all()) == runs_before


def test_the_guardian_module_asks_no_network_to_build_this_answer(seeded):
    """The status path is a projection of stored rows; an http client must not become reachable."""
    import ast
    from pathlib import Path

    tree = ast.parse(Path(guardian.__file__).read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    network = {"http", "httpx", "requests", "aiohttp", "urllib", "socket", "ssl"}
    assert not sorted(roots & network), sorted(roots & network)
    assert _status(seeded)["journey_id"] == seeded.ids["mine"]
