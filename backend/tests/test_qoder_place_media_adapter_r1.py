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


def entity_payload(qid: str, label: str, description: str, files: list[str],
                   located: list[str] | None = None) -> dict[str, Any]:
    """An entity document in the shape `Special:EntityData` answers with.

    `located` fills P131: without it the graph arm has nothing to climb, and a test that expects a
    chain bind on an entity with no location claim would be testing my mock, not the product.
    """
    claims: dict[str, Any] = {place_media.IMAGE_PROPERTY: [
        {"mainsnak": {"datavalue": {"value": name}}} for name in files]}
    if located:
        claims[place_media.LOCATION_PROPERTY] = [
            {"mainsnak": {"datavalue": {"value": {"id": item}}}} for item in located]
    return {"entities": {qid: {
        "labels": {"zh": {"value": label}},
        "descriptions": {"en": {"value": description}},
        "claims": claims,
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
        params = dict(request.url.params)
        if "wikidata" in host and params.get("action") == "wbgetentities":
            # The P131 climb asks for a batch of ids; the answer is a set of entity documents.
            return httpx.Response(200, json=script.get("chain", {"entities": {}}))
        if "wikidata" in host and params.get("action") == "wbsearchentities":
            # The region is now resolved as its own entity, so one mock has to answer two different
            # searches. `search_by` keys them by the term actually asked for.
            by_term = script.get("search_by") or {}
            return httpx.Response(200, json=by_term.get(params.get("search"), script["search"]))
        if "wikidata" in host and request.url.path.endswith("api.php"):
            return httpx.Response(200, json=script["search"])
        if "wikidata" in host:
            return httpx.Response(200, json=script["entity"])
        if "commons" in host:
            return httpx.Response(200, json=script["imageinfo"])
        return httpx.Response(200, json=script.get("amap", {}))
    return httpx.MockTransport(handler)


def chain_payload(*labels: str) -> dict[str, Any]:
    return {"entities": {
        f"Q{index}": {"labels": {"zh": {"value": text}}, "claims": {}}
        for index, text in enumerate(labels, start=1)}}


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
    # Both written contracts must be readable off one row: the 2026-10-19 order's nine names, and the
    # visual contract's additions (title/provenance/attribution_url/terms_url/confidence plus its
    # spelling "thumbnail_url").
    order_fields = {"place_id", "image_url", "thumb_url", "author", "license", "source_url",
                    "provider", "captured_at", "can_show"}
    visual_fields = {"title", "provenance", "attribution_url", "terms_url", "confidence",
                     "thumbnail_url"}
    assert order_fields <= set(media), sorted(order_fields - set(media))
    assert visual_fields <= set(media), sorted(visual_fields - set(media))
    assert media["thumbnail_url"] == media["thumb_url"]
    assert media["attribution_url"] == media["source_url"]
    assert media["provenance"] == "WIKIDATA_P18+COMMONS_IMAGEINFO"
    assert media["confidence"] == "EXACT_LABEL"
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


@pytest.mark.asyncio
async def test_the_graph_arm_binds_a_place_whose_label_and_description_both_miss_our_names():
    """外滩: the entity answers in English, its description repeats neither name, but `P131` leads to
    the very region we hold. Binding by climbing beats binding by string-guessing."""
    english = entity_payload("Q125474", "Bund", "waterfront in Huangpu, Shanghai", ["bund.jpg"],
                             located=["Q8686"])
    hit = {"search": [{"id": "Q125474", "label": "外滩", "description": "waterfront"}]}
    async with httpx.AsyncClient(transport=transport(script_for(
            search=hit, entity=english, chain=chain_payload("上海市")))) as client:
        result = await place_media.collect_place_media(
            place_id="N:2", label="外滩", region="上海市", client=client)

    assert result.status == place_media.STATUS_PHOTO
    assert result.readings[0]["chain_checked"] is True
    assert result.media is not None and result.media.can_show is True


@pytest.mark.asyncio
async def test_a_chain_that_leads_elsewhere_still_refuses():
    english = entity_payload("Q9", "Bund", "waterfront in Huangpu, Shanghai", ["x.jpg"],
                             located=["Q555"])
    hit = {"search": [{"id": "Q9", "label": "外滩", "description": "waterfront"}]}
    async with httpx.AsyncClient(transport=transport(script_for(
            search=hit, entity=english, chain=chain_payload("東京都")))) as client:
        result = await place_media.collect_place_media(
            place_id="N:3", label="外滩", region="上海市", client=client)

    assert result.status == place_media.STATUS_NO_MEDIA
    assert result.readings[0]["reason_code"] == "MEDIA_IDENTITY_UNBOUND"
    assert "上海市" not in result.readings[0]["chain_labels"]


@pytest.mark.asyncio
async def test_the_chain_is_not_climbed_when_the_strings_already_agree():
    seen: list[httpx.Request] = []
    async with httpx.AsyncClient(transport=transport(script_for(), seen)) as client:
        await place_media.collect_place_media(
            place_id="N:4", label="冠豸山", region="连城县", client=client)

    actions = [dict(request.url.params).get("action") for request in seen]
    assert "wbgetentities" not in actions


@pytest.mark.asyncio
async def test_the_region_binds_by_entity_id_when_neither_label_spells_the_region_our_way():
    """上海市 in our pocket, "Shanghai" on the graph: comparing strings would fail, comparing entity
    ids binds. This is the arm that makes 沪 / 上海市 / Shanghai one place instead of three guesses."""
    entity = entity_payload("Q125474", "Bund", "waterfront in Huangpu", ["bund.jpg"],
                            located=["Q8686"])
    hit = {"search": [{"id": "Q125474", "label": "外滩", "description": "waterfront"}]}
    region_hit = {"search": [{"id": "Q8686", "label": "上海市", "description": "municipality"}]}
    chain = {"entities": {"Q8686": {"labels": {"en": {"value": "Shanghai"}}, "claims": {}}}}
    async with httpx.AsyncClient(transport=transport(
            script_for(search=hit, search_by={"外滩": hit, "上海市": region_hit},
                       entity=entity, chain=chain))) as client:
        result = await place_media.collect_place_media(
            place_id="N:5", label="外滩", region="上海市", client=client)

    reading = result.readings[0]
    assert result.status == place_media.STATUS_PHOTO
    assert reading["binding_arm"] == "region_id"
    assert reading["region_qid"] == "Q8686"
    assert result.media is not None
    assert result.media.confidence == "REGION_ENTITY_MATCH"


@pytest.mark.asyncio
async def test_a_strong_binding_and_a_description_match_are_not_the_same_claim():
    """冠豸山 binds on its own label; the row must not be reported as if it had to fall back to prose."""
    async with httpx.AsyncClient(transport=transport(script_for())) as client:
        result = await place_media.collect_place_media(
            place_id="N:6", label="冠豸山", region="连城县", client=client)

    assert result.readings[0]["binding_arm"] == "label"
    assert result.media is not None and result.media.confidence == "EXACT_LABEL"
