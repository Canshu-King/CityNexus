"""The unified place-lead surface: one shape whichever provider answers, and a fallback that is named.

Nothing here reaches the network. Each "provider" is a stub with the same call signature the real
modules have (`search(query, *, city, limit)`), and the Amap-shaped rows are hand-written in the frame
the real answer arrives in. So no test in this file is evidence that a provider was contacted.

What is pinned, in the order the ruling asks it:

  * every lead carries `source, provider_item_id, region, adcode, coordinate_system, captured_at,
    verified_fields, unknown_fields`, and a GCJ-02 answer is re-expressed with the frame named;
  * one source that has a POI is enough for the traveller's DRAFT (`counts_as_draft_supply`), and an
    UNKNOWN ticket price / opening hour / transport cost never blocks it;
  * a source that answered zero or refused is a step, not an answer: the chain moves on and says so;
  * a leg that was never asked is recorded as SKIPPED, so "photon was fine" cannot be read from a run
    where nobody spoke to photon;
  * a named row with a name but no coordinate is kept with `position` unknown, never dropped and never
    given an invented point.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.integrations.capability import place_leads


class StubSource:
    def __init__(self, provider_key: str, *, rows: Any = None, error: Exception | None = None,
                 coordinate_system: str = "WGS84") -> None:
        self.provider_key = provider_key
        self.coordinate_system = coordinate_system
        self._rows = list(rows or [])
        self._error = error
        self.calls: list[dict[str, Any]] = []

    async def search(self, query: str, *, city: str, limit: int) -> list[Any]:
        self.calls.append({"query": query, "city": city, "limit": limit})
        if self._error is not None:
            raise self._error
        return list(self._rows)


AMAP_ROWS = [
    {
        "external_id": "B000A83M61",
        "name": "冠豸山",
        "latitude": 25.7093,
        "longitude": 116.7569,
        "source_crs": "GCJ02",
        "domain_crs": "WGS84",
        "conversion": "ITERATIVE_GCJ02_TO_WGS84",
        "provider_key": "amap-web-service",
        "adcode": "350825",
    }
]
PHOTON_ROWS = [
    {
        "external_id": "way:4412883",
        "name": "Tempel van de Hemel",
        "latitude": 39.8822,
        "longitude": 116.4066,
        "city": "Beijing",
        "country": "China",
        "provider_key": "photon",
    }
]


@pytest.mark.asyncio
async def test_amap_lead_carries_the_ruling_fields_and_names_its_frame():
    amap = StubSource("amap-web-service", rows=AMAP_ROWS)
    result = await place_leads.collect_place_leads("冠豸山", region="CN-35-08", sources=[amap])

    assert amap.calls == [{"query": "冠豸山", "city": "CN-35-08", "limit": 8}]
    lead = result.leads[0]
    payload = lead.as_payload()
    for field in (
        "source",
        "provider_item_id",
        "region",
        "adcode",
        "coordinate_system",
        "captured_at",
        "verified_fields",
        "unknown_fields",
    ):
        assert field in payload, field
    assert lead.source == "amap-web-service"
    assert lead.adcode == "350825"
    assert lead.coordinate_system == "WGS84"
    assert lead.native_coordinate_system == "GCJ02"
    assert lead.conversion == "ITERATIVE_GCJ02_TO_WGS84"
    assert "position" in lead.verified_fields and "adcode" in lead.verified_fields
    assert result.counts_as_draft_supply is True


@pytest.mark.asyncio
async def test_a_source_that_answered_zero_is_a_step_and_the_next_one_is_asked():
    amap = StubSource("amap-web-service", rows=[])
    photon = StubSource("photon", rows=PHOTON_ROWS)
    result = await place_leads.collect_place_leads("天坛", region="CN-11-01", sources=[amap, photon])

    assert amap.calls and photon.calls
    outcomes = [row["outcome"] for row in result.provider_readings]
    assert outcomes == ["ANSWERED_EMPTY", "ANSWERED"]
    assert [lead.source for lead in result.leads] == ["photon"]
    assert result.counts_as_draft_supply is True


@pytest.mark.asyncio
async def test_a_refused_source_is_named_and_the_chain_continues():
    amap = StubSource("amap-web-service", error=httpx.ConnectError("no route to host"))
    photon = StubSource("photon", rows=PHOTON_ROWS)
    result = await place_leads.collect_place_leads("天坛", region="CN-11-01", sources=[amap, photon])

    first = result.provider_readings[0]
    assert first["attempted"] is True and first["answered"] is False
    assert first["outcome"] == "NOT_ANSWERED_ConnectError"
    assert len(result.leads) == 1
    assert result.counts_as_draft_supply is True


@pytest.mark.asyncio
async def test_a_leg_never_asked_is_recorded_as_skipped_not_as_fine():
    amap = StubSource("amap-web-service", rows=AMAP_ROWS)
    photon = StubSource("photon", rows=PHOTON_ROWS)
    result = await place_leads.collect_place_leads("冠豸山", region="CN-35-08", sources=[amap, photon])

    assert photon.calls == []
    assert result.provider_readings[1]["outcome"] == "SKIPPED"
    assert result.provider_readings[1]["attempted"] is False
    assert result.provider_readings[1]["reason_code"] == "ANOTHER_SOURCE_ALREADY_ANSWERED"


@pytest.mark.asyncio
async def test_asking_every_source_is_a_different_answer_and_is_labelled():
    amap = StubSource("amap-web-service", rows=AMAP_ROWS)
    photon = StubSource("photon", rows=PHOTON_ROWS)
    result = await place_leads.collect_place_leads(
        "冠豸山", region="CN-35-08", sources=[amap, photon], stop_on_first_answer=False
    )

    assert amap.calls and photon.calls
    assert [lead.source for lead in result.leads] == ["amap-web-service", "photon"]
    assert all(row["outcome"] != "SKIPPED" for row in result.provider_readings)


@pytest.mark.asyncio
async def test_unknown_details_never_block_the_draft_but_are_listed():
    amap = StubSource("amap-web-service", rows=AMAP_ROWS)
    result = await place_leads.collect_place_leads("冠豸山", region="CN-35-08", sources=[amap])

    assert result.unknown_fields == ("opening_hours", "ticket_price", "transport_cost")
    assert result.counts_as_draft_supply is True


@pytest.mark.asyncio
async def test_a_named_place_without_a_coordinate_is_kept_not_invented():
    row = dict(AMAP_ROWS[0], latitude=None, longitude=None)
    amap = StubSource("amap-web-service", rows=[row])
    result = await place_leads.collect_place_leads("冠豸山", region="CN-35-08", sources=[amap])

    lead = result.leads[0]
    assert lead.latitude is None and lead.longitude is None
    assert "position" in lead.unknown_fields and "position" not in lead.verified_fields
    assert result.counts_as_draft_supply is False


@pytest.mark.asyncio
async def test_a_row_with_no_identity_at_all_is_not_a_lead():
    amap = StubSource("amap-web-service", rows=[{"name": None, "external_id": None}])
    result = await place_leads.collect_place_leads("x", region="CN-11-01", sources=[amap])

    assert result.leads == ()
    assert result.provider_readings[0]["outcome"] == "ANSWERED_EMPTY"
    assert result.counts_as_draft_supply is False


@pytest.mark.asyncio
async def test_the_recorder_sees_one_event_per_source_that_was_asked():
    events: list[dict[str, Any]] = []
    amap = StubSource("amap-web-service", rows=AMAP_ROWS)
    photon = StubSource("photon", rows=PHOTON_ROWS)
    await place_leads.collect_place_leads(
        "冠豸山", region="CN-35-08", sources=[amap, photon], on_provider_call=events.append
    )

    assert [event["source"] for event in events] == ["amap-web-service"]
    assert events[0]["outcome"] == "ANSWERED"
    assert events[0]["region"] == "CN-35-08"


def test_the_chain_only_offers_amap_inside_china_with_a_key(monkeypatch):
    from app.integrations.china import amap

    monkeypatch.delenv(amap.KEY_ENV_PREFERRED, raising=False)
    monkeypatch.delenv(amap.KEY_ENV_LEGACY, raising=False)
    fake_amap = StubSource("amap-web-service")
    fake_photon = StubSource("photon")

    assert [s.provider_key for s in place_leads.default_sources(
        amap=fake_amap, photon=fake_photon, city_code="CN-11-01")] == ["photon"]

    monkeypatch.setenv(amap.KEY_ENV_PREFERRED, "unit-test-placeholder")
    assert [s.provider_key for s in place_leads.default_sources(
        amap=fake_amap, photon=fake_photon, city_code="CN-11-01")] == ["amap-web-service", "photon"]
    assert [s.provider_key for s in place_leads.default_sources(
        amap=fake_amap, photon=fake_photon, city_code="NL-12")] == ["photon"]


@pytest.mark.asyncio
async def test_the_real_amap_provider_feeds_the_surface_with_adcode_and_a_named_frame(monkeypatch):
    """AmapPoiProvider -> collect_place_leads, over one MockTransport: no socket, no invented field."""
    import json

    from app.integrations.china import amap as amap_module

    secret = "unit-test-amap-placeholder-key"
    monkeypatch.setenv(amap_module.KEY_ENV_PREFERRED, secret)
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "status": "1",
                "info": "OK",
                "count": "1",
                "pois": [
                    {
                        "id": "B000A83M61",
                        "name": "冠豸山",
                        "location": "116.7569,25.7093",
                        "adcode": "350825",
                        "cityname": "龙岩市",
                    }
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sources = place_leads.build_sources(city_code="CN-35-08", client=client)
    try:
        result = await place_leads.collect_place_leads("冠豸山", region="龙岩市", sources=sources)
    finally:
        await client.aclose()

    assert [source.provider_key for source in sources] == ["amap-web-service", "photon"]
    assert [lead.source for lead in result.leads] == ["amap-web-service"]
    lead = result.leads[0]
    assert lead.provider_item_id == "B000A83M61"
    assert lead.adcode == "350825" and lead.region == "龙岩市"
    assert lead.coordinate_system == "WGS84" and lead.native_coordinate_system == "GCJ02"
    assert lead.has_position() and abs(lead.longitude - 116.7569) > 0.0002
    assert "adcode" in lead.verified_fields and "region" in lead.verified_fields
    assert result.counts_as_draft_supply is True
    # the region filter and the administrative code are what separate two places with one name
    assert "citylimit=true" in seen["url"] and httpx.URL(seen["url"]).params["region"] == "龙岩市"
    assert secret in seen["url"]
    blob = json.dumps(result.as_payload(), default=str)
    assert secret not in blob and "key=" not in blob


def test_build_sources_hands_amap_only_to_a_chinese_region_with_a_key(monkeypatch):
    from app.integrations.china import amap as amap_module

    monkeypatch.delenv(amap_module.KEY_ENV_PREFERRED, raising=False)
    monkeypatch.delenv(amap_module.KEY_ENV_LEGACY, raising=False)
    # Nothing is called here: the selection is decided before a request exists, so the geocoder only
    # needs the object it is handed, not a live client.
    client = object()

    assert [s.provider_key for s in place_leads.build_sources(
        city_code="CN-11-01", client=client)] == ["photon"]
    monkeypatch.setenv(amap_module.KEY_ENV_LEGACY, "unit-test-legacy-value")
    assert [s.provider_key for s in place_leads.build_sources(
        city_code="CN-11-01", client=client)] == ["amap-web-service", "photon"]
    assert [s.provider_key for s in place_leads.build_sources(
        city_code="JP-13", client=client)] == ["photon"]


def test_the_surface_shape_is_the_shape_the_ruling_named():
    payload = place_leads.PlaceLead(
        source="photon",
        provider_item_id="way:1",
        name="x",
        latitude=1.0,
        longitude=2.0,
        region="CN-11-01",
        adcode=None,
        coordinate_system="WGS84",
        native_coordinate_system=None,
        conversion=None,
        captured_at="2026-10-19T07:00:00+00:00",
        verified_fields=("name",),
        unknown_fields=("ticket_price",),
    ).as_payload()
    assert payload["adcode"] is None
    assert payload["verified_fields"] == ["name"]
    assert set(payload) == {
        "source",
        "provider_item_id",
        "name",
        "latitude",
        "longitude",
        "region",
        "adcode",
        "coordinate_system",
        "native_coordinate_system",
        "conversion",
        "captured_at",
        "verified_fields",
        "unknown_fields",
    }


@pytest.mark.asyncio
async def test_the_geocoder_leg_flows_through_its_real_dataclass_shape(monkeypatch):
    """Photon answers with `GeocodedPlace` objects, not dicts -- that shape must still become a lead."""
    from app.integrations.china import amap as amap_module
    from app.integrations.discovery.photon import GeocodedPlace

    monkeypatch.delenv(amap_module.KEY_ENV_PREFERRED, raising=False)
    monkeypatch.delenv(amap_module.KEY_ENV_LEGACY, raising=False)
    calls: list[tuple[str, int]] = []

    class FakeGeocoder:
        provider_key = "photon"

        async def search(self, query, *, limit=8, lang=None):
            calls.append((query, limit))
            return [
                GeocodedPlace(
                    external_id="city:123",
                    name="龙岩",
                    latitude=25.09,
                    longitude=116.92,
                    country="中国",
                    city="龙岩市",
                    raw={},
                )
            ]

    sources = place_leads.build_sources(city_code="CN-35-08", client=object(), photon=FakeGeocoder())
    result = await place_leads.collect_place_leads("龙岩", region="CN-35-08", sources=sources)

    assert [source.provider_key for source in sources] == ["photon"]
    assert calls == [("龙岩", 8)]
    lead = result.leads[0]
    assert lead.provider_item_id == "city:123" and lead.name == "龙岩"
    assert lead.region == "龙岩市"
    assert lead.coordinate_system == "WGS84" and lead.native_coordinate_system is None
    assert "adcode" not in lead.verified_fields
    assert result.counts_as_draft_supply is True
