"""Source-bound city identity and explicitly published public classroom snapshots."""

import hashlib
import json
import re
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import ForeignKey, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base, ProviderCall


class SimulationCityIdentity(Base):
    __tablename__ = "simulation_city_identities"
    journey_id: Mapped[str] = mapped_column(ForeignKey("journeys.id"), primary_key=True)
    provider: Mapped[str] = mapped_column(String)
    provider_adcode: Mapped[str] = mapped_column(String)
    public_name: Mapped[str] = mapped_column(String)
    source_call_id: Mapped[str] = mapped_column(ForeignKey("provider_calls.id"))
    source_sha256: Mapped[str] = mapped_column(String)
    bound_at: Mapped[str] = mapped_column(String)


class SimulationPublicCitySnapshot(Base):
    __tablename__ = "simulation_public_city_snapshots"
    provider_adcode: Mapped[str] = mapped_column(String, primary_key=True)
    snapshot_json: Mapped[str] = mapped_column(Text)
    snapshot_sha256: Mapped[str] = mapped_column(String)
    published_at: Mapped[str] = mapped_column(String)
    published_by: Mapped[str] = mapped_column(ForeignKey("travelers.id"))


def acquired_amap_places(session):
    sources = {}
    for call in session.scalars(
        select(ProviderCall)
        .where(
            ProviderCall.operation.in_(["goal_amap_search", "goal_amap_nearby"]),
            ProviderCall.provider_key == "amap-web-service",
            ProviderCall.status == "SUCCESS",
        )
        .order_by(ProviderCall.created_at.desc())
    ):
        for place in json.loads(call.response_json or "{}").get("places", []):
            if not isinstance(place, dict):
                continue
            ident = str(
                place.get("provider_object_id")
                or place.get("external_id")
                or place.get("poi_id")
                or place.get("id")
                or ""
            ).removeprefix("amap:")
            code = str(place.get("adcode") or "")
            if ident and re.fullmatch(r"[0-9]{6}", code):
                sources.setdefault(
                    ident,
                    {"adcode": code, "captured_at": call.created_at, "source_call_id": call.id},
                )
    return sources


def city_contains(adcode, place_adcode):
    width = (
        2
        if adcode in {"110000", "120000", "310000", "500000"}
        else 4
        if adcode.endswith("00")
        else 6
    )
    return adcode[:width] == place_adcode[:width]


def bind_identity(session, journey, member, task_id):
    from app.agent.goal_tasks import _require_task

    _, _, _, _, task = _require_task(session, journey, member, task_id, require_draft=False)
    region = task.get("amap_region") or {}
    code = str(region.get("adcode") or "")
    if region.get("status") != "RESOLVED" or not re.fullmatch(r"[0-9]{6}", code):
        raise HTTPException(409, "CITY_PROVIDER_REGION_REQUIRED")
    if region.get("level") != "city" and not (
        region.get("level") == "province" and code in {"110000", "120000", "310000", "500000"}
    ):
        raise HTTPException(409, "CITY_LEVEL_SOURCE_REQUIRED")
    source = None
    for call in session.scalars(
        select(ProviderCall)
        .where(
            ProviderCall.operation == "goal_amap_district",
            ProviderCall.provider_key == "amap-web-service",
            ProviderCall.status == "SUCCESS",
        )
        .order_by(ProviderCall.created_at.desc())
    ):
        request = json.loads(call.request_json or "{}")
        response = json.loads(call.response_json or "{}")
        if request.get("region") != region.get("query"):
            continue
        if any(
            str(row.get("adcode")) == code
            and row.get("name") == region.get("name")
            and row.get("level") == region.get("level")
            for row in response.get("districts", [])
            if isinstance(row, dict)
        ):
            source = call
            break
    if source is None:
        raise HTTPException(409, "CITY_PROVIDER_RECEIPT_REQUIRED")
    existing = session.get(SimulationCityIdentity, journey.id)
    if existing and (existing.provider_adcode != code or existing.provider != "amap"):
        raise HTTPException(409, "CITY_IDENTITY_ALREADY_BOUND")
    if not existing:
        existing = SimulationCityIdentity(
            journey_id=journey.id,
            provider="amap",
            provider_adcode=code,
            public_name=region["name"],
            source_call_id=source.id,
            source_sha256=hashlib.sha256(source.response_json.encode()).hexdigest(),
            bound_at=datetime.now(timezone.utc).isoformat(),
        )
        session.add(existing)
    session.flush()
    return identity_payload(existing, journey.city_code)


def identity_payload(row, internal_city_code):
    return {
        "internal_city_code": internal_city_code,
        "provider": row.provider,
        "provider_city_adcode": row.provider_adcode,
        "public_name": row.public_name,
        "source_call_id": row.source_call_id,
        "source_sha256": row.source_sha256,
        "bound_at": row.bound_at,
    }


def publish_city(session, journey, actor_id):
    from app.simulation.preflight import cities_for

    binding = session.get(SimulationCityIdentity, journey.id)
    if binding is None:
        raise HTTPException(409, "CITY_PROVIDER_IDENTITY_REQUIRED")
    report = cities_for(session, actor_id, 0, journey_ids={journey.id}, include_public=False)
    candidate = next(
        (
            row
            for row in report["cities"]
            if row.get("provider_city_adcode") == binding.provider_adcode
        ),
        None,
    )
    if not candidate or candidate["missing"]:
        raise HTTPException(
            409,
            {
                "code": "CITY_SNAPSHOT_INCOMPLETE",
                "missing": candidate["missing"]
                if candidate
                else ["ACQUIRED_PUBLIC_FACTS_REQUIRED"],
            },
        )
    # Only public facts are copied: no Journey/Plan/member/task identities.
    poi = [
        {
            key: item[key]
            for key in (
                "place_id",
                "name",
                "provider",
                "external_id",
                "latitude",
                "longitude",
                "coordinate_system",
                "captured_at",
                "expires_at",
                "provenance",
            )
        }
        for item in candidate["poi"]
    ]
    routes = [
        {
            key: item[key]
            for key in (
                "origin_place_id",
                "destination_place_id",
                "minutes",
                "provider",
                "captured_at",
                "snapshot_sha256",
                "provenance",
            )
        }
        for item in candidate["routes"]
    ]
    public = {
        "provider_city_adcode": binding.provider_adcode,
        "public_name": binding.public_name,
        "provenance": "CAPTURED_PROVIDER_SNAPSHOT",
        "poi": poi,
        "routes": routes,
    }
    raw = json.dumps(public, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    row = session.get(SimulationPublicCitySnapshot, binding.provider_adcode)
    if row and row.snapshot_sha256 == digest:
        return {
            "provider_city_adcode": row.provider_adcode,
            "snapshot_sha256": digest,
            "published_at": row.published_at,
        }
    if row is None:
        row = SimulationPublicCitySnapshot(provider_adcode=binding.provider_adcode)
        session.add(row)
    row.snapshot_json = raw
    row.snapshot_sha256 = digest
    row.published_at = datetime.now(timezone.utc).isoformat()
    row.published_by = actor_id
    return {
        "provider_city_adcode": row.provider_adcode,
        "snapshot_sha256": digest,
        "published_at": row.published_at,
    }
