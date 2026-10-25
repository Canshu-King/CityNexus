import json
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.concurrency_guards import journey_write_lock
from app.core.config import settings
from app.db.models import Event, Journey, JourneyMember
from app.db.session import get_session
from app.demo_access import require_demo_database, require_demo_presenter
from app.simulation import runtime as rt
from app.simulation.models import SimulationRun, SimulationCommand
from app.simulation.clock import journey_business_time
from app.simulation.city_catalog import bind_identity, publish_city
from app.traveler_principal import require_journey_read, member_has_capability

router = APIRouter(prefix="/api/v1/journeys/{journey_id}/simulation", tags=["simulation"])


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Start(Input):
    seed: int = Field(ge=0, le=2147483647)


class Advance(Input):
    expected_sequence: int = Field(ge=0)
    # Omit minutes to visit exactly the next native execution phase.
    minutes: int | None = Field(default=None, ge=1, le=10080)


class Scene(Input):
    expected_sequence: int = Field(ge=0)
    scene_id: str = Field(min_length=1, max_length=100)
    event_type: Literal["CLOSURE", "WEATHER", "SCHEDULE_DELAY"]
    activity_id: UUID
    delay_minutes: int = Field(default=0, ge=0, le=1440)


class Guardian(Input):
    expected_sequence: int = Field(ge=0)
    model_consent: Literal[True]


class Resume(Input):
    expected_sequence: int = Field(ge=0)


class CityIdentity(Input):
    source_task_id: UUID


class PublishCity(Input):
    publish_public_facts: Literal[True]


