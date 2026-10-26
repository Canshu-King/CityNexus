from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from app.agent import goal_amap
from app.agent.goal_mobility import StoredAmapRoutes, route_geometry_wgs84
from app.agent.goal_route_freeze import _orient_reused_route
from app.integrations.china.amap import gcj02_to_wgs84
from app.integrations.mobility.snapshot_capture import capture_mobility_snapshot
from test_goal_tasks import goal_scope


class _RouteClient:
    path = {
        "type": "LineString",
        "coordinates": [[116.403895, 39.896152], [116.410829, 39.881913]],
        "coordinate_system": "GCJ02",
    }

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def district(self, query):
        return {
            "status": "ok",
            "http_status": 200,
            "districts": [{"name": "连城县", "adcode": "350825", "level": "district"}],
        }

    def search(self, query, **kwargs):
        return {
            "status": "ok",
            "http_status": 200,
            "places": [
                {"external_id": "amap:B00001", "name": "冠豸山", "latitude": 25.7, "longitude": 116.7, "adcode": "350825"},
                {"external_id": "amap:B00002", "name": "石门湖", "latitude": 25.71, "longitude": 116.71, "adcode": "350825"},
            ],
        }

    def walking(self, origin, destination):
        return {
            "status": "ok",
            "http_status": 200,
            "route": {
                "provider_key": "amap-web-service",
                "mode": "WALK",
                "distance_m": 900,
                "duration_seconds": 700,
                "coordinate_system": "GCJ02",
                "path": self.path,
            },
        }


def test_goal_route_research_keeps_provider_path_and_converted_provenance(goal_scope, monkeypatch) -> None:
    session, journey, _member = goal_scope
    monkeypatch.setattr(goal_amap, "settings", replace(goal_amap.settings, amap_web_key="TEST_FIXTURE"))
    monkeypatch.setattr(goal_amap, "_client", _RouteClient)
    monkeypatch.setattr("app.agent.goal_artifacts.public_city_label", lambda *args: "连城县")
    task: dict = {}

    goal_amap.discover_amap_goal_places(session, journey, task, query="景点")
    result = goal_amap.route_public_places(
        session,
        journey,
        task,
        from_place_id="amap:B00001",
        to_place_id="amap:B00002",
    )

    stored = task["research_routes"][0]
    feature = stored["route_geometry"]
    expected = [
        [gcj02_to_wgs84(39.896152, 116.403895)[1], gcj02_to_wgs84(39.896152, 116.403895)[0]],
        [gcj02_to_wgs84(39.881913, 116.410829)[1], gcj02_to_wgs84(39.881913, 116.410829)[0]],
    ]
    assert result["status"] == "ROUTE_READY"
    assert stored["path"] == _RouteClient.path
    assert stored["geometry_status"] == "AVAILABLE"
    assert feature["geometry"]["coordinates"] == expected
    assert feature["properties"]["source_crs"] == "GCJ02"
    assert feature["properties"]["domain_crs"] == "WGS84"
    assert feature["properties"]["conversion"] == "ITERATIVE_GCJ02_TO_WGS84"
    assert feature["properties"]["provider_call_id"] == stored["id"]
    assert feature["properties"]["measurement_captured_at"] == stored["captured_at"]


