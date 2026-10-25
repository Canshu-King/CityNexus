"""The Amap Web-service key: where it is read from, and what must never reach a message.

Covered here, in the order the interface was asked for:

  * two environment names with a stated preference, and the already-existing one still honoured so a
    machine configured today keeps answering;
  * the status reason naming both environments instead of pointing at one;
  * `httpx`'s own failure text carries the full request URL, and the key is a query parameter -- so the
    helper that replaces `raise_for_status()` is tested against a secret value, not against a shape;
  * a transport failure says only the exception type;
  * the POI search restricts the answer to the named administrative region when one is given, because
    a same-named place in another city is not the place the traveller asked about.

Nothing here touches the network: the request leg is faked with `httpx.MockTransport`, and the parameter
leg is observed through the module's own `amap_get`. The secret used in these tests is a literal that
exists only inside this file.
"""

from __future__ import annotations

import httpx
import pytest

from app.integrations.china import amap

FAKE_KEY = "unit-test-secret-key-DO-NOT-LEAK"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in (amap.KEY_ENV_PREFERRED, amap.KEY_ENV_LEGACY):
        monkeypatch.delenv(name, raising=False)


def test_preferred_name_wins_and_legacy_still_counts(monkeypatch):
    assert amap.web_key() is None
    monkeypatch.setenv(amap.KEY_ENV_LEGACY, FAKE_KEY)
    assert amap.web_key() == FAKE_KEY
    assert amap.key_env_name() == amap.KEY_ENV_LEGACY
    monkeypatch.setenv(amap.KEY_ENV_PREFERRED, "newer-" + FAKE_KEY)
    assert amap.web_key() == "newer-" + FAKE_KEY
    assert amap.key_env_name() == amap.KEY_ENV_PREFERRED


def test_missing_key_reason_names_both_environments():
    status = amap.amap_status()
    assert status.status == "NOT_CONFIGURED"
    assert status.provenance == "UNAVAILABLE"
    assert amap.KEY_ENV_PREFERRED in status.reason and amap.KEY_ENV_LEGACY in status.reason
    # The reason is an operator-facing string: it must not become a place a key can be echoed into.
    assert FAKE_KEY not in status.reason


def test_sanitize_url_masks_the_key_wherever_it_sits():
    for url in (
        f"https://restapi.amap.com/v5/place/text?key={FAKE_KEY}&keywords=%E7%AB%99",
        f"https://restapi.amap.com/v5/direction/walking?origin=1,2&destination=3,4&key={FAKE_KEY}",
    ):
        masked = amap.sanitize_url(url)
        assert FAKE_KEY not in masked
        assert "key=***" in masked
        assert "restapi.amap.com" in masked
    # A parameter that merely ends in the letters "key" is not the credential, and must survive intact.
    untouched = amap.sanitize_url("https://restapi.amap.com/x?monkeys=1&keyword=%E7%AB%99")
    assert untouched == "https://restapi.amap.com/x?monkeys=1&keyword=%E7%AB%99"


@pytest.mark.asyncio
async def test_http_status_failure_message_cannot_contain_the_key(monkeypatch):
    monkeypatch.setenv(amap.KEY_ENV_PREFERRED, FAKE_KEY)

    def fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request, text="upstream said no")

    seen: list[str] = []

    def record_transport(request: httpx.Request) -> None:
        seen.append(str(request.url))

    original = httpx.MockTransport(fail)

    class RecordingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            record_transport(request)
            return await original.handle_async_request(request)

    async with httpx.AsyncClient(transport=RecordingTransport()) as client:
        with pytest.raises(RuntimeError) as caught:
            await amap.amap_get(
                client,
                "https://restapi.amap.com/v5/place/text",
                {"key": FAKE_KEY, "keywords": "车站"},
            )
    message = str(caught.value)
    assert FAKE_KEY not in message, "the failure message would put the key into any log line"
    assert "http_status=500" in message and "key=***" in message
    # The request really did carry the key -- proving the test would have failed had masking been absent.
    assert FAKE_KEY in seen[0]


@pytest.mark.asyncio
async def test_transport_failure_says_only_the_type(monkeypatch):
    monkeypatch.setenv(amap.KEY_ENV_PREFERRED, FAKE_KEY)

    def explode(request: httpx.Request) -> httpx.Response:
        # The real transport failure httpx raises for "the port is not listening".
        raise httpx.ConnectError("connection refused", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(explode)) as client:
        with pytest.raises(RuntimeError) as caught:
            await amap.amap_get(client, "https://restapi.amap.com/v5/place/text", {"key": FAKE_KEY})
    message = str(caught.value)
    assert FAKE_KEY not in message and "ConnectError" in message


@pytest.mark.asyncio
async def test_poi_search_limits_to_the_named_administrative_region(monkeypatch):
    captured: dict = {}

    async def fake_get(client, url, params):
        captured["url"] = url
        captured["params"] = dict(params)
        return httpx.Response(
            200, json={"status": "1", "pois": [{"id": "B0", "name": "西站", "location": "116.3,39.9"}]}
        )

    monkeypatch.setattr(amap, "amap_get", fake_get)
    monkeypatch.setenv(amap.KEY_ENV_PREFERRED, FAKE_KEY)

    rows = await amap.AmapPoiProvider().search("西站", "110000", limit=5)
    assert captured["params"]["citylimit"] == "true", "a same-named place in another city must not pass"
    assert captured["params"]["region"] == "110000"
    assert rows[0]["source_crs"] == "GCJ02" and rows[0]["domain_crs"] == "WGS84"
    assert rows[0]["conversion"] == "ITERATIVE_GCJ02_TO_WGS84"

    # With no region there is nothing to limit to, and the request must not claim a filter it lacks.
    captured.clear()
    await amap.AmapPoiProvider().search("西站", "", limit=5)
    assert "citylimit" not in captured["params"]


def test_an_internal_city_code_is_refused_instead_of_sent_as_a_region(monkeypatch):
    """Measured 2026-10-25: Amap ignores an unrecognised `region` rather than refusing it.

    `region=CN-11-01&citylimit=true` answered status=1 with a POI in another province, so a caller
    passing our internal city code got credible-looking results from the wrong place. The provider
    now refuses the form before any request is made.
    """
    import asyncio

    captured: dict = {}

    async def fake_get(client, url, params):
        captured["params"] = dict(params)
        return httpx.Response(200, json={"status": "1", "pois": []})

    monkeypatch.setattr(amap, "amap_get", fake_get)
    monkeypatch.setenv(amap.KEY_ENV_PREFERRED, FAKE_KEY)

    with pytest.raises(ValueError) as caught:
        asyncio.run(amap.AmapPoiProvider().search("西站", "CN-11-01", limit=5))
    assert "city name or a 6-digit adcode" in str(caught.value)
    assert captured == {}, "the unusable region still reached the provider"
