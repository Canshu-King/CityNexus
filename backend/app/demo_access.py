"""Explicit database and presenter boundary for classroom credentials."""

import hmac
import hashlib
import os
from pathlib import Path

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings


def require_demo_database(session: Session) -> None:
    if not settings.demo_mode or settings.environment.lower() in {"production", "prod"}:
        raise HTTPException(404, "DEMO_DISABLED")
    declared = os.getenv("CITYNEXUS_DEMO_DATABASE_PATH", "")
    url = session.get_bind().url
    if not declared or url.get_backend_name() != "sqlite" or not url.database:
        raise HTTPException(503, "DEMO_DATABASE_NOT_ISOLATED")
    expected = Path(declared)
    actual = Path(url.database).resolve()
    if (
        not expected.is_absolute()
        or expected.resolve() != actual
        or actual.name.lower() in {"citynexus.db", "_live.db"}
    ):
        raise HTTPException(503, "DEMO_DATABASE_NOT_ISOLATED")


def database_binding(session: Session) -> str:
    path = os.path.normcase(str(Path(session.get_bind().url.database).resolve()))
    return hashlib.sha256(path.encode()).hexdigest()


def require_demo_presenter(
    request: Request, session: Session, *, journey_id: str | None = None
) -> None:
    require_demo_database(session)
    configured = os.getenv("CITYNEXUS_DEMO_PRESENTER_KEY", "")
    supplied = request.headers.get("X-CityNexus-Presenter-Key", "")
    if len(configured) >= 32 and supplied.isascii() and hmac.compare_digest(supplied, configured):
        return
    if journey_id is not None:
        from app.traveler_principal import resolve_traveler_principal

        try:
            principal = resolve_traveler_principal(request, session)
            if principal.demo_presenter_journey_id == str(
                journey_id
            ) and principal.demo_database_sha256 == database_binding(session):
                return
        except HTTPException:
            pass
    raise HTTPException(403, "DEMO_PRESENTER_REQUIRED")
