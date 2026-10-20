"""Guardian's recovery epoch: one open reality per Journey, superseded on change.

The epoch is server-owned and semantic: two provider rows for the same incident
do not open a new generation just because their Event ids differ, while a new
actionable incident does.  The watch opens one only when it found a material
conflict; a clean refresh does not.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.main as main_module
from app.agent.guardian_stream import guardian_stream
from app.core import config as config_module
from app.db.models import Event, Journey, RecoveryEpoch
from app.db.session import SessionLocal
from app.recovery_epoch import (
    SUPERSEDED,
    current_open_recovery_epoch,
    ensure_recovery_epoch,
)
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)


@pytest.fixture(scope="module", autouse=True)
def _schema_present() -> None:
    from app.db.session import ensure_schema

    ensure_schema()


def _planned_journey() -> str:
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    generated = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
    )
    assert generated.status_code == 201, generated.text
    selected = client.post(
        f"/api/v1/journeys/{journey_id}/plans/{generated.json()[0]['id']}/select"
    )
    assert selected.status_code == 200, selected.text
    return journey_id


def _event(journey_id: str, *, marker: str, activity_id: str | None = None) -> str:
    now = datetime.now(timezone.utc).isoformat()
    event_id = str(uuid4())
    with SessionLocal() as session:
        session.add(
            Event(
                id=event_id,
                journey_id=journey_id,
                provider_key="truth-mesh",
                provenance="SYSTEM_DERIVED",
                event_type="CLOSURE",
                severity="MAJOR",
                status="DETECTED",
                affected_activity_id=activity_id,
                occurred_at=now,
                detected_at=now,
                payload_json=json.dumps({"incident_fingerprint": marker}),
                created_at=now,
            )
        )
        session.commit()
    return event_id


def test_r1_same_reality_reuses_the_open_epoch() -> None:
    journey_id = _planned_journey()
    event_id = _event(journey_id, marker="incident-a")
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        first = ensure_recovery_epoch(session, journey)
        session.commit()
        first_id = first.id
        assert first.generation == 1
        assert event_id in json.loads(first.triggering_event_ids_json)
    with SessionLocal() as session:
        second = ensure_recovery_epoch(session, session.get(Journey, journey_id))
        session.commit()
        assert second.id == first_id, "the same reality opened a second epoch"
    with SessionLocal() as session:
        count = session.scalar(
            select(func.count())
            .select_from(RecoveryEpoch)
            .where(RecoveryEpoch.journey_id == journey_id)
        )
    assert count == 1


def test_r2_a_new_incident_supersedes_and_opens_the_next_generation() -> None:
    journey_id = _planned_journey()
    _event(journey_id, marker="incident-a")
    with SessionLocal() as session:
        first = ensure_recovery_epoch(session, session.get(Journey, journey_id))
        session.commit()
        first_id = first.id
    _event(journey_id, marker="incident-b")
    with SessionLocal() as session:
        second = ensure_recovery_epoch(session, session.get(Journey, journey_id))
        session.commit()
        second_id = second.id
        assert second.generation == 2
        old = session.get(RecoveryEpoch, first_id)
        assert old is not None
        assert old.status == SUPERSEDED
        assert old.superseded_by_recovery_epoch_id == second_id
    with SessionLocal() as session:
        current = current_open_recovery_epoch(session, journey_id)
        assert current is not None and current.id == second_id


def test_r3_the_stream_exposes_the_open_epoch() -> None:
    journey_id = _planned_journey()
    _event(journey_id, marker="incident-stream")
    with SessionLocal() as session:
        epoch = ensure_recovery_epoch(session, session.get(Journey, journey_id))
        session.commit()
        epoch_id = epoch.id
        stream = guardian_stream(session, session.get(Journey, journey_id))
    assert stream["recovery_epoch"] is not None
    assert stream["recovery_epoch"]["id"] == epoch_id
    assert stream["recovery_epoch"]["generation"] == 1


def test_r4_refresh_with_a_material_conflict_opens_an_epoch(monkeypatch) -> None:
    journey_id = _planned_journey()
    monkeypatch.setattr(
        config_module,
        "settings",
        config_module.settings.__class__(
            **{**config_module.settings.__dict__, "guardian_autorun": True}
        ),
    )
    import app.live_context_watch as watch_module

    def conflicting(session, journey, **_kwargs):
        now = datetime.now(timezone.utc).isoformat()
        session.add(
            Event(
                id=str(uuid4()),
                journey_id=journey.id,
                provider_key="truth-mesh",
                provenance="SYSTEM_DERIVED",
                event_type="CLOSURE",
                severity="MAJOR",
                status="DETECTED",
                affected_activity_id=None,
                occurred_at=now,
                detected_at=now,
                payload_json=json.dumps({"incident_fingerprint": "incident-watch"}),
                created_at=now,
            )
        )
        session.flush()
        return {
            "status": "MATERIAL_CONFLICT",
            "material_conflicts": [{"activity_id": "a1", "reason_code": "EXPLICIT_CLOSED_STATE"}],
            "created_recovery_event_ids": [],
        }

    monkeypatch.setattr(watch_module, "run_live_context_watch", conflicting)
    answer = client.post(
        "/api/v1/agent/tools/v2/refresh_live_context",
        json={"request_id": "reform-epoch-" + str(uuid4()), "journey_id": journey_id},
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "REFRESHED", body
    assert body["recovery_epoch"] is not None, body
    assert body["recovery_epoch"]["generation"] == 1


def test_r5_a_clean_refresh_does_not_open_an_epoch(monkeypatch) -> None:
    journey_id = _planned_journey()
    monkeypatch.setattr(
        config_module,
        "settings",
        config_module.settings.__class__(
            **{**config_module.settings.__dict__, "guardian_autorun": True}
        ),
    )
    import app.live_context_watch as watch_module

    def clean(*_args, **_kwargs):
        return {
            "status": "NO_MATERIAL_CHANGE",
            "material_conflicts": [],
            "created_recovery_event_ids": [],
        }

    monkeypatch.setattr(watch_module, "run_live_context_watch", clean)
    answer = client.post(
        "/api/v1/agent/tools/v2/refresh_live_context",
        json={"request_id": "reform-epoch-" + str(uuid4()), "journey_id": journey_id},
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "REFRESHED", body
    assert body["recovery_epoch"] is None, body
    with SessionLocal() as session:
        count = session.scalar(
            select(func.count())
            .select_from(RecoveryEpoch)
            .where(RecoveryEpoch.journey_id == journey_id)
        )
    assert count == 0
