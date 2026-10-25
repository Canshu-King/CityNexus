"""Regression coverage for server-owned identifiers passed to Guardian recovery."""

from __future__ import annotations

import json
from types import SimpleNamespace

from app.agent import guardian as guardian_module


def test_recovery_mission_exposes_authoritative_ids_without_changing_gates(monkeypatch):
    journey = SimpleNamespace(id="journey-server-id", traveler_id="traveler-id")
    standing = SimpleNamespace(
        id="standing-mission-id",
        user_text="Keep the protected stop unchanged.",
        objective_codes_json='["PRESERVE_COMMITMENTS"]',
        protected_activity_ids_json='["protected-activity-id"]',
        mutable_activity_ids_json='["affected-activity-id"]',
        intent_json='{"requested_mode":"PLAN_ONLY"}',
        resolved_intent_json=(
            '{"authority":{"mode":"PLAN_ONLY"},'
            '"server_owned_recovery_context":{"journey_id":"forged-journey",'
            '"trigger_event_id":"forged-trigger"}}'
        ),
        allowed_action_classes_json='["REPLAN"]',
        unresolved_references_json="[]",
        compiler_provider_key="fixture-compiler",
        compiler_model_key="fixture-model",
        compiler_confidence=1.0,
        max_cost_delta_minor=5000,
        max_loss_minor=0,
        max_schedule_drift_min=60,
        preferences_json="{}",
        requested_autonomy="PLAN_ONLY",
    )
    trigger = SimpleNamespace(
        id="trigger-event-id",
        event_type="CLOSURE",
        severity="MAJOR",
        affected_activity_id="affected-activity-id",
    )
    added = []
    session = SimpleNamespace(add=added.append, flush=lambda: None)
    monkeypatch.setattr(guardian_module, "record_audit", lambda *args, **kwargs: None)

    recovery = guardian_module._recovery_mission(session, journey, standing, trigger)

    expected_binding = {
        "journey_id": journey.id,
        "standing_mission_id": standing.id,
        "recovery_mission_id": recovery.id,
        "trigger_event_id": trigger.id,
        "trigger_event_type": trigger.event_type,
        "trigger_severity": trigger.severity,
        "affected_activity_id": trigger.affected_activity_id,
    }
    resolved_intent = json.loads(recovery.resolved_intent_json)
    assert resolved_intent["authority"] == {"mode": "PLAN_ONLY"}
    assert resolved_intent["server_owned_recovery_context"] == expected_binding

    marker = "Server-owned recovery binding JSON (authoritative identifiers only):\n"
    user_binding = recovery.user_text.split(marker, maxsplit=1)[1].splitlines()[0]
    assert json.loads(user_binding) == expected_binding
    assert json.loads(user_binding) == resolved_intent["server_owned_recovery_context"]
    assert recovery.journey_id == journey.id
    assert recovery.parent_mission_id == standing.id
    assert recovery.trigger_event_id == trigger.id
    for field in (
        "objective_codes_json",
        "protected_activity_ids_json",
        "mutable_activity_ids_json",
        "intent_json",
        "allowed_action_classes_json",
        "unresolved_references_json",
        "max_cost_delta_minor",
        "max_loss_minor",
        "max_schedule_drift_min",
        "preferences_json",
        "requested_autonomy",
    ):
        assert getattr(recovery, field) == getattr(standing, field)
    assert recovery.is_standing is False
    assert added == [recovery]

