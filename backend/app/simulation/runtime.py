from datetime import datetime, timedelta, timezone
import hashlib
import json
import random
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, update

from app.core.audit import record_audit
from app.db.models import Activity, Place, PlanVersion, SimulationClock
from app.execution.truth import append_execution_truth, SIMULATED_STATE_TRANSITION
from app.simulation.models import SimulationRun, SimulationCommand


def wall_now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def request_hash(operation, body):
    return hashlib.sha256(encode({"operation": operation, "body": body}).encode()).hexdigest()


def replay(session, journey_id, actor, key, digest):
    row = session.scalar(
        select(SimulationCommand).where(
            SimulationCommand.journey_id == journey_id,
            SimulationCommand.actor_id == actor,
            SimulationCommand.idempotency_key == key,
        )
    )
    if row:
        if row.request_sha256 != digest:
            raise HTTPException(409, "IDEMPOTENCY_KEY_REUSED")
        return json.loads(row.result_json)


def payload(run):
    return {
        "run_id": run.id,
        "journey_id": run.journey_id,
        "city_code": run.city_code,
        "seed": run.seed,
        "virtual_now": run.virtual_now,
        "timezone": run.timezone,
        "sequence": run.sequence,
        "status": run.status,
        "state": json.loads(run.state_json),
        "history": json.loads(run.history_json),
        "execution_truth": SIMULATED_STATE_TRANSITION,
        "updated_at": run.updated_at,
    }


def remember(session, run, actor, key, digest, result):
    session.add(
        SimulationCommand(
            id=str(uuid4()),
            journey_id=run.journey_id,
            run_id=run.id,
            actor_id=actor,
            idempotency_key=key,
            request_sha256=digest,
            result_json=encode(result),
            created_at=wall_now(),
        )
    )


def append_history(run, event, **data):
    history = json.loads(run.history_json)
    history.append(
        {
            "sequence": run.sequence,
            "event": event,
            "virtual_now": run.virtual_now,
            "recorded_at": wall_now(),
            **data,
        }
    )
    run.history_json = encode(history)


def persist_clock(session, run):
    row = session.get(SimulationClock, run.journey_id)
    if row is None:
        row = SimulationClock(
            journey_id=run.journey_id, virtual_now=run.virtual_now, version=0, updated_at=wall_now()
        )
        session.add(row)
    row.virtual_now, row.updated_at = run.virtual_now, wall_now()
    row.version += 1


def claim_sequence(session, run, expected):
    changed = session.execute(
        update(SimulationRun)
        .where(SimulationRun.id == run.id, SimulationRun.sequence == expected)
        .values(sequence=expected + 1)
        .execution_options(synchronize_session=False)
    )
    if changed.rowcount != 1:
        raise HTTPException(409, "SIMULATION_SEQUENCE_STALE")
    session.refresh(run)


def activities(session, journey):
    plan = (
        session.get(PlanVersion, journey.active_plan_version_id)
        if journey.active_plan_version_id
        else None
    )
    if not plan or plan.journey_id != journey.id or plan.status != "ACTIVE":
        raise HTTPException(409, "SIMULATION_REQUIRES_NATIVE_ACTIVE_PLAN")
    rows = list(
        session.scalars(
            select(Activity)
            .where(Activity.plan_version_id == plan.id)
            .order_by(Activity.sequence_no)
        )
    )
    if not rows:
        raise HTTPException(409, "SIMULATION_PLAN_EMPTY")
    return rows


def snapshot_reference(session, journey):
    plan = session.get(PlanVersion, journey.active_plan_version_id)
    raw = plan.mobility_evidence_json or "{}"
    evidence = json.loads(raw)
    qualities = sorted(
        {
            str(row.get("fact_quality") or "UNKNOWN")
            for row in evidence.get("facts", [])
            if isinstance(row, dict)
        }
    )
    return {
        "plan_version_id": plan.id,
        "snapshot_id": plan.mobility_snapshot_id,
        "sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "captured_at": evidence.get("captured_at"),
        "fact_qualities": qualities,
        "provenance": "CAPTURED_PROVIDER_SNAPSHOT"
        if qualities == ["LIVE_PROVIDER_CAPTURE"]
        else "TEST_PROVIDER"
        if "EXPLICIT_FROZEN_FIXTURE" in qualities
        else "UNKNOWN",
    }


