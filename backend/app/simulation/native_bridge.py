from fastapi import HTTPException
from sqlalchemy import select

from app.simulation.models import SimulationRun


def require_native_execution_unmanaged(session, journey_id):
    if session.scalar(select(SimulationRun.id).where(SimulationRun.journey_id == str(journey_id))):
        raise HTTPException(409, "USE_SIMULATION_RUN_ADVANCE")
