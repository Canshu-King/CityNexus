"""Navigator: one signed Journey + one Mission, no hand-filled development parameters.

The gateway tools `compare_routes` and `acquire_route` already know how to read
and capture one grounded-origin -> active-target edge.  What a Mission needs is a
thin adapter that:

  * verifies the Mission belongs to the signed Journey (the owner check stays in
    the signed route, this function only refuses a cross-Journey id);
  * resolves the target and the grounded origin with the product's own chain;
  * answers with stored facts, their ETA source/time, cost status and limits --
    or says `UNKNOWN` when no edge was actually acquired;
  * triggers acquisition through the same gateway/approval path the model uses.

It never accepts an origin, coordinate, ETA or cost from the caller.  A route
that was not acquired is `UNKNOWN`, not a zero.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.gateway import AgentToolGateway
from app.db.models import Journey, JourneyMission, MobilityFact
from app.execution.launch_origin import grounded_launch_origin
from app.schemas import AgentToolCall


def _require_mission(session: Session, journey: Journey, mission_id: str) -> JourneyMission:
    mission = session.get(JourneyMission, str(mission_id))
    if mission is None or str(mission.journey_id) != str(journey.id):
        raise HTTPException(404, "JourneyMission was not found for this Journey")
    return mission


def _edge(session: Session, journey: Journey) -> tuple[Any, dict[str, Any]]:
    """The active exact target and the grounded origin, resolved by the server."""

    from app.main import _launch_target_activity

    target = _launch_target_activity(session, journey)
    if target is None or not target.place_id:
        return None, {
            "status": "NO_EXACT_TARGET",
            "reason_code": "EXACT_ROUTE_TARGET_UNAVAILABLE",
            "next_legal_path": "select or advance to an exact activity with a server-owned Place",
        }
    origin = grounded_launch_origin(session, journey, target_activity=target)
    if origin.get("state") != "READY" or not origin.get("origin_key"):
        return target, {
            "status": "NO_GROUNDED_ORIGIN",
            "reason_code": "GROUNDED_LAUNCH_ORIGIN_UNAVAILABLE",
            "next_legal_path": "confirm a planned origin on this Journey",
        }
    if str(origin.get("source") or "") == "FOREGROUND_LOCATION":
        return target, {
            "status": "NO_PERSISTED_ORIGIN",
            "reason_code": "ROUTE_ACQUISITION_REQUIRES_EXACT_ORIGIN_PLACE",
            "next_legal_path": "persist the current location as a Place, or confirm a planned origin",
        }
    return target, {
        "status": "READY",
        "origin_key": str(origin["origin_key"]),
        "origin_name": origin.get("name"),
        "origin_authority": origin.get("authority"),
        "origin_source": origin.get("source"),
        "target_activity_id": str(target.id),
        "target_place_id": str(target.place_id),
    }


def route_snapshot(
    session: Session,
    journey: Journey,
    mission_id: str,
    *,
    mode: str | None = None,
) -> dict[str, Any]:
    """Read the stored edge for this Mission; never acquires anything."""

    mission = _require_mission(session, journey, mission_id)
    target, edge = _edge(session, journey)
    base: dict[str, Any] = {
        "tool": "mission_route_snapshot",
        "journey_id": journey.id,
        "mission_id": mission.id,
        "authority": "STORED_FACT_ONLY",
    }
    if edge["status"] != "READY":
        return {**base, **edge, "eta": {"status": "UNKNOWN"}, "cost": {"status": "UNKNOWN"}, "options": []}

    requested = (mode or "TRANSIT").upper()
    query = select(MobilityFact).where(
        MobilityFact.journey_id == journey.id,
        MobilityFact.from_key == edge["origin_key"],
        MobilityFact.to_key == edge["target_place_id"],
        MobilityFact.mode == requested,
    )
    rows = session.scalars(query.order_by(MobilityFact.captured_at.desc())).all()
    options = [
        {
            "mode": row.mode,
            "duration_min": row.duration_min,
            "distance_m": row.distance_m,
            "transfers": row.transfers,
            "walking_min": row.walking_min,
            "provider": row.provider_key,
            "provenance": row.provenance,
            "captured_at": row.captured_at,
            "cost_status": row.cost_status,
            "cost_amount_minor": row.cost_amount_minor,
            "currency": row.currency,
        }
        for row in rows
    ]
    if not options:
        return {
            **base,
            **edge,
            "mode": requested,
            "status": "UNKNOWN",
            "reason_code": "ROUTE_NOT_ACQUIRED",
            "eta": {"status": "UNKNOWN"},
            "cost": {"status": "UNKNOWN"},
            "options": [],
            "next_legal_path": "acquire this edge through the Mission route action",
        }
    first = options[0]
    return {
        **base,
        **edge,
        "mode": requested,
        "status": "STORED_FACTS",
        "eta": {
            "status": "STORED_FACT",
            "duration_min": first["duration_min"],
            "source": first["provenance"],
            "provider": first["provider"],
            "captured_at": first["captured_at"],
        },
        "cost": {
            "status": first["cost_status"] or "UNKNOWN",
            "amount_minor": first["cost_amount_minor"],
            "currency": first["currency"],
        },
        "limits": {
            "mode": first["mode"],
            "transfers": first["transfers"],
            "walking_min": first["walking_min"],
            "distance_m": first["distance_m"],
        },
        "options": options,
    }


def acquire_route_for_mission(
    session: Session,
    journey: Journey,
    mission_id: str,
    *,
    mode: str | None = None,
    agent_id: str = "mission-adapter",
    request_id: str | None = None,
    approval_id: str | None = None,
) -> dict[str, Any]:
    """Trigger one exact edge through the gateway, with its approval semantics."""

    mission = _require_mission(session, journey, mission_id)
    request = AgentToolCall(
        request_id=request_id or f"mission-route-{uuid4()}",
        agent_id=agent_id,
        journey_id=journey.id,
        mission_id=mission.id,
        route_mode=(mode or "TRANSIT").upper(),
        approval_id=approval_id,
    )
    return AgentToolGateway(session).dispatch("acquire_route", request)
