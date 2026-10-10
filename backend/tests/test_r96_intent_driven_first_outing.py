from urllib.parse import parse_qs, unquote_plus

import httpx

from app.integrations.discovery.real_city import OverpassPOIProvider


def test_r96_explicit_outing_intents_emit_bounded_overpass_categories():
    """The four user choices must remain deterministic provider questions."""

    queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = parse_qs(request.content.decode("utf-8"))
        queries.append(unquote_plus(payload["data"][0]))
        return httpx.Response(200, json={"elements": []})

    provider = OverpassPOIProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        base_url="https://controlled.example/api",
    )
    try:
        for query in ("museum/gallery", "park/garden", "cafe", "library"):
            candidates, attempts = provider.search_with_evidence(
                query,
                latitude=31.2304,
                longitude=121.4737,
                radius_m=2500,
                limit=3,
                max_attempts=1,
            )
            assert candidates == []
            assert attempts[0]["answered"] is True
    finally:
        provider.close()

    assert len(queries) == 4
    assert 'nwr["tourism"~"museum|gallery"]' in queries[0]
    assert 'nwr["amenity"="arts_centre"]' in queries[0]
    assert 'nwr["leisure"~"park|garden"]' in queries[1]
    assert 'nwr["amenity"~"cafe|coffee"]' in queries[2]
    assert 'nwr["amenity"="library"]' in queries[3]
    assert '"amenity"~"cafe|coffee"' not in queries[0]
    assert '"amenity"~"cafe|coffee"' not in queries[1]
