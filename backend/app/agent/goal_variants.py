"""Task-owned tentative alternatives, using the existing editable draft contract."""
from copy import deepcopy
from typing import Any
from fastapi import HTTPException
from app.agent.goal_artifacts import normalize_draft, goal_tool_definitions

_IDS = {"relaxed", "budget", "local"}


def save_draft_variants(journey, task: dict, variants: Any) -> dict:
    if not isinstance(variants, list) or not 2 <= len(variants) <= 3:
        raise HTTPException(422, "DRAFT_VARIANTS_INVALID")
    sources = set(task.get("candidate_place_ids") or []) | {
        lead["id"] for lead in task.get("research_places") or []
        if lead.get("provider_provenance") == "LIVE_PROVIDER" and lead.get("region_status") != "CONFLICT"
    }
    output, seen = [], set()
    for variant in variants:
        if not isinstance(variant, dict) or set(variant) != {"id", "title", "comparison", "days"}:
            raise HTTPException(422, "DRAFT_VARIANT_FIELDS_INVALID")
        identity = variant["id"]
        if not isinstance(identity, str) or identity not in _IDS or identity in seen:
            raise HTTPException(422, "DRAFT_VARIANT_ID_INVALID")
        seen.add(identity)
        title, comparison = variant["title"], variant["comparison"]
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 60 or not isinstance(comparison, str) or not 1 <= len(comparison.strip()) <= 300:
            raise HTTPException(422, "DRAFT_VARIANT_TEXT_INVALID")
        artifact = normalize_draft(journey, task, variant["days"], author="MODEL_SUGGESTION")
        slots = [slot for day in artifact["days"] for slot in day["slots"]]
        ids = sorted({slot["place_id"] for slot in slots if slot.get("place_id")})
        if not ids or any(identity not in sources for identity in ids):
            raise HTTPException(422, "DRAFT_VARIANT_SOURCE_REQUIRED")
        routes = [route for route in task.get("research_routes") or []
                  if route.get("from_place_id") in ids and route.get("to_place_id") in ids and route.get("id")]
        pairs = {(route.get("from_place_id"), route.get("to_place_id")) for route in routes}
        required_pairs = set()
        for day in artifact["days"]:
            places = [slot["place_id"] for slot in day["slots"] if slot.get("place_id")]
            required_pairs.update(zip(places, places[1:]))
        unknown = ["营业时间与票价待查"]
        if required_pairs - pairs:
            unknown.append("部分地点间的交通时间待查")
        if any(not slot.get("place_id") for slot in slots):
            unknown.append("部分安排还需要确定地点")
        output.append({"id": identity, "title": title.strip(), "comparison": comparison.strip(),
                       "artifact": artifact, "source_place_ids": ids,
                       "route_ids": sorted({route["id"] for route in routes}), "unknown_summary": unknown})
    # Publish atomically only after every alternative has passed the existing date/source rules.
    task["draft_variants"] = deepcopy(output)
    return {"tool": "save_draft_variants", "status": "VARIANTS_SAVED", "variants": output}


def variant_definition() -> dict:
    draft = next(item for item in goal_tool_definitions() if item["function"]["name"] == "save_draft_itinerary")
    days = deepcopy(draft["function"]["parameters"]["properties"]["days"])
    return {"type": "function", "function": {
        "name": "save_draft_variants",
        "description": "Save two or three source-backed tentative alternatives: relaxed, budget, local. Compare actual researched places/routes; keep unknown prices/hours unknown. Does not replace the current draft or activate a plan.",
        "parameters": {"type": "object", "properties": {"variants": {"type": "array", "minItems": 2, "maxItems": 3,
            "items": {"type": "object", "properties": {"id": {"type": "string", "enum": sorted(_IDS)},
                "title": {"type": "string", "maxLength": 60}, "comparison": {"type": "string", "maxLength": 300}, "days": days},
                "required": ["id", "title", "comparison", "days"], "additionalProperties": False}}},
            "required": ["variants"], "additionalProperties": False}}}
