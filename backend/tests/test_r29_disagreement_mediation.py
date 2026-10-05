from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from app.agent.runtime import _acceptance_requested, _collective_mediation_requested
from app.db.models import JourneyMission


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_r29_disagreement_mediation_is_not_authority_to_accept_a_side() -> None:
    mission = JourneyMission(
        id=str(uuid4()),
        journey_id=str(uuid4()),
        traveler_id=str(uuid4()),
        user_text=(
            "Mediate the unresolved shared Journey disagreement without choosing a winner."
        ),
        requested_autonomy="EXECUTE_WITHIN_BOUNDS",
        resolved_intent_json=json.dumps(
            {
                "collective_mediation": {
                    "kind": "DISAGREEMENT_MEDIATION",
                    "round": 1,
                    "required_member_ids": ["member-owner", "member-admin"],
                    "member_choices": [
                        {"member_id": "member-owner", "proposal_id": "proposal-garden"},
                        {"member_id": "member-admin", "proposal_id": "proposal-museum"},
                    ],
                }
            },
            sort_keys=True,
        ),
        status="CREATED",
        created_at=_now(),
    )

    assert _collective_mediation_requested(mission) is True
    assert _acceptance_requested(mission) is False


def test_r29_plan_only_mediator_stays_non_mutating() -> None:
    mission = JourneyMission(
        id=str(uuid4()),
        journey_id=str(uuid4()),
        traveler_id=str(uuid4()),
        user_text="Mediate the disagreement.",
        requested_autonomy="PLAN_ONLY",
        resolved_intent_json=json.dumps(
            {"collective_mediation": {"kind": "DISAGREEMENT_MEDIATION", "round": 1}}
        ),
        status="CREATED",
        created_at=_now(),
    )

    assert _collective_mediation_requested(mission) is True
    assert _acceptance_requested(mission) is False
