import json

from sqlalchemy import select

from app.db.models import Event
from app.simulation.models import SimulationRun


def refresh_run_signals(session, journey, fixture):
    """Reuse the injected scene; a worker refresh must not invent another disruption."""
    from app.agent.signal_pipeline import SignalPipelineResult

    data = json.loads(fixture.payload_json)
    run = session.get(SimulationRun, data["simulation_run_id"])
    if run is None or run.journey_id != journey.id:
        raise ValueError("simulation fixture is not bound to this Journey")
    state = json.loads(run.state_json)
    events = list(
        session.scalars(
            select(Event).where(
                Event.journey_id == journey.id,
                Event.status.in_(["DETECTED", "ACKNOWLEDGED"]),
                Event.provenance == "SIMULATED",
                Event.payload_json.contains(run.id),
            )
        )
    )
    return SignalPipelineResult(
        provider_key="classroom-simulation",
        state="DISRUPTED" if events else "NORMAL",
        observation_ids=tuple(state.get("provider_observation_ids", [])),
        event_ids=tuple(event.id for event in events),
        created_event_ids=(),
        resolved_event_ids=(),
        degraded=False,
        provider_states={"environment": "SIMULATED"},
        provider_provenance={"environment": "SIMULATED"},
        captured_at=fixture.updated_at,
    )
