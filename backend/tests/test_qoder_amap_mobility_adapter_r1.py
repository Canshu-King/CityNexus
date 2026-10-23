"""The Amap routing adapter that feeds the runtime mobility capture.

What these tests pin, in the order a reader would ask about it:

  1. one Amap direction answer is read exactly once (`normalize_direction_payload`), and the geometry
     leaves in WGS84 `[[lon, lat], ...]` -- the order the capture's own geometry reader wants;
  2. the capture accepts the adapter as a primary and freezes a leg with live provenance;
  3. a leg the provider cannot answer raises, and the message cannot carry the key;
  4. the region / env / seam rule that decides whether a Chinese journey is routed here at all;
  5. a configured Valhalla keeps its leg -- this adapter answers for the country, it does not take
     over a deployment that already has a router.

Every transport here is `httpx.MockTransport`: no request leaves the process, so nothing in this file
is evidence that a real Amap answer arrived.  The key is a fabricated 32-hex placeholder.
"""

from __future__ import annotations

import json
import logging
import math
import types

import httpx
import pytest

from app.integrations.china import amap
from app.integrations.mobility import amap_http, runtime
from app.integrations.mobility.amap_http import AmapHTTPMobilityProvider, AmapRouteError
from app.integrations.mobility.snapshot_capture import capture_mobility_snapshot
from app.replanning.provider_snapshots import LIVE_PROVIDER_CAPTURE

PLACEHOLDER_KEY = "0123456789abcdef0123456789abcdef"
BEIJING_STATION = (39.9042, 116.4074)
TEMPLE_OF_HEAVEN = (39.9164, 116.4038)
PLACES = {"from": BEIJING_STATION, "to": TEMPLE_OF_HEAVEN}


class _StopCapture(Exception):
    """Stops the runtime capture the moment it has been handed a provider."""


def _lookup(key: str):
    latitude, longitude = PLACES[key]
    return {"latitude": latitude, "longitude": longitude}


def _driving_payload():
    return {
        "status": "1",
        "info": "OK",
        "infocode": "10000",
        "route": {
            "paths": [
                {
                    "distance": "8120",
                    "cost": {"duration": "1560", "taxi_fee": "23.5"},
                    "steps": [
                        {"polyline": "116.4074,39.9042;116.4060,39.9060"},
                        {"polyline": "116.4045,39.9120;116.4038,39.9164"},
                    ],
                }
            ]
        },
    }


def _provider(handler, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return AmapHTTPMobilityProvider(
        client=client,
        place_lookup=_lookup,
        city_code="CN-11-01",
        api_key=kwargs.pop("api_key", PLACEHOLDER_KEY),
        **kwargs,
    )


def test_one_reader_of_the_direction_answer():
    """The adapter and the async provider share the parse instead of each owning one."""
    assert amap_http.normalize_direction_payload is amap.normalize_direction_payload


def test_direction_answer_is_read_into_domain_units():
    route = amap.normalize_direction_payload(_driving_payload(), "AUTO")
    assert route.duration_min == 26  # ceil(1560 s / 60)
    assert route.distance_m == 8120
    assert route.cost_amount_minor == 2350
    assert route.currency == "CNY"
    assert route.cost_status == "ESTIMATED"
    assert route.source_crs == "GCJ02" and route.domain_crs == "WGS84"


def test_geometry_leaves_in_wgs84_lon_lat_order():
    route = amap.normalize_direction_payload(_driving_payload(), "AUTO")
    points = route.geometry["geometry"]["coordinates"]
    assert len(points) == 4
    # Sent as GCJ-02, so the answer must arrive shifted, not merely reordered.
    first_lon, first_lat = points[0]
    assert abs(first_lon - BEIJING_STATION[1]) > 0.0002
    assert math.isclose(first_lon, 116.4074, abs_tol=0.01)
    assert math.isclose(first_lat, 39.9042, abs_tol=0.01)
    assert -180 <= first_lon <= 180 and -90 <= first_lat <= 90


def test_capture_accepts_the_adapter_as_primary_and_freezes_a_live_leg():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["origin"] = request.url.params["origin"]
        return httpx.Response(200, json=_driving_payload())

    result = capture_mobility_snapshot(
        [("from", "to")],
        primary=_provider(handler, mode="AUTO"),
        operation_key="reform:amap-leg",
    )
    fact = result.snapshot.facts[("from", "to")]
    assert fact.minutes == 26
    assert fact.provider_key == "amap-web-service"
    assert fact.fact_quality == LIVE_PROVIDER_CAPTURE
    assert fact.route_provenance == "LIVE_PROVIDER_CAPTURE"
    assert fact.mode == "AUTO"
    # The distance IS on the estimate this adapter returned, but the capture's own fact construction
    # carries no `distance_m=` (app/integrations/mobility/snapshot_capture.py:188), so no live
    # provider's distance reaches a frozen fact today.  Asserting 8120 here would be asserting a hole
    # closed by code that does not exist; the named gap goes into the receipt instead.
    assert fact.distance_m is None
    assert len(fact.route_geometry) == 4
    assert fact.geometry_provider == "amap-web-service"
    assert result.snapshot.degraded is False
    assert seen["path"] == "/v5/direction/driving"
    # The leg is asked for in the frame the provider speaks.
    origin_lon, origin_lat = (float(part) for part in seen["origin"].split(","))
    assert math.isclose(origin_lon, 116.4074, abs_tol=0.01)
    assert math.isclose(origin_lat, 39.9042, abs_tol=0.01)
    assert abs(origin_lon - BEIJING_STATION[1]) > 0.0002
    assert abs(origin_lat - BEIJING_STATION[0]) > 0.0002


def test_the_key_never_leaves_the_request():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_driving_payload())

    estimate = _provider(handler).estimate("from", "to")
    blob = json.dumps(
        [estimate.duration_min, estimate.distance_m, estimate.cost_status, estimate.raw],
        default=str,
    )
    assert PLACEHOLDER_KEY not in blob
    assert "key=" not in blob


