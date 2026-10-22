"""Task-owned source leads -> licensed media, shared by the UI and Agent tool."""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import time
from threading import RLock
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import HTTPException
from sqlalchemy import select

from app.agent.goal_artifacts import goal_research_lead, public_city_label, _validated_osm_reference
from app.db.models import ProviderCall
from app.integrations.china.amap import gcj02_to_wgs84
from app.integrations.discovery.provider_identity import PROVIDER_USER_AGENT
from app.integrations.media.place_media import WikimediaMediaProvider, collect_place_media
from app.integrations.provider_config import trust_environment_for_public_providers

OPERATION = "goal_place_media"
_MEDIA_LOCK = RLock()


def source_lead(task: dict, candidate_id: str) -> dict:
    lead = goal_research_lead(task, candidate_id)
    if lead is None:
        raise HTTPException(404, "PLACE_NOT_IN_GOAL_TASK_SCOPE")
    if lead.get("region_status") == "CONFLICT":
        raise HTTPException(404, "PLACE_NOT_IN_GOAL_TASK_SCOPE")
    return lead


def empty_media(candidate_id: str, status: str, reason: str) -> dict:
    return {"candidate_id": candidate_id, "place_id": candidate_id, "status": status,
            "reason_code": reason, "media": None, "identity_status": "UNBOUND",
            "blocked_itinerary": False}


def _commons_url(value: object, *, image: bool = False) -> bool:
    """Wikimedia's own hosts only -- never a URL a client handed us.

    Images live on two of them: the file itself on ``upload.wikimedia.org`` and the resized version
    Commons' API hands back on ``thumb.wikimedia.org``. Measured 2026-10-22: a 南锣鼓巷 photo arrived
    with a real author, a ``CC BY 2.0`` licence and a valid file page, and the screen still showed the
    neutral placeholder, because the only thing the gate disliked was that Wikimedia's own thumbnail
    host was not the one spelled here. Widening to the second Wikimedia host is not a licence
    weakening: an outside image URL is still refused, as its own test arm shows.
    """
    if not isinstance(value, str):
        return False
    url = urlparse(value)
    allowed = {"upload.wikimedia.org", "thumb.wikimedia.org"} if image else {"commons.wikimedia.org"}
    return url.scheme == "https" and not url.username and url.hostname in allowed


def displayable_media(payload: dict, candidate_id: str) -> dict:
    media = payload.get("media")
    if not isinstance(media, dict):
        return payload
    license_name = str(media.get("license") or "").casefold()
    licensed = bool(re.match(r"^(?:cc[ -]by|cc0|public domain|pdm)", license_name))
    if (media.get("place_id") != candidate_id or not media.get("can_show") or not licensed
            or not media.get("author") or not _commons_url(media.get("source_url"))
            or not _commons_url(media.get("image_url"), image=True)
            or (media.get("thumb_url") and not _commons_url(media["thumb_url"], image=True))):
        return empty_media(candidate_id, "NO_PERMISSION", "ATTRIBUTION_OR_LICENSE_UNAVAILABLE")
    terms = urlparse(str(media.get("terms_url") or ""))
    if terms.scheme != "https" or terms.hostname not in {"creativecommons.org", "www.gnu.org", "gnu.org"}:
        media["terms_url"] = None
    return payload


