"""Acquire source-linked Place facts without weakening planning authority.

The provider observation is deliberately separate from planning.  A current
unknown observation replaces an older positive observation, search snippets
remain candidates, and a provider-tag website is fetched only after its URL
and every redirect have passed the public-network boundary.
"""

from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
from datetime import date, datetime, timezone
from typing import Any, Mapping
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Journey, Place
from app.integrations.discovery.real_city import (
    OVERPASS_MIRRORS,
    cost_evidence_from_tags,
    normalize_opening_hours,
)
from app.integrations.provider_config import trust_environment_for_public_providers
from app.integrations.web.searxng import SearXNGSearchProvider


KNOWN_COST_STATUSES = frozenset({"KNOWN", "VERIFIED_PROVIDER"})
_JSON_LD_SCRIPT = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_SCHEMA_DAYS = {
    "monday": "Mo", "tuesday": "Tu", "wednesday": "We", "thursday": "Th",
    "friday": "Fr", "saturday": "Sa", "sunday": "Su",
}
_BLOCKED_HOSTNAMES = {
    "localhost", "localhost.localdomain", "metadata", "metadata.google.internal",
    "instance-data.ec2.internal",
}
_OFFICIAL_SOURCE_CLASSES = frozenset(
    {
        "OFFICIAL_WEB",
        "OFFICIAL_OPERATOR",
        "OFFICIAL_TICKETING",
        "MUNICIPAL_AUTHORITY",
    }
)


def _element_ref(place: Place) -> tuple[str, str] | None:
    external = str(place.external_id or "")
    if not external.startswith("overpass:"):
        return None
    kind, separator, number = external.removeprefix("overpass:").partition("/")
    if not separator or kind not in {"node", "way", "relation"} or not number.isdigit():
        return None
    return kind, number


def _query(refs: list[tuple[str, str]]) -> str:
    clauses = ";".join(f"{kind}({number})" for kind, number in refs)
    return f"[out:json][timeout:20];({clauses};);out tags center;"


def _overpass_endpoints() -> list[str]:
    configured = settings.overpass_url.rstrip("/")
    if not configured.endswith("/interpreter"):
        configured = f"{configured}/interpreter" if configured.endswith("/api") else configured
    return [configured, *[endpoint for endpoint in OVERPASS_MIRRORS if endpoint != configured]]


