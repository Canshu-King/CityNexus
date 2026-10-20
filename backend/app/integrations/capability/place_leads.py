"""One typed surface for "where is this place", whichever provider answers.

Arbiter ruling 2026-10-19 (Revolution Autonomy Upgrade) item 2 asks for `discover_source_leads`,
Amap POI search, Photon/Nominatim and OSM area discovery to become one surface the model can choose
from and fall back across, carrying `source, provider_item_id, region/adcode, coordinate_system,
captured_at, verified_fields, unknown_fields` -- and it says plainly: if one source has a POI, the
agent may keep an editable itinerary; an UNKNOWN ticket price, opening hour or transport cost must not
block the whole DRAFT.

Why this module and not a fourth chain: the product already has `source_discovery.search_with_fallback`
for web sources and `real_city.capture_real_city_candidates` for the grounded-city chain. This one adds
the *place-lead* shape on top of provider callables, keeps every provider's own signature (nothing here
edits them), and is deliberately dependency-free -- no Session, no DB write, no FastAPI. A caller that
must persist a `ProviderCall` row passes `on_provider_call`; a caller that has an OSM-area source passes
it in `sources`. That is the cherry-pick seam Codex PR #23 is asked to consume.

Coordinate rule: `coordinate_system` describes the numbers this lead actually carries. An Amap answer
arrives in GCJ-02 and is re-expressed here in WGS84, so the row says `WGS84` and names the native frame
and the conversion next to it. A frame is never left implicit and never mixed inside one row.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol, Sequence

import httpx

OPTIONAL_DETAILS = ("ticket_price", "opening_hours", "transport_cost")
MIN_LEAD_LIMIT = 1
MAX_LEADS_PER_SOURCE = 25


class PlaceSource(Protocol):
    """One provider of place leads. `search` returns rows this module can normalise."""

    provider_key: str
    coordinate_system: str

    async def search(self, query: str, *, city: str, limit: int) -> list[Any]: ...


@dataclass(frozen=True)
class PlaceLead:
    source: str
    provider_item_id: str
    name: str
    latitude: float | None
    longitude: float | None
    region: str | None
    adcode: str | None
    coordinate_system: str
    native_coordinate_system: str | None
    conversion: str | None
    captured_at: str
    verified_fields: tuple[str, ...]
    unknown_fields: tuple[str, ...]

    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def as_payload(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "provider_item_id": self.provider_item_id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "region": self.region,
            "adcode": self.adcode,
            "coordinate_system": self.coordinate_system,
            "native_coordinate_system": self.native_coordinate_system,
            "conversion": self.conversion,
            "captured_at": self.captured_at,
            "verified_fields": list(self.verified_fields),
            "unknown_fields": list(self.unknown_fields),
        }


@dataclass(frozen=True)
class PlaceLeadResult:
    query: str
    region: str
    leads: tuple[PlaceLead, ...]
    provider_readings: tuple[dict[str, Any], ...]
    counts_as_draft_supply: bool
    unknown_fields: tuple[str, ...]

    def as_payload(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "region": self.region,
            "counts_as_draft_supply": self.counts_as_draft_supply,
            "unknown_fields": list(self.unknown_fields),
            "leads": [lead.as_payload() for lead in self.leads],
            "provider_readings": [dict(row) for row in self.provider_readings],
        }


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _number(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _as_row(item: Any) -> dict[str, Any]:
    """Accept whatever a provider hands back: a mapping (Amap rows) or a dataclass (Photon).

    Normalising here means a source never has to reshape its own answer to please this surface, and a
    dataclass that gains a field does not silently disappear from a lead.
    """
    if isinstance(item, Mapping):
        return dict(item)
    if is_dataclass(item) and not isinstance(item, type):
        return asdict(item)
    return {}


def lead_from_row(row: Any, *, fallback_source: str) -> PlaceLead | None:
    """Normalise one provider row. Returns None only when the row has no identity at all.

    A row that carries a name but no coordinate is kept: its position goes to `unknown_fields`.
    Dropping it would silently turn "the provider named this place but did not locate it" into
    "nobody answered", which is the exact reading the autonomy ruling forbids.
    """
    row = _as_row(row)
    name = _text(row.get("name"))
    item_id = _text(row.get("provider_item_id") or row.get("external_id") or row.get("id"))
    if name is None and item_id is None:
        return None
    latitude = _number(row.get("latitude"))
    longitude = _number(row.get("longitude"))
    captured = _text(row.get("captured_at")) or _stamp()
    lead = PlaceLead(
        source=_text(row.get("source") or row.get("provider_key")) or fallback_source,
        provider_item_id=item_id or "unresolved:" + (name or ""),
        name=name or item_id or "",
        latitude=latitude,
        longitude=longitude,
        region=_text(row.get("region") or row.get("city") or row.get("country")),
        adcode=_text(row.get("adcode")),
        coordinate_system=_text(row.get("coordinate_system") or row.get("domain_crs")) or "WGS84",
        native_coordinate_system=_text(row.get("source_crs") or row.get("native_coordinate_system")),
        conversion=_text(row.get("conversion")),
        captured_at=captured,
        verified_fields=(),
        unknown_fields=(),
    )
    verified = ["provider_item_id"] if item_id else []
    if lead.name:
        verified.append("name")
    if lead.has_position():
        verified.append("position")
    if lead.region:
        verified.append("region")
    if lead.adcode:
        verified.append("adcode")
    unknown: list[str] = []
    if not lead.has_position():
        unknown.append("position")
    unknown.extend(detail for detail in OPTIONAL_DETAILS if detail not in row)
    return _with(lead, tuple(verified), tuple(unknown))


def _with(lead: PlaceLead, verified: tuple[str, ...], unknown: tuple[str, ...]) -> PlaceLead:
    return PlaceLead(
        source=lead.source,
        provider_item_id=lead.provider_item_id,
        name=lead.name,
        latitude=lead.latitude,
        longitude=lead.longitude,
        region=lead.region,
        adcode=lead.adcode,
        coordinate_system=lead.coordinate_system,
        native_coordinate_system=lead.native_coordinate_system,
        conversion=lead.conversion,
        captured_at=lead.captured_at,
        verified_fields=verified,
        unknown_fields=unknown,
    )


def default_sources(*, amap: Any | None, photon: Any | None, city_code: str) -> list[Any]:
    """Amap first inside China when it is configured, then the global geocoder. Never a silent skip.

    A source that was not asked because another one answered is recorded by the caller as
    `attempted: False`, so a reading can never be re-read as "photon was fine" when nobody spoke to it
    -- the same rule the anchor chain already follows.
    """
    from app.integrations.china.amap import provider_for_region, web_key

    chain: list[Any] = []
    if amap is not None and provider_for_region(city_code) == "amap-web-service" and web_key():
        chain.append(amap)
    if photon is not None:
        chain.append(photon)
    return chain


class AmapLeadSource:
    """`AmapPoiProvider` behind the call shape this surface uses.

    The provider takes `city` positionally and returns GCJ-02 answers already re-expressed in WGS84;
    this wrapper is the only place that knows that, instead of every caller learning it.
    """

    provider_key = "amap-web-service"
    coordinate_system = "WGS84"

    def __init__(self, provider: Any, client: Any | None = None) -> None:
        self._provider = provider
        self._client = client

    async def search(self, query: str, *, city: str, limit: int) -> list[Any]:
        return await self._provider.search(query, city, limit=limit, client=self._client)


class GeocoderLeadSource:
    """Photon/Nominatim-shaped geocoder behind the same call.

    It has no region argument to pass: a global geocoder's answer carries its own country and city, and
    those become the lead's `region`. Pretending the region was a filter here would be a claim the
    provider never made.
    """

    coordinate_system = "WGS84"

    def __init__(self, geocoder: Any) -> None:
        self._geocoder = geocoder
        self.provider_key = str(getattr(geocoder, "provider_key", "photon"))

    async def search(self, query: str, *, city: str, limit: int) -> list[Any]:
        return await self._geocoder.search(query, limit=limit)


def build_sources(*, city_code: str, client, amap: Any | None = None, photon: Any | None = None):
    """The two providers this tree already has, in the order the region and the key allow.

    `client` is required because both legs ride on an `httpx.AsyncClient` the caller owns -- that is how
    the anchor chain does it, and it is what lets one test drive a whole lead collection over a single
    MockTransport without a socket.
    """
    from app.integrations.china.amap import AmapPoiProvider
    from app.integrations.discovery.photon import PhotonGeocoder

    return default_sources(
        amap=AmapLeadSource(amap if amap is not None else AmapPoiProvider(), client),
        photon=GeocoderLeadSource(photon if photon is not None else PhotonGeocoder(client=client)),
        city_code=city_code,
    )


async def collect_place_leads(
    query: str,
    *,
    region: str,
    sources: Sequence[Any],
    limit: int = 8,
    stop_on_first_answer: bool = True,
    on_provider_call: Callable[[dict[str, Any]], None] | None = None,
) -> PlaceLeadResult:
    """Ask the given sources in order; keep every answer's own identity, provenance and frame.

    `stop_on_first_answer` is the fallback rule the ruling asks for: one source that returns leads ends
    the chain, because the traveller's DRAFT can already be built. It does not stop on a source that
    refused or failed -- that is a step, not an answer.
    """
    wanted = max(MIN_LEAD_LIMIT, min(int(limit or MIN_LEAD_LIMIT), MAX_LEADS_PER_SOURCE))
    leads: list[PlaceLead] = []
    readings: list[dict[str, Any]] = []
    asked = 0

    for source in sources:
        if stop_on_first_answer and leads:
            readings.append(
                {
                    "source": getattr(source, "provider_key", "unknown"),
                    "attempted": False,
                    "outcome": "SKIPPED",
                    "reason_code": "ANOTHER_SOURCE_ALREADY_ANSWERED",
                }
            )
            continue
        asked += 1
        provider_key = str(getattr(source, "provider_key", "unknown"))
        started = _stamp()
        try:
            rows = await source.search(query, city=region, limit=wanted)
        except (httpx.HTTPError, RuntimeError, ValueError, TypeError, KeyError) as failure:
            # A provider boundary: a refused source is named and the chain moves on. A bug in the
            # source itself (AttributeError, IndexError, a typo) is deliberately NOT in this tuple --
            # it must reach the caller instead of being filed as "the provider did not answer".
            readings.append(
                {
                    "source": provider_key,
                    "attempted": True,
                    "answered": False,
                    "outcome": "NOT_ANSWERED_" + type(failure).__name__,
                    "captured_at": started,
                }
            )
            if on_provider_call is not None:
                on_provider_call(
                    {
                        "source": provider_key,
                        "query": query,
                        "region": region,
                        "outcome": "NOT_ANSWERED",
                        "error_type": type(failure).__name__,
                        "captured_at": started,
                    }
                )
            continue
        normalised = [lead for lead in (lead_from_row(row, fallback_source=provider_key) for row in rows)
                      if lead is not None]
        readings.append(
            {
                "source": provider_key,
                "attempted": True,
                "answered": True,
                "outcome": "ANSWERED" if normalised else "ANSWERED_EMPTY",
                "rows": len(list(rows)),
                "usable": len(normalised),
                "captured_at": started,
            }
        )
        if on_provider_call is not None:
            on_provider_call(
                {
                    "source": provider_key,
                    "query": query,
                    "region": region,
                    "outcome": readings[-1]["outcome"],
                    "rows": readings[-1]["rows"],
                    "captured_at": started,
                }
            )
        leads.extend(normalised[:wanted])

    supply = [lead for lead in leads if lead.has_position()]
    unknown = sorted({field for lead in leads for field in lead.unknown_fields})
    return PlaceLeadResult(
        query=query,
        region=region,
        leads=tuple(leads),
        provider_readings=tuple(readings),
        counts_as_draft_supply=len(supply) > 0,
        unknown_fields=tuple(unknown),
    )
