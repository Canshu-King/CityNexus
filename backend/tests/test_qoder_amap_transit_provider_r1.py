"""The public-transport arm of the AMap client, pinned to what the live service actually answers.

Why this file exists: every hop in a saved candidate is measured by `AmapClient.walking` and nothing
else, so the one link a traveller does not walk -- the hop that closes one day and opens the next --
carries a walking minute for a trip nobody makes.  Before writing the method, the endpoint was asked
directly (trial/results/20261022_v3_human_chrome/amap-transit-capability-1.txt and
amap-transit-night-3.txt), and three of those readings are the rules below: a departure hour only
travels as a `date`+`time` pair, `nightflag` reads 0 even on a night line, and the city parameter wants
AMap's telephone code ("010"), not the six-digit adcode a place search hands back.

The fixtures are the shapes those files record, not invented ones.
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx

from app.integrations.china.amap_provider import AmapClient


def _client(payload, *, calls: list[httpx.Request] | None = None) -> AmapClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        return httpx.Response(200, json=payload)

    return AmapClient(api_key="test-amap-key", transport=httpx.MockTransport(handler))


def _night_payload() -> dict:
    """The answer the live service gave for 前门大街 -> 天坛公园 asked at 03:00 on 2026-12-04."""
    return {
        "status": "1",
        "infocode": "10000",
        "route": {
            "origin": "116.403895,39.896152",
            "destination": "116.410829,39.881913",
            "distance": "4210",
            "cost": {"taxi_fee": "13"},
            "transits": [
                {
                    "cost": {"duration": "3366", "transit_fee": "2.0"},
                    "distance": "4210",
                    "nightflag": "0",
                    "walking_distance": "900",
                    "segments": [
                        {"walking": {"distance": "900"}},
                        {"bus": {"buslines": [{"name": "夜7路(北京丰台站--平乐园北)"}]}},
                    ],
                }
            ],
        },
    }


ORIGIN = (39.896152, 116.403895)
DESTINATION = (39.881913, 116.410829)


def test_a_night_hour_reaches_the_wire_as_a_date_and_time_pair() -> None:
    calls: list[httpx.Request] = []
    client = _client(_night_payload(), calls=calls)
    try:
        result = client.transit(ORIGIN, DESTINATION, "010",
                                departure_date="2026-12-04", departure_time="03:00")
    finally:
        client.close()
    assert result["status"] == "ok"
    query = parse_qs(urlparse(str(calls[0].url)).query)
    assert query["date"] == ["2026-12-04"]
    assert query["time"] == ["03:00"]
    assert query["city1"] == ["010"] and query["city2"] == ["010"]
    assert query["origin"] == ["116.403895,39.896152"]
    assert calls[0].url.path == "/v5/direction/transit/integrated"


def test_departure_time_is_never_sent_because_it_measured_useless() -> None:
    """The live check: three spellings of `departure_time` returned the daytime answer unchanged."""
    calls: list[httpx.Request] = []
    client = _client(_night_payload(), calls=calls)
    try:
        client.transit(ORIGIN, DESTINATION, "010", departure_date="2026-12-04", departure_time="03:00")
        client.transit(ORIGIN, DESTINATION, "010")
    finally:
        client.close()
    assert len(calls) == 2
    for request in calls:
        query = parse_qs(urlparse(str(request.url)).query)
        assert "departure_time" not in query
    assert "date" not in parse_qs(urlparse(str(calls[1].url)).query)


def test_the_lines_the_provider_names_survive_to_the_product() -> None:
    client = _client(_night_payload())
    try:
        result = client.transit(ORIGIN, DESTINATION, "010",
                                departure_date="2026-12-04", departure_time="03:00")
    finally:
        client.close()
    route = result["route"]
    assert route["mode"] == "TRANSIT"
    assert route["lines"] == ["夜7路(北京丰台站--平乐园北)"]
    assert route["duration_seconds"] == 3366
    assert route["duration_min"] == 57
    assert route["distance_m"] == 4210
    assert route["walking_distance_m"] == 900
    assert route["fare_minor"] == 200
    assert route["requested_departure"] == {"date": "2026-12-04", "time": "03:00"}
    assert route["coordinate_system"] == "GCJ02"


def test_nightflag_is_carried_as_sent_and_never_turned_into_a_claim() -> None:
    """A night line came back with nightflag 0, so this method must not invent a night boolean."""
    client = _client(_night_payload())
    try:
        route = client.transit(ORIGIN, DESTINATION, "010",
                               departure_date="2026-12-04", departure_time="03:00")["route"]
    finally:
        client.close()
    assert route["nightflag"] == "0"
    assert route["lines"][0].startswith("夜")
    assert not {"night", "is_night", "night_service"} & set(route)


def test_a_half_specified_departure_is_refused_before_anything_is_sent() -> None:
    """Dropping one half of the pair would silently ask a daytime question; that is the real risk."""
    for kwargs in ({"departure_date": "2026-12-04"}, {"departure_time": "03:00"}):
        calls: list[httpx.Request] = []
        client = _client(_night_payload(), calls=calls)
        try:
            result = client.transit(ORIGIN, DESTINATION, "010", **kwargs)
        finally:
            client.close()
        assert result["reason_code"] == "AMAP_INVALID_DEPARTURE", kwargs
        assert result["route"] is None
        assert calls == []


def test_a_malformed_date_or_hour_is_refused_rather_than_looked_up() -> None:
    for kwargs in ({"departure_date": "2026-13-04", "departure_time": "03:00"},
                   {"departure_date": "2026-12-04", "departure_time": "24:00"},
                   {"departure_date": "2026-12-4", "departure_time": "3:00"}):
        calls: list[httpx.Request] = []
        client = _client(_night_payload(), calls=calls)
        try:
            result = client.transit(ORIGIN, DESTINATION, "010", **kwargs)
        finally:
            client.close()
        assert result["reason_code"] == "AMAP_INVALID_DEPARTURE", kwargs
        assert calls == []


def test_an_adcode_is_not_accepted_where_a_city_code_is_required() -> None:
    """Place rows carry a six-digit adcode; the transit endpoint wants the telephone code. Sending the
    wrong one is how a provider starts answering for a different city."""
    calls: list[httpx.Request] = []
    client = _client(_night_payload(), calls=calls)
    try:
        result = client.transit(ORIGIN, DESTINATION, "110101")
    finally:
        client.close()
    assert result["reason_code"] == "AMAP_INVALID_CITY_CODE"
    assert calls == []


def test_an_empty_transit_list_is_no_route_rather_than_a_zero_minute_hop() -> None:
    payload = {"status": "1", "route": {"cost": {}, "transits": []}}
    client = _client(payload)
    try:
        result = client.transit(ORIGIN, DESTINATION, "010")
    finally:
        client.close()
    assert result["status"] == "error"
    assert result["reason_code"] == "AMAP_NO_ROUTE"
    assert result["route"] is None
