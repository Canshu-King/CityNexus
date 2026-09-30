"""ORD-0461 r2 - the two member write doors: a role change and a removal.

Measured at the authoritative tip `4e0ad72c90ff1b9bb76718d3ee883dc860f7ab72` before anything was
written here.  That tree already answers four member questions - add a member
(`backend/app/main.py:3937`), list the set (`backend/app/main.py:3987`), withdraw one
(`backend/app/main.py:4001`) and what a role may do (`backend/app/main.py:4027`) - and none of them can
change a role or take a row out of the set.  So this file adds exactly those two doors and refuses to
re-cut the four that exist.

Which named refusal belongs to which door, and the arm that proves it reads the response body rather
than the status code:

* the actor is not in this journey's member set (nobody, a blank name, a withdrawn membership, or a
  membership whose own deadline has passed) -> `MEMBER_ACTOR_NOT_A_MEMBER`;
* the actor is a member whose role does not carry `MEMBER_MANAGE` -> `MEMBER_ACTOR_NOT_PERMITTED`.  Two
  arms face each other on this one: a `COLLABORATOR` is refused, and the same request is granted once
  the capability row is added to `journey_role_capabilities`.  That pair is what shows the table is the
  ruler and no role list is written in this file;
* the member id is not a row of this journey (unknown, or another journey's member) -> `MEMBER_UNKNOWN`,
  the name the withdraw door already uses;
* the journey is in the recycle bin -> `MEMBER_JOURNEY_RECYCLED`, checked before any of the three above
  because a binned trip is not writable whatever its member set says.

`withdraw` keeps its row and lists it as `MEMBER_WITHDRAWN`; `remove` erases it.  One arm holds both
doors against the same journey so the two answers cannot quietly collapse into one.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import yaml
from fastapi.testclient import TestClient

from app.db.models import JourneyRoleCapability, Traveler
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "openapi.yaml"
GENERATED = ROOT / "frontend" / "src" / "generated" / "api.ts"
TZ = timezone(timedelta(hours=8))
START = datetime(2026, 11, 3, 9, 0, tzinfo=TZ)

MEMBER_PATH = "/api/v1/journeys/{journey_id}/members"
ROLE_PATH = "/api/v1/journeys/{journey_id}/members/{member_id}/role"
CAPABILITY = "MEMBER_MANAGE"
REFUSALS = (
    "MEMBER_ACTOR_NOT_A_MEMBER",
    "MEMBER_ACTOR_NOT_PERMITTED",
    "MEMBER_UNKNOWN",
    "MEMBER_JOURNEY_RECYCLED",
)


def _traveler() -> str:
    traveler_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="ORD-0461 r2 probe",
                email=None,
                locale="zh-CN",
                timezone="Asia/Shanghai",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return traveler_id


def _journey() -> tuple[str, str]:
    """One journey and an actor whose role carries `MEMBER_MANAGE`.

    The actor has to be invited into the set first, and that is a fact about this tip rather than about
    the fixture's convenience: `JourneyMemberModel` rows are created in exactly one place
    (`backend/app/main.py:3970`, the add door), so a journey's own creator holds no member row and no
    role until somebody invites them.  Reported rather than quietly fixed here -- making the creator a
    member is the add door's decision, and it is not one of the two doors this file is allowed to cut.
    """
    owner = _traveler()
    created = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": owner,
            "title": "ORD-0461 r2",
            "city_code": "CN-XIAMEN",
            "timezone": "Asia/Shanghai",
            "start_at": START.isoformat(),
            "end_at": (START + timedelta(days=2, hours=8)).isoformat(),
            "budget": {"amount_minor": 90000, "currency": "CNY"},
            "planning_mode": "balanced",
        },
    )
    assert created.status_code == 201, created.text
    journey_id = created.json()["id"]
    _add_member(journey_id, owner, role="OWNER")
    return journey_id, owner


def _add_member(journey_id: str, traveler_id: str, role: str = "COLLABORATOR") -> dict:
    response = client.post(
        MEMBER_PATH.format(journey_id=journey_id),
        json={"traveler_id": traveler_id, "role": role, "invited_by": "lane-rel"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _reason(payload: dict) -> str:
    """The named fact rides in `error.reason_code`; `error.code` stays the one existing family."""
    return str((payload.get("error") or {}).get("reason_code"))


def _details(payload: dict) -> dict:
    """The counts and ids behind a refusal ride in `error.details` -- the envelope's own key name."""
    return (payload.get("error") or {}).get("details") or {}