def test_a_refused_answer_becomes_a_named_failure_without_the_key():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "0", "info": "INVALID_USER_KEY"})

    with pytest.raises(AmapRouteError) as caught:
        _provider(handler).estimate_minutes("from", "to")
    message = str(caught.value)
    assert "INVALID_USER_KEY" in message
    assert PLACEHOLDER_KEY not in message


def test_a_transport_failure_is_a_failed_leg_not_a_zero_minute_trip():
    def handler(request: httpx.Request):
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(AmapRouteError) as caught:
        _provider(handler).estimate_minutes("from", "to")
    assert "ConnectError" in str(caught.value)
    assert "key=" not in str(caught.value)


def test_a_missing_key_refuses_before_anything_is_asked(monkeypatch):
    monkeypatch.delenv(amap.KEY_ENV_PREFERRED, raising=False)
    monkeypatch.delenv(amap.KEY_ENV_LEGACY, raising=False)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json=_driving_payload())

    provider = AmapHTTPMobilityProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        place_lookup=_lookup,
        city_code="CN-11-01",
    )
    with pytest.raises(AmapRouteError) as caught:
        provider.estimate_minutes("from", "to")
    assert calls == []
    assert amap.KEY_ENV_PREFERRED in str(caught.value)


def test_only_a_chinese_city_with_a_key_and_the_seam_on_routes_here(monkeypatch):
    monkeypatch.delenv(amap.KEY_ENV_PREFERRED, raising=False)
    monkeypatch.delenv(amap.KEY_ENV_LEGACY, raising=False)
    monkeypatch.delenv(amap.ROUTING_SEAM_ENV, raising=False)
    assert amap.routes_via_amap("CN-11-01") is False  # no key: the answer this tree gave before
    monkeypatch.setenv(amap.KEY_ENV_PREFERRED, PLACEHOLDER_KEY)
    assert amap.routes_via_amap("CN-11-01") is True
    assert amap.routes_via_amap("US-36") is False  # not this provider's region
    monkeypatch.delenv(amap.KEY_ENV_PREFERRED)
    monkeypatch.setenv(amap.KEY_ENV_LEGACY, PLACEHOLDER_KEY)
    assert amap.routes_via_amap("CN-11-01") is True  # either name is enough
    monkeypatch.setenv(amap.ROUTING_SEAM_ENV, "off")
    assert amap.routes_via_amap("CN-11-01") is False


