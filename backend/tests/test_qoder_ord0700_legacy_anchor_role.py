"""ORD-0700 slice A: a C4 row written before ``anchor_role`` still names its node.

The policy below is read verbatim from the live preview library - commitment
``bf6d8757`` on the Tianjin journey, created before ``anchor_role`` was part of
the shape, stating its node in ``semantic_node_key`` instead.  Until that second
statement is allowed to answer, the row keeps the database Place id it stored,
while every candidate the planner emits is keyed by the structural anchor, so the
feasibility gate drops the whole batch with ``LOCKED_COMMITMENT_LOST`` and the
traveller is told the model refused.

The tests below pin both halves of the fix: the constraint the gate compares, and
the node identity the write door claims.  They disagree, the journey answers
``C4_ANCHOR_OVERLAP`` instead - so a change to one must move the other.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from app.planning.anchors import (
    ARRIVAL_ROLE,
    DEPARTURE_ROLE,
    anchor_claim_identity,
    anchor_identity_from_policy,
    anchor_role_from_policy,
    structural_place_id,
)
from app.replanning.protected_commitments import active_c4_hard_constraints

JOURNEY_ID = "1cfb54f2-5934-4161-99e0-5aa78ec16706"
LEGACY_PLACE_ID = "160022ba-d830-53ca-970a-f38b0e42fb1c"

LEGACY_ARRIVAL_POLICY = {
    "price_status": "KNOWN",
    "scheduled_start_at": "2026-10-09T08:00:00+08:00",
    "semantic_key": LEGACY_PLACE_ID,
    "semantic_node_key": "arrival-anchor",
    "source": "USER_CONFIRMED_EXTERNAL_RESERVATION",
}


def _commitment(policy: dict, *, journey_id: str = JOURNEY_ID) -> SimpleNamespace:
    return SimpleNamespace(
        status="ACTIVE",
        level="C4_Anchored",
        journey_id=journey_id,
        policy_json=json.dumps(policy),
    )


def _params(policy: dict) -> dict:
    constraints = active_c4_hard_constraints([_commitment(policy)])
    assert [row["rule_code"] for row in constraints] == ["LOCKED_COMMITMENT"], constraints
    return constraints[0]["params"]


def test_legacy_arrival_row_reaches_the_structural_anchor_identity() -> None:
    params = _params(LEGACY_ARRIVAL_POLICY)

    assert params["anchor_role"] == ARRIVAL_ROLE
    assert params["semantic_ref"] == structural_place_id(JOURNEY_ID, ARRIVAL_ROLE)
    assert params["semantic_ref"] != LEGACY_PLACE_ID
    assert params["location_evidence"] == "STRUCTURAL_ANCHOR"
    assert params["time_boundary"] == "START"


def test_legacy_node_key_alone_is_enough_for_the_identity_view() -> None:
    identity = anchor_identity_from_policy(LEGACY_ARRIVAL_POLICY, journey_id=JOURNEY_ID)

    assert identity.role == ARRIVAL_ROLE
    assert identity.semantic_key == structural_place_id(JOURNEY_ID, ARRIVAL_ROLE)


def test_the_door_that_claims_the_node_agrees_with_the_door_that_constrains_it() -> None:
    """Half-recognition is how a journey ends up overlapping with itself."""

    claimed = anchor_claim_identity(LEGACY_ARRIVAL_POLICY, journey_id=JOURNEY_ID)
    constrained = _params(LEGACY_ARRIVAL_POLICY)["semantic_ref"]

    assert claimed == constrained == structural_place_id(JOURNEY_ID, ARRIVAL_ROLE)


def test_legacy_departure_alias_is_not_read_as_arrival() -> None:
    policy = dict(LEGACY_ARRIVAL_POLICY, semantic_node_key="anchor:departure")
    params = _params(policy)

    assert params["anchor_role"] == DEPARTURE_ROLE
    assert params["semantic_ref"] == structural_place_id(JOURNEY_ID, DEPARTURE_ROLE)
    assert params["time_boundary"] == "END"
    assert anchor_role_from_policy(policy) == DEPARTURE_ROLE


def test_a_booking_anchor_keeps_its_own_place_identity() -> None:
    """The negative control: a commerce row names a place, not a planner node."""

    policy = {
        "price_status": "KNOWN",
        "scheduled_start_at": "2026-10-09T19:30:00+08:00",
        "semantic_key": "place-tea-house-0001",
        "source": "MOCK_BOOKING_PROVIDER",
    }
    params = _params(policy)

    assert params["anchor_role"] == ""
    assert params["semantic_ref"] == "place-tea-house-0001"
    assert params["generator_owns_anchor"] is False
    assert params["location_evidence"] == "RESOLVED"
    assert anchor_claim_identity(policy, journey_id=JOURNEY_ID) is None


def test_a_row_with_nothing_to_say_stays_on_the_activity_id_path() -> None:
    """No role, no structural node, no schedule: emitted by neither door."""

    policy = {"price_status": "KNOWN", "semantic_key": LEGACY_PLACE_ID, "source": "IMPORTED"}

    assert active_c4_hard_constraints([_commitment(policy)]) == []
    assert anchor_role_from_policy(policy) == ""
    assert anchor_claim_identity(policy, journey_id=JOURNEY_ID) is None
