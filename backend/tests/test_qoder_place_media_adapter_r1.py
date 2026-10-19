"""The place-media leg: bound or silent, never a guess, and never a blocker.

Nothing here touches the network. Every "provider" is a MockTransport that answers in the exact shape
the live Wikidata / Commons / Amap bodies arrive in (learned by probing them, see
`_commons_probe_1019ai.py`), so no test in this file is proof a provider was contacted.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from app.integrations.china import amap as amap_module
from app.integrations.media import place_media


def entity_payload(qid: str, label: str, description: str, files: list[str]) -> dict[str, Any]:
    return {"entities": {qid: {
        "labels": {"zh": {"value": label}},
        "descriptions": {"en": {"value": description}},
        "claims": {place_media.IMAGE_PROPERTY: [
            {"mainsnak": {"datavalue": {"value": name}}} for name in files]},
    }}}


def imageinfo_payload(url: str | None, *, artist: str = '<a href="https://e.x">某作者</a>',
                      license_short: str = "CC BY 3.0", thumb: str = "https://thumb.example/t.jpg",
                      descriptionurl: str = "https://commons.wikimedia.org/wiki/File:X.jpg"
                      ) -> dict[str, Any]:
    entry: dict[str, Any] = {"extmetadata": {
        "Artist": {"value": artist},
        "LicenseShortName": {"value": license_short},
    }}
    if url is not None:
        entry.update({"url": url, "thumburl": thumb, "descriptionurl": descriptionurl,
                      "width": 1555, "height": 1166, "mime": "image/jpeg"})
    return {"query": {"pages": {"1": {"imageinfo": [entry]}}}}


def transport(script: dict[str, Any], seen: list[httpx.Request] | None = None
              ) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        host = request.url.host or ""
        if "wikidata" in host and request.url.path.endswith("api.php"):
            return httpx.Response(200, json=script["search"])
        if "wikidata" in host:
            return httpx.Response(200, json=script["entity"])
        if "commons" in host:
            return httpx.Response(200, json=script["imageinfo"])
        return httpx.Response(200, json=script.get("amap", {}))
    return httpx.MockTransport(handler)


def script_for(**overrides: Any) -> dict[str, Any]:
    base = {
        "search": {"search": [{"id": "Q10895162", "label": "冠豸山",
                               "description": "mountain in Liancheng, Longyan, Fujian"}]},
        "entity": entity_payload("Q10895162", "冠豸山",
                                 "mountain in Liancheng, Longyan, Fujian",
                                 ["灵芝峰顶看长寿亭.jpg"]),
        "imageinfo": imageinfo_payload("https://upload.wikimedia.org/x.jpg"),
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_a_bound_commons_answer_carries_author_licence_and_source_page():
    async with httpx.AsyncClient(transport=transport(script_for())) as client:
        result = await place_media.collect_place_media(
            place_id="N:6617849504", label="冠豸山", region="连城县", client=client)

    payload = result.as_payload()
    assert payload["status"] == place_media.STATUS_PHOTO
    media = payload["media"]
    assert set(media) == {"place_id", "image_url", "thumb_url", "author", "license", "source_url",
                          "provider", "captured_at", "can_show"}
    assert media["image_url"] == "https://upload.wikimedia.org/x.jpg"
    assert media["thumb_url"] == "https://thumb.example/t.jpg"
    assert media["author"] == "某作者" and "<" not in media["author"]
    assert media["license"] == "CC BY 3.0"
    assert media["source_url"].startswith("https://commons.wikimedia.org/")
    assert media["can_show"] is True
    assert payload["blocked_itinerary"] is False


@pytest.mark.asyncio
async def test_a_picture_of_the_wrong_place_is_no_media_not_a_nice_landscape():
    """The entity's label disagrees and its description never mentions the region we hold."""
    wrong = entity_payload("Q9", "鼓浪屿", "island in Xiamen, Fujian", ["beach.jpg"])
    async with httpx.AsyncClient(transport=transport(
            script_for(entity=wrong))) as client:
        result = await place_media.collect_place_media(
            place_id="N:1", label="冠豸山", region="连城县", client=client)

    assert result.media is None
    assert result.status == place_media.STATUS_NO_MEDIA
    assert result.readings[0]["reason_code"] == "MEDIA_IDENTITY_UNBOUND"