def _selection_probe(monkeypatch, *, city_code, key, seam, valhalla_url, hard=False):
    seen = {}

    def fake_capture(pairs, **kwargs):
        seen["primary_key"] = kwargs["primary"].provider_key
        seen["fallback_key"] = getattr(kwargs.get("fallback"), "provider_key", None)
        raise _StopCapture

    monkeypatch.setattr(runtime, "capture_mobility_snapshot", fake_capture)
    monkeypatch.setattr(
        runtime, "settings", types.SimpleNamespace(live_valhalla_url=valhalla_url)
    )
    for name in (amap.KEY_ENV_PREFERRED, amap.KEY_ENV_LEGACY, amap.ROUTING_SEAM_ENV):
        monkeypatch.delenv(name, raising=False)
    if key:
        monkeypatch.setenv(amap.KEY_ENV_PREFERRED, PLACEHOLDER_KEY)
    if seam:
        monkeypatch.setenv(amap.ROUTING_SEAM_ENV, seam)
    if valhalla_url:
        monkeypatch.setattr(
            runtime,
            "ValhallaHTTPMobilityProvider",
            lambda **kwargs: types.SimpleNamespace(
                provider_key="valhalla-http",
                status_capabilities=lambda: {"status": "OK"},
            ),
        )
    try:
        runtime.capture_runtime_mobility_snapshot(
            None,
            types.SimpleNamespace(city_code=city_code),
            [("from", "to")],
            operation_key="reform:selection",
            require_explicit_facts=hard,
        )
    except _StopCapture:
        pass
    return seen


def test_a_cn_journey_with_a_key_chooses_the_amap_primary(monkeypatch):
    seen = _selection_probe(
        monkeypatch, city_code="CN-11-01", key=True, seam=None, valhalla_url=""
    )
    assert seen["primary_key"] == "amap-web-service"
    # A soft capture still gets the pair-level mock fallback, and the capture's own tail is what
    # later strips that fallback of hard-eligibility -- same rule Valhalla is under.
    assert seen["fallback_key"] == "mock-mobility"


def test_a_hard_cn_capture_gets_no_mock_fallback(monkeypatch):
    seen = _selection_probe(
        monkeypatch, city_code="CN-11-01", key=True, seam=None, valhalla_url="", hard=True
    )
    assert seen["primary_key"] == "amap-web-service"
    assert seen["fallback_key"] is None


def test_a_cn_journey_with_no_valhalla_at_all_never_builds_that_adapter(monkeypatch):
    """`None`, not `""`: that is what `settings.live_valhalla_url` actually holds in a deployment
    that never configured Valhalla -- and the probe above passed `""`, which the adapter tolerated.
    Constructing the Valhalla adapter before swapping in Amap used to die on `None.rstrip("/")` in
    its own constructor, so the Amap route was unreachable precisely in the shape this machine is in.
    """
    seen = _selection_probe(
        monkeypatch, city_code="CN-11-01", key=True, seam=None, valhalla_url=None
    )
    assert seen["primary_key"] == "amap-web-service", seen


def test_a_none_valhalla_url_leaves_a_non_chinese_city_on_the_previous_provider(monkeypatch):
    """The other half of the same value: with no Valhalla and no Amap routing, nothing is built --
    the offline answer is the mock's, and the missing URL is not an error the traveller sees."""
    seen = _selection_probe(
        monkeypatch, city_code="FR-11", key=True, seam=None, valhalla_url=None
    )
    assert seen["primary_key"] == "mock-mobility", seen


def test_a_city_that_is_not_chinese_keeps_the_previous_provider(monkeypatch):
    seen = _selection_probe(
        monkeypatch, city_code="FR-11", key=True, seam=None, valhalla_url=""
    )
    assert seen["primary_key"] != "amap-web-service"
    assert seen["primary_key"] == "mock-mobility"


def test_a_configured_valhalla_is_not_displaced_by_the_amap_key(monkeypatch):
    seen = _selection_probe(
        monkeypatch,
        city_code="CN-11-01",
        key=True,
        seam=None,
        valhalla_url="http://valhalla.test",
    )
    assert seen["primary_key"] == "valhalla-http"


def test_the_seam_switch_returns_the_city_to_the_previous_provider(monkeypatch):
    seen = _selection_probe(
        monkeypatch, city_code="CN-11-01", key=True, seam="off", valhalla_url=""
    )
    assert seen["primary_key"] == "mock-mobility"


