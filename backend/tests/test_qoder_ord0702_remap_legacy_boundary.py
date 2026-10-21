"""ORD-0702 slice B: a departure anchor says *leave by*, whatever release wrote it.

The role of a persisted C4 policy is now read through one shared function, because a row written
before ``anchor_role`` existed states its node only in ``semantic_node_key``.  The feasibility gate
and the schedule injector were fixed in ORD-0700; this door - the one that re-binds a commitment
onto a replacement activity - still read ``anchor_role`` straight off the policy, so a legacy
departure anchor was remapped as if it constrained the *start* of its activity.  That is the
opposite of what the traveller confirmed, and it is silent: the plan passes, the wrong end moves.

``activity`` is the commitment's current activity, which ``resolve_commitment_target`` passes in;
``None`` is the shape a freshly imported anchor has, so the boundary must not depend on it.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from app.replanning.commitment_remap import commitment_identity

ANCHOR_PLACE_ID = "160022ba-d830-53ca-970a-f38b0e42fb1c"
SCHEDULED = "2026-10-11T15:00:00+08:00"


def _activity(*, semantic_key: str, place_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        metadata_json=json.dumps({"semantic_key": semantic_key}),
        place_id=place_id,
        city_service_id=None,
    )


def test_a_legacy_departure_node_still_constrains_the_end() -> None:
    identity = commitment_identity(
        policy={
            "semantic_key": ANCHOR_PLACE_ID,
            "semantic_node_key": "departure-anchor",
            "scheduled_start_at": SCHEDULED,
            "source": "USER_CONFIRMED_EXTERNAL_RESERVATION",
        },
        activity=None,
    )

    assert identity.boundary == "END"
    assert identity.scheduled_at == SCHEDULED
    assert ANCHOR_PLACE_ID in identity.strong


def test_the_old_alias_for_the_same_node_also_reads_as_a_departure() -> None:
    identity = commitment_identity(
        policy={"semantic_node_key": "anchor:departure", "scheduled_start_at": SCHEDULED},
        activity=None,
    )

    assert identity.boundary == "END"


def test_a_legacy_arrival_node_keeps_constraining_the_start() -> None:
    identity = commitment_identity(
        policy={
            "semantic_key": ANCHOR_PLACE_ID,
            "semantic_node_key": "arrival-anchor",
            "scheduled_start_at": "2026-10-09T08:00:00+08:00",
        },
        activity=None,
    )

    assert identity.boundary == "START"


def test_an_explicit_role_answers_exactly_as_the_legacy_node_key_does() -> None:
    """One rule, one answer: the pre-existing shape must not drift as the legacy one is fixed."""

    explicit = commitment_identity(
        policy={"anchor_role": "DEPARTURE", "scheduled_start_at": SCHEDULED}, activity=None
    )
    legacy = commitment_identity(
        policy={"semantic_node_key": "departure-anchor", "scheduled_start_at": SCHEDULED},
        activity=None,
    )

    assert explicit.boundary == legacy.boundary == "END"


def test_a_booking_anchor_keeps_its_own_identity_and_its_start() -> None:
    activity = _activity(semantic_key="place-tea-house-0001", place_id="place-tea-house-0001")
    identity = commitment_identity(
        policy={
            "semantic_key": "booking-ref-77",
            "scheduled_start_at": "2026-10-10T19:30:00+08:00",
            "source": "MOCK_BOOKING_PROVIDER",
        },
        activity=activity,
    )

    assert identity.boundary == "START"
    assert identity.strong == {"booking-ref-77", "place-tea-house-0001"}


def test_the_remap_door_no_longer_reads_the_role_straight_off_the_policy() -> None:
    """A second role reader is how the two doors disagree again."""

    source = (
        Path(__file__).resolve().parents[1] / "app" / "replanning" / "commitment_remap.py"
    ).read_text(encoding="utf-8")

    assert 'policy.get("anchor_role")' not in source
    assert "anchor_role_from_policy(policy)" in source
