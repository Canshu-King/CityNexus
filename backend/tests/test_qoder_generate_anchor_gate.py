"""Mission 002 C: the generate path must honour a paid C4 anchor it cannot place.

``app/services.py:_journey_constraints_with_capabilities`` is the one place on
``POST /plans/generate`` that turns durable ACTIVE ``C4_Anchored`` commitments
into hard planner constraints.  The RX-4 Worker measured (and this file re-proves
on the authoritative tree) that changing that single predicate to
``C3_Guaranteed`` leaves the whole truth suite green while generation quietly
returns candidates built as if the traveller had never paid: the constraint
assembly disappears, nothing else on this path re-adds it.

Two nodes, deliberately not more:

  * the refusal itself - an anchor no planner can reach must make generation
    fail and name the anchor, never be reported as satisfied;
  * the premise plus a control - the fixture must really be the single-guard
    case (nothing else pins this node), and the same payload without a
    confirmed commitment must still generate, so the refusal above can only be
    caused by the C4 constraint assembly this mutant deletes.

The cruise/booking scenario is *not* repeated here: it is protected twice over
(the schedule-pinning pass covers what the assembly covers), so asserting it
would duplicate existing gates while killing nothing.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.models import Activity, Commitment, Journey
from app.db.session import SessionLocal
from app.main import app

# Not a place in the demo fixture and not resolvable from any coordinate, so the
# only thing that can put this node into a plan is the commitment's hard
# constraint.  Renaming it changes nothing; making it resolvable would collapse
# the gate into the double-protected case the next docstring explains.
UNREACHABLE_KEY = "place-qoder-gate-unreachable"
CONFIRMATION_REF = "QODER-GENERATE-C4-GATE"


def _reservation(*, anchor_role: str) -> dict:
    return {
        "reservation_type": "FERRY",
        "provider_key": "qoder-generate-gate",
        "confirmation_ref": f"{CONFIRMATION_REF}-{anchor_role}",
        "origin": {"name": "Tianjin Port", "latitude": 39.0, "longitude": 117.7},
        "destination": {"name": "Nowhere Terminal", "latitude": 38.0, "longitude": 118.0},
        "scheduled_departure_at": "2026-10-10T13:00:00+08:00",
        "scheduled_arrival_at": "2026-10-10T13:40:00+08:00",
        "price_amount_minor": 3200,
        "currency": "CNY",
        "price_status": "KNOWN",
        "anchor_role": anchor_role,
        "semantic_node_key": UNREACHABLE_KEY,
    }


def _journey_with_active_plan(client: TestClient) -> str:
    journey_id = client.post("/api/v1/demo/reset").json()["journey_id"]
    generated = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
    )
    assert generated.status_code == 201, generated.text
    plan = generated.json()[0]
    selected = client.post(f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select")
    assert selected.status_code == 200, selected.text
    return journey_id


def _import_reservation(client: TestClient, journey_id: str, *, confirm: bool) -> str | None:
    imported = client.post(
        f"/api/v1/journeys/{journey_id}/inbox/import",
        json={"artifact_type": "STRUCTURED_JSON", "payload": {"reservation": _reservation(
            anchor_role="MID_TRIP")}},
    )
    assert imported.status_code == 201, imported.text
    draft_id = imported.json()["id"]
    if not confirm:
        return None
    confirmed = client.post(f"/api/v1/journeys/{journey_id}/inbox/{draft_id}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()["commitment"]["id"]


def _active_c4(session, journey_id: str) -> list[Commitment]:
    return list(
        session.query(Commitment)
        .filter_by(journey_id=journey_id, status="ACTIVE", level="C4_Anchored")
        .all()
    )


def _active_plan_version_id(session, journey_id: str) -> str:
    """The plan the product itself considers live, read from the Journey pointer."""
    journey = session.get(Journey, journey_id)
    assert journey is not None and journey.active_plan_version_id, (
        f"journey {journey_id} has no ACTIVE plan version to check against"
    )
    return str(journey.active_plan_version_id)


def test_unresolvable_paid_anchor_makes_generation_refuse_by_name() -> None:
    """The mutant target: drop the ACTIVE-C4 assembly and this becomes a 201.

    With the predicate pointed at ``C3_Guaranteed`` the commitment stops being a
    constraint, the solver never sees the anchor, and the route answers 201 with
    candidates that leave a paid commitment out and say nothing about it.  That
    is exactly the fabricated-truth shape this whole line of gates exists for,
    one layer above the projection.
    """
    client = TestClient(app)
    journey_id = _journey_with_active_plan(client)
    commitment_id = _import_reservation(client, journey_id, confirm=True)
    assert commitment_id is not None

    with SessionLocal() as session:
        assert [row.id for row in _active_c4(session, journey_id)] == [commitment_id]

    response = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 3}
    )
    if response.status_code == 201:
        offenders = [
            plan["id"]
            for plan in response.json()
            if not any(item.get("place_id") == UNREACHABLE_KEY for item in plan["activities"])
        ]
        raise AssertionError(
            "generation answered 201 while a paid C4 anchor is unbuilt; the "
            "hard-constraint assembly is the only guard on this path and it did "
            f"not run. Candidates that omit {commitment_id}: {offenders}"
        )
    assert response.status_code == 422, response.text
    message = response.json()["error"]["message"]
    assert "C4_ANCHOR_UNRESOLVED" in message, message
    assert UNREACHABLE_KEY in message, (
        "a refusal that does not name the anchor it cannot honour is not "
        f"actionable for the traveller: {message}"
    )


def test_the_refusal_is_caused_by_the_commitment_and_nothing_else() -> None:
    """Premise + control, so the gate above cannot pass for the wrong reason.

    Two things have to hold for the 422 above to be evidence about the C4
    constraint assembly: no Activity anywhere in the ACTIVE plan carries this
    node (so nothing else can pin it into a schedule), and the identical
    reservation without a confirmed commitment generates normally (so the
    refusal is not the payload shape talking).
    """
    client = TestClient(app)
    _planned = _journey_with_active_plan(client)
    with SessionLocal() as session:
        strays = session.query(Activity).filter(Activity.place_id == UNREACHABLE_KEY).count()
    assert strays == 0, "the seeded fixture already holds the unreachable anchor node"

    control_journey = _journey_with_active_plan(client)
    _import_reservation(client, control_journey, confirm=False)
    with SessionLocal() as session:
        assert _active_c4(session, control_journey) == [], (
            "an unconfirmed draft must not create an ACTIVE C4 commitment; "
            "without this the control below proves nothing"
        )
    control = client.post(
        f"/api/v1/journeys/{control_journey}/plans/generate", json={"candidate_count": 3}
    )
    assert control.status_code == 201, control.text
    assert len(control.json()) == 3

    gated = _journey_with_active_plan(client)
    _import_reservation(client, gated, confirm=True)
    with SessionLocal() as session:
        anchored = _active_c4(session, gated)
        assert len(anchored) == 1
        assert anchored[0].activity_id is None, (
            "the gate only discriminates while no Activity stands behind the "
            "commitment: an activity_id here means the fixture collapsed into "
            "the double-protected booking case"
        )
        pinned_key = _active_plan_version_id(session, gated)
        pinned = session.query(Activity).filter_by(
            place_id=UNREACHABLE_KEY, plan_version_id=pinned_key
        ).count()
        assert pinned == 0, "the ACTIVE plan already pins the node; another guard exists"
        refusal = client.post(
            f"/api/v1/journeys/{gated}/plans/generate", json={"candidate_count": 3}
        )
    assert refusal.status_code == 422, refusal.text
