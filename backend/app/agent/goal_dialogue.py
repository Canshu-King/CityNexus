"""Traveler-facing questions and choices inside the existing GoalTask runtime."""
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException


def dialogue_definition() -> dict:
    return {"type": "function", "function": {"name": "ask_traveler",
        "description": "Ask one useful travel question with concrete choices and wait for the traveler. Use for preferences or tradeoffs, not internal execution details.",
        "parameters": {"type": "object", "properties": {
            "question": {"type": "string", "maxLength": 600},
            "options": {"type": "array", "minItems": 2, "maxItems": 4, "items": {
                "type": "object", "properties": {"label": {"type": "string", "maxLength": 100},
                    "description": {"type": "string", "maxLength": 250}}, "required": ["label", "description"], "additionalProperties": False}}},
            "required": ["question", "options"], "additionalProperties": False}}}


def validate_question(raw: dict) -> dict:
    if set(raw) != {"question", "options"} or not isinstance(raw.get("question"), str) or not 1 <= len(raw["question"].strip()) <= 600:
        raise HTTPException(422, "TRAVELER_QUESTION_INVALID")
    options = raw.get("options")
    if not isinstance(options, list) or not 2 <= len(options) <= 4:
        raise HTTPException(422, "TRAVELER_OPTIONS_INVALID")
    result = []
    for option in options:
        if not isinstance(option, dict) or set(option) != {"label", "description"}:
            raise HTTPException(422, "TRAVELER_OPTIONS_INVALID")
        if any(not isinstance(option.get(key), str) or len(option[key]) > limit for key, limit in (("label", 100), ("description", 250))) or not option["label"].strip():
            raise HTTPException(422, "TRAVELER_OPTIONS_INVALID")
        result.append({key: option[key].strip() for key in ("label", "description")})
    return {"question": raw["question"].strip(), "options": result}


def ask_question(task: dict, args: dict) -> dict:
    question = {"id": str(uuid4()), **validate_question(args)}
    task["pending_question"] = question
    task["assistant_summary"] = question["question"]
    transcript = list(task.get("conversation") or [])
    transcript.append({"role": "assistant", "text": question["question"], "message_id": question["id"],
        "at": datetime.now(timezone.utc).isoformat()})
    task["conversation"] = transcript
    return {"status": "WAITING_FOR_TRAVELER", "options": question["options"]}
