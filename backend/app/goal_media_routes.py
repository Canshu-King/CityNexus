"""Signed media reads use GoalTask candidate identity, never a guessed Place PK."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.agent.goal_media import read_source_media
from app.agent.goal_tasks import read_goal_task
from app.db.models import Journey
from app.db.session import get_session
from app.traveler_principal import member_has_capability, resolve_journey_member_principal

router = APIRouter()


@router.get("/api/v1/journeys/{journey_id}/agent/goal-tasks/{task_id}/place-media")
def signed_goal_place_media(journey_id: UUID, task_id: UUID, request: Request, response: Response,
        candidate_id: str = Query(min_length=1, max_length=200), session: Session = Depends(get_session)) -> dict:
    _, member = resolve_journey_member_principal(request, session, journey_id=str(journey_id))
    if not member_has_capability(session, member, "JOURNEY_READ"):
        raise HTTPException(403, "JOURNEY_READ required")
    journey = session.get(Journey, str(journey_id))
    if journey is None:
        raise HTTPException(404, "JOURNEY_NOT_FOUND")
    task = read_goal_task(session, journey, member, str(task_id))
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
    result = read_source_media(session, journey, task, str(task_id), candidate_id)
    session.commit()
    return result