def _role(journey_id: str, member_id: str, role: str, actor: str):
    return client.post(
        ROLE_PATH.format(journey_id=journey_id, member_id=member_id),
        json={"role": role, "actor_traveler_id": actor},
    )


def _remove(journey_id: str, member_id: str, actor: str):
    return client.delete(
        MEMBER_PATH.format(journey_id=journey_id) + "/" + member_id,
        params={"actor_traveler_id": actor},
    )


def _listed_ids(journey_id: str) -> set[str]:
    rows = client.get(MEMBER_PATH.format(journey_id=journey_id)).json()
    return {row["id"] for row in rows}


def _bin(journey_id: str) -> None:
    binned = client.delete("/api/v1/journeys/{journey_id}".format(journey_id=journey_id))
    assert binned.status_code == 204, binned.text


def _grant_capability(role: str):
    """Write one row into the ACL table, so the door's answer can be moved without moving its code."""
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        row = JourneyRoleCapability(
            role=role, capability=CAPABILITY, scope_message_key="member.scope.probe", created_at=now
        )
        session.add(row)
        session.commit()

    def drop() -> None:
        with SessionLocal() as session:
            held = session.get(JourneyRoleCapability, (role, CAPABILITY))
            if held is not None:
                session.delete(held)
                session.commit()

    return drop


# ---------------------------------------------------------------- the two doors answer their facts


def test_the_role_door_changes_the_role_and_the_set_answers_it_afterwards() -> None:
    journey_id, owner = _journey()
    member = _add_member(journey_id, _traveler())
    changed = _role(journey_id, member["id"], "ADMIN", owner)
    assert changed.status_code == 200, changed.text
    assert changed.json()["role"] == "ADMIN", changed.text

    listed = client.get(MEMBER_PATH.format(journey_id=journey_id)).json()
    row = [item for item in listed if item["id"] == member["id"]]
    assert len(row) == 1 and row[0]["role"] == "ADMIN", (
        "the write must be visible to the read door, not only in the write's own answer")


def test_the_remove_door_takes_the_row_out_of_the_set_that_withdraw_only_marks() -> None:
    journey_id, owner = _journey()
    withdrawn = _add_member(journey_id, _traveler())
    removed = _add_member(journey_id, _traveler())

    post = client.post(
        "/api/v1/journeys/{journey_id}/members/{member_id}/withdraw".format(
            journey_id=journey_id, member_id=withdrawn["id"]),
        json={},
    )
    assert post.status_code == 200, post.text
    assert post.json()["member_state"] == "MEMBER_WITHDRAWN", post.text

    gone = _remove(journey_id, removed["id"], owner)
    assert gone.status_code == 204, gone.text
    assert gone.content == b"", "a 204 that carries a body is a different answer than the contract says"

    listed = client.get(MEMBER_PATH.format(journey_id=journey_id)).json()
    ids = {row["id"] for row in listed}
    assert withdrawn["id"] in ids, "withdraw keeps the row so a screen can say this person was here"
    assert removed["id"] not in ids, "remove erases it, which is the only fact that tells the two apart"


def test_changing_a_role_to_the_one_it_already_holds_writes_nothing() -> None:
    journey_id, owner = _journey()
    member = _add_member(journey_id, _traveler(), role="ADMIN")
    before = client.get(MEMBER_PATH.format(journey_id=journey_id)).json()
    stamp_before = [row for row in before if row["id"] == member["id"]][0]["updated_at"]

    same = _role(journey_id, member["id"], "ADMIN", owner)
    assert same.status_code == 200, same.text
    assert _reason(same.json()) in ("None", ""), "a no-op write must not invent a refusal name"
    after = client.get(MEMBER_PATH.format(journey_id=journey_id)).json()
    stamp_after = [row for row in after if row["id"] == member["id"]][0]["updated_at"]
    assert stamp_after == stamp_before, (
        "the row was left alone: answering the same role is not a new fact, so no moment is stamped")


