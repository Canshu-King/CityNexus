from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlparse

import httpx

from app.integrations.china.amap_provider import AmapClient


def _client(payload, *, calls=None, status_code: int = 200, key: str = "test-amap-key") -> AmapClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        return httpx.Response(status_code, json=payload)

    return AmapClient(api_key=key, transport=httpx.MockTransport(handler))


def test_district_resolves_adcodes_without_guessing() -> None:
    calls: list[httpx.Request] = []
    payload = {
        "status": "1",
        "districts": [
            {
                "name": "福建省",
                "adcode": "350000",
                "level": "province",
                "districts": [
                    {
                        "name": "龙岩市",
                        "adcode": "350800",
                        "level": "city",
                        "districts": [
                            {"name": "连城县", "adcode": "350825", "level": "district", "districts": []}
                        ],
                    }
                ],
            }
        ],
    }
    client = _client(payload, calls=calls)
    try:
        result = client.district("连城县")
    finally:
        client.close()

    assert result["status"] == "ok"
    assert result["http_status"] == 200
    assert any(
        item["name"] == "连城县"
        and item["adcode"] == "350825"
        and item["level"] == "district"
        and item["parent"] == "龙岩市"
        and item["ancestors"] == ["福建省", "龙岩市"]
        for item in result["districts"]
    )
    assert len(calls) == 1
    assert urlparse(str(calls[0].url)).path == "/v3/config/district"


def test_search_uses_exact_adcode_and_keeps_provider_gcj02_coordinates() -> None:
    calls: list[httpx.Request] = []
    client = _client(
        {
            "status": "1",
            "pois": [
                {
                    "id": "B000A1",
                    "name": "连城公园",
                    "type": "风景名胜;公园广场",
                    "address": "连城县",
                    "pname": "福建省",
                    "cityname": "龙岩市",
                    "adname": "连城县",
                    "adcode": "350825",
                    "citycode": "0597",
                    "location": "116.756123,25.710456",
                }
            ],
        },
        calls=calls,
    )
    try:
        result = client.search("公园", "连城县", adcode="350825", limit=8)
    finally:
        client.close()

    assert result["status"] == "ok"
    assert result["places"][0] == {
        "external_id": "amap:B000A1",
        "provider_id": "B000A1",
        "provider_key": "amap-web-service",
        "name": "连城公园",
        "category": "风景名胜;公园广场",
        "address": "连城县",
        "province": "福建省",
        "city": "龙岩市",
        "district": "连城县",
        "adcode": "350825",
        "citycode": "0597",
        "requested_adcode": "350825",
        "region_status": "MATCH",
        "latitude": 25.710456,
        "longitude": 116.756123,
        "coordinate_system": "GCJ02",
        # This POI carries no business block, so the sentence stays None: an absent provider answer is
        # recorded as absent, never as an opening time.
        "opening_hours_text": None,
    }
    query = parse_qs(urlparse(str(calls[0].url)).query)
    assert query["region"] == ["350825"]
    assert query["city_limit"] == ["true"]
    assert query["page_size"] == ["8"]
    assert len(calls) == 1


def test_search_carries_the_provider_own_opening_hours_sentence() -> None:
    """``show_fields=business`` was already requested; the projection used to throw the answer away.

    The sentence below is the shape measured live from AMap on 2026-10-23 for 天坛公园 and 天坛公园售票处
    (trial/results/20261022_v3_human_chrome/amap-opentime-values-1.txt).  Carrying it verbatim is the
    whole point: the departure door reads an opening fact only if somebody brought the fact home.
    """
    calls: list[httpx.Request] = []
    client = _client(
        {
            "status": "1",
            "pois": [
                {
                    "id": "B000A81CB2", "name": "天坛公园", "type": "风景名胜", "address": "天坛里",
                    "pname": "北京市", "cityname": "北京市", "adname": "东城区", "adcode": "110101",
                    "citycode": "010", "location": "116.410829,39.881913",
                    "business": {"opentime_week": "周一至周日 06:30-22:00 最晚进入21:00", "keytag": "5A景区"},
                },
                {
                    "id": "B0FFI0TMCV", "name": "天坛公园售票处", "type": "售票处", "address": "天坛路",
                    "pname": "北京市", "cityname": "北京市", "adname": "东城区", "adcode": "110101",
                    "citycode": "010", "location": "116.410000,39.882000",
                    "business": {"opentime_today": "08:30-20:30"},
                },
            ],
        },
        calls=calls,
    )
    try:
        result = client.search("天坛", "北京市", adcode="110101", limit=8)
    finally:
        client.close()

    assert parse_qs(urlparse(str(calls[0].url)).query)["show_fields"] == ["business"]
    assert result["places"][0]["opening_hours_text"] == "周一至周日 06:30-22:00 最晚进入21:00"
    # A POI that only answers for today still counts as an answer, and nothing here invents a week.
    assert result["places"][1]["opening_hours_text"] == "08:30-20:30"


