import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from test_issue47_simulation import sim  # noqa: F401
from test_issue47_private_reads import stack  # noqa: F401
from app.db.models import (
    Journey,
    JourneyMember,
    JourneyMission,
    Place,
    PlanVersion,
    ProviderCall,
    RealPlaceCandidate,
)
from app.replanning.provider_snapshots import LIVE_PROVIDER_CAPTURE, MobilitySnapshot, TravelEstimateFact
from app.simulation.city_catalog import SimulationCityIdentity, SimulationPublicCitySnapshot


INTERNAL_CITY_CODE = "CN-RV-3507014DDE2C"
CITY_ADCODE = "110000"


def _add_journey(
    session, *, journey_id, owner_id, city_code, stamp, role="OWNER", reader_id=None
):
    session.add(
        Journey(
            id=journey_id,
            traveler_id=owner_id,
            title="Issue 49 route fixture",
            city_code=city_code,
            timezone="Asia/Shanghai",
            start_at=stamp,
            end_at=stamp,
            budget_currency="CNY",
            budget_amount_minor=0,
            planning_mode="BALANCED",
            status="DRAFT",
            created_at=stamp,
            updated_at=stamp,
        )
    )
    session.add(
        JourneyMember(
            id=str(uuid4()),
            journey_id=journey_id,
            traveler_id=owner_id,
            role="OWNER",
            invited_by=owner_id,
            joined_at=stamp,
            created_at=stamp,
            updated_at=stamp,
        )
    )
    if reader_id and reader_id != owner_id:
        session.add(
            JourneyMember(
                id=str(uuid4()),
                journey_id=journey_id,
                traveler_id=reader_id,
                role=role,
                invited_by=owner_id,
                joined_at=stamp,
                created_at=stamp,
                updated_at=stamp,
            )
        )


def _add_region_binding_task(factory, journey_id, owner_id, city_code):
    stamp = datetime.now(timezone.utc).isoformat()
    task_id = str(uuid4())
    region = {
        "adcode": CITY_ADCODE,
        "name": "北京市",
        "level": "province",
        "query": "北京市",
        "status": "RESOLVED",
    }
    response_json = json.dumps({"status": "RESULTS", "districts": [region]}, ensure_ascii=False)
    db = factory()
    session = next(db)
    journey = session.get(Journey, journey_id)
    journey.city_code = city_code
    session.add(
        JourneyMission(
            id=task_id,
            journey_id=journey_id,
            traveler_id=owner_id,
            user_text="Issue 49 source-bound city fixture",
            requested_autonomy="PLAN_ONLY",
            status="COMPLETED",
            created_at=stamp,
            intent_json=json.dumps(
                {"mode": "GOAL_PLANNING", "goal_task": {"schema_version": 1, "amap_region": region}},
                ensure_ascii=False,
            ),
            max_cost_delta_minor=0,
            max_loss_minor=0,
            max_schedule_drift_min=0,
        )
    )
    session.add(
        ProviderCall(
            id=str(uuid4()),
            provider_key="amap-web-service",
            operation="goal_amap_district",
            request_json=json.dumps({"region": "北京市"}, ensure_ascii=False),
            response_json=response_json,
            status="SUCCESS",
            created_at=stamp,
        )
    )
    session.commit()
    db.close()
    return task_id


def _add_live_public_places(session, *, journey_id, city_code, stamp, prefix):
    poi_ids = []
    provider_rows = []
    for index in range(5):
        place_id = f"{prefix}-poi-{index}"
        external_id = f"amap:{prefix.upper()}-{index}"
        provider_rows.append(
            {"provider_object_id": external_id.removeprefix("amap:"), "adcode": "110101"}
        )
        session.add(
            Place(
                id=place_id,
                provider_key="amap",
                external_id=external_id,
                city_code=city_code,
                name=f"Public place {index}",
                category="PARK",
                latitude=39.90 + index * 0.001,
                longitude=116.39 + index * 0.001,
                coordinate_system="WGS84",
                source_coordinate_system="GCJ02",
                opening_hours_json="{}",
                tags_json="[]",
                metadata_json="{}",
                updated_at=stamp,
            )
        )
        session.add(
            RealPlaceCandidate(
                id=f"{prefix}-lead-{index}",
                journey_id=journey_id,
                provider_key="amap",
                external_id=external_id,
                city_code=city_code,
                name=f"Public place {index}",
                category="PARK",
                latitude=39.90 + index * 0.001,
                longitude=116.39 + index * 0.001,
                tags_json="[]",
                opening_hours_json="{}",
                metadata_json='{"discovery_mode":"live"}',
                captured_at=stamp,
                evidence_json="{}",
                materialized_place_id=place_id,
                status="MATERIALIZED",
            )
        )
        poi_ids.append(place_id)
    session.add(
        ProviderCall(
            id=str(uuid4()),
            provider_key="amap-web-service",
            operation="goal_amap_search",
            request_json="{}",
            response_json=json.dumps({"places": provider_rows}),
            status="SUCCESS",
            created_at=stamp,
        )
    )
    return poi_ids


