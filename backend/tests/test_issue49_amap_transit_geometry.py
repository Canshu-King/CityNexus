from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx

from app.integrations.china.amap_provider import AmapClient


ORIGIN = (39.896152, 116.403895)
DESTINATION = (39.881913, 116.410829)


def _client(payload: dict, *, calls: list[httpx.Request] | None = None) -> AmapClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        return httpx.Response(200, json=payload)

    return AmapClient(api_key="test-amap-key", transport=httpx.MockTransport(handler))


def _payload(segments: list[dict]) -> dict:
    return {
        "status": "1",
        "infocode": "10000",
        "route": {
            "transits": [
                {
                    "distance": "1200",
                    "cost": {"duration": "1800", "transit_fee": "2.0"},
                    "walking_distance": "100",
                    "segments": segments,
                }
            ]
        },
    }


def test_transit_keeps_connected_provider_walking_and_bus_polylines() -> None:
    payload = _payload(
        [
            {
                "walking": {
                    "distance": "100",
                    "steps": [
                        {
                            "distance": "100",
                            "polyline": "116.403895,39.896152;116.404000,39.897000",
                        }
                    ],
                }
            },
            {
                "bus": {
                    "buslines": [
                        {
                            "name": "公交示例线",
                            "distance": "1100",
                            "polyline": "116.404000,39.897000;116.410829,39.881913",
                        }
                    ]
                }
            },
        ]
    )
    calls: list[httpx.Request] = []
    client = _client(payload, calls=calls)
    try:
        route = client.transit(ORIGIN, DESTINATION, "010")["route"]
    finally:
        client.close()

    query = parse_qs(urlparse(str(calls[0].url)).query)
    assert query["show_fields"] == ["cost,polyline"]
    assert route["geometry_status"] == "AVAILABLE"
    assert route["path"] == {
        "type": "LineString",
        "coordinates": [
            [116.403895, 39.896152],
            [116.404, 39.897],
            [116.410829, 39.881913],
        ],
        "coordinate_system": "GCJ02",
    }
    assert [item["mode"] for item in route["geometry_segments"]] == ["WALK", "TRANSIT"]
    assert route["geometry_segments"][0]["source_field"] == "segments[0].walking.steps[0].polyline"
    assert route["geometry_segments"][1]["source_field"] == "segments[1].bus.buslines[0].polyline"
    assert route["geometry_provenance"]["source_coordinate_system"] == "GCJ02"
    assert route["geometry_provenance"]["conversion"] is None


def test_transit_without_polyline_keeps_time_but_marks_geometry_unavailable() -> None:
    payload = _payload(
        [
            {"walking": {"distance": "100"}},
            {"bus": {"buslines": [{"name": "线路名", "distance": "1100"}]}},
        ]
    )
    client = _client(payload)
    try:
        result = client.transit(ORIGIN, DESTINATION, "010")
    finally:
        client.close()

    route = result["route"]
    assert result["status"] == "ok"
    assert route["duration_seconds"] == 1800
    assert route["path"] is None
    assert route["geometry_segments"] == []
    assert route["geometry_status"] == "BLOCKED_GEOMETRY_UNAVAILABLE"


def test_disconnected_provider_polylines_are_preserved_without_a_connector() -> None:
    payload = _payload(
        [
            {"walking": {"distance": "100", "steps": [{"distance": "100", "polyline": "116.4,39.9;116.41,39.91"}]}},
            {"bus": {"buslines": [{"name": "线路名", "polyline": "116.42,39.92;116.43,39.93"}]}},
        ]
    )
    client = _client(payload)
    try:
        route = client.transit(ORIGIN, DESTINATION, "010")["route"]
    finally:
        client.close()

    assert route["path"] is None
    assert route["geometry_status"] == "BLOCKED_GEOMETRY_DISCONNECTED"
    assert len(route["geometry_segments"]) == 2


def test_v5_nested_polylines_and_alternative_buslines_are_not_concatenated():
    payload = _payload([
        {"walking": {"distance": "100", "steps": [{
            "distance": "100", "polyline": {"polyline": "116.4,39.9;116.41,39.91"},
        }]}},
        {"bus": {"buslines": [
            {"name": "First offered bus", "polyline": {"polyline": "116.41,39.91;116.42,39.92"}},
            {"name": "Alternative bus", "polyline": {"polyline": "116.41,39.91;116.42,39.92"}},
        ]}},
    ])
    with _client(payload) as client:
        route = client.transit(ORIGIN, DESTINATION, "010")["route"]
    assert route["geometry_status"] == "AVAILABLE"
    assert len(route["geometry_segments"]) == 2
    assert route["geometry_segments"][0]["source_field"].endswith(".polyline.polyline")
    assert route["line_alternatives"][0]["alternative_count"] == 2
    assert route["lines"] == ["First offered bus"]
    assert route["path"]["coordinates"] == [[116.4,39.9],[116.41,39.91],[116.42,39.92]]


def test_v5_walking_polyline_wrapper_reaches_geometry():
    payload = {"status":"1", "infocode":"10000", "route":{"paths":[{
        "distance":"100", "cost":{"duration":"180"}, "steps":[{
            "distance":"100", "polyline":{"polyline":"116.4,39.9;116.41,39.91"},
        }],
    }]}}
    with _client(payload) as client:
        result = client.walking(ORIGIN, DESTINATION)
    assert result["status"] == "ok"
    assert result["route"]["geometry_status"] == "AVAILABLE"
    assert result["route"]["path"]["coordinates"] == [[116.4,39.9],[116.41,39.91]]


def test_submetre_provider_junction_preserves_every_sample_but_not_a_missing_leg():
    parts = [
        {"coordinates":[[116.4,39.9],[116.41,39.91]]},
        {"coordinates":[[116.410004,39.91],[116.42,39.92]]},
    ]
    coordinates, status = AmapClient._join_polyline_segments(parts)
    assert status == "AVAILABLE"
    assert coordinates == parts[0]["coordinates"] + parts[1]["coordinates"]
    provenance = AmapClient._junction_provenance(parts)
    assert 0 < provenance["max_junction_gap_m"] < 1
    assert provenance["inserted_coordinate_count"] == 0
    parts[1]["coordinates"][0] = [116.4104,39.91]
    assert AmapClient._join_polyline_segments(parts) == (None,"BLOCKED_GEOMETRY_DISCONNECTED")