def test_search_marks_conflicts_and_unknowns_and_matches_parent_admin_level() -> None:
    client = _client(
        {
            "status": "1",
            "pois": [
                {
                    "id": "county-in-city",
                    "name": "龙岩城区地点",
                    "adcode": "350801",
                    "location": "117.000,25.000",
                },
                {
                    "id": "other-city",
                    "name": "泉州地点",
                    "adcode": "350500",
                    "location": "118.000,24.000",
                },
                {
                    "id": "missing-code",
                    "name": "地区未知地点",
                    "location": "117.100,25.100",
                },
            ],
        }
    )
    try:
        result = client.search("地点", "龙岩市", adcode="350800")
    finally:
        client.close()

    assert [place["region_status"] for place in result["places"]] == [
        "MATCH",
        "CONFLICT",
        "UNKNOWN",
    ]
    assert [place["external_id"] for place in result["places"]] == [
        "amap:county-in-city",
        "amap:other-city",
        "amap:missing-code",
    ]


def test_region_status_respects_province_and_city_adcode_levels() -> None:
    payload = {
        "status": "1",
        "pois": [
            {"id": "same-province", "name": "福建地点", "adcode": "350825", "location": "116.7,25.7"},
            {"id": "other-city-same-province", "name": "泉州地点", "adcode": "350500", "location": "118.0,24.8"},
            {"id": "other-province", "name": "江西地点", "adcode": "360100", "location": "115.8,28.7"},
        ],
    }
    client = _client(payload)
    try:
        province_result = client.search("地点", "福建省", adcode="350000")
        city_result = client.search("地点", "龙岩市", adcode="350800")
    finally:
        client.close()

    assert [place["region_status"] for place in province_result["places"]] == [
        "MATCH",
        "MATCH",
        "CONFLICT",
    ]
    assert [place["region_status"] for place in city_result["places"]] == [
        "MATCH",
        "CONFLICT",
        "CONFLICT",
    ]


def test_around_passes_native_gcj02_center_and_adcode() -> None:
    calls: list[httpx.Request] = []
    client = _client({"status": "1", "pois": []}, calls=calls)
    try:
        result = client.around(
            31.2304,
            121.4737,
            "咖啡馆",
            radius_m=1200,
            limit=5,
            adcode="310115",
        )
    finally:
        client.close()

    assert result["status"] == "ok"
    assert result["places"] == []
    query = parse_qs(urlparse(str(calls[0].url)).query)
    assert query["location"] == ["121.473700,31.230400"]
    assert query["region"] == ["310115"]
    assert query["radius"] == ["1200"]
    assert len(calls) == 1


def test_walking_returns_gcj02_path_and_cost_without_coordinate_conversion() -> None:
    calls: list[httpx.Request] = []
    client = _client(
        {
            "status": "1",
            "route": {
                "paths": [
                    {
                        "distance": "640",
                        "cost": {"duration": "510"},
                        "steps": [
                            {"polyline": "121.473700,31.230400;121.474000,31.230800"},
                            {"polyline": "121.474000,31.230800;121.475000,31.231000"},
                        ],
                    }
                ]
            },
        },
        calls=calls,
    )
    try:
        result = client.walking((31.2304, 121.4737), (31.231, 121.475), adcode="310115")
    finally:
        client.close()

    assert result["status"] == "ok"
    route = result["route"]
    assert route["distance_m"] == 640
    assert route["duration_seconds"] == 510
    assert route["coordinate_system"] == "GCJ02"
    assert route["path"]["coordinates"] == [
        [121.4737, 31.2304],
        [121.474, 31.2308],
        [121.475, 31.231],
    ]
    query = parse_qs(urlparse(str(calls[0].url)).query)
    assert query["origin"] == ["121.473700,31.230400"]
    assert query["destination"] == ["121.475000,31.231000"]
    assert query["show_fields"] == ["cost,polyline"]
    assert len(calls) == 1


def test_walking_accepts_legacy_top_level_duration() -> None:
    client = _client(
        {
            "status": "1",
            "route": {
                "paths": [
                    {
                        "distance": "40",
                        "duration": "75",
                        "steps": [{"polyline": "121.1,31.1;121.2,31.2"}],
                    }
                ]
            },
        }
    )
    try:
        result = client.walking((31.1, 121.1), (31.2, 121.2))
    finally:
        client.close()
    assert result["status"] == "ok"
    assert result["route"]["duration_seconds"] == 75


def test_missing_key_and_invalid_inputs_fail_before_network_call() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"status": "1", "pois": []})

    client = AmapClient(api_key="", transport=httpx.MockTransport(handler))
    try:
        missing_key = client.search("咖啡馆", "上海市", adcode="310000")
        invalid_adcode = client.search("咖啡馆", "上海市", adcode="31x")
        invalid_radius = client.around(31.2, 121.4, "咖啡馆", radius_m=10)
        invalid_query = client.district("x")
    finally:
        client.close()

    assert missing_key["reason_code"] == "AMAP_NOT_CONFIGURED"
    assert invalid_adcode["reason_code"] == "AMAP_INVALID_ADCODE"
    assert invalid_radius["reason_code"] == "AMAP_INVALID_RADIUS"
    assert invalid_query["reason_code"] == "AMAP_INVALID_QUERY"
    assert calls == []