@router.post("/city-identity")
def bind_city(
    journey_id: UUID,
    body: CityIdentity,
    request: Request,
    idempotency_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    with journey_write_lock(str(journey_id)):
        journey, principal = access(session, journey_id, request, write=True)
        key_value(idempotency_key)
        member = session.scalar(
            select(JourneyMember).where(
                JourneyMember.journey_id == journey.id,
                JourneyMember.traveler_id == principal.traveler_id,
            )
        )
        result = bind_identity(session, journey, member, body.source_task_id)
        session.commit()
        return result


@router.post("/cities/publish")
def publish(
    journey_id: UUID,
    body: PublishCity,
    request: Request,
    idempotency_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    with journey_write_lock(str(journey_id)):
        journey, principal = access(session, journey_id, request, write=True)
        key_value(idempotency_key)
        result = publish_city(session, journey, principal.traveler_id)
        session.commit()
        return result


def access(session, journey_id, request, *, write=False):
    if not settings.simulation_enabled:
        raise HTTPException(404, "SIMULATION_DISABLED")
    principal, member = require_journey_read(request, session, str(journey_id))
    if write and not member_has_capability(session, member, "JOURNEY_EXECUTION_UPDATE"):
        raise HTTPException(403, "JOURNEY_EXECUTION_UPDATE_REQUIRED")
    require_demo_database(session)
    if write:
        require_demo_presenter(request, session, journey_id=journey_id)
    journey = session.get(Journey, str(journey_id))
    if journey is None:
        raise HTTPException(404, "Journey not found")
    return journey, principal


def run_for(session, journey, run_id):
    row = session.get(SimulationRun, str(run_id))
    if row is None or row.journey_id != journey.id:
        raise HTTPException(404, "SIMULATION_RUN_NOT_FOUND")
    return row


def key_value(key):
    if not key or not key.strip() or len(key) > 200:
        raise HTTPException(422, "IDEMPOTENCY_KEY_REQUIRED")
    return key


@router.get("/cities")
def city_preflight(
    journey_id: UUID,
    request: Request,
    response: Response,
    seed: int = 0,
    session: Session = Depends(get_session),
):
    _, principal = access(session, journey_id, request)
    if seed < 0 or seed > 2147483647:
        raise HTTPException(422, "SIMULATION_SEED_INVALID")
    from app.simulation.preflight import cities_for

    response.headers["Cache-Control"] = "private, no-store"
    return cities_for(session, principal.traveler_id, seed)


@router.get("/runs/current")
def current(
    journey_id: UUID, request: Request, response: Response, session: Session = Depends(get_session)
):
    journey, _ = access(session, journey_id, request)
    response.headers["Cache-Control"] = "private, no-store"
    row = session.scalar(select(SimulationRun).where(SimulationRun.journey_id == journey.id))
    return (
        rt.payload(row)
        if row
        else {"run_id": None, "journey_id": journey.id, "status": "NOT_STARTED"}
    )


@router.get("/runs/{run_id}")
def read(
    journey_id: UUID,
    run_id: UUID,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    journey, _ = access(session, journey_id, request)
    response.headers["Cache-Control"] = "private, no-store"
    return rt.payload(run_for(session, journey, run_id))


@router.post("/runs", status_code=201)
def start(
    journey_id: UUID,
    body: Start,
    request: Request,
    idempotency_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    with journey_write_lock(str(journey_id)):
        journey, principal = access(session, journey_id, request, write=True)
        key = key_value(idempotency_key)
        digest = rt.request_hash("start", body.model_dump(mode="json"))
        prior = rt.replay(session, journey.id, principal.traveler_id, key, digest)
        if prior is not None:
            return prior
        run = rt.start_run(session, journey, principal.traveler_id, body.seed)
        result = rt.payload(run)
        rt.remember(session, run, principal.traveler_id, key, digest, result)
        session.commit()
        return result


def command(session, journey_id, run_id, request, key, operation, body, apply):
    with journey_write_lock(str(journey_id)):
        journey, principal = access(session, journey_id, request, write=True)
        run = run_for(session, journey, run_id)
        key = key_value(key)
        digest = rt.request_hash(operation, {"run_id": str(run_id), **body.model_dump(mode="json")})
        prior = rt.replay(session, journey.id, principal.traveler_id, key, digest)
        if prior is not None:
            return prior
        rt.claim_sequence(session, run, body.expected_sequence)
        with journey_business_time(session, journey.id):
            apply(journey, run, principal.traveler_id)
        result = rt.payload(run)
        rt.remember(session, run, principal.traveler_id, key, digest, result)
        session.commit()
        return result


@router.post("/runs/{run_id}/advance")
def advance(
    journey_id: UUID,
    run_id: UUID,
    body: Advance,
    request: Request,
    idempotency_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    return command(
        session,
        journey_id,
        run_id,
        request,
        idempotency_key,
        "advance",
        body,
        lambda j, r, a: rt.advance(session, j, r, minutes=body.minutes, actor_id=a),
    )


@router.post("/runs/{run_id}/scenes")
def scene(
    journey_id: UUID,
    run_id: UUID,
    body: Scene,
    request: Request,
    idempotency_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    def apply(j, r, a):
        if r.status != "RUNNING":
            raise HTTPException(409, "SIMULATION_NOT_RUNNING")
        rt.inject_scene(session, j, r, body.model_dump(mode="json", exclude={"expected_sequence"}))

    return command(session, journey_id, run_id, request, idempotency_key, "scene", body, apply)


@router.post("/runs/{run_id}/resume")
def resume(
    journey_id: UUID,
    run_id: UUID,
    body: Resume,
    request: Request,
    idempotency_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    def apply(j, r, a):
        if r.status not in {
            "PAUSED_FOR_GUARDIAN",
            "PAUSED_FOR_ACCEPTANCE",
            "PAUSED_MODEL_UNAVAILABLE",
        }:
            raise HTTPException(409, "SIMULATION_NOT_PAUSED")
        state = json.loads(r.state_json)
        event = (
            session.get(Event, state.get("pending_event_id"))
            if state.get("pending_event_id")
            else None
        )
        if event and event.status not in {"RESOLVED", "IGNORED"}:
            raise HTTPException(409, "SIMULATION_EVENT_REQUIRES_SIGNED_RESOLUTION")
        r.status = "RUNNING"
        rt.append_history(r, "SIM_RESUMED")
        r.updated_at = rt.wall_now()

    return command(session, journey_id, run_id, request, idempotency_key, "resume", body, apply)


@router.post("/runs/{run_id}/guardian")
def guardian(
    journey_id: UUID,
    run_id: UUID,
    body: Guardian,
    request: Request,
    idempotency_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    # Persist ownership before invoking a runtime which commits its own AgentRun records.
    with journey_write_lock(str(journey_id)):
        journey, principal = access(session, journey_id, request, write=True)
        run = run_for(session, journey, run_id)
        key = key_value(idempotency_key)
        digest = rt.request_hash(
            "guardian", {"run_id": str(run_id), **body.model_dump(mode="json")}
        )
        prior = rt.replay(session, journey.id, principal.traveler_id, key, digest)
        if prior is not None:
            return prior
        if run.status not in {
            "PAUSED_FOR_GUARDIAN",
            "PAUSED_MODEL_UNAVAILABLE",
            "PAUSED_REQUIRES_MISSION",
        }:
            raise HTTPException(409, "SIMULATION_GUARDIAN_NOT_PENDING")
        rt.claim_sequence(session, run, body.expected_sequence)
        run.status = "GUARDIAN_RUNNING"
        state = json.loads(run.state_json)
        state["guardian_lease_expires_at"] = (
            datetime.now(timezone.utc) + timedelta(minutes=30)
        ).isoformat()
        run.state_json = rt.encode(state)
        rt.append_history(run, "GUARDIAN_REQUESTED", model_consent=True)
        rt.remember(session, run, principal.traveler_id, key, digest, rt.payload(run))
        session.commit()
        from app.agent.guardian import scan_guardian

        try:
            with journey_business_time(session, journey.id):
                outcome = scan_guardian(session, journey, include_opportunity_signals=False)
            safe = {
                k: outcome.get(k)
                for k in ("id", "status", "action_status", "agent_run_id", "proposal_id")
            }
            run.status = (
                "PAUSED_FOR_ACCEPTANCE"
                if safe.get("proposal_id")
                else "PAUSED_REQUIRES_MISSION"
                if safe.get("action_status") == "MISSION_REQUIRED"
                else "PAUSED_MODEL_UNAVAILABLE"
            )
            rt.append_history(
                run,
                "GUARDIAN_RESULT",
                guardian=safe,
                execution_mode="SERVER_GUARDIAN_EXECUTED",
                model_execution="RUN_REFERENCE" if safe.get("agent_run_id") else "NOT_EXECUTED",
            )
        except Exception:
            session.rollback()
            session.refresh(run)
            run.status = "PAUSED_MODEL_UNAVAILABLE"
            rt.append_history(
                run, "GUARDIAN_UNAVAILABLE", error_code="GUARDIAN_RUNTIME_UNAVAILABLE"
            )
        run.updated_at = rt.wall_now()
        result = rt.payload(run)
        receipt = session.scalar(
            select(SimulationCommand).where(
                SimulationCommand.journey_id == journey.id,
                SimulationCommand.actor_id == principal.traveler_id,
                SimulationCommand.idempotency_key == key,
            )
        )
        receipt.result_json = rt.encode(result)
        session.commit()
        return result


@router.post("/runs/{run_id}/recover")
def recover(
    journey_id: UUID,
    run_id: UUID,
    body: Resume,
    request: Request,
    idempotency_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    def apply(j, r, a):
        lease = json.loads(r.state_json).get("guardian_lease_expires_at")
        if r.status != "GUARDIAN_RUNNING" or not lease:
            raise HTTPException(409, "SIMULATION_NO_INTERRUPTED_RUNTIME")
        if datetime.fromisoformat(lease) > datetime.now(timezone.utc):
            raise HTTPException(409, "SIMULATION_RUNTIME_LEASE_ACTIVE")
        r.status = "PAUSED_MODEL_UNAVAILABLE"
        r.updated_at = rt.wall_now()
        rt.append_history(r, "GUARDIAN_INTERRUPTED", error_code="RUNTIME_LEASE_EXPIRED")

    return command(session, journey_id, run_id, request, idempotency_key, "recover", body, apply)
