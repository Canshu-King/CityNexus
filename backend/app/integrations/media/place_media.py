"""Real photographs for a place the traveller already has an identity for -- and honest silence otherwise.

The owner's complaint of 2026-10-19 is precise: the product finds genuine POIs and shows zero
photographs of them. This module is the media leg of that surface. It deliberately says nothing about
layout: Hermes/Codex render it, the projection is the contract.

Three rules the ruling names, enforced here rather than in a prompt:

  1. A photograph is bound to a *source identity*, never to a vibe. A Wikimedia answer is accepted only
     when the entity's own label or description matches the place we asked for (exact label, or the
     region we were given appears in the entity's description). A fuzzy Chinese search that returns a
     pretty landscape of somewhere else is `MEDIA_IDENTITY_UNBOUND`, which reads as `NO_MEDIA` -- the
     ruling forbids filling a specific hall with generic scenery.
  2. Licences decide visibility. Wikimedia answers carry author + licence + the file page, so they may
     be shown with attribution. Amap's `show_fields=photos` is allowed by its API but its terms restrict
     storing and re-publishing the images, and the practical licence of an individual photo is not
     stated by the provider: those rows are reported with ``can_show=False`` and are never persisted as
     product truth.
  3. Missing media never blocks a trip. Every provider boundary here is a reading, not an exception,
     and the caller gets ``status`` plus per-source readings so "we did not ask" cannot be re-read as
     "there is nothing".

Nothing in this module writes to the database, and nothing needs an Amap key to work: with no key the
Amap leg reports ``NOT_CONFIGURED`` and the Commons leg still answers.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

import httpx

from app.integrations.china import amap
from app.integrations.discovery.provider_identity import PROVIDER_USER_AGENT

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
IMAGE_WIDTH = 640

STATUS_PHOTO = "REAL_POI_PHOTO"
STATUS_NO_MEDIA = "NO_MEDIA"
STATUS_UNAVAILABLE = "MEDIA_UNAVAILABLE"
STATUS_NOT_DISPLAYABLE = "MEDIA_NOT_DISPLAYABLE"

# `P18` is Wikidata's "image" property. Named here because a silent change to it would turn every
# answer into NO_MEDIA and look like the provider went quiet.
IMAGE_PROPERTY = "P18"
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

    def as_payload(self) -> dict[str, Any]:
        return {
            "place_id": self.place_id,
            "image_url": self.image_url,
            "thumb_url": self.thumb_url,
            "author": self.author,
            "license": self.license,
            "source_url": self.source_url,
            "provider": self.provider,
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

    def as_payload(self) -> dict[str, Any]:
        return {
            "place_id": self.place_id,
            "status": self.status,
            "reason_code": self.reason_code,
            "media": self.media.as_payload() if self.media else None,
            "provider_readings": [dict(row) for row in self.readings],
            "blocked_itinerary": self.blocked_itinerary,
        }


def identity_matches(label: str, entity_label: str | None, description: str | None,
                     region: str | None) -> bool:
    """Bind or refuse: the label must agree, or the region we were handed must appear in the entity.

    Two arms, because either alone is wrong: label equality only would refuse a mountain whose Wikidata
    label is English while the traveller's POI is Chinese, and region-only matching would accept any
    entity that happens to mention the county.
    """
    wanted = (label or "").strip()
    given = (entity_label or "").strip()
    if wanted and given and wanted == given:
        return True
    text = (description or "").strip().lower()
    region_text = (region or "").strip().lower()
    if not text or not region_text:
        return False
    return wanted.lower() in text or region_text in text


class WikimediaMediaProvider:
    """Wikidata `P18` -> Commons `imageinfo` with the attribution the licence requires."""

    provider_key = "wikimedia-commons"

    def __init__(self, *, client: httpx.AsyncClient) -> None:
        self._client = client

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
        return {
            "files": files,
            "label": next((row.get("value") for row in labels.values() if row.get("value")), None),
            "description": next((row.get("value") for row in descriptions.values()
                                if row.get("value")), None),
        }

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

    async def search(self, *, place_id: str, label: str, region: str | None,
                     wikidata_id: str | None) -> tuple[PlaceMedia | None, dict[str, Any]]:
        started = _stamp()
        try:
            qid = wikidata_id
            entity_label: str | None = None
            description: str | None = None
            if qid is None:
                candidates = await self._search(label)
                if not candidates:
                    return None, {"source": self.provider_key, "attempted": True,
                                  "outcome": "NO_MEDIA", "reason_code": "ENTITY_NOT_FOUND",
                                  "captured_at": started}
                qid = str(candidates[0].get("id") or "")
                entity_label = candidates[0].get("label") or _plain(
                    ((candidates[0].get("display") or {}).get("label") or {}).get("value"))
                description = candidates[0].get("description")
            document = await self._entity(qid)
            files = document["files"]
            # The entity document is the authority here, never the search hit: a fuzzy search returns
            # the label we typed back to us, and trusting it would let any near-miss "prove" itself.
            entity_label = document["label"]
            description = document["description"]
            if not identity_matches(label, entity_label, description, region):
                # The answer is about a different place, so for this POI there is no media.
                return None, {"source": self.provider_key, "attempted": True, "qid": qid,
                              "outcome": "NO_MEDIA", "reason_code": "MEDIA_IDENTITY_UNBOUND",
                              "entity_label": entity_label, "captured_at": started}
            if not files:
                return None, {"source": self.provider_key, "attempted": True, "qid": qid,
                              "outcome": "NO_MEDIA", "reason_code": "PROPERTY_EMPTY",
                              "captured_at": started}
            info = await self._file_info(files[0])
            if not info.get("url"):
                return None, {"source": self.provider_key, "attempted": True, "qid": qid,
                              "outcome": "NO_MEDIA", "reason_code": "FILE_WITHDRAWN",
                              "captured_at": started}
            meta = info.get("extmetadata") or {}
            license_name = _plain(meta.get("LicenseShortName")) or _plain(meta.get("License"))
            media = PlaceMedia(
                place_id=place_id,
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
                       "outcome": STATUS_PHOTO if media.can_show else "NO_MEDIA",
                       "reason_code": None if media.can_show else "LICENCE_UNNAMED",
                       "captured_at": started}
            return (media if media.can_show else None), reading
        except (httpx.HTTPError, ValueError, KeyError, TypeError, json.JSONDecodeError) as failure:
            return None, {"source": self.provider_key, "attempted": True,
                          "outcome": STATUS_UNAVAILABLE + "_" + type(failure).__name__,
                          "captured_at": started}


class AmapPhotosProvider:
    """Amap's `show_fields=photos` answers, kept non-displayable until a licence says otherwise."""

    provider_key = "amap-web-service"

    def __init__(self, *, client: httpx.AsyncClient) -> None:
        self._client = client

    async def search(self, *, place_id: str, label: str, region: str | None,
                     wikidata_id: str | None, amap_poi_id: str | None = None
                     ) -> tuple[PlaceMedia | None, dict[str, Any]]:
        started = _stamp()
        key = amap.web_key()
        if key is None:
            return None, {"source": self.provider_key, "attempted": False,
                          "outcome": "NOT_CONFIGURED",
                          "reason_code": amap.missing_key_reason(), "captured_at": started}
        if not amap_poi_id:
            return None, {"source": self.provider_key, "attempted": False, "outcome": "NO_MEDIA",
                          "reason_code": "PROVIDER_ITEM_ID_MISSING", "captured_at": started}
        try:
            response = await amap.amap_get(self._client, amap.AMAP_BASE_URL + "/v5/place/detail", {
                "key": key, "id": amap_poi_id, "show_fields": "photos"})
            payload = _json_payload(response, "Amap place detail")
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as failure:
            return None, {"source": self.provider_key, "attempted": True,
                          "outcome": STATUS_UNAVAILABLE + "_" + type(failure).__name__,
                          "captured_at": started}
        photos = [row for poi in (payload.get("pois") or []) for row in (poi.get("photos") or [])]
        url = next((str(row.get("url")) for row in photos if row.get("url")), None)
        if url is None:
            return None, {"source": self.provider_key, "attempted": True, "outcome": "NO_MEDIA",
                          "reason_code": "PROVIDER_RETURNED_NO_PHOTO", "captured_at": started}
        # Reported, never handed back as media: the provider does not state a licence for an individual
        # photo and its terms restrict storing it, so `author`/`license` stay None instead of being
        # guessed, and no PlaceMedia is produced for something this product may not display.
        return None, {"source": self.provider_key, "attempted": True, "outcome": "NOT_DISPLAYABLE",
                      "reason_code": "LICENCE_UNNAMED", "photos": len(photos),
                      "image_url_reported": url, "captured_at": started}


