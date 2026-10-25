"""Explicit database and presenter boundary for classroom credentials."""

import hmac
import ipaddress
import os
from pathlib import Path
from urllib.parse import urlsplit

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
    if (not expected.is_absolute() or expected.resolve() != actual
            or actual.name.lower() in {"citynexus.db", "_live.db"}):
        raise HTTPException(503, "DEMO_DATABASE_NOT_ISOLATED")


def _loopback(host: str | None) -> bool:
    try:
        return bool(host and ipaddress.ip_address(host).is_loopback)
    except ValueError:
        return host == "localhost"


def require_demo_presenter(request: Request, session: Session) -> None:
    require_demo_database(session)
    configured = os.getenv("CITYNEXUS_DEMO_PRESENTER_KEY", "")
    supplied = request.headers.get("X-CityNexus-Presenter-Key", "")
    if len(configured) >= 32 and hmac.compare_digest(supplied, configured):
        return
    # Forwarded headers never establish local access. Reject cross-origin browser probes.
    origin = request.headers.get("Origin")
    if (request.client and _loopback(request.client.host)
            and (not origin or _loopback(urlsplit(origin).hostname))):
        return
    raise HTTPException(403, "DEMO_PRESENTER_REQUIRED")