async def _collect(lead: dict, region: str) -> dict:
    candidate_id = lead["id"]
    point = (lead.get("latitude"), lead.get("longitude"))
    if not all(type(value) in (int, float) and math.isfinite(value) for value in point):
        return empty_media(candidate_id, "NO_IMAGE", "SOURCE_LOCATION_UNAVAILABLE")
    if lead.get("coordinate_system") == "GCJ02":
        point = gcj02_to_wgs84(*point)
    elif lead.get("coordinate_system", "WGS84") != "WGS84":
        return empty_media(candidate_id, "NO_IMAGE", "SOURCE_LOCATION_UNAVAILABLE")
    # Measured on this machine with the only working route to Wikimedia: a legitimate chain answers in
    # about two seconds per hop, and the stored receipts show two calls dying at 3.1 s and 5.0 s --
    # the second one exactly at the old five-second budget, so the traveller's screen simply had no
    # picture to show. The budget is per hop, and the whole chain is still bounded by this loop.
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=False,
            trust_env=trust_environment_for_public_providers()) as client:
        qid = None
        reference = _validated_osm_reference(candidate_id, lead.get("provider"), lead.get("source_url"))
        if reference:
            # Only a stored provider object can address this fixed OSM host.
            kind, osm_id = reference.rsplit("/", 2)[-2:]
            reply = await client.get(f"https://www.openstreetmap.org/api/0.6/{kind}/{osm_id}.json",
                headers={"User-Agent": PROVIDER_USER_AGENT})
            reply.raise_for_status()
            element = next((item for item in reply.json().get("elements", [])
                if str(item.get("id")) == osm_id and item.get("type") == kind), None)
            if element:
                value = str((element.get("tags") or {}).get("wikidata") or "")
                if re.fullmatch(r"Q[1-9][0-9]*", value):
                    qid = value
        provider = WikimediaMediaProvider(client=client, source_point=point)
        result = await collect_place_media(place_id=candidate_id, label=lead["name"], region=region,
            wikidata_id=qid, provider_object_id=candidate_id, sources=[provider], client=client)
        payload = result.as_payload()
        if str(payload.get("status")).startswith("UNAVAILABLE"):
            payload["status"] = "UNAVAILABLE"
        payload.update(candidate_id=candidate_id, place_name=lead["name"],
            source_reference=reference or lead.get("source_url"), source_wikidata_id=qid)
        # Provider internals are not part of the mobile contract.
        payload.pop("provider_readings", None)
        return displayable_media(payload, candidate_id)


def _read_source_media(session, journey, task: dict, task_id: str, candidate_id: str) -> dict:
    lead = source_lead(task, candidate_id)
    if not (task.get("consent") or {}).get("online_research"):
        return empty_media(candidate_id, "NO_PERMISSION", "ONLINE_CONSENT_REQUIRED")
    identity = {key: lead.get(key) for key in ("id", "name", "provider", "provider_object_id",
        "latitude", "longitude", "coordinate_system", "source_url", "captured_at")}
    request_key = json.dumps({"journey_id": journey.id, "owner": journey.traveler_id,
        "task_id": task_id, "source": identity}, ensure_ascii=False, sort_keys=True)
    cached = session.scalar(select(ProviderCall).where(ProviderCall.operation == OPERATION,
        ProviderCall.request_json == request_key).order_by(ProviderCall.created_at.desc()).limit(1))
    if cached and cached.response_json:
        payload = json.loads(cached.response_json)
        ttl = 3600 if payload.get("media") else 600
        if datetime.fromisoformat(cached.created_at) > datetime.now(timezone.utc) - timedelta(seconds=ttl):
            return {**payload, "cache_hit": True}
    started = time.monotonic()
    try:
        payload = asyncio.run(asyncio.wait_for(_collect(lead, public_city_label(journey, session)), timeout=10))
    except (httpx.HTTPError, TimeoutError, ValueError, TypeError, KeyError):
        payload = empty_media(candidate_id, "UNAVAILABLE", "MEDIA_SOURCE_UNAVAILABLE")
    payload.update(candidate_id=candidate_id, journey_id=journey.id, task_id=task_id,
        captured_at=datetime.now(timezone.utc).isoformat(), source_fingerprint=hashlib.sha256(request_key.encode()).hexdigest(), cache_hit=False)
    session.add(ProviderCall(id=str(uuid4()), provider_key="wikimedia-commons", operation=OPERATION,
        request_json=request_key, response_json=json.dumps(payload, ensure_ascii=False),
        status="FAILURE" if payload.get("status", "").startswith("UNAVAILABLE") else "SUCCESS",
        latency_ms=round((time.monotonic()-started)*1000), created_at=payload["captured_at"]))
    session.flush()
    return payload


def read_source_media(session, journey, task: dict, task_id: str, candidate_id: str) -> dict:
    # Commit each media receipt before another UI/tool reader can miss its cache.
    with _MEDIA_LOCK:
        result = _read_source_media(session, journey, task, task_id, candidate_id)
        result.update(journey_id=journey.id, task_id=task_id, candidate_id=candidate_id)
        session.commit()
        return result


def media_tool_definition() -> dict:
    return {"type": "function", "function": {"name": "research_place_media",
        "description": "Find a licensed source-bound photo for an existing task place. Reuses cached media; missing images never block saving the itinerary.",
        "parameters": {"type": "object", "properties": {"place_id": {"type": "string"}},
            "required": ["place_id"], "additionalProperties": False}}}