def default_sources(*, client: httpx.AsyncClient) -> list[Any]:
    """Commons first: it is the only source here whose licence is stated. Amap answers only with a key."""
    return [WikimediaMediaProvider(client=client), AmapPhotosProvider(client=client)]


async def collect_place_media(
    *,
    place_id: str,
    label: str,
    region: str | None = None,
    wikidata_id: str | None = None,
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
                                  "wikidata_id": wikidata_id}
        if isinstance(source, AmapPhotosProvider):
            # Only the Amap leg can be pointed at a provider item id; the Commons leg resolves identity
            # from the label, and handing it a stray keyword would be a TypeError read as a refusal.
            kwargs["amap_poi_id"] = amap_poi_id
        media, reading = await source.search(**kwargs)
        readings.append(reading)
        if media is not None:
            chosen = media
    if chosen is not None:
        return PlaceMediaResult(place_id=place_id, status=STATUS_PHOTO, media=chosen,
                                readings=tuple(readings))
    # Nothing displayable: say *why*, in the order the traveller's screen cares about. A provider that
    # could not be asked is a weaker statement than one that answered "no", and an unlicenced photo is
    # its own answer -- never fold those three into one blank NO_MEDIA.
    decided = None
    for reading in readings:
        outcome = str(reading.get("outcome") or "")
        if outcome.startswith(STATUS_UNAVAILABLE):
            decided = (outcome, reading.get("reason_code"))
            break
        if outcome == "NOT_DISPLAYABLE" and decided is None:
            decided = (STATUS_NOT_DISPLAYABLE, reading.get("reason_code"))
        if outcome in {"NO_MEDIA", "NOT_CONFIGURED"} and decided is None:
            decided = (STATUS_NO_MEDIA if outcome == "NO_MEDIA" else "NOT_CONFIGURED",
                       reading.get("reason_code"))
    status, reason = decided or (STATUS_NO_MEDIA, "NO_SOURCE_ANSWERED")
    return PlaceMediaResult(place_id=place_id, status=status, media=None, readings=tuple(readings),
                            reason_code=reason)
