"""Server-owned transactional recovery execution semantics."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

PLANNED = "PLANNED"
WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
EXECUTING = "EXECUTING"
PARTIALLY_APPLIED = "PARTIALLY_APPLIED"
COMPLETED = "COMPLETED"
FAILED_SAFE = "FAILED_SAFE"
NEEDS_ATTENTION = "NEEDS_ATTENTION"

TERMINAL = frozenset({COMPLETED, PARTIALLY_APPLIED, FAILED_SAFE, NEEDS_ATTENTION})


@dataclass(frozen=True)
class RecoveryExecutionAction:
    kind: str
    target_type: str
    target_id: str
    provider_key: str | None = None
    requires_approval: bool = True

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind.upper(),
            "target_type": self.target_type,
            "target_id": self.target_id,
            "provider_key": self.provider_key,
            "requires_approval": bool(self.requires_approval),
        }


def action_fingerprint(
    *,
    journey_id: str,
    recovery_epoch_id: str,
    action: RecoveryExecutionAction,
) -> str:
    payload = {
        "journey_id": str(journey_id),
        "recovery_epoch_id": str(recovery_epoch_id),
        "action": action.semantic_payload(),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def classify_execution_state(
    action_statuses: Iterable[str],
    *,
    unresolved_required_actions: bool = False,
) -> str:
    statuses = [str(item).upper() for item in action_statuses]
    if not statuses:
        return PLANNED
    if any(item == "RUNNING" for item in statuses):
        return EXECUTING
    succeeded = sum(item in {"SUCCEEDED", "COMPLETED", "CONFIRMED", "CANCELLED"} for item in statuses)
    failed = sum(item in {"FAILED", "ERROR", "DECLINED"} for item in statuses)
    pending = sum(item in {"PENDING", "WAITING_FOR_APPROVAL"} for item in statuses)
    if pending and succeeded == 0 and failed == 0:
        return WAITING_FOR_APPROVAL
    if failed and succeeded:
        return PARTIALLY_APPLIED
    if failed and succeeded == 0:
        return FAILED_SAFE
    if unresolved_required_actions:
        return NEEDS_ATTENTION
    return COMPLETED


def is_sandbox_provider(provider_key: str | None) -> bool:
    key = str(provider_key or "").lower()
    return key.startswith(("mock-", "sandbox-", "lab-"))


def provider_truth_label(provider_key: str | None) -> str:
    return "LAB_SANDBOX_PROVIDER" if is_sandbox_provider(provider_key) else "EXTERNAL_PROVIDER"


def model_supplied_transaction_fields_are_forbidden(payload: dict[str, Any]) -> bool:
    """The model may request intent, never claim provider-side transaction truth."""
    forbidden = {
        "external_ref",
        "provider_external_ref",
        "provider_status",
        "booking_status",
        "payment_status",
        "provider_success",
        "confirmed",
    }
    return any(key in payload for key in forbidden)