def start_run(session, journey, actor, seed):
    if journey.status != "ACTIVE":
        raise HTTPException(409, "SIMULATION_REQUIRES_NATIVE_ACTIVE_JOURNEY")
    activities(session, journey)
    if session.scalar(select(SimulationRun).where(SimulationRun.journey_id == journey.id)):
        raise HTTPException(409, "SIMULATION_RUN_ALREADY_EXISTS")
    stamp = datetime.fromisoformat(journey.start_at)
    if stamp.tzinfo is None:
        raise HTTPException(409, "JOURNEY_TIMEZONE_OFFSET_REQUIRED")
    clock = session.get(SimulationClock, journey.id)
    if clock:
        stamp = max(stamp, datetime.fromisoformat(clock.virtual_now))
    run = SimulationRun(
        id=str(uuid4()),
        journey_id=journey.id,
        actor_id=actor,
        city_code=journey.city_code,
        seed=seed,
        timezone=journey.timezone,
        virtual_now=stamp.isoformat(),
        sequence=0,
        status="RUNNING",
        state_json=encode(
            {
                "plan_version_id": journey.active_plan_version_id,
                "location": None,
                "completed_activity_ids": [],
                "provider_snapshot_refs": [snapshot_reference(session, journey)],
                "suggested_scene": random.Random(seed).choice(
                    ["CLOSURE", "WEATHER", "SCHEDULE_DELAY"]
                ),
            }
        ),
        history_json="[]",
        created_at=wall_now(),
        updated_at=wall_now(),
    )
    session.add(run)
    append_history(run, "SIM_STARTED")
    persist_clock(session, run)
    session.flush()
    return run


def _transition(session, journey, run, row, status, actor_id):
    from app.execution.activity_state import require_simulated_transition

    require_simulated_transition(session, journey, row, status)
    meta = json.loads(row.metadata_json or "{}")
    append_execution_truth(
        meta,
        kind=SIMULATED_STATE_TRANSITION,
        transition=status,
        captured_at=run.virtual_now,
        actor_type="TRAVELER",
        actor_id=actor_id,
        evidence={
            "simulation_run_id": run.id,
            "sequence": run.sequence,
            "recorded_at": wall_now(),
            "location_source": "SIMULATED_GPS",
        },
    )
    row.metadata_json, row.status, row.updated_at = encode(meta), status, wall_now()
    journey.current_activity_id = row.id
    event = {
        "EN_ROUTE": "SIM_DEPARTURE",
        "ARRIVED": "SIM_ARRIVAL",
        "IN_PROGRESS": "SIM_EXPERIENCE",
        "COMPLETED": "SIM_ACTIVITY_COMPLETED",
    }[status]
    append_history(run, event, activity_id=row.id)


def advance(session, journey, run, *, minutes=None, actor_id=None):
    if run.status != "RUNNING":
        raise HTTPException(409, "SIMULATION_NOT_RUNNING")
    rows = activities(session, journey)
    state = json.loads(run.state_json)
    if state["plan_version_id"] != journey.active_plan_version_id:
        append_history(
            run,
            "SIM_PLAN_CHANGED",
            before_plan_id=state["plan_version_id"],
            after_plan_id=journey.active_plan_version_id,
        )
        state["provider_snapshot_refs"].append(snapshot_reference(session, journey))
    now = datetime.fromisoformat(run.virtual_now)
    target = now + timedelta(minutes=minutes) if minutes is not None else None
    # Every native phase is visited, including when a single advance crosses midnight.
    progressed = False
    for row in rows:
        if row.status in {"COMPLETED", "SKIPPED", "CANCELLED"}:
            continue
        start, end = datetime.fromisoformat(row.start_at), datetime.fromisoformat(row.end_at)
        if start.tzinfo is None or end.tzinfo is None or end < start:
            raise HTTPException(409, "ACTIVITY_TIME_INVALID")
        travel = max(0, int(row.travel_from_prev_min or 0))
        timeline = [
            ("EN_ROUTE", start - timedelta(minutes=travel)),
            ("ARRIVED", start),
            ("IN_PROGRESS", start),
            ("COMPLETED", end),
        ]
        status_index = {
            "PENDING": -1,
            "PLANNED": -1,
            "READY": -1,
            "NOT_STARTED": -1,
            "ACTIVE": -1,
            "EN_ROUTE": 0,
            "ARRIVED": 1,
            "IN_PROGRESS": 2,
        }.get(row.status)
        if status_index is None:
            raise HTTPException(409, "SIMULATION_ACTIVITY_STATE_INVALID")
        for status, at in timeline[status_index + 1 :]:
            effective = max(now, at)
            if target is not None and effective > target:
                break
            run.virtual_now = effective.isoformat()
            _transition(session, journey, run, row, status, actor_id or run.actor_id)
            if status == "ARRIVED" and row.place_id:
                place = session.get(Place, row.place_id)
                if place:
                    state["location"] = {
                        "latitude": place.latitude,
                        "longitude": place.longitude,
                        "place_id": place.id,
                        "source": "SIMULATED_GPS",
                        "classification": "SCENARIO_SIMULATED_LOCATION",
                        "captured_virtual_at": run.virtual_now,
                        "recorded_at": wall_now(),
                        "coordinate_system": place.coordinate_system or "WGS84",
                    }
            if status == "COMPLETED":
                state["completed_activity_ids"] = list(
                    dict.fromkeys([*state["completed_activity_ids"], row.id])
                )
                remaining = [
                    item
                    for item in rows
                    if item.status not in {"COMPLETED", "SKIPPED", "CANCELLED"}
                ]
                if remaining:
                    remaining[0].status = "ACTIVE"
                    journey.current_activity_id = remaining[0].id
            now, progressed = effective, True
            if target is None:
                break
        if target is None or row.status != "COMPLETED":
            break
    pending = [row for row in rows if row.status not in {"COMPLETED", "SKIPPED", "CANCELLED"}]
    if not pending:
        run.status = "SIMULATED_COMPLETED"
        journey.status, journey.current_activity_id = "COMPLETED", None
        append_history(run, "SIMULATED_COMPLETED")
    else:
        journey.current_activity_id = pending[0].id
    if target is not None and run.status == "RUNNING":
        run.virtual_now = target.isoformat()
        append_history(run, "SIM_CLOCK_ADVANCED", minutes=minutes)
    elif not progressed and run.status == "RUNNING":
        raise HTTPException(409, "SIMULATION_NO_PROGRESS")
    state["plan_version_id"] = journey.active_plan_version_id
    run.state_json, run.updated_at = encode(state), wall_now()
    journey.updated_at = wall_now()
    persist_clock(session, run)
    record_audit(
        session,
        action="simulation.advanced",
        entity_type="SimulationRun",
        entity_id=run.id,
        journey_id=journey.id,
        actor_type="TRAVELER",
        actor_id=actor_id or run.actor_id,
        after={"sequence": run.sequence, "virtual_now": run.virtual_now, "status": run.status},
    )


