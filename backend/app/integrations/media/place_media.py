"""Wikidata P18 / Commons media adapter, adapted from Qoder PR #35.

Bind images using an OSM entity ID or exact name plus source coordinates.
Return attribution and licence metadata; the signed GoalTask service decides
which readings may be displayed and persists its scoped cache.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from time import monotonic
from typing import Any, Mapping, Sequence

import httpx

from app.integrations.discovery.provider_identity import PROVIDER_USER_AGENT

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
IMAGE_WIDTH = 640

STATUS_PHOTO = "REAL_POI_PHOTO"
STATUS_NO_MEDIA = "NO_IMAGE"
STATUS_UNAVAILABLE = "UNAVAILABLE"
STATUS_NOT_DISPLAYABLE = "NO_PERMISSION"

# `P18` is Wikidata's "image" property. Named here because a silent change to it would turn every
# answer into NO_MEDIA and look like the provider went quiet.
IMAGE_PROPERTY = "P18"
#: `P131` is "located in": the arm that binds a place to a region without trusting strings.
LOCATION_PROPERTY = "P131"
CHAIN_CAP = 4
#: The district slot asks for these two labels, in this order.  Chinese first because a traveller
#: reads this field on a Chinese screen; `en` is the fallback the node itself offers, not our guess.
DISTRICT_LANGS = ("zh", "en")
_TAG = re.compile(r"<[^>]+>")


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _plain(value: Any) -> str | None:
    """extmetadata hands back HTML fragments; strip tags, never invent an author."""
    if value is None:
        return None
    if isinstance(value, Mapping):
        value = value.get("value")
    text = _TAG.sub("", str(value or "")).strip()
    return text or None


def _json_payload(response: httpx.Response, where: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except (json.JSONDecodeError, ValueError) as failure:
        raise ValueError(f"{where} returned a body that is not JSON") from failure
    if not isinstance(payload, dict):
        raise TypeError(f"{where} returned a non-object body")
    return payload


# Two written contracts exist for this row and they do not use the same words:
#   * the 2026-10-19 order names place_id / image_url / thumb_url / author / license / source_url /
#     provider / captured_at / can_show;
#   * docs/reform/REVOLUTION_VISUAL_TRAVEL_UI_20261019.md (PR #41) adds title / provenance /
#     attribution_url / terms_url / confidence and spells the thumbnail "thumbnail_url".
# The payload carries both spellings of the two renamed fields instead of making a renderer guess, and
# "confidence" is not a made-up score: it names which arm of the binding actually fired.
CONFIDENCE_BY_ARM = {
    "source_id": "SOURCE_ENTITY_ID",
    "coordinates": "SOURCE_COORDINATE_MATCH",
    "label": "EXACT_LABEL",
    "region_id": "REGION_ENTITY_MATCH",
    "region_label": "REGION_CHAIN_LABEL",
    "description": "DESCRIPTION_SUBSTRING",
}


@dataclass(frozen=True)
class PlaceMedia:
    place_id: str
    image_url: str
    thumb_url: str | None
    author: str | None
    license: str | None
    source_url: str | None
    provider: str
    captured_at: str
    can_show: bool
    title: str | None = None
    provenance: str | None = None
    attribution_url: str | None = None
    terms_url: str | None = None
    confidence: str | None = None
    identity_status: str | None = None
    provider_object_id: str | None = None
    district: str | None = None
    #: The `P131` node's OWN entity id -- 区县身份 as an identity, not as whatever label iterated first.
    district_qid: str | None = None
    #: True when that node is the region the traveller typed: honest reading is "the city itself,
    # not a district inside it".  None means the region was never resolved, not that it disagrees.
    district_matches_region: bool | None = None

    def as_payload(self) -> dict[str, Any]:
        return {
            "place_id": self.place_id,
            "image_url": self.image_url,
            "thumb_url": self.thumb_url,
            "thumbnail_url": self.thumb_url,
            "author": self.author,
            "license": self.license,
            "source_url": self.source_url,
            "attribution_url": self.attribution_url or self.source_url,
            "terms_url": self.terms_url,
            "provider": self.provider,
            "provenance": self.provenance,
            "title": self.title,
            "confidence": self.confidence,
            "identity_status": self.identity_status or self.confidence,
            "provider_object_id": self.provider_object_id,
            "district": self.district,
            "district_qid": self.district_qid,
            "district_matches_region": self.district_matches_region,
            "captured_at": self.captured_at,
            "can_show": self.can_show,
        }


@dataclass(frozen=True)
class PlaceMediaResult:
    place_id: str
    status: str
    media: PlaceMedia | None
    readings: tuple[dict[str, Any], ...]
    reason_code: str | None = None
    blocked_itinerary: bool = False
    # 顶层也带一次身份状态：路由的读者看的是这一层，不该为了「能不能显示这张图」再去翻 media 或 readings。
    identity_status: str | None = None

    def as_payload(self) -> dict[str, Any]:
        return {
            "place_id": self.place_id,
            "status": self.status,
            "reason_code": self.reason_code,
            "media": self.media.as_payload() if self.media else None,
            "provider_readings": [dict(row) for row in self.readings],
            "identity_status": self.identity_status,
            "blocked_itinerary": self.blocked_itinerary,
        }


def identity_matches(label: str, entity_label: str | None, description: str | None,
                     region: str | None, chain_labels: Sequence[str] = (),
                     chain_qids: Sequence[str] = (), region_qid: str | None = None) -> str | None:
    """Which arm binds this entity to the place we asked for -- or None when nothing does.

    Returning the arm rather than a bool is what turns "confidence" into a fact: a caller can see
    whether the binding was an exact label, a shared region entity, a chain label or a description
    substring, and a renderer can choose to trust only the strong ones.
    """
    wanted = (label or "").strip()
    given = (entity_label or "").strip()
    if wanted and given and wanted == given:
        return "label"
    text = (description or "").strip().lower()
    region_text = (region or "").strip().lower()
    if region_qid and region_qid in set(chain_qids):
        # The strongest region arm: both sides resolved to a Wikidata entity, so the three spellings of
        # one city are one node instead of three strings that have to match character for character.
        return "region_id"
    if region_text and any(region_text == str(seen).strip().lower() for seen in chain_labels):
        return "region_label"
    if not text or not region_text:
        return None
    if wanted.lower() in text or region_text in text:
        return "description"
    return None


class WikimediaMediaProvider:
    """Wikidata `P18` -> Commons `imageinfo` with the attribution the licence requires."""

    provider_key = "wikimedia-commons"

    def __init__(self, *, client: httpx.AsyncClient, source_point: tuple[float, float] | None = None) -> None:
        self._client = client
        self._source_point = source_point

    async def _entity(self, qid: str) -> dict[str, Any]:
        response = await self._client.get(WIKIDATA_ENTITY.format(qid=qid),
                                          headers={"User-Agent": PROVIDER_USER_AGENT})
        response.raise_for_status()
        payload = _json_payload(response, "Wikidata entity")
        entities = payload.get("entities") or {}
        document = entities.get(qid) or {}
        claims = document.get("claims") or {}
        files = [
            snak["datavalue"]["value"]
            for claim in claims.get(IMAGE_PROPERTY, [])
            for snak in [claim.get("mainsnak") or {}]
            if isinstance(snak.get("datavalue"), dict)
            and isinstance(snak["datavalue"].get("value"), str)
        ]
        labels = document.get("labels") or {}
        descriptions = document.get("descriptions") or {}
        located = [
            snak["datavalue"]["value"]
            for claim in claims.get(LOCATION_PROPERTY, [])
            for snak in [claim.get("mainsnak") or {}]
            if isinstance(snak.get("datavalue"), dict)
            and isinstance(snak["datavalue"].get("value"), dict)
        ]
        return {
            "files": files,
            "labels": [str(row.get("value")) for row in labels.values() if row.get("value")],
            "coordinates": [snak["datavalue"]["value"]
                for claim in claims.get("P625", []) for snak in [claim.get("mainsnak") or {}]
                if isinstance(snak.get("datavalue"), dict) and isinstance(snak["datavalue"].get("value"), dict)],
            "label": next((row.get("value") for row in labels.values() if row.get("value")), None),
            "description": next((row.get("value") for row in descriptions.values()
                                if row.get("value")), None),
            "located_in": [str(item.get("id")) for item in located if item.get("id")],
        }

    async def _region_entity(self, region: str) -> str | None:
        """Resolve the traveller's own region string to a Wikidata entity id (one call, or none)."""
        for hit in await self._search(region):
            qid = str(hit.get("id") or "")
            if qid:
                return qid
        return None

    async def _region_chain(self, qids: Sequence[str]) -> tuple[list[str], list[str], list[str]]:
        """Climb `P131` a few hops and hand back every label and id seen.

        Short-circuits on the first hop that yields nothing: a chain that dead-ends cannot prove a
        region, and reading fewer rows than asked is reported, never padded.
        """
        seen: list[str] = []
        visited: list[str] = []
        chain_qids: list[str] = []
        current = list(qids)
        while current and len(visited) < CHAIN_CAP:
            batch = [qid for qid in current if qid not in visited]
            if not batch:
                break
            visited.extend(batch)
            response = await self._client.get(WIKIDATA_API, params={
                "action": "wbgetentities", "ids": "|".join(batch), "props": "claims|labels",
                "format": "json"}, headers={"User-Agent": PROVIDER_USER_AGENT})
            response.raise_for_status()
            payload = _json_payload(response, "Wikidata chain")
            nxt: list[str] = []
            for qid_seen, doc in (payload.get("entities") or {}).items():
                chain_qids.append(str(qid_seen))
                for row in (doc.get("labels") or {}).values():
                    if row.get("value"):
                        seen.append(str(row["value"]))
                for claim in (doc.get("claims") or {}).get(LOCATION_PROPERTY, []):
                    value = ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {}
                    if isinstance(value, dict) and value.get("id"):
                        nxt.append(str(value["id"]))
            current = nxt
        return seen, visited, chain_qids

    async def _district_node(self, qids: Sequence[str]) -> dict[str, Any]:
        """Ask the nearest `P131` node for its OWN id and its OWN Chinese name -- one call, one hop.

        The slot the ruling calls 区县身份 used to be filled from the chain walk's first label, which
        gave whatever language Wikidata happened to iterate: 外滩 came back `Shanghai` and 广州塔 came
        back 赤岗街道, and neither reading carried the node's identity.  An id plus a named language is
        the difference between "a name we happened to see" and "this place is inside THIS entity".
        """
        batch = [str(qid) for qid in list(qids)[:CHAIN_CAP] if qid]
        if not batch:
            return {}
        response = await self._client.get(WIKIDATA_API, params={
            "action": "wbgetentities", "ids": "|".join(batch), "props": "labels",
            "languages": "|".join(DISTRICT_LANGS), "format": "json"},
            headers={"User-Agent": PROVIDER_USER_AGENT})
        response.raise_for_status()
        payload = _json_payload(response, "Wikidata district node")
        entities = payload.get("entities") or {}
        for qid in batch:
            labels = (entities.get(qid) or {}).get("labels") or {}
            for language in DISTRICT_LANGS:
                value = (labels.get(language) or {}).get("value")
                if value:
                    return {"qid": qid, "name": str(value), "label_language": language}
        return {}

    async def _search(self, label: str, lang: str = "zh") -> list[dict[str, Any]]:
        # `language` is mandatory on this endpoint and decides which labels are searched: asking without
        # it comes back empty, which an earlier draft of this module mis-filed as "no such entity".
        response = await self._client.get(WIKIDATA_API, params={
            "action": "wbsearchentities", "search": label, "language": lang, "limit": 5,
            "format": "json"}, headers={"User-Agent": PROVIDER_USER_AGENT})
        response.raise_for_status()
        payload = _json_payload(response, "Wikidata search")
        if payload.get("error"):
            raise ValueError("Wikidata search refused: {}".format(
                str((payload["error"] or {}).get("info"))[:120]))
        return list(payload.get("search") or [])

    async def _file_info(self, filename: str) -> dict[str, Any]:
        response = await self._client.get(COMMONS_API, params={
            "action": "query", "titles": "File:" + filename, "prop": "imageinfo",
            "iiprop": "url|extmetadata|size|mime", "iiurlwidth": IMAGE_WIDTH, "format": "json"},
            headers={"User-Agent": PROVIDER_USER_AGENT})
        response.raise_for_status()
        pages = (_json_payload(response, "Commons imageinfo").get("query") or {}).get("pages") or {}
        for page in pages.values():
            rows = page.get("imageinfo") or []
            if rows:
                return rows[0]
        return {}

    def _binds(self, document: dict[str, Any], label: str) -> bool:
        """The one rule that turns a search hit into *this* task's place.

        The entity's own coordinates have to sit within 800 m of the point the provider gave us, and
        the entity's own labels have to contain this POI's name.  Nothing here reads the search hit's
        label: a fuzzy search echoes back whatever was typed, so trusting it would let any near-miss
        "prove" itself.
        """
        if not self._source_point:
            return False
        import math

        def same_name(value: str) -> bool:
            normalize = lambda text: re.sub(r"[\s·（）()]+", "", text).casefold()
            return normalize(value) == normalize(label)
        for coordinate in document["coordinates"]:
            lat, lon = coordinate.get("latitude"), coordinate.get("longitude")
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                continue
            distance = math.hypot((lat-self._source_point[0])*111_000,
                (lon-self._source_point[1])*111_000*math.cos(math.radians(lat)))
            if distance <= 800 and any(same_name(value) for value in document["labels"]):
                return True
        return False

    async def search(self, *, place_id: str, label: str, region: str | None,
                     wikidata_id: str | None, provider_object_id: str | None = None
                     ) -> tuple[PlaceMedia | None, dict[str, Any]]:
        started = _stamp()
        try:
            qid = wikidata_id
            entity_label: str | None = None
            description: str | None = None
            if qid is None:
                candidates = await self._search(label)
                if not candidates:
                    return None, {"source": self.provider_key, "attempted": True,
                                  "outcome": STATUS_NO_MEDIA, "reason_code": "ENTITY_NOT_FOUND",
                                  "captured_at": started}
                # Only the first hit used to be looked at.  Measured 2026-10-22: 天坛公园's own entity is
                # the *second* hit (its label says 天坛公园, its coordinate is 309 m away), while the first
                # is the temple complex, whose document never names the park -- so the traveller was told
                # "还没核实到具体是哪个地点" when the answer was one row further down.  Every hit is now
                # judged by the same rule, and the first document stays as the fallback so an unbound
                # lookup still reports the reason it always did.  Bounded by hits and by time: the whole
                # chain has ten seconds, and a refusal must not cost the traveller a timeout.
                deadline = monotonic() + 5.0
                document: dict[str, Any] | None = None
                for hit in candidates[:5]:
                    candidate_qid = str(hit.get("id") or "")
                    if not candidate_qid:
                        continue
                    candidate = await self._entity(candidate_qid)
                    if document is None:
                        qid, document = candidate_qid, candidate
                    if self._binds(candidate, label):
                        qid, document = candidate_qid, candidate
                        break
                    if monotonic() > deadline:
                        break
                # A hit list whose rows carry no entity id is "we could not find this place", not a
                # crash.  Left unhandled, the None below reaches a subscript and the traveller's receipt
                # reads UNAVAILABLE_TypeError -- a number that blames our own code for a provider answer.
                if document is None:
                    return None, {"source": self.provider_key, "attempted": True,
                                  "outcome": STATUS_NO_MEDIA, "reason_code": "ENTITY_NOT_FOUND",
                                  "captured_at": started}
            else:
                document = await self._entity(qid)
            files = document["files"]
            # The entity document is the authority here, never the search hit: a fuzzy search returns
            # the label we typed back to us, and trusting it would let any near-miss "prove" itself.
            entity_label = document["label"]
            description = document["description"]
            chain_labels: list[str] = []
            chain_qids: list[str] = []
            region_qid: str | None = None
            district: str | None = None
            district_qid: str | None = None
            arm = "source_id" if wikidata_id else ("coordinates" if self._binds(document, label) else None)
            # A region substring or an identical name alone cannot bind a task's POI.
            if arm is None:
                return None, {"source": self.provider_key, "attempted": True, "qid": qid,
                    "outcome": STATUS_NO_MEDIA, "reason_code": "MEDIA_IDENTITY_UNBOUND", "captured_at": started}

            # 区县身份 is asked on every arm: a place matched by its own label sits inside a district no
            # less than one matched through the chain.  It is asked only once we are going to show
            # something, so a refusal does not pay for a lookup nobody reads.
            node = await self._district_node(document["located_in"])
            district = node.get("name") or None
            district_qid = node.get("qid") or None
            district_matches_region = (district_qid == region_qid) if (district_qid and region_qid) else None
            if not files:
                # The arm above is the proof that this place *was* identified, so the receipt says so.
                # Measured 2026-10-22: 天坛公园 answered PROPERTY_EMPTY while the stored receipt read
                # UNBOUND -- two different answers to "did you find the place", and an auditor cannot
                # tell from that pair whether the photo is missing or the place never was.
                return None, {"source": self.provider_key, "attempted": True, "qid": qid,
                    "outcome": STATUS_NO_MEDIA, "reason_code": "PROPERTY_EMPTY",
                    "identity_status": "BOUND_" + CONFIDENCE_BY_ARM.get(arm or "", "UNKNOWN"),
                    "captured_at": started}
            info = await self._file_info(files[0])
            if not info.get("url"):
                return None, {"source": self.provider_key, "attempted": True, "qid": qid,
                              "outcome": STATUS_NO_MEDIA, "reason_code": "FILE_WITHDRAWN",
                              "identity_status": "BOUND_" + CONFIDENCE_BY_ARM.get(arm or "", "UNKNOWN"),
                              "captured_at": started}
            meta = info.get("extmetadata") or {}
            license_name = _plain(meta.get("LicenseShortName")) or _plain(meta.get("License"))
            media = PlaceMedia(
                place_id=place_id,
                title=_plain(meta.get("ImageDescription")) or files[0],
                provenance="WIKIDATA_" + IMAGE_PROPERTY + "+COMMONS_IMAGEINFO",
                attribution_url=info.get("descriptionurl") or None,
                terms_url=_plain(meta.get("LicenseUrl")) or None,
                confidence=CONFIDENCE_BY_ARM.get(arm or "", "UNKNOWN"),
                identity_status="BOUND_" + CONFIDENCE_BY_ARM.get(arm or "", "UNKNOWN"),
                provider_object_id=wikidata_id or provider_object_id or None,
                district=district,
                district_qid=district_qid,
                district_matches_region=district_matches_region,
                image_url=str(info["url"]),
                thumb_url=str(info["thumburl"]) if info.get("thumburl") else None,
                author=_plain(meta.get("Artist")),
                license=license_name,
                source_url=info.get("descriptionurl") or None,
                provider=self.provider_key,
                captured_at=_stamp(),
                # A licence we cannot name is not a licence to display.
                can_show=bool(license_name),
            )
            reading = {"source": self.provider_key, "attempted": True, "qid": qid,
                       "file": files[0], "license": media.license,
                       "binding_arm": arm, "chain_checked": bool(chain_labels),
                       "identity_status": "BOUND_" + CONFIDENCE_BY_ARM.get(arm or "", "UNKNOWN"),
                       "district": district, "district_qid": district_qid,
                       "district_matches_region": district_matches_region, "region_qid": region_qid,
                       # One vocabulary for refusals: the reading uses the same word the result does.
                       "outcome": STATUS_PHOTO if media.can_show else STATUS_NO_MEDIA,
                       "reason_code": None if media.can_show else "LICENCE_UNNAMED",
                       "captured_at": started}
            return (media if media.can_show else None), reading
        except (httpx.HTTPError, ValueError, KeyError, TypeError, json.JSONDecodeError) as failure:
            return None, {"source": self.provider_key, "attempted": True,
                          "outcome": STATUS_UNAVAILABLE + "_" + type(failure).__name__,
                          "captured_at": started}


