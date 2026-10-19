"""The place-media leg: bound or silent, never a guess, and never a blocker.

Nothing here touches the network. Every "provider" is a MockTransport that answers in the exact shape
the live Wikidata / Commons / Amap bodies arrive in (learned by probing them, see
`_commons_probe_1019ai.py`), so no test in this file is proof a provider was contacted.
"""

from __future__ import annotations

import json
import uuid
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
            # Two different asks share this endpoint.  The `P131` climb needs claims as well as labels;
            # the district hop asks for the node's own labels only.  Answering both from one script
            # would let a district reading silently satisfy the chain control -- the exact confusion
            # this module exists to remove, so the mock refuses to make it possible.
            if params.get("props") == "labels":
                return httpx.Response(200, json=script.get("district", {"entities": {}}))
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


def district_payload(qid: str, *, zh: str | None = None, en: str | None = None) -> dict[str, Any]:
    """One node's own labels -- what the 区县身份 hop is allowed to see (it asks for no claims)."""
    labels: dict[str, Any] = {}
    if zh:
        labels["zh"] = {"value": zh}
    if en:
        labels["en"] = {"value": en}
    return {"entities": {qid: {"labels": labels}}}


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
    district_fields = {"district", "district_qid", "district_matches_region"}
    assert order_fields <= set(media), sorted(order_fields - set(media))
    assert visual_fields <= set(media), sorted(visual_fields - set(media))
    assert district_fields <= set(media), sorted(district_fields - set(media))
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
    assert result.readings[0]["outcome"] == "UNAVAILABLE_ConnectTimeout"
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
    assert reading["outcome"] == place_media.STATUS_NOT_DISPLAYABLE and reading["reason_code"] == "LICENCE_UNNAMED"
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


@pytest.mark.asyncio
async def test_the_district_slot_is_the_nodes_own_id_in_the_language_the_traveller_reads():
    """冠豸山 binds on its own label, so the chain is never climbed -- yet 区县身份 still has to arrive,
    as that node's own id and its own Chinese name rather than whatever label iterated first."""
    entity = entity_payload("Q10895162", "冠豸山", "mountain in Liancheng", ["p.jpg"],
                            located=["Q10895200"])
    seen: list[httpx.Request] = []
    async with httpx.AsyncClient(transport=transport(
            script_for(entity=entity, district=district_payload("Q10895200", zh="连城县",
                                                                en="Liancheng County")),
            seen)) as client:
        result = await place_media.collect_place_media(
            place_id="N:7", label="冠豸山", region="连城县", client=client)

    media = result.media
    assert media is not None and media.confidence == "EXACT_LABEL"
    assert media.district == "连城县"
    assert media.district_qid == "Q10895200"
    asks = [dict(request.url.params) for request in seen
            if dict(request.url.params).get("action") == "wbgetentities"]
    assert len(asks) == 1, asks
    assert asks[0]["props"] == "labels" and asks[0]["languages"] == "zh|en"


@pytest.mark.asyncio
async def test_a_district_that_is_the_region_itself_is_said_to_be_the_region():
    """外滩 sits directly under 上海市, and 广州塔 sits under a node inside its region: the payload has
    to tell those two apart, because only one of them is a 区县."""
    hit = {"search": [{"id": "Q125474", "label": "外滩", "description": "waterfront"}]}
    region_hit = {"search": [{"id": "Q8686", "label": "上海市", "description": "municipality"}]}
    by_term = {"外滩": hit, "上海市": region_hit}

    city_itself = entity_payload("Q125474", "Bund", "waterfront in Huangpu", ["b.jpg"],
                                 located=["Q8686"])
    async with httpx.AsyncClient(transport=transport(script_for(
            search=hit, search_by=by_term, entity=city_itself, chain=chain_payload("上海市"),
            district=district_payload("Q8686", zh="上海市")))) as client:
        upper = await place_media.collect_place_media(
            place_id="N:8", label="外滩", region="上海市", client=client)
    assert upper.media is not None
    assert upper.media.district_qid == "Q8686"
    assert upper.media.district_matches_region is True

    nested = entity_payload("Q125474", "Bund", "waterfront in Huangpu", ["b.jpg"],
                            located=["Q42"])
    async with httpx.AsyncClient(transport=transport(script_for(
            search=hit, search_by=by_term, entity=nested,
            chain=chain_payload("黄浦区", "上海市"),
            district=district_payload("Q42", zh="黄浦区")))) as client:
        inside = await place_media.collect_place_media(
            place_id="N:9", label="外滩", region="上海市", client=client)
    assert inside.media is not None
    assert inside.media.district == "黄浦区"
    assert inside.media.district_matches_region is False