def _runtime_capture(monkeypatch, handler, *, hard: bool):
    """Drive the runtime capture itself with a client whose transport refuses.

    Only `httpx.Client`'s transport is swapped: the provider, the selection rule, the snapshot
    capture and the hard/soft tails are the product's own code paths.
    """

    def failing(request: httpx.Request):
        raise httpx.ConnectError("no route to host", request=request)

    real_client = httpx.Client

    def factory(**kwargs):
        return real_client(transport=httpx.MockTransport(handler or failing), timeout=10.0)

    monkeypatch.setattr(httpx, "Client", factory)
    monkeypatch.setattr(
        runtime,
        "_place_lookup",
        lambda session, key: {"latitude": PLACES[key][0], "longitude": PLACES[key][1]},
    )
    monkeypatch.setattr(
        runtime, "settings", types.SimpleNamespace(live_valhalla_url="")
    )
    monkeypatch.delenv(amap.KEY_ENV_LEGACY, raising=False)
    monkeypatch.delenv(amap.ROUTING_SEAM_ENV, raising=False)
    monkeypatch.setenv(amap.KEY_ENV_PREFERRED, PLACEHOLDER_KEY)
    journey = types.SimpleNamespace(city_code="CN-11-01")
    return runtime.capture_runtime_mobility_snapshot(
        None,
        journey,
        [("from", "to")],
        operation_key="reform:amap-fallback",
        require_explicit_facts=hard,
    )


def test_a_refused_amap_leg_degrades_softly_and_loses_hard_eligibility(monkeypatch):
    """Ruling 2026-10-19 item 3: a raw provider failure must not be pushed at the traveller.

    The soft capture still gets a number -- but only a number that is no longer hard-eligible, which
    is what stops "the provider did not answer" from becoming "the leg is feasible in 12 minutes".
    """
    result = _runtime_capture(monkeypatch, None, hard=False)
    pair = ("from", "to")
    fact = result.snapshot.facts[pair]

    assert result.degraded is True
    assert result.fallback_pairs == (pair,)
    assert result.failed_primary_pairs == (pair,)
    assert fact.provider_key == "mock-mobility"
    assert fact.fallback_reason == "AmapRouteError"
    # V5 blocker-1, applied by the runtime's own tail: a fact that came from the fixture *because a
    # live provider refused* carries no quality declaration, so the hard gate fails closed on it.
    assert fact.fact_quality is None


def test_a_refused_amap_leg_in_a_hard_capture_names_the_leg_and_invents_nothing(monkeypatch):
    from app.integrations.mobility.snapshot_capture import MobilitySnapshotCaptureError

    with pytest.raises(MobilitySnapshotCaptureError) as caught:
        _runtime_capture(monkeypatch, None, hard=True)
    message = str(caught.value)
    assert "from|to" in message
    assert "AmapRouteError" in message
    assert PLACEHOLDER_KEY not in message


def test_a_library_log_line_that_carries_the_key_is_masked_before_it_is_emitted(caplog):
    """The secret rides in a query string, and the library underneath prints that string.

    `sanitize_url` only covers messages this module writes.  The exposure that actually worries the
    standing rule "no Amap key in a log line" is `httpx`'s own INFO line for every request it makes -
    code this module does not write and cannot rewrite.  This door drives that logger for real and
    reads back what a handler would have received.
    """

    amap.install_log_redaction()
    noisy = logging.getLogger("httpx")
    previous_level, previous_propagate = noisy.level, noisy.propagate
    noisy.setLevel(logging.INFO)
    noisy.propagate = True
    try:
        noisy.info("HTTP Request: GET https://restapi.amap.com/v5/direction/walking?key=%s "
                   "\"HTTP/1.1 200 OK\"", PLACEHOLDER_KEY)
    finally:
        noisy.setLevel(previous_level)
        noisy.propagate = previous_propagate
    emitted = " | ".join(record.getMessage() for record in caplog.records)
    assert "key=***" in emitted, emitted
    assert PLACEHOLDER_KEY not in emitted, "the key reached the emitted line"


def test_the_redaction_is_installed_once_per_logger_whatever_the_caller_does():
    """Two writers adding a filter to the same logger would double-mask, and a third would grow the
    chain on every request; the promise is one filter per name, however often installation is asked."""

    name = "cmdr-0704-redaction-probe"
    try:
        amap.install_log_redaction(name)
        amap.install_log_redaction(name)
        amap.install_log_redaction(name)
        filters = logging.getLogger(name).filters
        assert sum(1 for item in filters if isinstance(item, amap.KeyRedactionFilter)) == 1, filters
    finally:
        logger = logging.getLogger(name)
        logger.filters = [item for item in logger.filters
                          if not isinstance(item, amap.KeyRedactionFilter)]
        amap.FILTERED_LOGGERS.discard(name)


