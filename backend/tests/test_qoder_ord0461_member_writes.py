"""ORD-0461 - the three membership write doors, and the five named refusals that fence them.

The tables were already on the tip (`journey_members`, `journey_role_capabilities`,
`journey_share_grants`); what was missing was any way to change a membership.  The gap this file
closes is the one the order named: 无权限者改角色 / 对已移除者再操作 / 最后一个创建者退出 /
成员数越上限 / 目标行程在回收站里.

Every arm asserts the **body**'s `error.reason_code`, because a status code cannot tell a screen which
sentence to show: 409 is also "already withdrawn", "in the bin", "at the cap" and "you are not a
member".  A few arms also assert the status, but never as the judgement.

Permission is read out of `journey_role_capabilities` rather than compared in Python, so the ADMIN arm
below is the proof that the table decides: ADMIN carries `MEMBER_MANAGE` and therefore works, while
COLLABORATOR does not and is refused.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import yaml
from fastapi.testclient import TestClient

from app.db.models import Traveler
from app.db.session import SessionLocal
from app.main import JOURNEY_MEMBER_CAP, app

client = TestClient(app, raise_server_exceptions=False)
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "openapi.yaml"

MEMBER_PATH = "/api/v1/journeys/{journey_id}/members"
ROLE_PATH = "/api/v1/journeys/{journey_id}/members/{member_id}/role"
WITHDRAW_PATH = "/api/v1/journeys/{journey_id}/members/{member_id}/withdraw"
LEAVE_PATH = "/api/v1/journeys/{journey_id}/members/leave"


def _reason(body: object) -> str | None:
    if not isinstance(body, dict):
        return None
    return (body.get("error") or {}).get("reason_code")


def _traveler() -> str:
    traveler_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="ORD-0461 probe",
                email=None,
                locale="zh-CN",
                timezone="Asia/Shanghai",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return traveler_id


def _journey(owner: str | None = None) -> tuple[str, str]:
    owner = owner or _traveler()
    start = datetime.now(timezone.utc) + timedelta(days=3)
    answer = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": owner,
            "title": "ORD-0461 membership writes",
            "city_code": "CN-XIAMEN",
            "timezone": "Asia/Shanghai",
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(days=2)).isoformat(),
            "budget": {"amount_minor": 90000, "currency": "CNY"},
        },
    )
    assert answer.status_code == 201, answer.text[:200]
    return answer.json()["id"], owner


def _add(journey_id: str, traveler_id: str, role: str = "COLLABORATOR") -> dict:
    answer = client.post(
        MEMBER_PATH.format(journey_id=journey_id),
        json={"traveler_id": traveler_id, "role": role, "invited_by": "ord0461"},
    )
    assert answer.status_code == 201, answer.text[:200]
    return answer.json()


def test_a_role_change_is_gated_by_the_capability_the_acl_table_grants() -> None:
    journey_id, owner = _journey()
    member = _add(journey_id, _traveler(), "COLLABORATOR")

    refused = client.post(
        ROLE_PATH.format(journey_id=journey_id, member_id=member["id"]),
        params={"actor_traveler_id": member["traveler_id"]},
        json={"role": "ADMIN"},
    )
    assert _reason(refused.json()) == "MEMBER_ACTOR_NOT_PERMITTED", refused.text[:200]
    assert refused.json()["error"]["details"]["capability"] == "MEMBER_MANAGE"
    assert refused.status_code == 403, "the body carries the judgement; the status only groups it"

    allowed = client.post(
        ROLE_PATH.format(journey_id=journey_id, member_id=member["id"]),
        params={"actor_traveler_id": owner},
        json={"role": "ADMIN"},
    )
    assert _reason(allowed.json()) is None, allowed.text[:200]
    body = allowed.json()
    assert (body["role"], body["previous_role"]) == ("ADMIN", "COLLABORATOR"), body

    # ADMIN works too, because the seeded table grants it MEMBER_MANAGE: the answer comes from the
    # rows, not from a role list written next to this code.
    admin = client.post(
        ROLE_PATH.format(journey_id=journey_id, member_id=_add(journey_id, _traveler(), "ADMIN")["id"]),
        params={"actor_traveler_id": member["traveler_id"]},
        json={"role": "COLLABORATOR"},
    )
    assert _reason(admin.json()) is None, admin.text[:200]


def test_operating_on_a_removed_member_is_refused_by_name_on_every_write() -> None:
    journey_id, owner = _journey()
    member = _add(journey_id, _traveler(), "ADMIN")
    gone = client.post(WITHDRAW_PATH.format(journey_id=journey_id, member_id=member["id"]),
                       params={"actor_traveler_id": owner})
    assert _reason(gone.json()) is None, gone.text[:200]
    assert gone.json()["removed_at"], "a withdrawal records its own moment"

    for name, call in {
        "withdraw": lambda: client.post(
            WITHDRAW_PATH.format(journey_id=journey_id, member_id=member["id"]),
            params={"actor_traveler_id": owner}),
        "role": lambda: client.post(
            ROLE_PATH.format(journey_id=journey_id, member_id=member["id"]),
            params={"actor_traveler_id": owner}, json={"role": "COLLABORATOR"}),
        "leave": lambda: client.post(
            LEAVE_PATH.format(journey_id=journey_id),
            params={"actor_traveler_id": member["traveler_id"]}),
    }.items():
        answer = call()
        assert _reason(answer.json()) == "MEMBER_ALREADY_WITHDRAWN", (name, answer.text[:200])


def test_the_last_creator_cannot_leave_and_their_rung_is_not_givable() -> None:
    journey_id, owner = _journey()
    refused = client.post(LEAVE_PATH.format(journey_id=journey_id),
                          params={"actor_traveler_id": owner})
    assert _reason(refused.json()) == "MEMBER_LAST_CREATOR_LEAVE", refused.text[:200]
    assert refused.status_code == 409, refused.text[:200]

    member = _add(journey_id, _traveler(), "COLLABORATOR")
    promote = client.post(
        ROLE_PATH.format(journey_id=journey_id, member_id=member["id"]),
        params={"actor_traveler_id": owner}, json={"role": "OWNER"},
    )
    assert _reason(promote.json()) == "MEMBER_ROLE_CREATOR_IMMUTABLE", promote.text[:200]
    same = client.post(
        ROLE_PATH.format(journey_id=journey_id, member_id=member["id"]),
        params={"actor_traveler_id": owner}, json={"role": "COLLABORATOR"},
    )
    assert _reason(same.json()) == "MEMBER_ROLE_UNCHANGED", same.text[:200]


def test_the_member_cap_is_one_named_constant_that_the_contract_repeats() -> None:
    journey_id, _owner = _journey()
    for _ in range(JOURNEY_MEMBER_CAP):
        _add(journey_id, _traveler())
    over = client.post(
        MEMBER_PATH.format(journey_id=journey_id),
        json={"traveler_id": _traveler(), "role": "COLLABORATOR", "invited_by": "ord0461"},
    )
    assert _reason(over.json()) == "MEMBER_CAP_REACHED", over.text[:200]
    details = over.json()["error"]["details"]
    assert details["cap"] == JOURNEY_MEMBER_CAP and details["standing_members"] == JOURNEY_MEMBER_CAP

    # The same number has to be readable in the contract, or a screen counts people itself.
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    door = MEMBER_PATH[len("/api/v1"):]
    description = spec["paths"][door]["post"]["responses"]["409"]["description"]
    digits = re.findall(r"\d+", description)
    assert str(JOURNEY_MEMBER_CAP) in digits, (digits, description[:200])


def test_a_journey_in_the_bin_takes_no_membership_write() -> None:
    journey_id, owner = _journey()
    member = _add(journey_id, _traveler(), "ADMIN")
    assert client.delete(f"/api/v1/journeys/{journey_id}").status_code == 204

    calls = {
        "add": lambda: client.post(
            MEMBER_PATH.format(journey_id=journey_id),
            json={"traveler_id": _traveler(), "role": "COLLABORATOR", "invited_by": "ord0461"}),
        "role": lambda: client.post(
            ROLE_PATH.format(journey_id=journey_id, member_id=member["id"]),
            params={"actor_traveler_id": owner}, json={"role": "COLLABORATOR"}),
        "withdraw": lambda: client.post(
            WITHDRAW_PATH.format(journey_id=journey_id, member_id=member["id"]),
            params={"actor_traveler_id": owner}),
        "leave": lambda: client.post(
            LEAVE_PATH.format(journey_id=journey_id),
            params={"actor_traveler_id": member["traveler_id"]}),
    }
    for name, call in calls.items():
        answer = call()
        assert _reason(answer.json()) == "MEMBER_JOURNEY_RECYCLED", (name, answer.text[:200])


def test_a_write_that_names_no_actor_changes_nothing_and_says_so() -> None:
    journey_id, _owner = _journey()
    member = _add(journey_id, _traveler(), "ADMIN")
    before = client.get(MEMBER_PATH.format(journey_id=journey_id)).json()

    answer = client.post(WITHDRAW_PATH.format(journey_id=journey_id, member_id=member["id"]))
    assert _reason(answer.json()) == "MEMBER_ACTOR_REQUIRED", answer.text[:200]
    assert answer.json()["error"]["details"]["field"] == "actor_traveler_id"
    assert client.get(MEMBER_PATH.format(journey_id=journey_id)).json() == before, (
        "a refusal must leave the set exactly as it was"
    )


def test_leaving_needs_no_permission_but_does_need_a_membership() -> None:
    journey_id, _owner = _journey()
    stranger = _traveler()
    not_a_member = client.post(LEAVE_PATH.format(journey_id=journey_id),
                               params={"actor_traveler_id": stranger})
    assert _reason(not_a_member.json()) == "MEMBER_ACTOR_NOT_A_MEMBER", not_a_member.text[:200]

    member = _add(journey_id, stranger, "COLLABORATOR")
    left = client.post(LEAVE_PATH.format(journey_id=journey_id),
                       params={"actor_traveler_id": stranger})
    assert _reason(left.json()) is None, left.text[:200]
    assert left.json()["removed_at"], "leaving records a withdrawal like any other exit"
    listed = client.get(MEMBER_PATH.format(journey_id=journey_id)).json()
    assert [row["id"] for row in listed] == [member["id"]], "the row is still listed, marked as gone"
    assert listed[0]["member_state"] == "MEMBER_WITHDRAWN"


def test_an_expiry_already_spent_is_refused_for_a_membership_too() -> None:
    """ORD-0460's shape, applied to the member door: refused at the write, and nothing stored.

    The grant door stopped minting dead tokens; a membership was left answering the same way -- 201
    with a row that `_member_state` immediately called `MEMBER_LAPSED`.  Both doors now read one
    verdict (`_expiry_verdict`), so the boundary ("exactly now") sits on the refused side here too.
    """
    journey_id, _owner = _journey()
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    refused = client.post(
        MEMBER_PATH.format(journey_id=journey_id),
        json={"traveler_id": _traveler(), "role": "COLLABORATOR", "invited_by": "ord0461",
              "expires_at": past},
    )
    assert _reason(refused.json()) == "MEMBER_EXPIRY_IN_PAST", refused.text[:200]
    assert refused.status_code == 422, refused.text[:200]
    assert client.get(MEMBER_PATH.format(journey_id=journey_id)).json() == [], (
        "a refused membership must not leave a row behind"
    )

    boundary = client.post(
        MEMBER_PATH.format(journey_id=journey_id),
        json={"traveler_id": _traveler(), "role": "COLLABORATOR", "invited_by": "ord0461",
              "expires_at": datetime.now(timezone.utc).isoformat()},
    )
    assert _reason(boundary.json()) == "MEMBER_EXPIRY_IN_PAST", boundary.text[:200]

    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    accepted = client.post(
        MEMBER_PATH.format(journey_id=journey_id),
        json={"traveler_id": _traveler(), "role": "COLLABORATOR", "invited_by": "ord0461",
              "expires_at": future},
    )
    assert _reason(accepted.json()) is None, accepted.text[:200]
    assert accepted.status_code == 201, accepted.text[:200]
    assert accepted.json()["member_state"] == "MEMBER_IN_FORCE", accepted.json()

    no_offset = client.post(
        MEMBER_PATH.format(journey_id=journey_id),
        json={"traveler_id": _traveler(), "role": "COLLABORATOR", "invited_by": "ord0461",
              "expires_at": "2030-01-01T00:00:00"},
    )
    assert _reason(no_offset.json()) == "MEMBER_EXPIRY_NO_OFFSET", (
        "the refusal that already worked keeps its own name"
    )


def test_an_unknown_member_id_keeps_its_own_name_apart_from_every_refusal_above() -> None:
    journey_id, owner = _journey()
    answer = client.post(WITHDRAW_PATH.format(journey_id=journey_id, member_id="no-such-row"),
                         params={"actor_traveler_id": owner})
    assert _reason(answer.json()) == "MEMBER_UNKNOWN", answer.text[:200]
    assert answer.status_code == 404, "never existing is a different fact from already gone"
