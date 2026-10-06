from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ProviderObservation


def _json_object(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _weather_context(row: ProviderObservation, payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = payload.get("snapshot") if isinstance(payload.get("snapshot"), dict) else {}
    activity_observations = payload.get("activity_observations")
    if not isinstance(activity_observations, list):
        activity_observations = []
    risk_facts = snapshot.get("facts") if isinstance(snapshot, dict) else []
    if not isinstance(risk_facts, list):
        risk_facts = []
    activity_risk_facts = payload.get("activity_risk_facts")
    if not isinstance(activity_risk_facts, list):
        activity_risk_facts = []
    return {
        "id": row.id,
        "provider_key": row.provider_key,
        "observation_type": row.observation_type,
        "state": row.state,
        "provenance": row.provenance,
        "captured_at": row.captured_at,
        "expires_at": row.expires_at,
        "query_scope": payload.get("query_scope"),
        # Bounded journey-relevant provider readings. These are evidence, not
        # disruption claims and not mutation authority.
        "activity_observations": activity_observations[:12],
        "risk_facts": risk_facts[:12],
        "activity_risk_facts": activity_risk_facts[:12],
        # A provider can forecast material weather at this Place outside the
        # planned activity window. Only activity-attributed risk is a Journey
        # materiality claim.
        "material_risk": bool(activity_risk_facts),
    }


def latest_world_context(
    session: Session,
    journey_id: str,
    *,
    limit: int = 6,
) -> dict[str, Any]:
    """Project recent server-captured provider context without inventing Events.

    ProviderObservation is the durable sensing record. A caller may inspect it,
    explain it, or decide that no action is needed. Only the domain-specific
    server ingestion path may promote a material fact into a trusted Event.
    """

    rows = session.scalars(
        select(ProviderObservation)
        .where(ProviderObservation.journey_id == str(journey_id))
        .order_by(
            ProviderObservation.captured_at.desc(),
            ProviderObservation.id.desc(),
        )
        .limit(max(1, min(int(limit), 20)))
    ).all()
    observations: list[dict[str, Any]] = []
    for row in rows:
        payload = _json_object(row.payload_json)
        if row.observation_type == "WEATHER":
            observations.append(_weather_context(row, payload))
            continue
        observations.append(
            {
                "id": row.id,
                "provider_key": row.provider_key,
                "observation_type": row.observation_type,
                "state": row.state,
                "provenance": row.provenance,
                "captured_at": row.captured_at,
                "expires_at": row.expires_at,
                "material_risk": False,
            }
        )
    return {
        "journey_id": str(journey_id),
        "observations": observations,
    }
