from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    journey_id: Mapped[str] = mapped_column(ForeignKey("journeys.id"), unique=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("travelers.id"))
    city_code: Mapped[str] = mapped_column(String)
    seed: Mapped[int] = mapped_column(Integer)
    timezone: Mapped[str] = mapped_column(String)
    virtual_now: Mapped[str] = mapped_column(String)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String)
    state_json: Mapped[str] = mapped_column(Text, default="{}")
    history_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)


class SimulationCommand(Base):
    __tablename__ = "simulation_commands"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    journey_id: Mapped[str] = mapped_column(ForeignKey("journeys.id"))
    run_id: Mapped[str] = mapped_column(ForeignKey("simulation_runs.id"))
    actor_id: Mapped[str] = mapped_column(ForeignKey("travelers.id"))
    idempotency_key: Mapped[str] = mapped_column(String)
    request_sha256: Mapped[str] = mapped_column(String)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String)
    __table_args__ = (UniqueConstraint("journey_id", "actor_id", "idempotency_key"),)