@pytest.mark.asyncio
async def test_an_english_label_still_binds_when_the_region_agrees():
    english = entity_payload("Q10895162", "Guanzhai Mountain",
                             "mountain in Liancheng, Longyan, Fujian", ["peak.jpg"])
    async with httpx.AsyncClient(transport=transport(
            script_for(entity=english))) as client:
        result = await place_media.collect_place_media(
            place_id="N:1", label="冠豸山", region="Liancheng", client=client)

    assert result.status == place_media.STATUS_PHOTO
    assert result.readings[0]["qid"] == "Q10895162"


@pytest.mark.asyncio
async def test_a_photo_without_a_named_licence_is_reported_but_never_shown():
    unnamed = imageinfo_payload("https://upload.wikimedia.org/y.jpg", license_short="")
    async with httpx.AsyncClient(transport=transport(script_for(imageinfo=unnamed))) as client:
        result = await place_media.collect_place_media(
            place_id="N:1", label="冠豸山", region="连城县", client=client)

    assert result.media is None
    assert result.readings[0]["reason_code"] == "LICENCE_UNNAMED"


@pytest.mark.asyncio
async def test_a_withdrawn_file_answers_with_no_media_instead_of_a_stale_url():
    async with httpx.AsyncClient(transport=transport(
            script_for(imageinfo=imageinfo_payload(None)))) as client:
        result = await place_media.collect_place_media(
            place_id="N:1", label="冠豸山", region="连城县", client=client)

    assert result.status == place_media.STATUS_NO_MEDIA
    assert result.readings[0]["reason_code"] == "FILE_WITHDRAWN"


@pytest.mark.asyncio
async def test_a_timeout_is_a_reading_and_the_itinerary_is_not_blocked():
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("boom")

    async with httpx.AsyncClient(transport=httpx.MockTransport(slow)) as client:
        result = await place_media.collect_place_media(
            place_id="N:1", label="冠豸山", region="连城县", client=client)

    assert result.status.startswith(place_media.STATUS_UNAVAILABLE)
    assert result.readings[0]["outcome"] == "MEDIA_UNAVAILABLE_ConnectTimeout"
    assert result.blocked_itinerary is False


@pytest.mark.asyncio
async def test_every_media_request_identifies_the_product(monkeypatch):
    seen: list[httpx.Request] = []
    async with httpx.AsyncClient(transport=transport(script_for(), seen)) as client:
        await place_media.collect_place_media(
            place_id="N:1", label="冠豸山", region="连城县", client=client)

    assert len(seen) == 3
    hosts = [str(request.url.host) for request in seen]
    assert hosts == ["www.wikidata.org", "www.wikidata.org", "commons.wikimedia.org"]
    from app.integrations.discovery.provider_identity import PROVIDER_USER_AGENT
    assert all(request.headers.get("user-agent") == PROVIDER_USER_AGENT for request in seen)


@pytest.mark.asyncio
async def test_amap_without_a_key_is_named_not_skipped_silently(monkeypatch):
    monkeypatch.delenv(amap_module.KEY_ENV_PREFERRED, raising=False)
    monkeypatch.delenv(amap_module.KEY_ENV_LEGACY, raising=False)
    async with httpx.AsyncClient(transport=transport(script_for())) as client:
        result = await place_media.collect_place_media(
            place_id="N:1", label="冠豸山", region="连城县", client=client,
            sources=[place_media.AmapPhotosProvider(client=client)])

    assert result.status == "NOT_CONFIGURED"
    assert result.readings[0]["attempted"] is False
    assert result.media is None


@pytest.mark.asyncio
async def test_amap_photos_are_recorded_as_not_displayable(monkeypatch):
    monkeypatch.setenv(amap_module.KEY_ENV_PREFERRED, "unit-test-key-DO-NOT-LEAK")
    payload = {"pois": [{"id": "B0FFF", "photos": [{"title": "外观", "url": "https://amap/x.png"}]}]}
    async with httpx.AsyncClient(transport=transport({"search": {}, "entity": {}, "imageinfo": {},
                                                     "amap": payload})) as client:
        result = await place_media.collect_place_media(
            place_id="N:1", label="冠豸山", region="连城县", amap_poi_id="B0FFF", client=client,
            sources=[place_media.AmapPhotosProvider(client=client)])

    reading = result.readings[0]
    assert reading["outcome"] == "NOT_DISPLAYABLE" and reading["reason_code"] == "LICENCE_UNNAMED"
    assert result.media is None
    assert "_media" not in reading
    assert result.status == place_media.STATUS_NOT_DISPLAYABLE
    assert "unit-test-key" not in json.dumps(result.as_payload(), ensure_ascii=False)