def default_sources(*, client: httpx.AsyncClient) -> list[Any]:
    """Commons first: it is the only source here whose licence is stated. Amap answers only with a key."""
    return [WikimediaMediaProvider(client=client)]


async def collect_place_media(
    *,
    place_id: str,
    label: str,
    region: str | None = None,
    wikidata_id: str | None = None,
    provider_object_id: str | None = None,
    amap_poi_id: str | None = None,
    sources: Sequence[Any] | None = None,
    client: httpx.AsyncClient | None = None,
) -> PlaceMediaResult:
    """Ask the sources in order; the first displayable photograph wins, failures are readings."""
    chain = list(sources if sources is not None else default_sources(client=client))  # type: ignore[arg-type]
    readings: list[dict[str, Any]] = []
    chosen: PlaceMedia | None = None
    for source in chain:
        if chosen is not None:
            readings.append({"source": getattr(source, "provider_key", "unknown"),
                             "attempted": False, "outcome": "SKIPPED",
                             "reason_code": "ANOTHER_SOURCE_ALREADY_ANSWERED"})
            continue
        kwargs: dict[str, Any] = {"place_id": place_id, "label": label, "region": region,
                                  "wikidata_id": wikidata_id,
                                  "provider_object_id": provider_object_id}
        media, reading = await source.search(**kwargs)
        readings.append(reading)
        if media is not None:
            chosen = media
    if chosen is not None:
        return PlaceMediaResult(place_id=place_id, status=STATUS_PHOTO, media=chosen,
                                readings=tuple(readings),
                                identity_status=chosen.identity_status)
    # Nothing displayable: say *why*, in the order the traveller's screen cares about. A provider that
    # could not be asked is a weaker statement than one that answered "no", and an unlicenced photo is
    # its own answer -- never fold those three into one blank NO_MEDIA.
    decided = None
    for reading in readings:
        outcome = str(reading.get("outcome") or "")
        if outcome.startswith(STATUS_UNAVAILABLE):
            decided = (outcome, reading.get("reason_code"))
            break
        if outcome == STATUS_NOT_DISPLAYABLE and decided is None:
            decided = (STATUS_NOT_DISPLAYABLE, reading.get("reason_code"))
        if outcome in {STATUS_NO_MEDIA, "NOT_CONFIGURED"} and decided is None:
            decided = (STATUS_NO_MEDIA if outcome == STATUS_NO_MEDIA else "NOT_CONFIGURED",
                       reading.get("reason_code"))
    status, reason = decided or (STATUS_NO_MEDIA, "NO_SOURCE_ANSWERED")
    # 拒的时候，身份状态说的是「为什么算没绑上」，不是抄一遍 status：没问过任何来源与问过但不是同一处，
    # 在屏上是两件事。
    unbound = next((str(row.get("identity_status")) for row in readings
                    if row.get("identity_status")), None)
    identity_status = unbound or ("NOT_ASKED" if not any(
        row.get("attempted") for row in readings) else "UNBOUND")
    return PlaceMediaResult(place_id=place_id, status=status, media=None, readings=tuple(readings),
                            reason_code=reason, identity_status=identity_status)
