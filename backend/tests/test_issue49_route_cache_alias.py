"""Issue49 regression: task-owned route aliases resolve to canonical Place edges offline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_bootstrap_place_facts import enabled_settings, signed_place  # noqa: F401
from test_goal_route_freeze import (
    PARK,
    TOWER,
    _draft_with_canonical_places,
    _freeze,
    _task,
)
from app.agent import goal_route_freeze
from app.db.models import Activity, Journey, JourneyMission, PlanVersion
from app.db.session import SessionLocal


TOWER_TO_PARK = [[116.390, 39.910], [116.395, 39.925], [116.390, 39.940]]
SCHEDULE = [
    {"day_index": 0, "slot_index": 0, "start_time": "09:00", "end_time": "10:00"},
    {"day_index": 0, "slot_index": 1, "start_time": "14:00", "end_time": "15:00"},
    {"day_index": 1, "slot_index": 0, "start_time": "09:00", "end_time": "10:00"},
]


def _source_ref(candidate_id, canonical_ids, style):
    return canonical_ids[candidate_id] if style == "canonical" else candidate_id


def _prepare_variant(client, owner, root, task_id, canonical_ids, *, style, reverse=False):
    restored = client.get(root + f"/agent/goal-tasks/{task_id}", headers=owner)
    assert restored.status_code == 200, restored.text
    draft = restored.json()["draft_artifact"]
    days = draft["days"]
    first, second = (PARK, TOWER) if reverse else (TOWER, PARK)
    days[0]["slots"][0]["place_id"] = _source_ref(first["id"], canonical_ids, style)
    days[0]["slots"][1]["place_id"] = _source_ref(second["id"], canonical_ids, style)
    days[1]["slots"][0]["place_id"] = _source_ref(second["id"], canonical_ids, style)

    updated = client.put(
        root + f"/agent/goal-tasks/{task_id}/draft",
        headers=owner,
        json={"expected_revision": draft["revision"], "days": days},
    )
    assert updated.status_code == 200, updated.text
    revision = updated.json()["draft_artifact"]["revision"]
    prepared = client.post(
        root + f"/agent/goal-tasks/{task_id}/prepare-plan",
        headers={**owner, "Idempotency-Key": str(uuid4())},
        json={"expected_revision": revision, "schedule": SCHEDULE},
    )
    assert prepared.status_code == 201, prepared.text
    return prepared.json()["plan_version_id"]


def _offline_route_doors(monkeypatch):
    counts = {"measure": 0, "provider_client": 0}

    def measure(*_args, **_kwargs):
        counts["measure"] += 1
        return None

    def provider_client(*_args, **_kwargs):
        counts["provider_client"] += 1
        raise AssertionError("the fixture must never open the AMap provider")

    monkeypatch.setattr(goal_route_freeze, "_measure_now", measure)
    monkeypatch.setattr(goal_route_freeze, "_client", provider_client)
    return counts


def _append_route(
    task_id,
    from_place_id,
    to_place_id,
    *,
    receipt_id,
    geometry=True,
    geometry_status=None,
    coordinates=None,
):
    route = {
        "id": receipt_id,
        "provider_call_id": receipt_id,
        "from_place_id": from_place_id,
        "to_place_id": to_place_id,
        "from_name": "TEST_FIXTURE 塔",
        "to_name": "TEST_FIXTURE 湖",
        "provider": "amap",
        "provider_key": "amap-web-service",
        "coordinate_system": "WGS84",
        "distance_m": 1840,
        "duration_seconds": 27 * 60,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source_url": "https://uri.amap.com/navigation?fixture=issue49",
    }
    if geometry:
        route["route_geometry"] = {
            "type": "Feature",
            "properties": {
                "domain_crs": "WGS84",
                "source_provider": "amap-web-service",
                "provider_call_id": receipt_id,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates or TOWER_TO_PARK,
            },
        }
        route["geometry_status"] = geometry_status or "AVAILABLE"
    elif geometry_status:
        route["geometry_status"] = geometry_status

    with SessionLocal() as session:
        mission = session.get(JourneyMission, task_id)
        assert mission is not None
        intent = json.loads(mission.intent_json)
        intent["goal_task"].setdefault("research_routes", []).append(route)
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.commit()
    return route


def _activity_sources_and_places(plan_id):
    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(Activity)
                .where(Activity.plan_version_id == plan_id)
                .order_by(Activity.sequence_no)
            )
        )
        return [
            (row.place_id, json.loads(row.metadata_json or "{}").get("source_candidate_id"))
            for row in rows
        ]


def _replace_activity_sources(plan_id, source_ids):
    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(Activity)
                .where(Activity.plan_version_id == plan_id)
                .order_by(Activity.sequence_no)
            )
        )
        assert len(rows) >= len(source_ids)
        for row, source_id in zip(rows, source_ids):
            metadata = json.loads(row.metadata_json or "{}")
            metadata["source_candidate_id"] = source_id
            row.metadata_json = json.dumps(metadata, ensure_ascii=False)
        session.commit()


def _add_foreign_task_aliases(task_id, aliases, canonical_ids):
    with SessionLocal() as session:
        mission = session.get(JourneyMission, task_id)
        assert mission is not None
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        task["research_places"] = [
            {**dict(lead), "id": aliases[candidate_id], "canonical_place_id": canonical_ids[candidate_id]}
            for candidate_id, lead in ((TOWER["id"], TOWER), (PARK["id"], PARK))
        ]
        task["candidate_place_ids"] = list(canonical_ids.values())
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.commit()


def _add_ambiguous_current_task_alias(task_id, source_id, conflicting_canonical_id):
    with SessionLocal() as session:
        mission = session.get(JourneyMission, task_id)
        assert mission is not None
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        existing = next(
            row for row in task["research_places"] if row.get("id") == source_id
        )
        task["research_places"].append(
            {**existing, "canonical_place_id": conflicting_canonical_id}
        )
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.commit()


def _freeze_edge(client, owner, root, task_id, plan_id):
    response = _freeze(client, owner, root, task_id, plan_id)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1, body
    return body["edges"][0], body


def _freeze_domain_edge(journey_id, task_id, plan_id):
    """Read the untrimmed domain result and the candidate's actual frozen evidence snapshot."""
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        mission = session.get(JourneyMission, task_id)
        plan = session.get(PlanVersion, plan_id)
        assert journey is not None and mission is not None and plan is not None
        intent = json.loads(mission.intent_json)
        result = goal_route_freeze.freeze_routes(
            session, journey, intent["goal_task"], plan, str(mission.id)
        )
        assert result["total"] == 1, result
        session.commit()
        session.refresh(plan)
        evidence = json.loads(plan.mobility_evidence_json or "{}")
        assert evidence["snapshot_id"] == plan.mobility_snapshot_id
        return result["edges"][0], result, evidence


