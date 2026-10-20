"""Provider-backed source leads that do not require a canonical Place.

`research_place_sources` starts from a server-owned Place.  When Photon,
Nominatim and the city catalogue all answer zero, the Agent has no Place to
start from, and the research loop stops exactly where it should begin.  This
module supplies the missing first step:

    public region + cleaned topic -> URL-bearing, non-authoritative source leads

Two rules are load-bearing:

  * a lead is never a Place.  Nothing here writes `Place`, coordinates or a plan
    item; every row is a `WebObservation` with `authority_status=NON_AUTHORITATIVE`;
  * the public region comes from the signed Journey's structured/declared
    region, never from its random id, custom title or member preferences.

With no configured provider the answer is `SOURCE_DISCOVERY_UNAVAILABLE` and a
named next legal path, not an invented lead.  Classroom mode is the one exception,
and it stays inside that rule: it answers `ESTIMATED` with the query angles a human
would try next and zero leads, never with a fabricated page.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.classroom_mode import (
    AUTHORITY,
    classroom_mode,
    estimated_search_angles,
)
from app.core import config
from app.db.models import Journey, ProviderCall, WebObservation
from app.integrations.ai.responses import DeepSeekResponsesClient, DeepSeekResponsesError
from app.integrations.ai.web_research import WebResearchProvider
from app.integrations.web.public_region import (
    REGION_PENDING,
    build_public_topic_query,
    public_city_label,
    sanitize_public_topic,
)
MAX_LEADS = 5


def provider_availability() -> dict[str, bool]:
    settings = config.settings
    return {
        "web": bool(settings.ai_api_key and settings.deepseek_web_search_enabled),
        "searxng": bool(settings.searxng_url),
    }


def choose_provider(requested: str | None) -> str | None:
    """Resolve `auto` against what this deployment actually configured."""

    available = provider_availability()
    if requested in (None, "", "auto"):
        if available["web"]:
            return "web"
        if available["searxng"]:
            return "searxng"
        return None
    return requested if available.get(requested) else None


def provider_chain(requested: str | None) -> list[str]:
    """The providers worth trying, in order, at most two.

    Issue #37's acceptance line is "first source returns zero and the Agent still
    continues": one provider answering zero or failing is a leg to step on, not a reason
    to hand the difficulty back to the traveler.
    """

    primary = choose_provider(requested)
    if primary is None:
        return []
    chain = [primary]
    other = "searxng" if primary == "web" else "web"
    if provider_availability().get(other):
        chain.append(other)
    return chain


def search_with_fallback(
    session: Session,
    query: str,
    *,
    requested: str | None,
    operation: str,
    request_payload: dict[str, Any],
    limit: int = MAX_LEADS,
) -> tuple[list[Any], str, str | None, list[dict[str, Any]]]:
    """Try each configured provider until one returns leads; audit every call made.

    Returns (drafts, status, reason_code, attempts). One `ProviderCall` row is written per
    attempt -- including the zero-result and failed ones -- so the retry is provable after
    the fact rather than a claim in the response.
    """

    attempts: list[dict[str, Any]] = []
    drafts: list[Any] = []
    status = "SOURCE_DISCOVERY_UNAVAILABLE"
    reason: str | None = "NO_WEB_PROVIDER"
    for provider_key in provider_chain(requested):
        began = time.perf_counter()
        found, provider_status, failure = run_web_search(
            query, provider=provider_key, limit=limit
        )
        elapsed_ms = round((time.perf_counter() - began) * 1000)
        record_provider_call(
            session,
            provider_key="deepseek-web-search" if provider_key == "web" else "searxng",
            operation=operation,
            request_payload={**request_payload, "provider": provider_key, "attempt": len(attempts) + 1},
            status="SUCCESS" if provider_status in {"CAPTURED", "NO_RESULTS"} else "FAILURE",
            latency_ms=elapsed_ms,
            response_payload={"status": provider_status, "count": len(found)},
        )
        attempts.append(
            {
                "provider": provider_key,
                "status": provider_status,
                "count": len(found),
                "elapsed_ms": elapsed_ms,
                **({"reason_code": failure} if failure else {}),
            }
        )
        drafts, status, reason = found, provider_status, failure
        if provider_status == "CAPTURED":
            break
    session.commit()
    return drafts, status, reason, attempts


def run_web_search(
    query: str, *, provider: str, limit: int = MAX_LEADS
) -> tuple[list[Any], str, str | None]:
    """One provider call.  Returns (drafts, status, reason_code)."""

    settings = config.settings
    if provider == "web":
        client = DeepSeekResponsesClient(
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            base_url=settings.deepseek_api_url,
            reasoning_effort="low",
            timeout_seconds=settings.impact_timeout_seconds,
        )
        try:
            drafts = list(WebResearchProvider(client).search(query)[:limit])
        except DeepSeekResponsesError:
            return [], "FAILED_EXTERNAL", "DEEPSEEK_WEB_SEARCH_FAILED"
        return drafts, ("CAPTURED" if drafts else "NO_RESULTS"), None
    if provider == "searxng":
        # Resolve through the module so a deployment (or a test) that replaces the provider
        # class after import is honoured; a direct class reference would silently keep the old one.
        from app.integrations.web import searxng as searxng_module

        provider_client = searxng_module.SearXNGSearchProvider(settings.searxng_url)
        try:
            drafts = list(provider_client.search(query, limit=limit))
        except Exception:
            return [], "FAILED_EXTERNAL", "SEARXNG_FAILED"
        finally:
            provider_client.close()
        return drafts, ("CAPTURED" if drafts else "NO_RESULTS"), None
    return [], "SOURCE_DISCOVERY_UNAVAILABLE", "NO_WEB_PROVIDER"


def record_provider_call(
    session: Session,
    *,
    provider_key: str,
    operation: str,
    request_payload: dict[str, Any],
    status: str,
    latency_ms: int | None,
    response_payload: dict[str, Any] | None = None,
) -> None:
    """Every external call leaves an auditable row, including zero-result calls."""

    import json

    session.add(
        ProviderCall(
            id=str(uuid4()),
            provider_key=provider_key,
            operation=operation,
            request_json=json.dumps(request_payload, ensure_ascii=False, sort_keys=True),
            response_json=(
                json.dumps(response_payload, ensure_ascii=False, sort_keys=True)
                if response_payload is not None
                else None
            ),
            status=status,
            latency_ms=latency_ms,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )


def _fingerprint(query: str, item: Any) -> str:
    return str(getattr(item, "evidence_fingerprint", "")) or hashlib.sha256(
        f"{query}|{item.url}|{item.title}|"
        f"{getattr(item, 'content_excerpt', getattr(item, 'content', ''))}".encode()
    ).hexdigest()


def capture_observations(
    session: Session, journey: Journey, drafts: list[Any], query: str
) -> list[WebObservation]:
    """Store URL-bearing leads once each; nothing here can become a Place."""

    rows: list[WebObservation] = []
    for item in drafts[:MAX_LEADS]:
        fingerprint = _fingerprint(query, item)
        existing = session.scalar(
            select(WebObservation).where(
                WebObservation.journey_id == journey.id,
                WebObservation.evidence_fingerprint == fingerprint,
            )
        )
        if existing is None:
            existing = WebObservation(
                id=str(uuid4()),
                journey_id=journey.id,
                query=item.query,
                url=item.url,
                domain=item.domain,
                title=item.title,
                source_class=getattr(item, "source_class", "OPEN_WEB"),
                provider_key=item.provider_key,
                model_key=getattr(item, "model_key", ""),
                captured_at=item.captured_at,
                evidence_fingerprint=fingerprint,
                content_excerpt=getattr(
                    item, "content_excerpt", getattr(item, "content", "")
                )[:2000],
                authority_status="NON_AUTHORITATIVE",
                created_at=item.captured_at,
            )
            session.add(existing)
        rows.append(existing)
    return rows


def lead_payload(row: WebObservation) -> dict[str, Any]:
    """The model-facing shape.  A lead says what it is and what it cannot do."""

    return {
        "id": row.id,
        "url": row.url,
        "domain": row.domain,
        "title": row.title,
        "provider": row.provider_key,
        "captured_at": row.captured_at,
        "authority_status": row.authority_status,
        "identity_status": "UNVERIFIED",
        "can_promote_to_place": False,
    }


def discover_source_leads(
    session: Session,
    journey: Journey,
    *,
    topic: str,
    provider: str | None,
    limit: int = MAX_LEADS,
) -> dict[str, Any]:
    """Zero-Place research: region + topic -> non-authoritative leads."""

    region = public_city_label(journey)
    if not region:
        pending_region = {
            "label": None,
            "source": "JOURNEY_PUBLIC_REGION",
            "confirmed": False,
        }
        if classroom_mode():
            # A demo Journey has no publicly confirmed city, and inventing one would aim the
            # estimate at the wrong place.  Keep the city unnamed and estimate on the topic.
            cleaned = sanitize_public_topic(topic)
            return {
                "status": "ESTIMATED",
                "region": pending_region,
                "topic": cleaned,
                "query": None,
                "authority": AUTHORITY,
                "estimate": estimated_search_angles(region="(city not confirmed)", topic=cleaned),
                "next_legal_path": (
                    "confirm a public region on this Journey to turn the angles into "
                    "provider-backed leads"
                ),
                "leads": [],
            }
        return {
            "status": REGION_PENDING,
            "reason_code": REGION_PENDING,
            "region": pending_region,
            "next_legal_path": (
                "ask the traveler to confirm a public region on this Journey, or "
                "research a canonical Place with research_place_sources"
            ),
            "authority": "NON_AUTHORITATIVE",
            "leads": [],
        }
    cleaned = sanitize_public_topic(topic)
    query = build_public_topic_query(cleaned, region)
    chosen = choose_provider(provider)
    if chosen is None:
        result: dict[str, Any] = {
            "status": "SOURCE_DISCOVERY_UNAVAILABLE",
            "reason_code": "NO_WEB_PROVIDER",
            "region": {"label": region, "source": "JOURNEY_PUBLIC_REGION", "confirmed": True},
            "topic": cleaned,
            "query": query,
            "provider_availability": provider_availability(),
            "next_legal_path": (
                "configure DeepSeek web search or SearXNG, or use a canonical "
                "Place with research_place_sources"
            ),
            "authority": "NON_AUTHORITATIVE",
            "leads": [],
        }
        if classroom_mode():
            # Nothing to search with: answer with the angles, not with fabricated pages.
            result["status"] = "ESTIMATED"
            result["authority"] = AUTHORITY
            result["estimate"] = estimated_search_angles(region=region, topic=cleaned)
            result["next_legal_path"] = (
                "continue planning with the estimate above, or configure a web provider "
                "to turn the angles into captured source leads"
            )
        return result

    began = time.perf_counter()
    drafts, status, reason, attempts = search_with_fallback(
        session,
        query,
        requested=provider,
        operation="source_lead_discovery",
        request_payload={"query": query, "region": region, "topic": cleaned, "limit": limit},
        limit=limit,
    )
    elapsed_ms = round((time.perf_counter() - began) * 1000)
    rows = capture_observations(session, journey, drafts, query)
    session.commit()
    result: dict[str, Any] = {
        "status": status,
        "region": {"label": region, "source": "JOURNEY_PUBLIC_REGION", "confirmed": True},
        "topic": cleaned,
        "query": query,
        "provider": attempts[-1]["provider"] if attempts else None,
        "attempts": attempts,
        "fallback_used": len(attempts) > 1,
        "elapsed_ms": elapsed_ms,
        "authority": "NON_AUTHORITATIVE",
        "leads": [lead_payload(row) for row in rows],
    }
    if reason:
        result["reason_code"] = reason
    if status == "NO_RESULTS":
        result["next_legal_path"] = (
            "try a different public topic or the other configured provider; zero "
            "results are an observation, not a stop"
        )
    elif status == "FAILED_EXTERNAL":
        result["next_legal_path"] = (
            "try the other configured provider, or continue with stored facts and "
            "ask the traveler to confirm the region"
        )
    if classroom_mode() and status in {"NO_RESULTS", "FAILED_EXTERNAL"}:
        # The provider answered with nothing or with an error: the loop still has to move.
        result["estimate"] = estimated_search_angles(region=region, topic=cleaned)
    return result
