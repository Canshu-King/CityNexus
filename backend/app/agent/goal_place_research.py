"""Explicit owner-requested public research, independent of model availability."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.agent.goal_artifacts import discover_goal_places
from app.agent.goal_tasks import DRAFT_RESEARCH_RUNNING, _require_task, refuse_draft_edit
from app.commerce.idempotency import canonical_request_signature
from app.concurrency_guards import journey_write_lock
from app.core.audit import record_audit
from app.db.models import IdempotencyKey, Journey
from app.db.session import get_session
from app.traveler_principal import resolve_journey_member_principal

router = APIRouter()
PATH = "/api/v1/journeys/{journey_id}/agent/goal-tasks/{task_id}/research-places"


class PlaceResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=120)
    source: Literal["amap"] = "amap"
    provider_consent: Literal[True]

    @field_validator("provider_consent", mode="before")
    @classmethod
    def explicit_consent(cls, value):
        if value is not True:
            raise ValueError("provider_consent must be the JSON boolean true")
        return value


@router.post(PATH)
def research_places(
    journey_id: UUID, task_id: UUID, body: PlaceResearchRequest,
    request: Request, response: Response,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=160),
    session: Session = Depends(get_session),
):
    with journey_write_lock(str(journey_id)):
        _principal, member = resolve_journey_member_principal(request, session, journey_id=str(journey_id))
        journey = session.get(Journey, str(journey_id))
        if journey is None:
            raise HTTPException(404, "Journey not found")
        journey, member, mission, intent, task = _require_task(
            session, journey, member, task_id, require_draft=False,
        )
        signature = canonical_request_signature({"task_id": str(task_id), "actor": member.id, **body.model_dump()})
        key = f"goal.research-places:{journey.id}:{idempotency_key}"
        existing = session.get(IdempotencyKey, key)
        if existing:
            if existing.request_hash != signature:
                raise HTTPException(409, "RESEARCH_KEY_REUSE_CONFLICT")
            response.headers["Cache-Control"] = "private, no-store, max-age=0"
            response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
            return {**json.loads(existing.response_json), "idempotency_replay": True}
        _require_task(session, journey, member, task_id, require_draft=True)
        if task.get("status") == "WORKING":
            raise refuse_draft_edit(DRAFT_RESEARCH_RUNNING)
        if task.get("status") == "CANCELLED":
            raise HTTPException(409, "GOAL_TASK_CANCELLED")
        if (task.get("consent") or {}).get("online_research") is not True:
            raise HTTPException(403, "ONLINE_RESEARCH_CONSENT_REQUIRED")
        query = " ".join(body.query.split())
        if len(query) < 2:
            raise HTTPException(422, "PUBLIC_QUERY_INVALID")
        if len(task.get("public_queries") or []) >= 64:
            raise HTTPException(409, "GOAL_TASK_PUBLIC_QUERY_LIMIT_REACHED")

        # The existing source service owns query deduplication, ProviderCall receipts,
        # region checks and materialization. A person pressing this door is not an AgentRun.
        result = discover_goal_places(
            session, journey, task, query=query, source=body.source,
            public_action="按旅客明确给出的关键词查找公开地点",
        )
        fields = {
            "id", "canonical_place_id", "name", "category", "provider", "provider_object_id",
            "provider_call_id", "provider_provenance", "source_url", "captured_at",
            "requested_adcode", "adcode", "region_status", "latitude", "longitude",
            "coordinate_system", "opening_status", "cost_status",
        }
        places = [{k: v for k, v in row.items() if k in fields}
                  for row in result.get("places", []) if isinstance(row, dict)]
        answer = {
            "journey_id": journey.id, "task_id": mission.id,
            "status": result.get("status", "PROVIDER_UNAVAILABLE"),
            "reason_code": result.get("reason_code"), "source": body.source,
            "provider_call_id": result.get("provider_call_id"), "places": places,
            "candidate_place_ids": list(task.get("candidate_place_ids") or []),
            "idempotency_replay": False,
        }
        now = datetime.now(timezone.utc)
        task["updated_at"] = now.isoformat()
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.add(IdempotencyKey(
            key=key, operation="goal.research-places", request_hash=signature,
            response_status=200, response_json=json.dumps(answer, ensure_ascii=False),
            created_at=now.isoformat(), expires_at=(now + timedelta(days=7)).isoformat(),
        ))
        record_audit(
            session, action="goal.public_places.researched", entity_type="AgentGoalTask",
            entity_id=mission.id, journey_id=journey.id, actor_type="TRAVELER",
            actor_id=member.traveler_id,
            after={"source": body.source, "query": query, "status": answer["status"],
                   "provider_call_id": answer["provider_call_id"], "place_count": len(places)},
        )
        session.commit()
        response.headers["Cache-Control"] = "private, no-store, max-age=0"
        response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
        return answer