def _acquire_overpass_payload(
    client: httpx.Client,
    refs: list[tuple[str, str]],
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    """Fetch one exact-entity question through bounded public mirrors.

    A successful HTTP response, including an empty ``elements`` list, is the
    provider's answer and ends rotation.  Only transport/status/payload
    failures move to the next endpoint.
    """

    attempts: list[dict[str, Any]] = []
    last_error: Exception | None = None
    for endpoint in _overpass_endpoints():
        started = datetime.now(timezone.utc)
        try:
            response = client.post(
                endpoint,
                data={"data": _query(refs)},
                headers={"User-Agent": "CityNexus/real-trip-facts"},
            )
            status = response.status_code
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
                raise ValueError("OVERPASS_INVALID_PAYLOAD")
            attempts.append(
                {
                    "endpoint": endpoint,
                    "answered": True,
                    "http_status": status,
                    "elapsed_ms": round((datetime.now(timezone.utc) - started).total_seconds() * 1000.0, 1),
                    "elements": len(payload["elements"]),
                }
            )
            return payload, endpoint, attempts
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            attempts.append(
                {
                    "endpoint": endpoint,
                    "answered": False,
                    "http_status": getattr(getattr(exc, "response", None), "status_code", None),
                    "elapsed_ms": round((datetime.now(timezone.utc) - started).total_seconds() * 1000.0, 1),
                    "error": f"{type(exc).__name__}: {str(exc)[:160]}",
                }
            )
            last_error = exc

    error = last_error or RuntimeError("NO_PROVIDER_ATTEMPTED")
    try:
        error.provider_attempts = attempts  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - frozen exception types refuse attributes
        pass
    raise error


def _nominatim_ids(refs: list[tuple[str, str]]) -> str:
    return ",".join(f"{kind[0].upper()}{number}" for kind, number in refs)


def _resolved_public_addresses(hostname: str) -> set[ipaddress._BaseAddress]:
    lowered = hostname.rstrip(".").casefold()
    if lowered in _BLOCKED_HOSTNAMES or lowered.endswith((".internal", ".local")):
        raise ValueError("OFFICIAL_SOURCE_PRIVATE_TARGET")
    try:
        return {ipaddress.ip_address(hostname)}
    except ValueError:
        pass
    try:
        rows = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("OFFICIAL_SOURCE_DNS_UNAVAILABLE") from exc
    addresses = {ipaddress.ip_address(row[4][0]) for row in rows if row[4]}
    if not addresses:
        raise ValueError("OFFICIAL_SOURCE_DNS_EMPTY")
    return addresses


def _validate_public_http_url(url: str, *, base_url: str | None = None) -> str:
    candidate = urljoin(base_url or "", str(url).strip())
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("OFFICIAL_SOURCE_URL_SCHEME_REJECTED")
    if parsed.username or parsed.password:
        raise ValueError("OFFICIAL_SOURCE_URL_CREDENTIALS_REJECTED")
    addresses = _resolved_public_addresses(parsed.hostname)
    for address in addresses:
        if (
            address.is_private or address.is_loopback or address.is_link_local
            or address.is_multicast or address.is_reserved or address.is_unspecified
        ):
            raise ValueError("OFFICIAL_SOURCE_PRIVATE_TARGET")
    return candidate


def _safe_get(client: httpx.Client, url: str, *, retrieved_at: str) -> tuple[httpx.Response, str]:
    """Fetch an official page while validating the target before every redirect."""

    current = _validate_public_http_url(url)
    for _ in range(4):
        response = client.get(
            current,
            headers={"User-Agent": "CityNexus/real-trip-facts"},
            follow_redirects=False,
        )
        if 300 <= response.status_code < 400:
            location = response.headers.get("location")
            if not location:
                raise ValueError("OFFICIAL_SOURCE_REDIRECT_WITHOUT_LOCATION")
            current = _validate_public_http_url(location, base_url=current)
            continue
        response.raise_for_status()
        return response, current
    raise ValueError("OFFICIAL_SOURCE_REDIRECT_LIMIT")


def _nominatim_lookup(
    client: httpx.Client, refs: list[tuple[str, str]]
) -> tuple[dict[tuple[str, str], dict[str, Any]], str]:
    endpoint = f"{settings.nominatim_url.rstrip('/')}/lookup"
    response = client.get(
        endpoint,
        params={"osm_ids": _nominatim_ids(refs), "format": "jsonv2", "extratags": 1, "namedetails": 1},
        headers={"User-Agent": "CityNexus/real-trip-facts"},
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list):
        raise ValueError("NOMINATIM_LOOKUP_INVALID_PAYLOAD")
    return {
        (str(row.get("osm_type")), str(row.get("osm_id"))): row
        for row in rows
        if isinstance(row, dict) and row.get("osm_type") and row.get("osm_id")
    }, endpoint


def _json_ld_nodes(body: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for raw in _JSON_LD_SCRIPT.findall(body):
        try:
            payload = json.loads(html.unescape(raw).strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            graph = candidate.get("@graph")
            if isinstance(graph, list):
                nodes.extend(item for item in graph if isinstance(item, dict))
            nodes.append(candidate)
    return nodes


def _official_opening(nodes: list[dict[str, Any]], source_url: str) -> dict[str, Any]:
    raw_values: list[str] = []
    for node in nodes:
        raw = node.get("openingHours")
        if isinstance(raw, str):
            raw_values.append(raw)
        elif isinstance(raw, list):
            raw_values.extend(str(item) for item in raw if isinstance(item, str))
        specifications = node.get("openingHoursSpecification")
        if isinstance(specifications, dict):
            specifications = [specifications]
        if not isinstance(specifications, list):
            continue
        for specification in specifications:
            if not isinstance(specification, dict):
                continue
            opens, closes = str(specification.get("opens") or ""), str(specification.get("closes") or "")
            if not opens or not closes:
                continue
            days = specification.get("dayOfWeek") or ["*"]
            if isinstance(days, str):
                days = [days]
            short_days = [_SCHEMA_DAYS.get(str(day).rsplit("/", 1)[-1].casefold(), "*") for day in days]
            prefix = ",".join(short_days)
            raw_values.append(f"{prefix} {opens}-{closes}" if prefix != "*" else f"{opens}-{closes}")
    for raw in raw_values:
        normalized = normalize_opening_hours(raw)
        if normalized.get("status") == "NORMALIZED_VALID":
            normalized.update({"status": "OFFICIAL_WEB_VERIFIED", "source": "official_web", "source_url": source_url})
            return normalized
    return {"status": "UNKNOWN", "raw": None, "intervals": []}


def _official_cost(nodes: list[dict[str, Any]], source_url: str) -> dict[str, Any]:
    for node in nodes:
        if node.get("isAccessibleForFree") is True:
            return {"status": "VERIFIED_PROVIDER", "amount_minor": 0, "currency": "CNY", "source": "official_web", "source_url": source_url}
        offers = node.get("offers")
        if isinstance(offers, dict):
            offers = [offers]
        for offer in offers if isinstance(offers, list) else []:
            if not isinstance(offer, dict) or offer.get("price") is None:
                continue
            try:
                amount = round(float(str(offer["price"]).replace(",", "")) * 100)
            except (TypeError, ValueError):
                continue
            return {
                "status": "VERIFIED_PROVIDER", "amount_minor": amount,
                "currency": str(offer.get("priceCurrency") or "CNY").upper(),
                "source": "official_web", "source_url": source_url,
            }
    return {"status": "UNKNOWN", "amount_minor": None, "currency": "CNY", "source": "official_web", "source_url": source_url}


def _official_source_url(tags: dict[str, Any]) -> str | None:
    for key in ("website", "contact:website", "url"):
        value = str(tags.get(key) or "").strip()
        if value.startswith(("https://", "http://")):
            return value
    return None



def _fact_source_binding(place: Place, metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Return an operator-approved source bound to this exact provider entity."""

    binding = metadata.get("fact_source_binding")
    if not isinstance(binding, dict):
        return None
    provider_entity = str(binding.get("provider_entity") or "")
    source_class = str(binding.get("source_class") or "").upper()
    source_url = str(binding.get("source_url") or "").strip()
    identity = binding.get("identity_basis")
    if provider_entity != str(place.external_id or ""):
        return None
    if source_class not in _OFFICIAL_SOURCE_CLASSES or not source_url.startswith(("http://", "https://")):
        return None
    if not isinstance(identity, dict) or identity.get("matched_provider_entity") is not True:
        return None
    if str(identity.get("provider_entity") or provider_entity) != provider_entity:
        return None
    return {
        "provider_entity": provider_entity,
        "source_url": source_url,
        "source_class": source_class,
        "identity_basis": identity,
        "approval": str(binding.get("approval") or "OPERATOR_VERIFIED"),
    }


def _requested_fact_source_binding(
    place: Place, requested: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    """Turn an operator-supplied URL into a binding for this exact provider entity."""

    if not isinstance(requested, Mapping):
        return None
    candidate = {
        "fact_source_binding": {
            "provider_entity": str(place.external_id or ""),
            "source_url": str(requested.get("source_url") or "").strip(),
            "source_class": str(requested.get("source_class") or "OFFICIAL_WEB").upper(),
            "identity_basis": {
                "matched_provider_entity": True,
                "provider_entity": str(place.external_id or ""),
                "basis": "OPERATOR_CONFIRMED_EXACT_PROVIDER_ENTITY",
            },
            "approval": "OPERATOR_VERIFIED",
        }
    }
    return _fact_source_binding(place, candidate)


def _visible_html_text(body: str) -> str:
    without_non_content = re.sub(
        r"<(script|style|noscript|template)\b[^>]*>.*?</\1>",
        " ",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r"<!--.*?-->", " ", without_non_content, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _reference_date(reference_at: str | datetime | date | None) -> date | None:
    if isinstance(reference_at, datetime):
        return reference_at.date()
    if isinstance(reference_at, date):
        return reference_at
    if not reference_at:
        return None
    try:
        return datetime.fromisoformat(str(reference_at).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _period_text(value: str) -> str:
    return str(value).translate(
        str.maketrans(
            {
                "\u3001": ",",
                "\uff0c": ",",
                "\uff1b": ";",
                "\uff08": "(",
                "\uff09": ")",
            }
        )
    )


_MONTH_TOKEN = re.compile(
    r"(?P<month>\d{1,2})\s*"
    + re.escape("\u6708")
    + r"(?:\s*(?P<day>\d{1,2})\s*"
    + re.escape("\u65e5")
    + r"?)?"
)


def _period_matches(period: str, reference_at: str | datetime | date | None) -> bool:
    reference = _reference_date(reference_at)
    period = _period_text(period)
    if reference is None or not period.strip():
        return True
    for segment in re.split(r"[,;]", period):
        tokens = list(_MONTH_TOKEN.finditer(segment))
        if not tokens:
            continue
        first = tokens[0]
        start_month = int(first.group("month"))
        start_day = int(first.group("day") or 1)
        range_chars = re.escape("-" + "\u2013" + "\u2014" + "\u81f3" + "\u5230")
        if len(tokens) == 1 or not re.search("[" + range_chars + "]", segment):
            if reference.month == start_month:
                return True
            continue
        last = tokens[-1]
        end_month = int(last.group("month"))
        end_day = int(last.group("day") or 31)
        start_value = (start_month, start_day)
        end_value = (end_month, end_day)
        current_value = (reference.month, reference.day)
        if "\u6b21\u5e74" in segment or end_value < start_value:
            if current_value >= start_value or current_value <= end_value:
                return True
        elif start_value <= current_value <= end_value:
            return True
    return False


def _lotsmall_order_notice_opening(
    order_notice: str,
    source_url: str,
    *,
    reference_at: str | datetime | date | None,
) -> dict[str, Any]:
    """Choose a date-bound interval from Lotsmall's exact provider notice."""

    text = html.unescape(str(order_notice or "")).replace("\xa0", " ")
    period = (
        r"(?P<period>\d{1,2}\s*月\s*\d{1,2}\s*日\s*[-–—至到]\s*"
        r"(?:次年\s*)?\d{1,2}\s*月\s*(?:\d{1,2}\s*日|底))"
    )
    pattern = re.compile(
        period
        + r"\s*[:：]\s*(?P<open>\d{1,2}:\d{2})[^；。]*?"
        + r"(?P<close>\d{1,2}:\d{2})\s*闭园"
    )
    seasonal: list[dict[str, Any]] = []
    for match in pattern.finditer(text):
        normalized = normalize_opening_hours(
            f"{_clock_value(match.group('open'))}-{_clock_value(match.group('close'))}"
        )
        if normalized.get("status") != "NORMALIZED_VALID":
            continue
        seasonal.append(
            {
                "period": _period_text(match.group("period") or "").strip(),
                "open": normalized["open"],
                "close": normalized["close"],
            }
        )
    if not seasonal:
        return {"status": "UNKNOWN", "raw": text[:4000], "intervals": []}
    # An empty period is the fallback/default.  Prefer an explicitly dated
    # period when it matches, otherwise retain the first (primary) range. This
    # keeps a facility's 09:00-17:00 opening window ahead of later tea-room
    # booking ranges such as 09:00-12:00.
    chosen = next(
        (
            item
            for item in seasonal
            if item["period"].strip()
            and _period_matches(item["period"], reference_at)
        ),
        seasonal[0],
    )
    normalized = normalize_opening_hours(f"{chosen['open']}-{chosen['close']}")
    normalized.update(
        {
            "status": "OFFICIAL_WEB_VERIFIED",
            "source": "official_web",
            "source_url": source_url,
            "raw": text[:4000],
            "seasonal_periods": seasonal,
        }
    )
    return normalized


def _clock_value(value: str) -> str:
    text = str(value).strip()
    if ":" not in text:
        return f"{int(text):02d}:00"
    hour, minute = text.split(":", 1)
    return f"{int(hour):02d}:{int(minute):02d}"


def _plain_text_opening(
    text: str,
    source_url: str,
    *,
    reference_at: str | datetime | date | None,
) -> dict[str, Any]:
    label_pattern = (
        "(?:"
        + "\u5f00\u653e\u65f6\u95f4"
        + "|"
        + "\u8425\u4e1a\u65f6\u95f4"
        + "|\u958b\u9928\u6642\u9593"
        + "|\u958b\u653e\u6642\u9593"
        + "|\u5229\u7528\u6642\u9593"
        + "|\u55b6\u696d\u6642\u9593"
        + "|\u958b\u5712\u6642\u9593|\u6642\u9593"
        + r"|opening\s+hours?|hours?)"
        + r"\s*["
        + re.escape(":\uFF1A")
        + r"]?"
    )
    label = re.search(label_pattern, text, re.IGNORECASE)
    if not label:
        return {"status": "UNKNOWN", "raw": None, "intervals": []}
    excerpt = text[label.end() : label.end() + 260].translate(
        str.maketrans({"\uff08": "(", "\uff09": ")", "\uff1a": ":"})
    )
    excerpt = re.sub(r"(\d{1,2})時(\d{2})分", r"\1:\2", excerpt)
    if re.search("\u5168\u5929\u5f00\u653e" + r"|all\s*day|24\s*hours?", excerpt, re.IGNORECASE):
        return {
            "status": "OFFICIAL_WEB_VERIFIED",
            "raw": excerpt,
            "open": "00:00",
            "close": "24:00",
            "always_available": True,
            "intervals": [{"open": "00:00", "close": "24:00"}],
            "source": "official_web",
            "source_url": source_url,
        }
    range_pattern = re.compile(
        r"(?P<open>\d{1,2}(?::\d{2})?)\s*["
        + re.escape("-\u2013\u2014\uff5e\u301c")
        + r"]\s*(?P<close>\d{1,2}(?::\d{2})?)"
        + r"\s*(?:\(\s*(?P<period>[^)]{1,80})\))?"
    )
    seasonal: list[dict[str, Any]] = []
    for match in range_pattern.finditer(excerpt):
        normalized = normalize_opening_hours(
            f"{_clock_value(match.group('open'))}-{_clock_value(match.group('close'))}"
        )
        if normalized.get("status") != "NORMALIZED_VALID":
            continue
        seasonal.append(
            {
                "period": _period_text(match.group("period") or "").strip(),
                "open": normalized["open"],
                "close": normalized["close"],
            }
        )
    if not seasonal:
        return {"status": "UNKNOWN", "raw": excerpt, "intervals": []}
    chosen = next(
        (item for item in seasonal if _period_matches(item["period"], reference_at)),
        seasonal[0],
    )
    normalized = normalize_opening_hours(f"{chosen['open']}-{chosen['close']}")
    normalized.update(
        {
            "status": "OFFICIAL_WEB_VERIFIED",
            "source": "official_web",
            "source_url": source_url,
            "raw": excerpt,
            "seasonal_periods": seasonal,
        }
    )
    return normalized


def _plain_text_cost(
    text: str,
    source_url: str,
    *,
    reference_at: str | datetime | date | None,
) -> dict[str, Any]:
    label_pattern = (
        "(?:"
        + "\u4ef7" + r"\s*" + "\u683c"
        + "|"
        + "\u7968" + r"\s*" + "\u4ef7"
        + "|"
        + "\u95e8" + r"\s*" + "\u7968" + r"(?:\s*" + "\u4ef7" + r"\s*" + "\u683c)?"
        + "|\u5165\u9928\u6599"
        + "|\u5165\u5834\u6599"
        + "|\u5165\u5712\u6599|\u62dd\u89b3\u6599"
        + "|(?<!利用)料金"
        + r"|admission\s+fee|entrance\s+fee|ticket)"
        + r"\s*["
        + re.escape(":\uFF1A")
        + r"]?"
    )
    label = re.search(label_pattern, text, re.IGNORECASE)
    if not label:
        return {
            "status": "UNKNOWN",
            "amount_minor": None,
            "currency": "CNY",
            "source": "official_web",
            "source_url": source_url,
        }
    excerpt = text[label.end() : label.end() + 300]
    next_label = re.search(
        "\u5f00\u653e\u65f6\u95f4|\u8425\u4e1a\u65f6\u95f4|\u7535\u8bdd|\u5730\u5740|\u7b80\u4ecb"
        + r"|opening\s+hours?|hours?|address",
        excerpt,
        re.IGNORECASE,
    )
    if next_label:
        excerpt = excerpt[: next_label.start()]
    excerpt = excerpt.translate(
        str.maketrans({"\uff08": "(", "\uff09": ")"})
    )
    if re.search("\u514d\u8d39|\u514d\u8cbb|\u7121\u6599" + r"|free", excerpt, re.IGNORECASE):
        return {
            "status": "VERIFIED_PROVIDER",
            "amount_minor": 0,
            "currency": "CNY",
            "source": "official_web",
            "source_url": source_url,
            "raw": excerpt,
        }
    price_pattern = re.compile(
        r"(?P<amount>\d+(?:\.\d{1,2})?)\s*(?P<currency>"
        + re.escape("\u5143")
        + r"|CNY|RMB|"
        + re.escape("\u00a5")
        + "|円|JPY"
        + r")\s*(?:\(\s*(?P<period>[^)]{1,100})\))?",
        re.IGNORECASE,
    )
    seasonal: list[dict[str, Any]] = []
    for match in price_pattern.finditer(excerpt):
        raw_currency = (match.group("currency") or "CNY").upper()
        currency = "JPY" if raw_currency == "円" else "CNY" if raw_currency in {"\u5143", "RMB", "\u00a5"} else raw_currency
        seasonal.append(
            {
                "period": _period_text(match.group("period") or "").strip(),
                "amount_minor": round(float(match.group("amount")) * 100),
                "currency": currency,
            }
        )
    if not seasonal:
        return {
            "status": "UNKNOWN",
            "amount_minor": None,
            "currency": "CNY",
            "source": "official_web",
            "source_url": source_url,
            "raw": excerpt,
        }
    chosen = next(
        (item for item in seasonal if _period_matches(item["period"], reference_at)),
        seasonal[0],
    )
    return {
        "status": "VERIFIED_PROVIDER",
        "amount_minor": chosen["amount_minor"],
        "currency": chosen["currency"],
        "source": "official_web",
        "source_url": source_url,
        "raw": excerpt,
        "seasonal_amounts": seasonal,
    }


def _lotsmall_bound_facts(
    client: httpx.Client,
    final_url: str,
    *,
    retrieved_at: str,
    reference_at: str | datetime | date | None,
    source_binding: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Read facts from the exact public Lotsmall ticket entity in a URL binding.

    The website tag is accepted only after the exact provider entity was returned
    by Nominatim/Overpass and the public ticket API echoes the same product id,
    product code, and merchant id.  A same-name result without those exact ids is
    not eligible for promotion.
    """

    parsed = urlparse(final_url)
    if parsed.hostname != "wap.lotsmall.cn" or parsed.path != "/vue/detail/ticket":
        return None
    if not source_binding or (source_binding.get("identity_basis") or {}).get("matched_provider_entity") is not True:
        return None
    query = parse_qs(parsed.query)
    product_id = str((query.get("id") or [""])[0]).strip()
    product_code = str((query.get("productCode") or [""])[0]).strip()
    merchant_id = str((query.get("m_id") or [""])[0]).strip()
    if not product_id.isdigit() or not product_code or not merchant_id.isdigit():
        return None

    api_root = "https://wap.lotsmall.cn/bff"
    detail_url = api_root + "/merchant/api/merchantParkInfo/merchantParkInfo?" + urlencode(
        {"merchantParkInfoId": product_id, "wayType": "1", "merchantInfoId": merchant_id}
    )
    detail_response, detail_source = _safe_get(client, detail_url, retrieved_at=retrieved_at)
    detail_payload = detail_response.json()
    detail = detail_payload.get("data") if isinstance(detail_payload, dict) else None
    if not isinstance(detail, dict):
        return None
    if (
        str(detail.get("id") or "") != product_id
        or str(detail.get("productCode") or "") != product_code
        or str(detail.get("merchantInfoId") or "") != merchant_id
    ):
        return None

    reference_date = _reference_date(reference_at) or date.today()
    grid_url = api_root + "/merchant/api/merchantParkTicketGridNew?" + urlencode(
        {
            "currPage": "1",
            "pageSize": "50",
            "playDate": reference_date.isoformat(),
            "businessType": "park",
            "merchantParkInfoId": product_id,
            "merchantInfoId": merchant_id,
        }
    )
    grid_response, grid_source = _safe_get(client, grid_url, retrieved_at=retrieved_at)
    grid_payload = grid_response.json()
    groups = grid_payload.get("data") if isinstance(grid_payload, dict) else None
    if not isinstance(groups, list):
        return None

    adult_ticket: dict[str, Any] | None = None
    for group in groups:
        if not isinstance(group, dict):
            continue
        label = str(group.get("labelValue") or "")
        for ticket in group.get("ticketList") or []:
            if not isinstance(ticket, dict):
                continue
            if (
                str(ticket.get("merchantParkInfoId") or "") != product_id
                or str(ticket.get("merchantInfoId") or "") != merchant_id
                or (str(ticket.get("saleStatus") or "").upper() not in {"T", "TRUE"})
                or ticket.get("buyDateAllow") is False
            ):
                continue
            model_name = str(ticket.get("modelName") or "")
            if label != "成人票" and "成人票" not in model_name:
                continue
            amount = ticket.get("price")
            if not isinstance(amount, (int, float)):
                amount = ticket.get("merchantLinePrice")
            if not isinstance(amount, (int, float)):
                continue
            adult_ticket = {"label": label, **ticket, "amount": amount}
            break
        if adult_ticket:
            break

    opening = _lotsmall_order_notice_opening(
        str(detail.get("orderNotice") or ""),
        final_url,
        reference_at=reference_at,
    )
    open_time = str(detail.get("openTime") or "").strip()
    close_time = str(detail.get("endTime") or "").strip()
    if opening.get("status") == "UNKNOWN" and open_time and close_time:
        normalized = normalize_opening_hours(f"{open_time}-{close_time}")
        if normalized.get("status") == "NORMALIZED_VALID":
            opening = normalized
    if opening.get("status") != "UNKNOWN":
        opening = {
            **opening,
            "status": "OFFICIAL_WEB_VERIFIED",
            "source": "official_web",
            "source_url": final_url,
            "source_api_url": detail_source,
            "provider_product_id": product_id,
            "provider_product_code": product_code,
            "raw": opening.get("raw") or str(detail.get("orderNotice") or "")[:4000],
        }

    cost = {
        "status": "UNKNOWN",
        "amount_minor": None,
        "currency": "CNY",
        "source": "official_web",
        "source_url": final_url,
    }
    if adult_ticket is not None:
        cost = {
            "status": "VERIFIED_PROVIDER",
            "amount_minor": round(float(adult_ticket["amount"]) * 100),
            "currency": "CNY",
            "source": "official_web",
            "source_url": final_url,
            "source_api_url": grid_source,
            "provider_product_id": product_id,
            "provider_product_code": product_code,
            "provider_ticket_id": str(adult_ticket.get("parkTicketId") or adult_ticket.get("id") or ""),
            "provider_model_code": str(adult_ticket.get("modelCode") or ""),
            "raw": str(adult_ticket.get("modelName") or adult_ticket.get("label") or ""),
        }

    return {
        "provider": "official_web",
        "source": final_url,
        "retrieved_at": retrieved_at,
        "status": "ACQUIRED" if opening["status"] != "UNKNOWN" or cost["status"] != "UNKNOWN" else "NO_STRUCTURED_FACTS",
        "opening_hours": opening,
        "cost_evidence": cost,
        "source_binding": source_binding,
        "provider_identity": {
            "provider_entity": source_binding.get("provider_entity"),
            "matched_provider_entity": True,
            "merchant_info_id": merchant_id,
            "merchant_park_info_id": product_id,
            "product_code": product_code,
            "detail_api_url": detail_source,
            "ticket_grid_api_url": grid_source,
            "reference_date": reference_date.isoformat(),
        },
    }


def _official_web_facts(
    client: httpx.Client,
    source_url: str,
    *,
    retrieved_at: str,
    reference_at: str | datetime | date | None = None,
    source_binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response, final_url = _safe_get(client, source_url, retrieved_at=retrieved_at)
    bound = _lotsmall_bound_facts(
        client,
        final_url,
        retrieved_at=retrieved_at,
        reference_at=reference_at,
        source_binding=source_binding,
    )
    if bound is not None:
        return bound
    body = response.text[:1_000_000]
    nodes = _json_ld_nodes(body)
    opening = _official_opening(nodes, final_url)
    cost = _official_cost(nodes, final_url)
    visible_text = _visible_html_text(body)
    if opening.get("status") == "UNKNOWN":
        opening = _plain_text_opening(visible_text, final_url, reference_at=reference_at)
    if cost.get("status") == "UNKNOWN":
        cost = _plain_text_cost(visible_text, final_url, reference_at=reference_at)
    status = "ACQUIRED" if opening.get("status") != "UNKNOWN" or cost.get("status") != "UNKNOWN" else "NO_STRUCTURED_FACTS"
    return {
        "provider": "official_web",
        "source": final_url,
        "retrieved_at": retrieved_at,
        "status": status,
        "opening_hours": opening,
        "cost_evidence": cost,
        "source_binding": source_binding,
    }


def _search_fact_candidates(
    client: httpx.Client,
    place: Place,
    journey: Journey,
    *,
    retrieved_at: str,
    nominatim_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect sourceful search leads without promoting them to Place truth."""

    unknown_opening = {"status": "UNKNOWN", "raw": None, "intervals": []}
    unknown_cost = {
        "status": "UNKNOWN",
        "amount_minor": None,
        "currency": "CNY",
        "source": "searxng",
    }
    if not settings.searxng_url:
        return {
            "provider": "searxng",
            "status": "UNCONFIGURED",
            "attempted": False,
            "observations": [],
            "opening_hours": unknown_opening,
            "cost_evidence": unknown_cost,
        }

    names: list[str] = [str(place.name).strip()]
    row = nominatim_row or {}
    display_name = str(row.get("display_name") or "").split(",", 1)[0].strip()
    if display_name:
        names.append(display_name)
    namedetails = row.get("namedetails")
    if isinstance(namedetails, dict):
        for key in ("name", "name:zh", "official_name", "official_name:zh"):
            value = str(namedetails.get(key) or "").strip()
            if value:
                names.append(value)
    public_names = list(dict.fromkeys(name for name in names if name))
    ref = _element_ref(place)
    identity = f"{ref[0]}/{ref[1]}" if ref else ""
    identity_terms = [f'"{name}"' for name in public_names]
    if identity:
        identity_terms.append(f'"{identity}"')
    query = " ".join((*identity_terms, "opening hours", "admission fee"))

    provider = SearXNGSearchProvider(settings.searxng_url, client=client)
    try:
        observations = provider.search(query, limit=5)
    finally:
        provider.close()

    opening = dict(unknown_opening)
    cost = dict(unknown_cost)
    retained: list[dict[str, Any]] = []
    opening_pattern = re.compile(
        r"(?:opening\s+hours?|开放时间|营业时间)\s*[:：]?\s*"
        r"(?P<value>\d{1,2}(?::\d{2})?\s*[-–—]\s*\d{1,2}(?::\d{2})?)",
        re.IGNORECASE,
    )
    cost_pattern = re.compile(
        r"(?:admission|entrance\s+fee|ticket|门票(?:价格)?|票价)\s*[:：]?\s*"
        r"(?P<amount>\d+(?:\.\d{1,2})?)\s*(?P<currency>元|CNY|RMB|¥)?",
        re.IGNORECASE,
    )
    for item in observations:
        content = f"{item.title}\n{item.content}".strip()
        opening_match = opening_pattern.search(content)
        cost_match = cost_pattern.search(content)
        parsed = {
            "url": item.url,
            "title": item.title,
            "domain": item.domain,
            "content_excerpt": item.content,
            "captured_at": item.captured_at,
            "provider": item.provider_key,
            "query": item.query,
            "parsed_fields": [],
            "authority_status": "SEARCH_CANDIDATE",
        }
        if opening_match:
            normalized = normalize_opening_hours(opening_match.group("value"))
            if normalized.get("status") == "NORMALIZED_VALID":
                opening = {
                    **normalized,
                    "status": "SEARCH_CANDIDATE",
                    "source": "searxng",
                    "source_url": item.url,
                    "retrieved_at": retrieved_at,
                }
                parsed["parsed_fields"].append("opening_hours")
        if cost_match:
            raw_currency = (cost_match.group("currency") or "CNY").upper()
            currency = "CNY" if raw_currency in {"元", "RMB", "¥"} else raw_currency
            cost = {
                "status": "SEARCH_CANDIDATE",
                "amount_minor": round(float(cost_match.group("amount")) * 100),
                "currency": currency,
                "source": "searxng",
                "source_url": item.url,
                "retrieved_at": retrieved_at,
            }
            parsed["parsed_fields"].append("cost_evidence")
        if parsed["parsed_fields"]:
            retained.append(parsed)
    return {
        "provider": "searxng",
        "status": "CANDIDATES_FOUND" if retained else "NO_STRUCTURED_FACTS",
        "attempted": True,
        "query": query,
        "retrieved_at": retrieved_at,
        "observations": retained,
        "opening_hours": opening,
        "cost_evidence": cost,
    }


def acquire_place_facts(
    session: Session,
    journey: Journey,
    *,
    place_ids: list[str] | None = None,
    source_bindings: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    statement = select(Place).where(Place.city_code == journey.city_code)
    if place_ids:
        statement = statement.where(Place.id.in_(place_ids))
    places = session.scalars(statement.order_by(Place.id)).all()
    selected = [(place, ref) for place in places if (ref := _element_ref(place))]
    retrieved_at = datetime.now(timezone.utc).isoformat()
    endpoint = _overpass_endpoints()[0]
    receipt: dict[str, Any] = {
        "provider": "overpass", "source": endpoint, "retrieved_at": retrieved_at,
        "journey_id": journey.id, "places": [], "known_opening_count": 0, "known_cost_count": 0,
        "overpass_attempts": [],
        "official_web": {"provider": "official_web", "status": "NO_SOURCE_URL", "attempted": 0, "acquired": 0},
        "search_source": {"provider": "searxng", "status": "UNCONFIGURED" if not settings.searxng_url else "PENDING", "attempted": False, "acquired": 0},
    }
    if not selected:
        receipt["status"] = "NO_PROVIDER_ENTITIES"
        return receipt
    refs = [ref for _, ref in selected]
    # Keep every network phase in one live context.  The old R77 version closed this
    # client after Overpass/Nominatim and then reused it for official/search fetches.
    with httpx.Client(timeout=25.0, trust_env=trust_environment_for_public_providers()) as client:
        payload, endpoint, overpass_attempts = _acquire_overpass_payload(client, refs)
        receipt["source"] = endpoint
        receipt["overpass_attempts"] = overpass_attempts
        try:
            nominatim_rows, nominatim_endpoint = _nominatim_lookup(client, refs)
            secondary = {"provider": "nominatim", "source": nominatim_endpoint, "status": "ACQUIRED", "element_count": len(nominatim_rows)}
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            nominatim_rows, nominatim_endpoint = {}, f"{settings.nominatim_url.rstrip('/')}/lookup"
            secondary = {"provider": "nominatim", "source": nominatim_endpoint, "status": "UNAVAILABLE", "error": type(exc).__name__}
        receipt["secondary_source"] = secondary
        elements = {
            (str(item.get("type")), str(item.get("id"))): item
            for item in payload.get("elements", []) if isinstance(item, dict)
        }
        for place, ref in selected:
            element = elements.get(ref, {})
            tags = dict(element.get("tags") or {})
            nominatim_row = nominatim_rows.get(ref) or {}
            nominatim_tags = dict(nominatim_row.get("extratags") or {})
            metadata = json.loads(place.metadata_json or "{}") if place.metadata_json else {}
            opening = normalize_opening_hours(tags.get("opening_hours"))
            cost = cost_evidence_from_tags(tags, source="overpass")
            if opening.get("status") == "UNKNOWN" and nominatim_tags.get("opening_hours"):
                opening = normalize_opening_hours(nominatim_tags["opening_hours"])
                opening["source"] = "nominatim"
            if cost.get("status") == "UNKNOWN" and nominatim_tags:
                candidate = cost_evidence_from_tags(nominatim_tags, source="nominatim")
                if candidate.get("status") != "UNKNOWN":
                    cost = candidate
            official = {"status": "NO_SOURCE_URL"}
            requested_binding = source_bindings.get(place.id) if source_bindings else None
            source_binding = _requested_fact_source_binding(place, requested_binding)
            if source_binding is None:
                source_binding = _fact_source_binding(place, metadata)
            source_url = (
                str(source_binding["source_url"])
                if source_binding
                else _official_source_url({**tags, **nominatim_tags})
            )
            if (
                source_binding is None
                and source_url
                and secondary.get("status") == "ACQUIRED"
                and ref in nominatim_rows
                and source_url in {
                    str(tags.get("website") or "").strip(),
                    str(nominatim_tags.get("website") or "").strip(),
                }
            ):
                source_binding = {
                    "provider_entity": place.external_id,
                    "source_url": source_url,
                    "source_class": "OFFICIAL_TICKETING",
                    "identity_basis": {
                        "matched_provider_entity": True,
                        "provider_entity": place.external_id,
                        "basis": "exact_provider_website_tag",
                        "secondary_provider": "nominatim",
                    },
                    "approval": "PROVIDER_TAG_EXACT_URL",
                }
            if source_url:
                receipt["official_web"]["attempted"] += 1
                try:
                    official = _official_web_facts(
                        client,
                        source_url,
                        retrieved_at=retrieved_at,
                        reference_at=journey.start_at,
                        source_binding=source_binding,
                    )
                    receipt["official_web"]["status"] = official["status"]
                    if official["status"] == "ACQUIRED":
                        receipt["official_web"]["acquired"] += 1
                    # OSM/Nominatim tags are useful discovery evidence, but a fresh,
                    # operator-bound municipal page is the stronger source for these
                    # same facts.  Do not promote an arbitrary website tag here.
                    if (
                        source_binding
                        and official.get("opening_hours", {}).get("status") == "OFFICIAL_WEB_VERIFIED"
                    ):
                        opening = official["opening_hours"]
                    if (
                        source_binding
                        and official.get("cost_evidence", {}).get("status") == "VERIFIED_PROVIDER"
                        and official.get("cost_evidence", {}).get("amount_minor") is not None
                    ):
                        cost = official["cost_evidence"]
                except (httpx.HTTPError, ValueError, AttributeError) as exc:
                    official = {"provider": "official_web", "source": source_url, "retrieved_at": retrieved_at, "status": "UNAVAILABLE", "error": type(exc).__name__}
                    receipt["official_web"]["status"] = "UNAVAILABLE"
            search = _search_fact_candidates(
                client,
                place,
                journey,
                retrieved_at=retrieved_at,
                nominatim_row=nominatim_row,
            )
            receipt["search_source"] = {"provider": "searxng", "status": search.get("status"), "attempted": bool(search.get("attempted")), "acquired": len(search.get("observations") or [])}
            if opening.get("status") in {"NORMALIZED_VALID", "CLOSED", "OFFICIAL_WEB_VERIFIED", "VERIFIED_PROVIDER"}:
                receipt["known_opening_count"] += 1
            if str(cost.get("status") or "UNKNOWN").upper() in KNOWN_COST_STATUSES and cost.get("amount_minor") is not None:
                receipt["known_cost_count"] += 1
            metadata["fact_acquisition"] = {
                "source": endpoint, "provider": "overpass", "retrieved_at": retrieved_at,
                "provider_entity": place.external_id,
                "secondary_source": {"provider": "nominatim", "source": nominatim_endpoint, "provider_entity": place.external_id, "supporting_content": {"extratags": nominatim_tags}},
                "official_web": official, "search_source": search,
                "supporting_content": {"tags": tags, "nominatim_extratags": nominatim_tags},
                "claims": {"opening_hours": {"status": opening.get("status"), "normalized": opening}, "cost": cost},
            }
            if source_binding is not None:
                metadata["fact_source_binding"] = source_binding
            # Fresh provider observations reset stale values when data is absent;
            # operator-bound municipal evidence above supersedes lower-priority map tags.
            place.opening_hours_json = json.dumps(opening, ensure_ascii=False)
            price_known = str(cost.get("status") or "UNKNOWN").upper() in KNOWN_COST_STATUSES and cost.get("amount_minor") is not None
            metadata["cost_evidence"] = cost
            metadata["cost_minor"] = int(cost["amount_minor"]) if price_known else 0
            metadata["price_known"] = price_known
            place.metadata_json = json.dumps(metadata, ensure_ascii=False)
            place.updated_at = retrieved_at
            row_receipt = {
                "place_id": place.id, "provider": "overpass", "source": endpoint,
                "provider_entity": place.external_id, "retrieved_at": retrieved_at,
                "source_binding": source_binding,
                "secondary_source": {"provider": "nominatim", "source": nominatim_endpoint, "status": secondary["status"], "matched_provider_entity": ref in nominatim_rows},
                "supporting_content": {"tags": tags, "nominatim_extratags": nominatim_tags},
                "opening_hours": opening, "cost_evidence": cost, "official_web": official, "search_source": search,
            }
            receipt["places"].append(row_receipt)
    receipt["status"] = "ACQUIRED"
    receipt["element_count"] = len(elements)
    return receipt