def test_stored_route_estimate_supplies_wgs84_geometry_and_reverses_without_new_measurement() -> None:
    route = {
        "id": "provider-call-123",
        "from_place_id": "place-a",
        "to_place_id": "place-b",
        "captured_at": "2026-10-26T01:02:03+00:00",
        "coordinate_system": "GCJ02",
        "duration_seconds": 900,
        "distance_m": 1200,
        "mode": "TRANSIT",
        "geometry_status": "AVAILABLE",
        "path": _RouteClient.path,
        "geometry_provenance": {"source_fields": ["segments[0].bus.buslines[0].polyline"]},
    }
    provider = StoredAmapRoutes([("place-a", "place-b", route)])

    forward = provider.estimate("place-a", "place-b")
    reverse = provider.estimate("place-b", "place-a")

    assert forward.duration_min == reverse.duration_min == 15
    assert forward.geometry["geometry"]["coordinates"] == list(reversed(reverse.geometry["geometry"]["coordinates"]))
    assert reverse.geometry["properties"]["lookup_direction"] == "REVERSED_STORED_MEASUREMENT"
    assert reverse.raw["measurement_id"] == "provider-call-123"
    assert reverse.raw["measurement_captured_at"] == route["captured_at"]
    assert reverse.raw["lookup_reused_in_reverse"] is True

    capture = capture_mobility_snapshot(
        [("place-a", "place-b")],
        primary=provider,
        operation_key="issue49-route-geometry-fixture",
        captured_at="2026-10-26T01:02:03+00:00",
    )
    fact = capture.snapshot.facts[("place-a", "place-b")]
    assert fact.route_geometry == tuple(tuple(point) for point in forward.geometry["geometry"]["coordinates"])
    assert fact.geometry_provider == "amap-web-service"


def test_route_freeze_reverses_reused_task_geometry_but_keeps_original_receipt() -> None:
    route = {
        "id": "provider-call-reverse",
        "from_place_id": "place-a",
        "to_place_id": "place-b",
        "captured_at": "2026-10-26T01:02:03+00:00",
        "coordinate_system": "GCJ02",
        "duration_seconds": 900,
        "mode": "TRANSIT",
        "geometry_status": "AVAILABLE",
        "path": _RouteClient.path,
        "geometry_segments": [
            {"source_field": "segments[0].bus.buslines[0].polyline", "coordinates": _RouteClient.path["coordinates"]}
        ],
        "geometry_provenance": {"source_fields": ["segments[0].bus.buslines[0].polyline"]},
    }
    route["route_geometry"] = route_geometry_wgs84(route)

    oriented = _orient_reused_route(
        route,
        "place-b",
        "place-a",
        SimpleNamespace(name="石门湖"),
        SimpleNamespace(name="冠豸山"),
    )
    provider = StoredAmapRoutes([("canonical-b", "canonical-a", oriented)])
    estimate = provider.estimate("canonical-b", "canonical-a")

    assert oriented["path"]["coordinates"] == list(reversed(route["path"]["coordinates"]))
    assert oriented["route_geometry"]["geometry"]["coordinates"] == list(
        reversed(route["route_geometry"]["geometry"]["coordinates"])
    )
    assert oriented["geometry_provenance"]["lookup_direction"] == "REVERSED_STORED_MEASUREMENT"
    assert oriented["id"] == route["id"]
    assert oriented["captured_at"] == route["captured_at"]
    assert estimate.geometry["geometry"]["coordinates"] == oriented["route_geometry"]["geometry"]["coordinates"]
    assert estimate.raw["lookup_reused_in_reverse"] is True
    assert estimate.raw["measurement_from_place_id"] == "place-a"
    assert estimate.raw["measurement_to_place_id"] == "place-b"


def test_stored_route_without_geometry_remains_an_explicit_snapshot_gap() -> None:
    route = {"id": "provider-call-empty", "duration_seconds": 300, "coordinate_system": "GCJ02"}
    provider = StoredAmapRoutes([("place-a", "place-b", route)])

    estimate = provider.estimate("place-a", "place-b")
    capture = capture_mobility_snapshot(
        [("place-a", "place-b")],
        primary=provider,
        operation_key="issue49-route-geometry-gap-fixture",
        captured_at="2026-10-26T01:02:03+00:00",
    )
    fact = capture.snapshot.facts[("place-a", "place-b")]

    assert estimate.geometry is None
    assert estimate.raw["geometry_status"] == "BLOCKED_GEOMETRY_UNAVAILABLE"
    assert fact.route_geometry == ()
    assert fact.geometry_provider is None