def _add_route_plan(session, *, journey_id, version_no, pairs, stamp, source="GOAL_TASK"):
    facts = {}
    points_by_pair = {}
    for index, pair in enumerate(pairs):
        points = (
            (116.39 + index * 0.001, 39.90 + index * 0.001),
            (116.40 + index * 0.001, 39.91 + index * 0.001),
        )
        points_by_pair[pair] = [list(point) for point in points]
        facts[pair] = TravelEstimateFact(
            origin_key=pair[0],
            destination_key=pair[1],
            minutes=12 + index,
            provider_key="amap-web-service",
            captured_at=stamp,
            route_geometry=points,
            geometry_provider="amap-web-service",
            route_provenance=LIVE_PROVIDER_CAPTURE,
            fact_quality=LIVE_PROVIDER_CAPTURE,
        )
    snapshot = MobilitySnapshot(
        facts=facts,
        source_provider_key="amap-web-service",
        captured_at=stamp,
        snapshot_id=str(uuid4()),
    )
    plan_id = str(uuid4())
    session.add(
        PlanVersion(
            id=plan_id,
            journey_id=journey_id,
            version_no=version_no,
            planning_mode="BALANCED",
            status="DRAFT",
            source=source,
            total_cost_minor=0,
            currency="CNY",
            estimated_duration_min=60,
            mobility_snapshot_id=snapshot.snapshot_id,
            mobility_evidence_json=json.dumps(snapshot.to_evidence(), sort_keys=True),
            created_at=stamp,
        )
    )
    return plan_id, points_by_pair


def _public_poi(place_id):
    return {
        "place_id": place_id,
        "name": place_id,
        "provider": "amap",
        "external_id": f"amap:{place_id}",
        "latitude": 39.90,
        "longitude": 116.39,
        "coordinate_system": "WGS84",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None,
        "provenance": "CAPTURED_PROVIDER_SNAPSHOT",
    }


def _public_route(origin, destination, *, captured_at=None):
    return {
        "origin_place_id": origin,
        "destination_place_id": destination,
        "minutes": 12,
        "provider": "amap-web-service",
        "captured_at": captured_at or datetime.now(timezone.utc).isoformat(),
        "fact_quality": LIVE_PROVIDER_CAPTURE,
        "route_geometry": [[116.39, 39.90], [116.40, 39.91]],
        "geometry_crs": "WGS84",
        "geometry_provider": "amap-web-service",
        "route_provenance": LIVE_PROVIDER_CAPTURE,
        "snapshot_sha256": "a" * 64,
        "provenance": "CAPTURED_PROVIDER_SNAPSHOT",
    }