def test_the_async_provider_and_the_sync_adapter_share_the_request_leg(monkeypatch):
    """One rule for "how an Amap request fails", for both shapes of client.

    Before this, the async provider called `client.get` directly: the message that reached a log line
    was httpx's own, and httpx prints the URL the key travels in.  Both legs now go through the same
    reader, so a failure that reaches a log line or a traveller has passed the same mask.
    """

    import asyncio

    monkeypatch.setenv(amap.KEY_ENV_PREFERRED, PLACEHOLDER_KEY)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(500, json={"info": "boom"})
    )
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: real_async_client(transport=transport)
    )
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(
            amap.AmapMobilityProvider().route(
                "AUTO",
                origin_wgs84=BEIJING_STATION,
                destination_wgs84=TEMPLE_OF_HEAVEN,
                city_code="CN-11-01",
            )
        )
    message = str(caught.value)
    assert "http_status=500" in message, message
    assert PLACEHOLDER_KEY not in message, message


# ---------------------------------------------------------------------------
# ORD-0705 甲: a leg Amap already answered is not re-asked, and it keeps the instant it was answered
# at.  Measured on the demo journey (132 identical pairs asked in three generations, 38-39 answered
# each time, 81 answered across them, no pair ever giving two different durations): the re-ask is
# pure cost and the refusals that follow are the rate limit, not the road.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _every_door_starts_cold():
    """Empty the process leg memory around every test in this file.

    These doors count requests, so a leg remembered by the previous test would silently turn a "we
    asked once" assertion into "we never asked at all" -- and a refusal door would go green because
    the answer came from memory instead of from the transport that was built to refuse.
    """

    amap_http.reset_process_leg_memory()
    yield
    amap_http.reset_process_leg_memory()


def _counting_provider(counter, **kwargs):
    """A provider whose transport records every request that actually reached it."""

    def handler(request):
        counter["n"] += 1
        if counter.get("refuse"):
            raise httpx.ConnectError("no route to host", request=request)
        return httpx.Response(200, json=_driving_payload())

    counter.setdefault("n", 0)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return AmapHTTPMobilityProvider(
        client=client,
        place_lookup=_lookup,
        city_code=kwargs.pop("city_code", "CN-11-01"),
        api_key=kwargs.pop("api_key", PLACEHOLDER_KEY),
        **kwargs,
    )


def test_a_leg_answered_once_is_not_asked_again_by_the_next_generation():
    counter = {}
    first = _counting_provider(counter)
    assert first.estimate("from", "to").duration_min == 26
    assert counter["n"] == 1, counter

    second = _counting_provider(counter)
    estimate = second.estimate("from", "to")

    assert counter["n"] == 1, "the second generation asked Amap again: %s" % counter
    assert estimate.duration_min == 26, "a remembered leg must read exactly like a fresh one"
    assert second.legs_from_memory == 1
    assert second.requests_sent == 0


def test_a_remembered_leg_carries_its_own_measurement_instant(monkeypatch):
    """The one door that decides whether reuse is honest or a forgery.

    `time_basis` says AMAP_ROUTE_CAPTURED_AT.  A leg measured at 04:57 that is stamped 05:05 because
    that is when the *snapshot* was taken claims a measurement that did not happen.  So the fact keeps
    04:57 while the snapshot keeps 05:05, and the only thing that got cheaper is the request.
    """

    measured_at = "2026-10-22T04:57:00+00:00"
    monkeypatch.setattr(amap_http, "_utc_iso_now", lambda: measured_at)
    counter = {}

    def capture(stamp):
        return _memory_capture(monkeypatch, counter, captured_at=stamp)

    first = capture("2026-10-22T04:57:00+00:00")
    second = capture("2026-10-22T05:05:00+00:00")
    pair = ("from", "to")

    assert counter["n"] == 1, counter
    assert second.snapshot.captured_at == "2026-10-22T05:05:00+00:00"
    assert first.snapshot.facts[pair].captured_at == measured_at
    assert second.snapshot.facts[pair].captured_at == measured_at
    assert second.snapshot.facts[pair].captured_at != second.snapshot.captured_at
    caps = second.snapshot.provider_capabilities["amap-web-service"]
    assert caps["legs_from_memory"] == 1, caps
    assert caps["requests_sent"] == 0, caps


def test_a_leg_the_provider_refused_is_never_remembered():
    """A refusal is not an answer, and must not be able to become one by sitting in memory."""

    counter = {"refuse": True}
    refused = _counting_provider(counter)
    with pytest.raises(AmapRouteError):
        refused.estimate("from", "to")
    assert len(amap_http.process_leg_memory()) == 0
    assert counter["n"] == 1, counter

    counter["refuse"] = False
    asked_again = _counting_provider(counter)
    assert asked_again.estimate("from", "to").duration_min == 26
    assert counter["n"] == 2, "a refused leg has to be asked again, not served from memory"


