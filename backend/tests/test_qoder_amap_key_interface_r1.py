"""The Amap Web-service key: where it is read from, and what must never reach a message.

Covered here, in the order the interface was asked for:

  * two environment names with a stated preference, and the already-existing one still honoured so a
    machine configured today keeps answering;
  * the status reason naming both environments instead of pointing at one;
  * `httpx`'s own failure text carries the full request URL, and the key is a query parameter -- so the
    helper that replaces `raise_for_status()` is tested against a secret value, not against a shape;
  * a transport failure says only the exception type;
  * the logger `httpx` uses for its own request line prints the whole URL, so the guard there is a
    filter installed by the same helper that makes the request -- not the module's own `sanitize_url`,
    which can only reach messages this module writes;
  * the POI search restricts the answer to the named administrative region when one is given, because
    a same-named place in another city is not the place the traveller asked about.

Nothing here touches the network: the request leg is faked with `httpx.MockTransport`, and the parameter
leg is observed through the module's own `amap_get`. The secret used in these tests is a literal that
exists only inside this file.
"""

from __future__ import annotations

import logging

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


def test_the_backend_reads_the_name_the_local_tool_writes(monkeypatch):
    """The launcher exports CITYNEXUS_AMAP_WEB_KEY; this is the promise that makes that enough."""
    assert amap.amap_status().status == 'NOT_CONFIGURED'
    monkeypatch.setenv(amap.KEY_ENV_PREFERRED, FAKE_KEY)
    ready = amap.amap_status()
    assert ready.status == 'READY' and ready.provenance == 'LIVE'
    assert ready.coordinate_crs == 'GCJ02'
    assert FAKE_KEY not in repr(ready)


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

    rows = await amap.AmapPoiProvider().search("西站", "CN-11-01", limit=5)
    assert captured["params"]["citylimit"] == "true", "a same-named place in another city must not pass"
    assert captured["params"]["region"] == "CN-11-01"
    assert rows[0]["source_crs"] == "GCJ02" and rows[0]["domain_crs"] == "WGS84"
    assert rows[0]["conversion"] == "ITERATIVE_GCJ02_TO_WGS84"

    # With no region there is nothing to limit to, and the request must not claim a filter it lacks.
    captured.clear()
    await amap.AmapPoiProvider().search("西站", "", limit=5)
    assert "citylimit" not in captured["params"]

def test_no_http_surface_prints_the_key_when_the_provider_is_ready(monkeypatch):
    """The order said the static key must not reach the browser. This is the machine-checked version.

    A synthetic value goes into the environment the backend reads; the provider-status route is then
    asked, and the raw response text is searched for it. The test also asserts the key really was
    configured -- a route that answered NOT_CONFIGURED would pass the absence check for the wrong
    reason, which is the empty-green this campaign keeps having to write rulers against.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setenv(amap.KEY_ENV_PREFERRED, FAKE_KEY)
    client = TestClient(app)
    answer = client.get('/api/v1/providers/v9')
    assert answer.status_code == 200
    body = answer.text
    payload = answer.json()
    assert payload['amap']['status'] == 'READY', 'the configured leg must be the one asserting absence'
    assert payload['amap']['provenance'] == 'LIVE'
    assert payload['amap']['coordinate_crs'] == 'GCJ02'
    assert FAKE_KEY not in body
    assert 'key=' not in body

    monkeypatch.delenv(amap.KEY_ENV_PREFERRED)
    missing = client.get('/api/v1/providers/v9').json()
    assert missing['amap']['status'] == 'NOT_CONFIGURED'
    assert amap.KEY_ENV_PREFERRED in missing['amap']['reason']
    assert FAKE_KEY not in client.get('/api/v1/providers/v9').text


def test_the_request_logger_of_the_library_underneath_never_prints_the_key(caplog):
    """`httpx` logs the whole URL of every request it makes, and the key rides in that query string.

    `sanitize_url` cannot reach that line: it only rewrites messages this module builds.  So the
    request helper installs a filter on the logger before it sends anything.
    """
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"status": "1", "pois": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with caplog.at_level(logging.INFO, logger="httpx"):
        response = amap.amap_get_sync(
            client,
            amap.AMAP_BASE_URL + "/v5/place/text",
            {"key": FAKE_KEY, "keywords": "西站"},
        )

    assert response.status_code == 200
    # The secret really was on the wire in this test -- otherwise the next two lines prove nothing.
    assert FAKE_KEY in seen["url"]
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert logged != ""
    assert FAKE_KEY not in logged
    assert "key=***" in logged


def test_the_redaction_filter_is_installed_once_not_once_per_request():
    logger = logging.getLogger("httpx")

    def installed():
        return sum(1 for one in logger.filters if isinstance(one, amap.KeyRedactionFilter))

    before = installed()
    amap.install_log_redaction()
    amap.install_log_redaction()
    assert installed() == max(before, 1)