def test_http_and_provider_errors_are_stable_redacted_and_never_retried(caplog) -> None:
    calls: list[httpx.Request] = []

    def failing_handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(502, text="raw gateway failure with test-amap-key")

    caplog.set_level(logging.INFO, logger="httpx")
    client = AmapClient(api_key="test-amap-key", transport=httpx.MockTransport(failing_handler))
    try:
        result = client.search("咖啡馆", "上海市")
    finally:
        client.close()
    assert result == {
        "status": "error",
        "reason_code": "AMAP_HTTP_ERROR",
        "http_status": 502,
        "places": [],
    }
    assert len(calls) == 1
    assert "test-amap-key" not in str(result)
    assert "test-amap-key" not in caplog.text

    provider_calls: list[httpx.Request] = []
    provider_client = _client(
        {"status": "0", "info": "raw provider detail contains test-amap-key", "infocode": "10001"},
        calls=provider_calls,
    )
    try:
        provider_result = provider_client.district("连城县")
    finally:
        provider_client.close()
    assert provider_result["reason_code"] == "AMAP_INVALID_KEY"
    assert "test-amap-key" not in str(provider_result)
    assert "raw provider detail" not in str(provider_result)
    assert len(provider_calls) == 1


def test_provider_infocodes_map_to_stable_key_quota_and_permission_codes() -> None:
    cases = {
        "10001": "AMAP_INVALID_KEY",
        "10003": "AMAP_QUOTA_EXCEEDED",
        "10012": "AMAP_SERVICE_PERMISSION_DENIED",
        # Asked too often at once, which is not today's allowance spent.  Measured: eight walking calls
        # fired back to back on one short city pair answered OK, OK, OK then three times infocode 10021
        # CUQPS_HAS_EXCEEDED_THE_LIMIT, and one call four seconds later answered OK again
        # (trial/results/20261022_v3_human_chrome/amap-burst-infocode-1.txt:2 against :3).
        "10021": "AMAP_RATE_LIMITED",
        "10004": "AMAP_RATE_LIMITED",
        # Measured, not guessed: walking 王府井步行街 -> 八达岭长城 answered this code while an 800 m
        # hop in the same city answered OK at the same minute
        # (trial/results/20261022_v3_human_chrome/amap-quota-vs-qps-1.txt:2 and :3).
        "20803": "AMAP_OUT_OF_PROVIDER_RANGE",
        "77777": "AMAP_PROVIDER_REJECTED",
    }
    for infocode, expected_code in cases.items():
        client = _client(
            {
                "status": "0",
                "info": "free-form provider detail must not escape",
                "infocode": infocode,
            }
        )
        try:
            result = client.district("连城县")
        finally:
            client.close()
        assert result["reason_code"] == expected_code
        assert "free-form provider detail" not in str(result)


def test_httpcore_protocol_child_logger_redacts_key_query(caplog) -> None:
    logger = logging.getLogger("httpcore.http11")
    caplog.set_level(logging.DEBUG, logger="httpcore.http11")
    logger.debug("request=%s", "https://restapi.amap.com/v5/place/text?key=private-test-value")

    assert "private-test-value" not in caplog.text
    assert "[redacted]" in caplog.text



def test_the_status_door_reads_the_key_the_agent_leg_reads(monkeypatch) -> None:
    """``/providers/v9`` must not call AMap unconfigured while the Agent is calling it configured.

    Measured on the stack booted for the 2026-10-23 departure walk: the status said
    ``NOT_CONFIGURED / AMAP_WEB_KEY is absent`` in the same process whose Agent research leg was routing
    real Beijing places, because config.py names the secret ``CITYNEXUS_AMAP_WEB_KEY`` and this module
    had been reading the bare ``AMAP_WEB_KEY``.
    """

    from types import SimpleNamespace

    from app.integrations.china import amap as amap_module

    monkeypatch.delenv("AMAP_WEB_KEY", raising=False)
    monkeypatch.setattr(amap_module, "settings", SimpleNamespace(amap_web_key="settings-name-key"))
    ready = amap_module.amap_status()
    assert ready.status == "READY" and ready.provenance == "LIVE" and ready.reason is None, ready

    monkeypatch.setattr(amap_module, "settings", SimpleNamespace(amap_web_key=None))
    monkeypatch.setenv("AMAP_WEB_KEY", "bare-name-key")
    assert amap_module.amap_status().status == "READY", "the older spelling must keep working"

    monkeypatch.delenv("AMAP_WEB_KEY", raising=False)
    absent = amap_module.amap_status()
    assert absent.status == "NOT_CONFIGURED" and absent.provenance == "UNAVAILABLE", absent
    assert absent.reason and "key" in absent.reason.lower()
    # A refusal never carries the secret, whichever name supplied it.
    assert "settings-name-key" not in str(absent) and "bare-name-key" not in str(absent)