def test_native_candidates_share_one_task_route_across_provider_and_canonical_ids(
    signed_place, monkeypatch
):
    client, owner, _outsider, journey_id, *_ = signed_place
    calls = _offline_route_doors(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, provider_candidate, canonical_ids = _draft_with_canonical_places(
        client, owner, journey_id, task_id
    )
    canonical_candidate = _prepare_variant(
        client, owner, root, task_id, canonical_ids, style="canonical"
    )
    cached_route = _append_route(
        task_id,
        TOWER["id"],
        PARK["id"],
        receipt_id="TEST_FIXTURE_ROUTE_PROVIDER_KEY",
        geometry=False,
    )

    provider_rows = _activity_sources_and_places(provider_candidate)
    canonical_rows = _activity_sources_and_places(canonical_candidate)
    assert [place_id for place_id, _source_id in provider_rows] == [
        place_id for place_id, _source_id in canonical_rows
    ]
    assert provider_rows[0][1] == TOWER["id"]
    assert canonical_rows[0][1] == canonical_ids[TOWER["id"]]
    assert provider_candidate != canonical_candidate

    provider_edge, provider_body = _freeze_edge(
        client, owner, root, task_id, provider_candidate
    )
    canonical_edge, canonical_body = _freeze_edge(
        client, owner, root, task_id, canonical_candidate
    )
    for edge, body in ((provider_edge, provider_body), (canonical_edge, canonical_body)):
        assert edge["status"] == goal_route_freeze.REUSED, edge
        assert edge["minutes"] == 27, edge
        assert edge["captured_at"] == cached_route["captured_at"], edge
        assert body["frozen"] is True, body
    assert calls == {"measure": 0, "provider_client": 0}


@pytest.mark.parametrize(
    ("stored_key_style", "candidate_key_style", "reverse"),
    [
        ("provider", "canonical", False),
        ("canonical", "provider", False),
        ("provider", "canonical", True),
        ("canonical", "provider", True),
    ],
)
def test_cached_route_key_aliases_keep_geometry_direction_and_provider_receipt(
    signed_place, monkeypatch, stored_key_style, candidate_key_style, reverse
):
    client, owner, _outsider, journey_id, *_ = signed_place
    calls = _offline_route_doors(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, provider_candidate, canonical_ids = _draft_with_canonical_places(
        client, owner, journey_id, task_id
    )
    if candidate_key_style == "provider" and not reverse:
        plan_id = provider_candidate
    else:
        plan_id = _prepare_variant(
            client,
            owner,
            root,
            task_id,
            canonical_ids,
            style=candidate_key_style,
            reverse=reverse,
        )

    def key_for(candidate_id):
        return _source_ref(candidate_id, canonical_ids, stored_key_style)

    receipt_id = "TEST_FIXTURE_ROUTE_DIRECTION_RECEIPT"
    cached_route = _append_route(
        task_id,
        key_for(TOWER["id"]),
        key_for(PARK["id"]),
        receipt_id=receipt_id,
        coordinates=TOWER_TO_PARK,
    )

    origin_id = canonical_ids[PARK["id"]] if reverse else canonical_ids[TOWER["id"]]
    destination_id = canonical_ids[TOWER["id"]] if reverse else canonical_ids[PARK["id"]]
    edge, result, evidence = _freeze_domain_edge(journey_id, task_id, plan_id)
    fact = evidence["facts"][0]
    expected_coordinates = list(reversed(TOWER_TO_PARK)) if reverse else TOWER_TO_PARK

    assert edge["status"] == goal_route_freeze.REUSED, edge
    assert (edge["from_place_id"], edge["to_place_id"]) == (origin_id, destination_id), edge
    assert edge["minutes"] == 27 and edge["geometry_status"] == "AVAILABLE", edge
    assert edge["route_geometry"]["geometry"]["coordinates"] == expected_coordinates, edge
    assert edge["captured_at"] == cached_route["captured_at"], edge
    assert edge["geometry_provenance"]["provider_call_id"] == receipt_id, edge
    assert edge["route_geometry"]["properties"]["provider_call_id"] == receipt_id, edge
    assert fact["minutes"] == 27, fact
    assert fact["route_geometry"] == expected_coordinates, fact
    if reverse:
        assert edge["geometry_provenance"]["lookup_direction"] == "REVERSED_STORED_MEASUREMENT", edge
        assert edge["geometry_provenance"]["measurement_from_place_id"] == key_for(TOWER["id"]), edge
        assert edge["geometry_provenance"]["measurement_to_place_id"] == key_for(PARK["id"]), edge
    else:
        assert edge["geometry_provenance"].get("lookup_direction") is None, edge
    assert result["frozen"] is True, result
    assert calls == {"measure": 0, "provider_client": 0}


def test_blocked_cached_geometry_keeps_provider_duration_without_measuring_again(
    signed_place, monkeypatch
):
    client, owner, _outsider, journey_id, *_ = signed_place
    calls = _offline_route_doors(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, canonical_ids = _draft_with_canonical_places(
        client, owner, journey_id, task_id
    )
    cached_route = _append_route(
        task_id,
        canonical_ids[TOWER["id"]],
        canonical_ids[PARK["id"]],
        receipt_id="TEST_FIXTURE_BLOCKED_GEOMETRY_RECEIPT",
        geometry=False,
        geometry_status="BLOCKED_GEOMETRY_UNAVAILABLE",
    )

    edge, result, evidence = _freeze_domain_edge(journey_id, task_id, plan_id)
    assert edge["status"] == goal_route_freeze.REUSED, edge
    assert edge["minutes"] == 27, edge
    assert edge["geometry_status"] == "BLOCKED_GEOMETRY_UNAVAILABLE", edge
    assert edge["route_geometry"] is None, edge
    assert edge["captured_at"] == cached_route["captured_at"], edge
    assert edge["geometry_provenance"]["provider_call_id"] == "TEST_FIXTURE_BLOCKED_GEOMETRY_RECEIPT", edge
    assert evidence["facts"][0]["minutes"] == 27, evidence
    assert evidence["facts"][0]["route_geometry"] == [], evidence
    assert result["frozen"] is True, result
    assert calls == {"measure": 0, "provider_client": 0}


@pytest.mark.parametrize("alias_scope", ["unknown", "foreign_task"])
def test_unknown_or_foreign_task_alias_does_not_satisfy_the_route_edge(
    signed_place, monkeypatch, alias_scope
):
    client, owner, _outsider, journey_id, *_ = signed_place
    calls = _offline_route_doors(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, canonical_ids = _draft_with_canonical_places(
        client, owner, journey_id, task_id
    )
    aliases = {
        TOWER["id"]: f"amap:TEST_FIXTURE_{alias_scope.upper()}_TOWER",
        PARK["id"]: f"amap:TEST_FIXTURE_{alias_scope.upper()}_PARK",
    }
    if alias_scope == "foreign_task":
        other_task = _task(client, owner, journey_id)
        _add_foreign_task_aliases(other_task, aliases, canonical_ids)
    _replace_activity_sources(plan_id, [aliases[TOWER["id"]], aliases[PARK["id"]], aliases[PARK["id"]]])
    _append_route(
        task_id,
        aliases[TOWER["id"]],
        aliases[PARK["id"]],
        receipt_id=f"TEST_FIXTURE_{alias_scope.upper()}_MUST_NOT_REUSE",
        geometry=True,
    )

    edge, body = _freeze_edge(client, owner, root, task_id, plan_id)
    assert edge["status"] != goal_route_freeze.REUSED, edge
    assert body["frozen"] is False and body["verified"] == 0, body
    assert calls == {"measure": 1, "provider_client": 0}


def test_ambiguous_current_task_provider_alias_does_not_reuse_a_canonical_route(
    signed_place, monkeypatch
):
    client, owner, _outsider, journey_id, *_ = signed_place
    calls = _offline_route_doors(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, canonical_ids = _draft_with_canonical_places(
        client, owner, journey_id, task_id
    )
    _add_ambiguous_current_task_alias(
        task_id, TOWER["id"], canonical_ids[PARK["id"]]
    )
    _append_route(
        task_id,
        TOWER["id"],
        PARK["id"],
        receipt_id="TEST_FIXTURE_AMBIGUOUS_ALIAS_MUST_NOT_REUSE",
        geometry=True,
    )

    edge, body = _freeze_edge(client, owner, root, task_id, plan_id)
    assert edge["status"] != goal_route_freeze.REUSED, edge
    assert body["frozen"] is False and body["verified"] == 0, body
    assert calls == {"measure": 1, "provider_client": 0}
