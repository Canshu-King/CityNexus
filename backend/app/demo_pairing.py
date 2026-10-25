"""Operator-issued, single-use classroom pairing tickets."""

import hashlib
import secrets
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ForeignKey, Integer, String, select, text, update
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.db.models import Base, Journey, JourneyMember
from app.db.session import get_session
from app.demo_access import require_demo_database, require_demo_presenter, database_binding
from app.traveler_principal import _member_is_in_force, member_has_capability, issue_traveler_token


class DemoPairingTicket(Base):
    __tablename__ = "demo_pairing_tickets"
    ticket_sha256: Mapped[str] = mapped_column(String, primary_key=True)
    journey_id: Mapped[str] = mapped_column(ForeignKey("journeys.id"))
    traveler_id: Mapped[str] = mapped_column(ForeignKey("travelers.id"))
    expires_at: Mapped[int] = mapped_column(Integer)
    consumed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DemoPairingAttempt(Base):
    __tablename__ = "demo_pairing_attempts"
    bucket: Mapped[str] = mapped_column(String, primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer)


router = APIRouter(prefix="/api/v1/demo/pairing", tags=["demo pairing"])


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    journey_id: UUID


class Redeem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket: str = Field(min_length=32, max_length=200)


def owner_seat(session, journey):
    seat = session.scalar(
        select(JourneyMember).where(
            JourneyMember.journey_id == journey.id, JourneyMember.traveler_id == journey.traveler_id
        )
    )
    if (
        not seat
        or not _member_is_in_force(seat)
        or not member_has_capability(session, seat, "JOURNEY_READ")
    ):
        raise HTTPException(403, "DEMO_OWNER_MEMBERSHIP_REQUIRED")


@router.post("", status_code=201)
def issue(
    body: Issue, request: Request, response: Response, session: Session = Depends(get_session)
):
    require_demo_presenter(request, session)
    journey = session.get(Journey, str(body.journey_id))
    if not journey or journey.deleted_at:
        raise HTTPException(404, "DEMO_JOURNEY_NOT_FOUND")
    owner_seat(session, journey)
    ticket = secrets.token_urlsafe(32)
    expires = int(time.time()) + 120
    session.add(
        DemoPairingTicket(
            ticket_sha256=hashlib.sha256(ticket.encode()).hexdigest(),
            journey_id=journey.id,
            traveler_id=journey.traveler_id,
            expires_at=expires,
        )
    )
    session.commit()
    response.headers["Cache-Control"] = "private, no-store"
    return {"ticket": ticket, "expires_at": expires, "journey_id": journey.id}


@router.post("/redeem")
def redeem(
    body: Redeem, request: Request, response: Response, session: Session = Depends(get_session)
):
    require_demo_database(session)
    now = int(time.time())
    # Limit the actual peer, not caller-controlled Forwarded headers. A proxy shares this bucket.
    peer = hashlib.sha256(
        str(request.client.host if request.client else "unknown").encode()
    ).hexdigest()
    bucket = f"{peer}:{now // 60}"
    session.execute(
        text(
            "INSERT INTO demo_pairing_attempts (bucket,attempts) VALUES (:bucket,1) "
            "ON CONFLICT(bucket) DO UPDATE SET attempts=attempts+1"
        ),
        {"bucket": bucket},
    )
    attempts = session.execute(
        text("SELECT attempts FROM demo_pairing_attempts WHERE bucket=:bucket"), {"bucket": bucket}
    ).scalar_one()
    session.commit()
    if attempts > 20:
        raise HTTPException(
            429, "DEMO_PAIRING_RATE_LIMITED", headers={"Retry-After": str(60 - now % 60)}
        )
    digest = hashlib.sha256(body.ticket.encode()).hexdigest()
    row = session.get(DemoPairingTicket, digest)
    if row is None or row.consumed_at is not None or row.expires_at <= now:
        raise HTTPException(401, "DEMO_PAIRING_INVALID_OR_EXPIRED")
    journey = session.get(Journey, row.journey_id)
    if journey is None or journey.deleted_at or journey.traveler_id != row.traveler_id:
        raise HTTPException(401, "DEMO_PAIRING_INVALID_OR_EXPIRED")
    owner_seat(session, journey)
    changed = session.execute(
        update(DemoPairingTicket)
        .where(
            DemoPairingTicket.ticket_sha256 == digest,
            DemoPairingTicket.consumed_at.is_(None),
            DemoPairingTicket.expires_at > now,
        )
        .values(consumed_at=now)
    ).rowcount
    if changed != 1:
        raise HTTPException(401, "DEMO_PAIRING_INVALID_OR_EXPIRED")
    token = issue_traveler_token(
        row.traveler_id,
        ttl_seconds=900,
        demo_presenter_journey_id=journey.id,
        demo_database_sha256=database_binding(session),
    )
    session.commit()
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "access_token": token,
        "traveler_id": row.traveler_id,
        "journey_id": journey.id,
        "journey_title": journey.title,
        "expires_in": 900,
    }
