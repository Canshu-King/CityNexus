"""Reform 2026-10-18, second baton: a recovery credential the person holds.

The night order's line was "no bare traveler_id or uuid for a token", and the 2026-10-18 probe
closed the cheap alternative: the refresh door refuses a credential the server has already named
expired. So the way back has to be an actual re-authentication, not a later deletion.

This module is that door's server half:

  - issuing: the server generates 32 random bytes, stores only an HMAC-SHA256 digest bound to the
    credential id, and returns the secret exactly once;
  - redeeming: constant-time comparison, single use, expiry, revocation, and a per-credential
    failure counter that locks the credential for a while;
  - signing: the redeemed session is minted by the same `renew_traveler_session` every other door
    uses, so this adds a way in, not a second identity system.

The lifecycle is server-side because the client cannot be trusted to forget: a used credential that
still worked would be a replay, and a revoked one that still worked would make revocation a word.
"""

from __future__ import annotations

import hmac
import secrets
import time
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models import TravelerRecoveryCredential
from app.traveler_principal import recovery_digest

RECOVERY_TTL_SECONDS = 30 * 24 * 3600
MAX_FAILED_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60


class RecoveryRefusal(Exception):
    """A named refusal, so the route answers with a reason code rather than a guess."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _iso(clock: float) -> str:
    return datetime.fromtimestamp(clock, timezone.utc).isoformat()


def _instant(value: str) -> float:
    return datetime.fromisoformat(value).timestamp()


def issue_recovery_credential(
    session: Session, traveler_id: str, *, now: float | None = None
) -> dict[str, object]:
    clock = time.time() if now is None else now
    credential_id = str(uuid4())
    secret = secrets.token_urlsafe(32)
    row = TravelerRecoveryCredential(
        id=credential_id,
        traveler_id=str(traveler_id),
        digest=recovery_digest(credential_id, secret),
        created_at=_iso(clock),
        expires_at=_iso(clock + RECOVERY_TTL_SECONDS),
        failed_attempts=0,
    )
    session.add(row)
    session.commit()
    return {
        "recovery_id": credential_id,
        # Returned exactly once. The server keeps only the digest.
        "recovery_secret": secret,
        "expires_at": row.expires_at,
        "shown_once": True,
    }


def redeem_recovery_credential(
    session: Session, credential_id: str, secret: str, *, now: float | None = None
) -> TravelerRecoveryCredential:
    clock = time.time() if now is None else now
    row = session.get(TravelerRecoveryCredential, credential_id)
    if row is None:
        raise RecoveryRefusal(401, "RECOVERY_UNKNOWN", "this recovery credential does not exist")
    if row.revoked_at is not None:
        raise RecoveryRefusal(401, "RECOVERY_REVOKED", "this recovery credential was revoked")
    if row.used_at is not None:
        raise RecoveryRefusal(401, "RECOVERY_USED", "this recovery credential has already been used")
    if _instant(row.expires_at) <= clock:
        raise RecoveryRefusal(401, "RECOVERY_EXPIRED", "this recovery credential has expired")
    if row.locked_until is not None and _instant(row.locked_until) > clock:
        raise RecoveryRefusal(
            429, "RECOVERY_LOCKED", "too many wrong attempts; wait before trying again"
        )
    if not hmac.compare_digest(row.digest, recovery_digest(credential_id, secret)):
        row.failed_attempts = int(row.failed_attempts or 0) + 1
        if row.failed_attempts >= MAX_FAILED_ATTEMPTS:
            row.locked_until = _iso(clock + LOCK_SECONDS)
        session.commit()
        raise RecoveryRefusal(
            401, "RECOVERY_SECRET_MISMATCH", "that is not this credential's secret"
        )
    # Consume atomically. Two tabs presenting the same secret at the same instant must not both get
    # a session: the read above cannot decide that, so the UPDATE carries the condition and its
    # row count is the verdict. The loser re-reads to name why it lost.
    consumed = session.execute(
        update(TravelerRecoveryCredential)
        .where(
            TravelerRecoveryCredential.id == credential_id,
            TravelerRecoveryCredential.used_at.is_(None),
            TravelerRecoveryCredential.revoked_at.is_(None),
        )
        .values(used_at=_iso(clock), failed_attempts=0)
    )
    if consumed.rowcount != 1:
        session.rollback()
        latest = session.get(TravelerRecoveryCredential, credential_id)
        if latest is not None and latest.revoked_at is not None:
            raise RecoveryRefusal(401, "RECOVERY_REVOKED", "this recovery credential was revoked")
        raise RecoveryRefusal(401, "RECOVERY_USED", "this recovery credential has already been used")
    session.commit()
    return session.get(TravelerRecoveryCredential, credential_id)  # type: ignore[return-value]


def revoke_recovery_credential(
    session: Session, traveler_id: str, credential_id: str, *, now: float | None = None
) -> TravelerRecoveryCredential:
    clock = time.time() if now is None else now
    row = session.get(TravelerRecoveryCredential, credential_id)
    if row is None or row.traveler_id != str(traveler_id):
        raise RecoveryRefusal(
            404, "RECOVERY_UNKNOWN", "no such recovery credential for this traveller"
        )
    if row.revoked_at is None:
        row.revoked_at = _iso(clock)
        session.commit()
    return row