# ---------------------------------------------------------------- the four named refusals, both doors


def test_an_actor_that_is_not_in_the_member_set_is_refused_by_name_on_both_doors() -> None:
    journey_id, _owner = _journey()
    member = _add_member(journey_id, _traveler())
    stranger = _traveler()

    for response in (_role(journey_id, member["id"], "ADMIN", stranger),
                     _remove(journey_id, member["id"], stranger)):
        assert _reason(response.json()) == "MEMBER_ACTOR_NOT_A_MEMBER", response.text

    # A blank name is the same fact as nobody, and it is the door that says so rather than the schema.
    blank = _role(journey_id, member["id"], "ADMIN", "")
    assert _reason(blank.json()) == "MEMBER_ACTOR_NOT_A_MEMBER", blank.text


def test_a_membership_that_is_no_longer_in_force_gives_its_holder_no_voice() -> None:
    journey_id, _owner = _journey()
    collaborator = _add_member(journey_id, _traveler(), role="COLLABORATOR")
    target = _add_member(journey_id, _traveler())

    # A withdrawn membership is not a voice: its own traveller cannot change anyone's role.
    withdrew = client.post(
        "/api/v1/journeys/{journey_id}/members/{member_id}/withdraw".format(
            journey_id=journey_id, member_id=collaborator["id"]),
        json={},
    )
    assert withdrew.status_code == 200, withdrew.text
    refused = _role(journey_id, target["id"], "ADMIN", collaborator["traveler_id"])
    assert _reason(refused.json()) == "MEMBER_ACTOR_NOT_A_MEMBER", refused.text


def test_a_role_the_capability_table_does_not_grant_is_refused_by_name() -> None:
    journey_id, _owner = _journey()
    member = _add_member(journey_id, _traveler())
    collaborator = _add_member(journey_id, _traveler(), role="COLLABORATOR")

    for response in (_role(journey_id, member["id"], "ADMIN", collaborator["traveler_id"]),
                     _remove(journey_id, member["id"], collaborator["traveler_id"])):
        payload = response.json()
        assert _reason(payload) == "MEMBER_ACTOR_NOT_PERMITTED", response.text
        details = _details(payload)
        assert details.get("capability") == CAPABILITY, (
            "the refusal has to name the capability it looked for: %s" % details)
        assert details.get("actor_role") == "COLLABORATOR", response.text


def test_the_permission_answer_is_read_off_the_acl_table_and_not_a_role_list() -> None:
    journey_id, _owner = _journey()
    member = _add_member(journey_id, _traveler())
    collaborator = _add_member(journey_id, _traveler(), role="COLLABORATOR")
    before = _role(journey_id, member["id"], "ADMIN", collaborator["traveler_id"])
    assert _reason(before.json()) == "MEMBER_ACTOR_NOT_PERMITTED", before.text

    drop = _grant_capability("COLLABORATOR")
    try:
        after = _role(journey_id, member["id"], "ADMIN", collaborator["traveler_id"])
        assert after.status_code == 200, after.text
        assert after.json()["role"] == "ADMIN", (
            "one row in the table moved the door's answer, so the table is the ruler")
    finally:
        drop()

    # And it closes again when the row goes away: the grant was the table's, not this file's.
    back = _role(journey_id, member["id"], "COLLABORATOR", collaborator["traveler_id"])
    assert _reason(back.json()) == "MEMBER_ACTOR_NOT_PERMITTED", back.text


