"""DRAFT adapters over existing Place tools and Qoder's stored-route reader.

Route projection adapted from PR #35 e6455c239878; no route provider is called.
The other adapters dispatch the current branch's existing gateway methods.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Journey, MobilityFact


DOMAIN_TOOLS = frozenset({"acquire_place_facts", "estimate_place_facts", "generate_plans", "compare_routes"})


def domain_args(name: str, raw: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    known = {str(item) for item in task.get("candidate_place_ids") or []}
    allowed = {
        "acquire_place_facts": {"place_id", "source_observation_id"},
        "estimate_place_facts": {"place_id", "estimated_open_minutes", "estimated_close_minutes", "estimated_cost_minor"},
        "generate_plans": {"place_ids", "candidate_count", "planning_mode"},
        "compare_routes": {"from_key", "to_key", "route_mode"},
    }[name]
    if set(raw) - allowed - {"journey_id"}:
        raise HTTPException(422, "TOOL_ARGUMENTS_INVALID")
    args = {key: value for key, value in raw.items() if key in allowed and value is not None}
    if name == "generate_plans":
        ids = args.get("place_ids")
        if not isinstance(ids, list) or not 2 <= len(ids) <= 12 or any(not isinstance(item, str) for item in ids):
            raise HTTPException(422, "TOOL_ARGUMENTS_INVALID")
        if not set(ids) <= known:
            raise HTTPException(403, "PLACE_NOT_IN_GOAL_TASK_SCOPE")
    elif name == "compare_routes":
        if not all(isinstance(args.get(key), str) and args[key] in known for key in ("from_key", "to_key")):
            raise HTTPException(403, "PLACE_NOT_IN_GOAL_TASK_SCOPE")
        if args.get("route_mode") not in {None, "WALK", "TRANSIT", "TAXI", "DRIVE", "BICYCLE"}:
            raise HTTPException(422, "TOOL_ARGUMENTS_INVALID")
    else:
        if not isinstance(args.get("place_id"), str) or args["place_id"] not in known:
            raise HTTPException(403, "PLACE_NOT_IN_GOAL_TASK_SCOPE")
        observation = args.get("source_observation_id")
        if observation is not None and str(observation) not in task.get("source_observation_ids", []):
            raise HTTPException(403, "SOURCE_NOT_IN_GOAL_TASK_SCOPE")
    return args


def compare_stored_routes(session: Session, journey: Journey, **args: Any) -> dict[str, Any]:
    query = select(MobilityFact).where(MobilityFact.journey_id == journey.id,
        MobilityFact.from_key == args["from_key"], MobilityFact.to_key == args["to_key"])
    if args.get("route_mode"):
        query = query.where(MobilityFact.mode == args["route_mode"])
    rows = session.scalars(query.order_by(MobilityFact.mode)).all()
    return {"tool": "compare_routes", "status": "STORED_FACTS" if rows else "NO_STORED_ROUTE_FACTS",
        "pair": {key: args[key] for key in ("from_key", "to_key")}, "acquisition_attempted": False,
        "options": [{key: getattr(row, key) for key in ("mode", "duration_min", "distance_m",
            "cost_amount_minor", "currency", "cost_status", "transfers", "walking_min",
            "provider_key", "provenance", "captured_at", "expires_at")} for row in rows]}


def domain_result(name: str, raw: dict[str, Any]) -> dict[str, Any]:
    if name == "compare_routes":
        return raw
    if name == "estimate_place_facts":
        return {"tool": name, "status": "ESTIMATED_AGENT", "estimate": raw.get("estimate"), "authority_eligible": False}
    if name == "acquire_place_facts":
        return {"tool": name, "place_id": raw.get("place_id"), "receipt": raw.get("receipt")}
    # Collective member preferences/profiles in gateway results are not model context.
    return {"tool": name, "candidate_count": raw.get("candidate_count", 0),
        "plans": [{key: plan.get(key) for key in ("id", "status", "selectable", "place_ids", "unresolved_facts", "authority_state", "mobility_provider")}
                  for plan in raw.get("plans", []) if isinstance(plan, dict)], "activation_attempted": False}


def route_tool_definition() -> dict[str, Any]:
    return {"type": "function", "function": {"name": "compare_routes",
        "description": "Compare stored route facts between two canonical Place IDs returned in this task. No live route query; missing or expired facts stay visible.",
        "parameters": {"type": "object", "properties": {"from_key": {"type": "string"}, "to_key": {"type": "string"},
            "route_mode": {"type": "string", "enum": ["WALK", "TRANSIT", "TAXI", "DRIVE", "BICYCLE"]}},
            "required": ["from_key", "to_key"], "additionalProperties": False}}}
