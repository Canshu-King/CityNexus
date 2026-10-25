# ruff: noqa: F811 -- pytest fixture arguments use imported fixture names
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from test_issue47_simulation import sim  # noqa: F401
from test_issue47_private_reads import stack  # noqa: F401
from app import main
from app.db.models import Activity, Journey, JourneyMission, ProviderCall
from app.simulation.city_catalog import SimulationCityIdentity


def region_source(factory, ids, *, with_receipt=True, level="city", code="320100"):
    db = factory()
    s = next(db)
    journey = s.get(Journey, ids["journey"])
    journey.city_code = "CN-RV-fixture-unique"
    region = {
        "adcode": code,
        "name": "南京市",
        "level": level,
        "query": "南京",
        "status": "RESOLVED",
    }
    task = str(uuid4())
    stamp = datetime.now(timezone.utc).isoformat()
    s.add(
        JourneyMission(
            id=task,
            journey_id=journey.id,
            traveler_id=ids["owner"],
            user_text="Source fixture",
            requested_autonomy="PLAN_ONLY",
            status="COMPLETED",
            created_at=stamp,
            intent_json=json.dumps(
                {"mode": "GOAL_PLANNING", "goal_task": {"schema_version": 1, "amap_region": region}}
            ),
            max_cost_delta_minor=0,
            max_loss_minor=0,
            max_schedule_drift_min=0,
        )
    )
    if with_receipt:
        s.add(
            ProviderCall(
                id=str(uuid4()),
                provider_key="amap-web-service",
                operation="goal_amap_district",
                request_json=json.dumps({"region": "南京"}),
                response_json=json.dumps({"status": "RESULTS", "districts": [region]}),
                status="SUCCESS",
                created_at=stamp,
            )
        )
    s.commit()
    db.close()
    return task


def test_internal_city_is_preserved_and_provider_binding_requires_source(sim):
    client, ids, path, factory, headers, url, post = sim
    task = region_source(factory, ids)
    endpoint = url.replace("/runs", "/city-identity")
    response = post(endpoint, {"source_task_id": task})
    assert response.status_code == 200, response.text
    assert response.json()["internal_city_code"] == "CN-RV-fixture-unique"
    assert response.json()["provider_city_adcode"] == "320100"
    assert post(endpoint, {"source_task_id": task}).json() == response.json()
    db = factory()
    s = next(db)
    assert s.get(Journey, ids["journey"]).city_code == "CN-RV-fixture-unique"
    assert s.get(SimulationCityIdentity, ids["journey"]).source_call_id
    db.close()


@pytest.mark.parametrize(
    "receipt,level,code,reason",
    [
        (False, "city", "320100", "CITY_PROVIDER_RECEIPT_REQUIRED"),
        (True, "district", "320102", "CITY_LEVEL_SOURCE_REQUIRED"),
    ],
)
def test_unacquired_or_district_identity_not_published(sim, receipt, level, code, reason):
    client, ids, path, factory, headers, url, post = sim
    task = region_source(factory, ids, with_receipt=receipt, level=level, code=code)
    response = post(url.replace("/runs", "/city-identity"), {"source_task_id": task})
    assert response.status_code == 409, response.text
    assert reason in response.text


def test_missing_city_data_cannot_be_published(sim):
    client, ids, path, factory, headers, url, post = sim
    task = region_source(factory, ids)
    assert post(url.replace("/runs", "/city-identity"), {"source_task_id": task}).status_code == 200
    response = post(url.replace("/runs", "/cities/publish"), {"publish_public_facts": True})
    assert response.status_code == 409, response.text
    assert "CITY_SNAPSHOT_INCOMPLETE" in response.text