def _insert_public_snapshot(factory, owner_id, code, payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    db = factory()
    session = next(db)
    session.add(
        SimulationPublicCitySnapshot(
            provider_adcode=code,
            snapshot_json=raw,
            snapshot_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            published_at=datetime.now(timezone.utc).isoformat(),
            published_by=owner_id,
        )
    )
    session.commit()
    db.close()


def _add_conflicting_verified_identity(session, *, journey_id, stamp):
    code = "350100"
    name = "福州市"
    region = {"adcode": code, "name": name, "level": "city"}
    response_json = json.dumps({"status": "RESULTS", "districts": [region]}, ensure_ascii=False)
    call_id = str(uuid4())
    session.add(
        ProviderCall(
            id=call_id,
            provider_key="amap-web-service",
            operation="goal_amap_district",
            request_json=json.dumps({"region": name}, ensure_ascii=False),
            response_json=response_json,
            status="SUCCESS",
            created_at=stamp,
        )
    )
    session.add(
        SimulationCityIdentity(
            journey_id=journey_id,
            provider="amap",
            provider_adcode=code,
            public_name=name,
            source_call_id=call_id,
            source_sha256=hashlib.sha256(response_json.encode()).hexdigest(),
            bound_at=stamp,
        )
    )


def test_publish_merges_owner_same_city_draft_routes_and_reloads_geometry(sim):
    client, ids, _, factory, headers, url, post = sim
    task_id = _add_region_binding_task(factory, ids["journey"], ids["owner"], INTERNAL_CITY_CODE)
    identity_url = url.replace("/runs", "/city-identity")
    bound = post(identity_url, {"source_task_id": task_id})
    assert bound.status_code == 200, bound.text
    assert bound.json()["provider_city_adcode"] == CITY_ADCODE

    db = factory()
    session = next(db)
    stamp = datetime.now(timezone.utc).isoformat()
    # Sort after the bound old Journey so the regression exercises the prior None-overwrite order.
    new_journey_id = f"zz-{uuid4()}"
    _add_journey(
        session,
        journey_id=new_journey_id,
        owner_id=ids["owner"],
        city_code=INTERNAL_CITY_CODE,
        stamp=stamp,
    )
    companion_journey_id = str(uuid4())
    _add_journey(
        session,
        journey_id=companion_journey_id,
        owner_id=ids["stranger"],
        city_code=INTERNAL_CITY_CODE,
        role="COLLABORATOR",
        reader_id=ids["owner"],
        stamp=stamp,
    )
    other_city_journey_id = str(uuid4())
    _add_journey(
        session,
        journey_id=other_city_journey_id,
        owner_id=ids["owner"],
        city_code="CN-RV-OTHER-CITY",
        stamp=stamp,
    )
    poi_ids = _add_live_public_places(
        session,
        journey_id=ids["journey"],
        city_code=INTERNAL_CITY_CODE,
        stamp=stamp,
        prefix="issue49-owned",
    )
    owned_pairs = [(poi_ids[0], poi_ids[1]), (poi_ids[1], poi_ids[2]), (poi_ids[2], poi_ids[3])]
    companion_pairs = [(poi_ids[0], poi_ids[3]), (poi_ids[1], poi_ids[4]), (poi_ids[0], poi_ids[4])]
    other_city_pairs = [(poi_ids[0], poi_ids[2]), (poi_ids[1], poi_ids[3]), (poi_ids[2], poi_ids[4])]
    own_plan_id, expected_geometry = _add_route_plan(
        session,
        journey_id=new_journey_id,
        version_no=1,
        pairs=owned_pairs,
        stamp=stamp,
    )
    companion_plan_id, _ = _add_route_plan(
        session,
        journey_id=companion_journey_id,
        version_no=1,
        pairs=companion_pairs,
        stamp=stamp,
    )
    other_city_plan_id, _ = _add_route_plan(
        session,
        journey_id=other_city_journey_id,
        version_no=1,
        pairs=other_city_pairs,
        stamp=stamp,
    )
    target_identity = session.get(SimulationCityIdentity, ids["journey"])
    session.add(
        SimulationCityIdentity(
            journey_id=companion_journey_id,
            provider=target_identity.provider,
            provider_adcode=target_identity.provider_adcode,
            public_name=target_identity.public_name,
            source_call_id=target_identity.source_call_id,
            source_sha256=target_identity.source_sha256,
            bound_at=target_identity.bound_at,
        )
    )
    assert session.get(SimulationCityIdentity, new_journey_id) is None
    assert session.query(RealPlaceCandidate).filter_by(journey_id=new_journey_id).count() == 0
    session.commit()
    db.close()

    publish_url = url.replace("/runs", "/cities/publish")
    published = post(publish_url, {"publish_public_facts": True})
    assert published.status_code == 200, published.text
    db = factory()
    session = next(db)
    row = session.get(SimulationPublicCitySnapshot, CITY_ADCODE)
    public = json.loads(row.snapshot_json)
    assert len(public["poi"]) == 5
    assert len(public["routes"]) == 3
    by_pair = {
        (route["origin_place_id"], route["destination_place_id"]): route
        for route in public["routes"]
    }
    assert set(by_pair) == set(owned_pairs)
    for pair in owned_pairs:
        route = by_pair[pair]
        assert route["route_geometry"] == expected_geometry[pair]
        assert route["geometry_crs"] == "WGS84"
        assert route["geometry_provider"] == "amap-web-service"
        assert route["route_provenance"] == LIVE_PROVIDER_CAPTURE
        assert route["fact_quality"] == LIVE_PROVIDER_CAPTURE
        assert "source_call_id" not in route and "provider_call_id" not in route
    for private_id in (
        ids["journey"],
        new_journey_id,
        companion_journey_id,
        other_city_journey_id,
        own_plan_id,
        companion_plan_id,
        other_city_plan_id,
        task_id,
    ):
        assert private_id not in row.snapshot_json
    assert session.get(Journey, ids["journey"]).status == "ACTIVE"
    session.close()
    db.close()

    reloaded = client.get(url.replace("/runs", "/cities") + "?seed=17", headers=headers)
    assert reloaded.status_code == 200, reloaded.text
    catalog_city = next(
        item
        for item in reloaded.json()["cities"]
        if item.get("catalog") == "EXPLICITLY_PUBLISHED_PUBLIC"
        and item.get("provider_city_adcode") == CITY_ADCODE
    )
    assert catalog_city["status"] == "ELIGIBLE_CAPTURED_SNAPSHOT"
    assert len(catalog_city["routes"]) == 3
    assert all(route["route_geometry"] for route in catalog_city["routes"])


def test_publish_rejects_conflicting_valid_city_bindings_for_same_owner_city(sim):
    _, ids, _, factory, _, url, post = sim
    task_id = _add_region_binding_task(factory, ids["journey"], ids["owner"], INTERNAL_CITY_CODE)
    bound = post(
        url.replace("/runs", "/city-identity"),
        {"source_task_id": task_id},
    )
    assert bound.status_code == 200, bound.text

    db = factory()
    session = next(db)
    stamp = datetime.now(timezone.utc).isoformat()
    conflicting_journey_id = str(uuid4())
    _add_journey(
        session,
        journey_id=conflicting_journey_id,
        owner_id=ids["owner"],
        city_code=INTERNAL_CITY_CODE,
        stamp=stamp,
    )
    _add_conflicting_verified_identity(
        session,
        journey_id=conflicting_journey_id,
        stamp=stamp,
    )
    session.commit()
    session.close()
    db.close()

    response = post(url.replace("/runs", "/cities/publish"), {"publish_public_facts": True})
    assert response.status_code == 409, response.text
    assert "CITY_IDENTITY_BINDING_CONFLICT" in response.json()["detail"]["missing"]


def test_legacy_public_snapshot_without_geometry_is_not_eligible_on_reload(sim):
    client, ids, _, factory, headers, url, _ = sim
    code = "350100"
    poi_ids = [f"legacy-{index}" for index in range(5)]
    payload = {
        "provider_city_adcode": code,
        "public_name": "Legacy geometry-less snapshot",
        "provenance": "CAPTURED_PROVIDER_SNAPSHOT",
        "poi": [_public_poi(place_id) for place_id in poi_ids],
        "routes": [
            {
                "origin_place_id": poi_ids[index],
                "destination_place_id": poi_ids[index + 1],
                "minutes": 12,
                "provider": "amap-web-service",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "snapshot_sha256": "b" * 64,
                "provenance": "CAPTURED_PROVIDER_SNAPSHOT",
            }
            for index in range(3)
        ],
    }
    _insert_public_snapshot(factory, ids["owner"], code, payload)

    response = client.get(url.replace("/runs", "/cities") + "?seed=17", headers=headers)
    assert response.status_code == 200, response.text
    city = next(
        item
        for item in response.json()["cities"]
        if item.get("catalog") == "EXPLICITLY_PUBLISHED_PUBLIC"
        and item.get("provider_city_adcode") == code
    )
    assert city["status"] == "BLOCKED"
    assert "AT_LEAST_3_CAPTURED_ROUTES_REQUIRED" in city["missing"]
    assert city["routes"] == []


@pytest.mark.parametrize(
    "code,mutation",
    [
        ("330000", "crs"),
        ("340000", "points"),
        ("350000", "source_crs"),
        ("360000", "source_provider"),
    ],
)
def test_public_snapshot_with_malformed_route_geometry_or_source_is_blocked(sim, code, mutation):
    client, ids, _, factory, headers, url, _ = sim
    poi_ids = [f"malformed-{code}-{index}" for index in range(5)]
    routes = [
        _public_route(poi_ids[index], poi_ids[index + 1])
        for index in range(3)
    ]
    if mutation == "crs":
        routes[0]["geometry_crs"] = "GCJ-02"
    elif mutation == "points":
        routes[0]["route_geometry"] = [[116.39, 39.90], [181, 39.91]]
    elif mutation == "source_crs":
        routes[0]["source_crs"] = "UNKNOWN"
    else:
        routes[0]["provider"] = "UNKNOWN"
        routes[0]["geometry_provider"] = "UNKNOWN"
        routes[0]["route_provenance"] = "UNKNOWN"
    payload = {
        "provider_city_adcode": code,
        "public_name": f"Malformed {mutation}",
        "provenance": "CAPTURED_PROVIDER_SNAPSHOT",
        "poi": [_public_poi(place_id) for place_id in poi_ids],
        "routes": routes,
    }
    _insert_public_snapshot(factory, ids["owner"], code, payload)

    response = client.get(url.replace("/runs", "/cities") + "?seed=17", headers=headers)
    assert response.status_code == 200, response.text
    city = next(
        item
        for item in response.json()["cities"]
        if item.get("catalog") == "EXPLICITLY_PUBLISHED_PUBLIC"
        and item.get("provider_city_adcode") == code
    )
    assert city["status"] == "BLOCKED"
    assert "AT_LEAST_3_CAPTURED_ROUTES_REQUIRED" in city["missing"]
    assert len(city["routes"]) == 2