def inject_scene(session, journey, run, scene):
    from app.agent.signal_pipeline import (
        _upsert_fixture_event,
        set_fixture_state,
        _record_observation,
    )

    state = json.loads(run.state_json)
    if scene["scene_id"] in state.get("scene_ids", []):
        raise HTTPException(409, "SIMULATION_SCENE_ALREADY_APPLIED")
    row = session.get(Activity, scene["activity_id"])
    if (
        not row
        or row.plan_version_id != journey.active_plan_version_id
        or row.status in {"COMPLETED", "SKIPPED", "CANCELLED"}
    ):
        raise HTTPException(409, "SIMULATION_SCENE_ACTIVITY_INVALID")
    set_fixture_state(
        session,
        journey,
        state="DISRUPTED",
        payload={
            "source": "CLASSROOM_SIMULATION",
            "simulation_run_id": run.id,
            "scene_id": scene["scene_id"],
        },
    )
    event, _ = _upsert_fixture_event(
        session,
        journey,
        event_type=scene["event_type"],
        severity="MAJOR",
        activity=row,
        scope_key=row.place_id or row.id,
        occurred_at=run.virtual_now,
        provenance="SIMULATED",
        payload={
            "source": "CLASSROOM_SIMULATION",
            "simulation_run_id": run.id,
            "scene_id": scene["scene_id"],
            "disruption_class": scene["event_type"],
            "delay_minutes": scene.get("delay_minutes", 0),
            "is_closed": scene["event_type"] == "CLOSURE",
        },
    )
    state["scene_ids"] = [*state.get("scene_ids", []), scene["scene_id"]]
    state["pending_event_id"] = event.id
    observation = _record_observation(
        session,
        journey,
        state="DISRUPTED",
        payload={
            "simulation_run_id": run.id,
            "scene_id": scene["scene_id"],
            "environment_provenance": "SIMULATED",
            "virtual_now": run.virtual_now,
            "active_plan_version_id": journey.active_plan_version_id,
        },
        fingerprints=[json.loads(event.payload_json)["incident_fingerprint"]],
        captured_at=wall_now(),
        provider_key="classroom-simulation",
        provenance="REPLAY",
    )
    state["provider_observation_ids"] = [*state.get("provider_observation_ids", []), observation.id]
    run.status, run.state_json = "PAUSED_FOR_GUARDIAN", encode(state)
    run.updated_at = wall_now()
    append_history(
        run,
        "SIM_SCENE_INJECTED",
        scene_id=scene["scene_id"],
        event_id=event.id,
        environment_provenance="SIMULATED",
    )