def test_public_catalog_is_explicit_deduplicated_and_has_no_private_ids(sim):
    client, ids, path, factory, headers, url, post = sim
    from app.simulation.city_catalog import SimulationPublicCitySnapshot

    db = factory()
    s = next(db)
    # Controlled public-snapshot fixtures exercise selection, not real provider acquisition.
    for code in ["320100", "330100", "350200"]:
        raw = json.dumps(
            {
                "provider_city_adcode": code,
                "public_name": code,
                "provenance": "CAPTURED_PROVIDER_SNAPSHOT",
                "poi": [],
                "routes": [],
            }
        )
        s.add(
            SimulationPublicCitySnapshot(
                provider_adcode=code,
                snapshot_json=raw,
                snapshot_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                published_at=datetime.now(timezone.utc).isoformat(),
                published_by=ids["owner"],
            )
        )
    s.commit()
    db.close()
    response = client.get(url.replace("/runs", "/cities") + "?seed=17", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["eligible_city_count"] == 3
    assert response.json()["selected_provider_adcode"] in {"320100", "330100", "350200"}
    assert ids["owner"] not in response.text and ids["journey"] not in response.text


def test_native_http_writes_are_blocked_after_run_started(sim, monkeypatch):
    client, ids, path, factory, headers, url, post = sim
    post(url, {"seed": 17})
    for route in main.app.routes:
        if getattr(route, "path", "") in {
            "/api/v1/journeys/{journey_id}/activities/{activity_id}/depart",
            "/api/v1/journeys/{journey_id}/activities/{activity_id}/complete",
            "/api/v1/journeys/{journey_id}/activities/{activity_id}/skip",
        }:
            client.app.add_api_route(
                route.path,
                route.endpoint,
                methods=list(route.methods),
                response_model=route.response_model,
            )
    prefix = "/api/v1/journeys/" + ids["journey"] + "/activities/" + ids["activities"][0]
    for action in ("depart", "complete", "skip"):
        result = client.post(prefix + "/" + action, headers=headers)
        assert result.status_code == 409, result.text
        assert "USE_SIMULATION_RUN_ADVANCE" in result.text
    assert client.get(url + "/current", headers=headers).json()["sequence"] == 0


def test_wrong_current_cursor_rolls_back_entire_simulation_command(sim):
    client, ids, path, factory, headers, url, post = sim
    run = post(url, {"seed": 17}).json()
    db = factory()
    s = next(db)
    s.get(Journey, ids["journey"]).current_activity_id = ids["activities"][1]
    s.commit()
    db.close()
    result = post(url + "/" + run["run_id"] + "/advance", {"expected_sequence": 0})
    assert result.status_code == 409, result.text
    restored = client.get(url + "/current", headers=headers).json()
    assert restored == run
    db = factory()
    s = next(db)
    assert s.get(Activity, ids["activities"][0]).status == "ACTIVE"
    db.close()


def test_publish_copies_only_acquired_public_facts_and_is_idempotent(sim):
    client, ids, path, factory, headers, url, post = sim
    task = region_source(factory, ids)
    assert post(url.replace("/runs", "/city-identity"), {"source_task_id": task}).status_code == 200
    from app.db.models import Place, RealPlaceCandidate, PlanVersion
    from app.replanning.provider_snapshots import MobilitySnapshot
    from app.simulation.city_catalog import SimulationPublicCitySnapshot

    db = factory()
    s = next(db)
    stamp = datetime.now(timezone.utc).isoformat()
    poi_ids = []
    source_places = []
    for n in range(5):
        pid = "public-poi-" + str(n)
        ext = "amap:POI000" + str(n)
        poi_ids.append(pid)
        s.add(
            Place(
                id=pid,
                provider_key="amap",
                external_id=ext,
                city_code="CN-RV-fixture-unique",
                name="Public POI " + str(n),
                category="PARK",
                latitude=32 + n * 0.001,
                longitude=118 + n * 0.001,
                opening_hours_json="{}",
                tags_json="[]",
                metadata_json="{}",
                updated_at=stamp,
            )
        )
        s.add(
            RealPlaceCandidate(
                id="rpc-fixture-" + str(n),
                journey_id=ids["journey"],
                provider_key="amap",
                external_id=ext,
                city_code="CN-RV-fixture-unique",
                name="Public POI " + str(n),
                category="PARK",
                latitude=32 + n * 0.001,
                longitude=118 + n * 0.001,
                tags_json="[]",
                opening_hours_json="{}",
                metadata_json='{"discovery_mode":"live"}',
                captured_at=stamp,
                evidence_json="{}",
                materialized_place_id=pid,
                status="MATERIALIZED",
            )
        )
        source_places.append({"provider_object_id": ext[5:], "adcode": "320102"})
    s.add(
        ProviderCall(
            id=str(uuid4()),
            provider_key="amap-web-service",
            operation="goal_amap_search",
            request_json="{}",
            response_json=json.dumps({"places": source_places}),
            status="SUCCESS",
            created_at=stamp,
        )
    )
    pairs = {(poi_ids[n], poi_ids[n + 1]): 10 for n in range(3)}
    snapshot = MobilitySnapshot.from_minutes(
        source_provider_key="amap-fixture",
        minutes=pairs,
        fact_quality="LIVE_PROVIDER_CAPTURE",
        route_geometries={pair: [[118, 32], [118.01, 32.01]] for pair in pairs},
    )
    plan = s.get(PlanVersion, ids["plan"])
    plan.mobility_snapshot_id = snapshot.snapshot_id
    plan.mobility_evidence_json = json.dumps(snapshot.to_evidence())
    s.commit()
    db.close()


    endpoint = url.replace("/runs", "/cities/publish")
    response = post(endpoint, {"publish_public_facts": True})
    assert response.status_code == 200, response.text
    assert post(endpoint, {"publish_public_facts": True}).json() == response.json()
    db = factory()
    s = next(db)
    row = s.get(SimulationPublicCitySnapshot, "320100")
    assert len(json.loads(row.snapshot_json)["poi"]) == 5
    assert len(json.loads(row.snapshot_json)["routes"]) == 3
    assert ids["journey"] not in row.snapshot_json
    assert ids["owner"] not in row.snapshot_json
    assert ids["plan"] not in row.snapshot_json
    db.close()


def test_paired_session_controls_only_bound_journey_without_shared_presenter_key(sim):
    client, ids, path, factory, headers, url, post = sim
    from app import demo_pairing
    from app.demo_access import require_demo_presenter
    from starlette.requests import Request

    client.app.include_router(demo_pairing.router)
    issued = client.post(
        "/api/v1/demo/pairing", json={"journey_id": ids["journey"]}, headers=headers
    )
    assert issued.status_code == 201, issued.text
    response = client.post("/api/v1/demo/pairing/redeem", json={"ticket": issued.json()["ticket"]})
    assert response.status_code == 200, response.text
    paired = {"Authorization": "Bearer " + response.json()["access_token"]}
    native = post(url, {"seed": 17}, as_headers=paired)
    assert native.status_code == 201, native.text
    db = factory()
    s = next(db)
    request = Request(
        {"type": "http", "headers": [(b"authorization", paired["Authorization"].encode())]}
    )
    with pytest.raises(Exception) as exc:
        require_demo_presenter(request, s, journey_id=str(uuid4()))
    assert exc.value.status_code == 403
    db.close()