def test_the_memory_asks_again_once_the_leg_has_gone_stale():
    """The memory is minutes old, not forever: past the ttl the provider asks Amap again."""

    counter = {}
    clock = {"t": 0.0}
    memory = amap_http.AmapLegMemory(ttl_s=600.0, clock=lambda: clock["t"])
    first = _counting_provider(counter, leg_memory=memory)
    first.estimate("from", "to")

    key = ("WALK", "CN-11-01", "from", "to")
    memory.touch(key, 601.0)
    second = _counting_provider(counter, leg_memory=memory)
    second.estimate("from", "to")

    assert counter["n"] == 2, counter
    assert second.legs_from_memory == 0


def test_a_remembered_leg_is_still_declared_live():
    """Reuse must not quietly downgrade a measurement to an estimate.

    The capture reads the attestation off the provider that answered, so a leg served from memory has
    to reach the same quality as the leg that was measured.  If this ever goes the other way, hard
    feasibility would start refusing legs it already accepted.
    """

    counter = {}
    _counting_provider(counter).estimate("from", "to")

    from app.integrations.mobility.snapshot_capture import capture_mobility_snapshot

    warm = _counting_provider(counter)
    captured = capture_mobility_snapshot([("from", "to")], primary=warm)
    fact = captured.snapshot.facts[("from", "to")]

    assert counter["n"] == 1, counter
    assert warm.legs_from_memory == 1
    assert fact.fact_quality == LIVE_PROVIDER_CAPTURE, fact
    assert fact.provider_key == "amap-web-service", fact
    assert captured.degraded is False


def test_a_different_mode_or_city_never_borrows_a_remembered_leg():
    """A taxi leg is not a walking leg, and another city's road is not this city's road."""

    counter = {}
    _counting_provider(counter).estimate("from", "to")

    driving = _counting_provider(counter, mode="AUTO")
    assert driving.estimate("from", "to").duration_min == 26
    assert driving.legs_from_memory == 0, "AUTO borrowed a WALK measurement"

    shanghai = _counting_provider(counter, city_code="CN-31-01")
    assert shanghai.estimate("from", "to").duration_min == 26
    assert shanghai.legs_from_memory == 0, "CN-31-01 borrowed a CN-11-01 measurement"
    assert counter["n"] == 3, counter


def test_the_leg_memory_forgets_the_oldest_leg_when_it_is_full():
    """Bounded: a long-lived process cannot grow this memory without limit."""

    memory = amap_http.AmapLegMemory(ttl_s=600.0, max_entries=2, clock=lambda: 0.0)
    route = _counting_provider({}, leg_memory=memory).estimate("from", "to").route
    for index in range(3):
        memory.remember(
            ("WALK", "CN-11-01", "from", str(index)),
            route,
            "2026-10-22T04:5%d:00+00:00" % index,
        )

    assert len(memory) == 2
    assert memory.get(("WALK", "CN-11-01", "from", "0")) is None
    assert memory.get(("WALK", "CN-11-01", "from", "2")) is not None


def _memory_capture(monkeypatch, counter, *, captured_at):
    """One generation of the runtime capture, with the transport counted and the stamp fixed."""

    def handler(request):
        counter["n"] = counter.get("n", 0) + 1
        return httpx.Response(200, json=_driving_payload())

    real_client = httpx.Client

    def factory(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), timeout=10.0)

    monkeypatch.setattr(httpx, "Client", factory)
    monkeypatch.setattr(runtime, "_place_lookup", lambda session, key: _lookup(key))
    monkeypatch.setattr(runtime, "settings", types.SimpleNamespace(live_valhalla_url=None))
    monkeypatch.delenv(amap.KEY_ENV_LEGACY, raising=False)
    monkeypatch.delenv(amap.ROUTING_SEAM_ENV, raising=False)
    monkeypatch.setenv(amap.KEY_ENV_PREFERRED, PLACEHOLDER_KEY)
    journey = types.SimpleNamespace(city_code="CN-11-01")
    return runtime.capture_runtime_mobility_snapshot(
        None,
        journey,
        [("from", "to")],
        operation_key="reform:amap-leg-memory",
        captured_at=captured_at,
    )

