"""ORD-0685 -- who is the traveller this request speaks for?

The authoritative line had no door that could answer that, which is why the Copilot cache fix
(Issue 27) could only choose "never store anything": a key bound to a journey cannot tell two
people on that journey apart.  This module is the missing answer, and only the answer -- it
verifies a signed principal, it never invents one.

The token is the shape the design line already carries (`backend/app/traveler_principal.py`
on `design/revolution-mobile-first-v1`), kept deliberately compatible so the two lines do not
grow two identity schemes: a base64url JSON payload `{v, aud, sub, iat, exp}` and a base64url
HMAC-SHA256 signature over the payload, joined by a dot.  It is accepted from
`Authorization: Bearer <token>` or `X-CityNexus-Traveler-Token: <token>`.

Two rules this file exists to keep:

* no configured secret means **refuse** (503, named), never "accept anything";
* every refusal carries a `reason_code` the screen can branch on (ORD-0101's envelope reads
  the attribute off the exception), so a 401 is not one undifferentiated sentence.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Traveler

_TOKEN_VERSION = 1
_TOKEN_AUDIENCE = "citynexus-traveler"

REASON_NOT_CONFIGURED = "TRAVELER_AUTH_NOT_CONFIGURED"
REASON_CREDENTIALS_MISSING = "TRAVELER_CREDENTIALS_MISSING"
REASON_CREDENTIALS_INVALID = "TRAVELER_CREDENTIALS_INVALID"
REASON_CREDENTIALS_EXPIRED = "TRAVELER_CREDENTIALS_EXPIRED"
REASON_PRINCIPAL_UNKNOWN = "TRAVELER_PRINCIPAL_NOT_FOUND"
# ORD-0687: the credential was fine, the trip it is being used on was not this person's.
# Two different facts from two different doors, so the screen can say which one happened.
REASON_JOURNEY_NOT_SCOPED = "JOURNEY_POINTER_NOT_OURS"
REASON_TRAVELER_NOT_PRINCIPAL = "TRAVELER_NOT_PRINCIPAL"


@dataclass(frozen=True)
class TravelerPrincipal:
    traveler_id: str
    auth_method: str
    expires_at: int


def _refuse(status: int, message: str, reason_code: str) -> HTTPException:
    """One refusal shape: the message is for logs, the reason_code is for the screen."""

    exc = HTTPException(status, message)
    exc.reason_code = reason_code
    return exc


SESSION_STATE_SIGNED = "SIGNED"
SESSION_STATE_NOT_CONFIGURED = "NOT_CONFIGURED"
SESSION_STATE_MISCONFIGURED = "MISCONFIGURED"


def signing_state() -> str:
    """Can this process sign a traveller at all -- decided in one place, not per caller.

    The create door (ORD-0687) and the verifier must agree: a short secret is an operator
    mistake that has to look different, on the screen and in a test, from "this build never
    turned identity on".  Anything that asks twice will eventually answer twice differently.
    """

    configured = (settings.traveler_auth_secret or "").strip()
    if not configured:
        return SESSION_STATE_NOT_CONFIGURED
    if len(configured.encode("utf-8")) < 32:
        return SESSION_STATE_MISCONFIGURED
    return SESSION_STATE_SIGNED


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _secret() -> bytes:
    configured = settings.traveler_auth_secret
    if not configured:
        raise _refuse(503, "traveller principal verifier is not configured", REASON_NOT_CONFIGURED)
    encoded = configured.encode("utf-8")
    if len(encoded) < 32:
        # A short secret is a misconfiguration, not a traveller's mistake: refuse the door
        # loudly instead of accepting signatures an offline guess can forge.
        raise _refuse(503, "traveller principal secret is too short", REASON_NOT_CONFIGURED)
    return encoded


def _token_ttl(ttl_seconds: int | None) -> int:
    """One place decides how long a window is, so nothing can be told a second different expiry."""

    ttl = int(settings.traveler_auth_ttl_seconds if ttl_seconds is None else ttl_seconds)
    if ttl <= 0 or ttl > 86_400:
        raise ValueError("traveller token ttl must be between 1 and 86400 seconds")
    return ttl


def issue_traveler_token(
    traveler_id: str,
    *,
    ttl_seconds: int | None = None,
    now: int | None = None,
) -> str:
    """Sign a short-lived token for one traveller.

    Server-side helper, not a public door: an identity provider (or a trusted operator/test
    process) mints the token after it has authenticated the person.  There is deliberately no
    route that hands one out from a bare `traveler_id`.
    """

    clock = int(time.time() if now is None else now)
    ttl = _token_ttl(ttl_seconds)
    payload = {
        "v": _TOKEN_VERSION,
        "aud": _TOKEN_AUDIENCE,
        "sub": str(traveler_id),
        "iat": clock,
        "exp": clock + ttl,
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _b64encode(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{signature}"


def renew_traveler_session(
    traveler_id: str,
    *,
    ttl_seconds: int | None = None,
    now: int | None = None,
) -> tuple[str, int]:
    """Sign a fresh window *and* return the expiry the signature actually carries.

    Why this is here instead of `issue_traveler_token` plus arithmetic in the route: a renewal
    answer has to tell the client how long it has, and a second computation of `now + ttl` would
    be a number the token never promised.  One call, one clock, both halves from the same tick.
    """

    clock = int(time.time() if now is None else now)
    token = issue_traveler_token(traveler_id, ttl_seconds=ttl_seconds, now=clock)
    return token, clock + _token_ttl(ttl_seconds)


def _presented_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization", "")
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        return value.strip()
    explicit = request.headers.get("X-CityNexus-Traveler-Token")
    return explicit.strip() if explicit and explicit.strip() else None


def presented_principal(
    request: Request,
    session: Session,
    *,
    now: int | None = None,
) -> TravelerPrincipal | None:
    """The signed traveller behind this request, or `None` when nobody presented a credential.

    This is the seam the journey doors use (ORD-0687).  Today an anonymous request keeps working
    exactly as it did -- this build has no password wall to switch on -- but the moment a token
    *is* presented it stops being optional: a token that fails verification refuses by name, and
    a token that verifies narrows what that request may see.  That is the smallest rule that
    closes the real defect ("the phone still holds the previous traveller's journey uuid, so show
    it") without turning identity on for every other caller in one leap.
    """

    if _presented_token(request) is None:
        return None
    return resolve_traveler_principal(request, session, now=now)


def resolve_traveler_principal(
    request: Request,
    session: Session,
    *,
    now: int | None = None,
) -> TravelerPrincipal:
    """Verify the presented token and return the principal it names, or refuse by name."""

    token = _presented_token(request)
    if token is None:
        raise _refuse(401, "signed traveller credentials are required", REASON_CREDENTIALS_MISSING)
    # The verifier's own configuration is a server fact, so it is judged before the caller's
    # token is judged: an unconfigured door must not answer "your credentials are malformed"
    # about a token it never had the means to check.
    secret = _secret()
    body, _, signature = token.partition(".")
    if not body or not signature:
        raise _refuse(401, "traveller credentials are malformed", REASON_CREDENTIALS_INVALID)
    expected = _b64encode(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise _refuse(401, "traveller credentials are invalid", REASON_CREDENTIALS_INVALID)
    try:
        payload: dict[str, Any] = json.loads(_b64decode(body).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _refuse(401, "traveller credentials are invalid", REASON_CREDENTIALS_INVALID) from exc
    if payload.get("v") != _TOKEN_VERSION or payload.get("aud") != _TOKEN_AUDIENCE:
        raise _refuse(401, "traveller credentials are invalid", REASON_CREDENTIALS_INVALID)
    traveler_id = str(payload.get("sub") or "")
    try:
        issued_at = int(payload.get("iat"))
        expires_at = int(payload.get("exp"))
    except (TypeError, ValueError) as exc:
        raise _refuse(401, "traveller credentials are invalid", REASON_CREDENTIALS_INVALID) from exc
    clock = int(time.time() if now is None else now)
    if not traveler_id or issued_at > clock + 60:
        raise _refuse(401, "traveller credentials are invalid", REASON_CREDENTIALS_INVALID)
    if expires_at <= clock:
        raise _refuse(401, "traveller credentials have expired", REASON_CREDENTIALS_EXPIRED)
    if session.get(Traveler, traveler_id) is None:
        # The signature was genuine, but the person it names is gone: that is a different fact
        # from "your token is bad", and the screen deserves to see which one it is.
        raise _refuse(401, "traveller principal no longer exists", REASON_PRINCIPAL_UNKNOWN)
    return TravelerPrincipal(
        traveler_id=traveler_id,
        auth_method="SIGNED_HMAC_BEARER",
        expires_at=expires_at,
    )
