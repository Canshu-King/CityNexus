from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime

from fastapi import HTTPException

from app.core.config import settings
from app.db.models import SimulationClock
from app.demo_access import require_demo_database
from app.execution.clock import execution_clock

_simulation_scope = ContextVar("simulation_scope", default=False)


def simulation_scope_active():
    return _simulation_scope.get()


@contextmanager
def journey_business_time(session, journey_id):
    value = None
    if settings.simulation_enabled:
        try:
            require_demo_database(session)
            clock = session.get(SimulationClock, str(journey_id))
            value = datetime.fromisoformat(clock.virtual_now) if clock else None
        except HTTPException:
            pass
    if value is None:
        yield
    else:
        token = _simulation_scope.set(True)
        try:
            with execution_clock.freeze(value):
                yield
        finally:
            _simulation_scope.reset(token)