@pytest.mark.asyncio
async def test_the_district_hop_cannot_be_mistaken_for_the_region_chain():
    """A district name is evidence of WHERE the place is, not evidence that it belongs to the region we
    were given.  Here the climb says 東京都 while the district hop happens to answer 上海市: binding on
    that name would be the fuzzy-string defect wearing a graph costume, so the row must still refuse."""
    hit = {"search": [{"id": "Q125474", "label": "外滩", "description": "waterfront"}]}
    region_hit = {"search": [{"id": "Q8686", "label": "上海市", "description": "municipality"}]}
    entity = entity_payload("Q125474", "Bund", "waterfront in Huangpu", ["b.jpg"], located=["Q777"])
    async with httpx.AsyncClient(transport=transport(script_for(
            search=hit, search_by={"外滩": hit, "上海市": region_hit}, entity=entity,
            chain=chain_payload("東京都"), district=district_payload("Q777", zh="上海市")))) as client:
        result = await place_media.collect_place_media(
            place_id="N:10", label="外滩", region="上海市", client=client)

    assert result.status == place_media.STATUS_NO_MEDIA
    assert result.media is None
    assert result.readings[0]["reason_code"] == "MEDIA_IDENTITY_UNBOUND"
    assert result.readings[0]["region_qid"] == "Q8686"


@pytest.mark.asyncio
async def test_the_route_shape_is_what_a_signed_member_reads():
    """The GET is the contract's other half: 200 with NO_IMAGE for a place that exists but has no
    showable photograph, 404 only when there is no place or no journey to attribute it to."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app import place_media_routes
    from app.db.models import Base, Journey, Place, Traveler
    from app.db.session import get_session

    # 路由吃 UUID 是这棵树的规矩（其他 journey 路由都写 journey_id: UUID），所以种子行也用真 UUID，
    # 不然我测的是自己的路径解析，不是「签名成员读得到」。
    journey_id = str(uuid.uuid4())
    # TestClient runs the endpoint on another thread, so the in-memory database has to be
    # shareable across threads instead of owning itself into a ProgrammingError.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                         poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with TestingSession() as seed:
        seed.add(Traveler(id="trv-media", display_name="media", locale="zh",
                          timezone="Asia/Shanghai", created_at="now", updated_at="now"))
        seed.add(Journey(id=journey_id, traveler_id="trv-media", title="t", city_code="350825",
                         timezone="Asia/Shanghai", start_at="now", end_at="now",
                         budget_currency="CNY", budget_amount_minor=1, status="ACTIVE",
                         created_at="now", updated_at="now"))
        seed.add(Place(id="plc-media", provider_key="photon", external_id="N:6617849504",
                       city_code="350825", name="冠豸山", category="poi", latitude=25.7,
                       longitude=116.75, opening_hours_json="{}", tags_json="[]",
                       metadata_json="{}", updated_at="now"))
        seed.commit()

    app = FastAPI()
    app.include_router(place_media_routes.router)

    def override_session():
        with TestingSession() as session:
            yield session

    async def override_client():
        return httpx.AsyncClient(transport=transport(script_for()))

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[place_media_routes._media_client] = override_client
    client = TestClient(app)

    ok = client.get("/api/v1/journeys/" + journey_id + "/places/plc-media/media")
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["status"] == place_media.STATUS_PHOTO
    assert body["identity_status"].startswith("BOUND_")
    assert body["place_name"] == "冠豸山" and body["journey_id"] == journey_id
    assert body["media"]["can_show"] is True

    missing_place = client.get("/api/v1/journeys/" + journey_id + "/places/plc-nope/media")
    assert missing_place.status_code == 404
    missing_journey = client.get("/api/v1/journeys/" + str(uuid.uuid4()) + "/places/plc-media/media")
    assert missing_journey.status_code == 404


@pytest.mark.asyncio
async def test_a_refusal_says_why_the_identity_did_not_bind_at_the_top_level():
    """The screen needs one field, not a hunt through readings, and "nobody was asked" is a different
    sentence from "asked, and it was somewhere else"."""
    english = entity_payload("Q9", "Bund", "waterfront in Huangpu, Shanghai", ["x.jpg"],
                             located=["Q555"])
    hit = {"search": [{"id": "Q9", "label": "外滩", "description": "waterfront"}]}
    async with httpx.AsyncClient(transport=transport(
            script_for(search=hit, entity=english, chain=chain_payload("東京都")))) as client:
        result = await place_media.collect_place_media(
            place_id="N:9", label="外滩", region="上海市", client=client)

    payload = result.as_payload()
    assert payload["status"] == place_media.STATUS_NO_MEDIA
    assert payload["identity_status"] == "UNBOUND"
    assert payload["media"] is None


def test_the_media_route_is_mounted_on_the_real_app():
    """A router in its own module only helps if the product's app actually carries it.

    This is the control for the two lines in `main.py`: it asks the shipped app's own OpenAPI document,
    so a forgotten `include_router` -- or a merge that drops it -- goes red here rather than turning the
    endpoint into a module nobody can reach.
    """
    from app.main import app

    paths = app.openapi().get("paths", {})
    assert "/api/v1/journeys/{journey_id}/places/{place_id}/media" in paths, sorted(
        path for path in paths if "places" in path)
    assert "get" in paths["/api/v1/journeys/{journey_id}/places/{place_id}/media"]