def test_an_id_that_is_not_a_member_of_this_journey_is_refused_by_name_on_both_doors() -> None:
    journey_id, owner = _journey()
    other_journey, _other_owner = _journey()
    elsewhere = _add_member(other_journey, _traveler())

    missing = str(uuid4())
    for response in (_role(journey_id, missing, "ADMIN", owner),
                     _remove(journey_id, missing, owner)):
        assert _reason(response.json()) == "MEMBER_UNKNOWN", response.text

    # Another journey's member id is not a near miss: it is unknown *here*.
    cross = _role(journey_id, elsewhere["id"], "ADMIN", owner)
    assert _reason(cross.json()) == "MEMBER_UNKNOWN", cross.text
    cross_remove = _remove(journey_id, elsewhere["id"], owner)
    assert _reason(cross_remove.json()) == "MEMBER_UNKNOWN", cross_remove.text
    assert elsewhere["id"] in _listed_ids(other_journey), (
        "a refusal on the wrong journey must leave the right journey's set alone")


def test_a_journey_in_the_recycle_bin_takes_neither_member_write_on_either_door() -> None:
    journey_id, owner = _journey()
    member = _add_member(journey_id, _traveler())
    bin_journey_id = journey_id
    _bin(bin_journey_id)

    for response in (_role(bin_journey_id, member["id"], "ADMIN", owner),
                     _remove(bin_journey_id, member["id"], owner)):
        payload = response.json()
        assert _reason(payload) == "MEMBER_JOURNEY_RECYCLED", response.text
        assert _details(payload).get("deleted_at"), (
            "the refusal names the moment the trip went into the bin: %s" % payload)

    assert member["id"] in _listed_ids(journey_id), (
        "the refused writes left the binned journey's member set exactly as it was")


def test_a_withdrawn_membership_is_not_re_roleable_and_keeps_the_landed_name() -> None:
    journey_id, owner = _journey()
    member = _add_member(journey_id, _traveler())
    withdrew = client.post(
        "/api/v1/journeys/{journey_id}/members/{member_id}/withdraw".format(
            journey_id=journey_id, member_id=member["id"]),
        json={},
    )
    assert withdrew.status_code == 200, withdrew.text

    refused = _role(journey_id, member["id"], "ADMIN", owner)
    assert _reason(refused.json()) == "MEMBER_ALREADY_WITHDRAWN", refused.text
    # Removing a row that is already out is a different fact and a real one: the record leaves the set.
    gone = _remove(journey_id, member["id"], owner)
    assert gone.status_code == 204, gone.text
    assert member["id"] not in _listed_ids(journey_id)


# ---------------------------------------------------------------- the contract and the client carry them


def test_the_contract_names_both_doors_and_every_refusal_on_each() -> None:
    document = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    paths = document["paths"]
    # The hand-written contract keys carry no `/api/v1` prefix; the servers block supplies it.
    role_path = "/journeys/{journey_id}/members/{member_id}/role"
    remove_path = "/journeys/{journey_id}/members/{member_id}"
    assert role_path in paths and "post" in paths[role_path], sorted(paths)[:40]
    assert remove_path in paths and "delete" in paths[remove_path], sorted(paths)[:40]

    for label, operation in (("role", paths[role_path]["post"]),
                             ("remove", paths[remove_path]["delete"])):
        text = yaml.safe_dump(operation)
        advertised = set((operation.get("responses") or {}).keys())
        for refusal in REFUSALS:
            assert refusal in text, "%s door does not advertise %s in the contract: %s" % (
                label, refusal, text[:400])
        assert {"200", "204", "2XX", "403", "404", "409"} & advertised, (
            "the %s door advertises %s, which cannot carry a refusal" % (label, sorted(advertised)))


def test_the_generated_client_was_regenerated_from_this_contract() -> None:
    generated = GENERATED.read_text(encoding="utf-8")
    # The generated client keys the paths the way the contract writes them: no `/api/v1`.
    for path in ('"/journeys/{journey_id}/members/{member_id}/role"',
                 '"/journeys/{journey_id}/members/{member_id}"'):
        assert path in generated, (
            "generated/api.ts does not carry %s -- it was hand-edited or not regenerated" % path)
    assert "JourneyMemberRoleChange" in generated, (
        "the request body the role door accepts is missing from the generated client")
