"""Product-facing reasoning-runtime state for the Autonomous Journey Operator."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeCandidate:
    key: str
    configured: bool
    provider_label: str
    model_label: str | None = None


def configured_runtime_candidates(settings: Any) -> list[RuntimeCandidate]:
    """Return supported external reasoning runtimes without probing providers."""

    candidates: list[RuntimeCandidate] = []

    hermes_compat = bool(
        getattr(settings, "hermes_api_url", None)
        and getattr(settings, "hermes_api_key", None)
    )
    candidates.append(
        RuntimeCandidate(
            key="hermes",
            configured=hermes_compat,
            provider_label="Hermes-compatible",
            model_label=getattr(settings, "hermes_model", None),
        )
    )

    deepseek = bool(getattr(settings, "ai_api_key", None))
    candidates.append(
        RuntimeCandidate(
            key="deepseek",
            configured=deepseek,
            provider_label="DeepSeek",
            model_label=getattr(settings, "ai_model", None),
        )
    )

    native_hermes = bool(
        getattr(settings, "hermes_native_api_url", None)
        and getattr(settings, "hermes_api_server_key", None)
    )
    candidates.append(
        RuntimeCandidate(
            key="hermes-native",
            configured=native_hermes,
            provider_label="Hermes native",
            model_label=getattr(settings, "hermes_native_model", None),
        )
    )
    return candidates


def safe_external_handoff(*, tool_step_count: int, approval_created: bool) -> bool:
    """Cross-provider handoff is safe only before the run influenced domain action."""

    return int(tool_step_count) == 0 and not approval_created


def operator_brain_state(
    *,
    configured_candidates: list[RuntimeCandidate],
    selected_runtime: str | None = None,
    active_agent_status: str | None = None,
    blocked_recovery_pending: bool = False,
    last_failure_reason: str | None = None,
    safe_to_resume: bool = False,
) -> dict[str, Any]:
    configured = [item for item in configured_candidates if item.configured]

    if active_agent_status in {"RUNNING", "PLANNING"}:
        state = "ACTIVE"
        headline = "I’m working out the best recovery."
    elif blocked_recovery_pending and configured and safe_to_resume:
        state = "RECOVERING"
        headline = "Planning is available again. I can continue the recovery."
    elif not configured:
        state = "UNCONFIGURED"
        headline = "I’m watching your trip, but no planning AI is connected."
    elif blocked_recovery_pending:
        state = "TEMPORARILY_UNAVAILABLE"
        headline = (
            "I noticed a problem. My planning AI is unavailable, so I’m holding "
            "the trip state and will retry safely."
        )
    elif last_failure_reason:
        state = "TEMPORARILY_UNAVAILABLE"
        headline = "My planning AI is temporarily unavailable."
    else:
        state = "READY"
        headline = "Planning AI is ready."

    return {
        "state": state,
        "headline": headline,
        "configured_runtimes": [item.key for item in configured],
        "preferred_runtime": selected_runtime or (configured[0].key if configured else None),
        "last_failure_reason": last_failure_reason,
        "recovery_resume": {
            "pending": bool(blocked_recovery_pending),
            "safe_to_resume": bool(safe_to_resume),
        },
    }
