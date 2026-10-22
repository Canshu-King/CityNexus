"""Member-bound consent on one shared future: who must answer, who did, what the rule decides.

The V3 order's fourth item is 多人决策, and its acceptance chain names the two numbers this file is
built around: 2/3 must not take effect, 3/3 is what updates the shared plan. `app.collective_consent`
reuses the shipped arithmetic (`collective_decision_epoch`) and the shipped predicates
(`_member_state`, `_role_capabilities`) rather than re-deciding them; what it adds is the press bound
to a credential and the durable receipt of it. No migration is used: the presses are `audit_logs`
rows, the authority boundary is a `collective_authority_receipts` row -- whose three json columns had
no writer before this module -- and the retry guard is `idempotency_keys`.

One design fact is tested on purpose: the door reads the roster through the two predicates, not
through `active_journey_members_with_capabilities`, because that projection writes a twin snapshot
for every member it projects. The status arm shows every statement the read runs is a read; the
parity arm shows the two answers still agree over the same rows.
"""

from __future__ import annotations

import ast
import json
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import collective_consent, departure_read, traveler_principal
from app.core.config import settings
from app.db.models import (
    Activity,
    AuditLog,
    Base,
    CollectiveAuthorityReceipt,
    Event,
    Journey,
    JourneyMember,
    JourneyRoleCapability,
    PlanVersion,
    ReplanProposal,
    Traveler,
    TravelerTwinSnapshot,
)
from app.db.session import get_session

SECRET = uuid.uuid4().hex + uuid.uuid4().hex  # generated, never printed, never committed
CITY = "350800"

CONSENT = "/api/v1/journeys/{}/replan-proposals/{}/consent"

#: The shipped plan door's own sentence for a candidate with no frozen mobility evidence. Reproduced
#: here as the marker that the call reached it: nothing in the consent module could produce this
#: string, and nothing in the consent module may swallow it.
SHIPPED_EVIDENCE_REFUSAL = "replan mobility evidence is missing or invalid; regenerate proposal"

CAPABILITIES = [
    ("OWNER", "JOURNEY_READ"),
    ("OWNER", "JOURNEY_UPDATE"),
    ("ADMIN", "JOURNEY_READ"),
    ("ADMIN", "JOURNEY_UPDATE"),
    ("COLLABORATOR", "JOURNEY_READ"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _then(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def _traveler(session, key: str) -> str:
    ident = str(uuid.uuid4())
    session.add(Traveler(id=ident, display_name=key, email=None, locale="zh-CN",
                         timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
    return ident


def _journey(session, ident: str, owner_id: str, *, active_plan_id: str) -> None:
    """A journey on the road, with its active plan named up front.

    The id is minted by the caller because a journey and its active plan point at each other, and a
    replan can only be answered on a journey whose `active_plan_version_id` is that base. Minting one
    id and writing both rows with it is what keeps that promise in a single flush -- `session.get`
    after an un-flushed `add` answers None, which is how this shape was found.
    """
    session.add(Journey(id=ident, traveler_id=owner_id, title="连城", city_code=CITY,
                        timezone="Asia/Shanghai", start_at=_then(60), end_at=_then(60 * 24),
                        budget_currency="CNY", budget_amount_minor=500_00, status="ACTIVE",
                        active_plan_version_id=active_plan_id, created_at=_now(),
                        updated_at=_now()))


def _plan(session, journey_id: str, *, number: int, status: str, mint: str) -> str:
    session.add(PlanVersion(id=mint, journey_id=journey_id, version_no=number,
                            planning_mode="balanced", status=status, source="INITIAL",
                            total_cost_minor=470_00, currency="CNY", estimated_duration_min=240,
                            created_at=_now()))
    _activity(session, mint, 1, title="冠豸山" if status == "ACTIVE" else "龙王滩")
    return mint


def _activity(session, plan_id: str, sequence_no: int, *, title: str) -> str:
    ident = str(uuid.uuid4())
    session.add(Activity(id=ident, plan_version_id=plan_id, sequence_no=sequence_no,
                         activity_type="SIGHTSEE", title=title, place_id=None,
                         city_service_id=None, start_at=_then(60), end_at=_then(105),
                         travel_from_prev_min=0, estimated_cost_minor=6000, currency="CNY",
                         status="PLANNED", locked=False, metadata_json="{}",
                         created_at=_now(), updated_at=_now()))
    return ident


def _member(session, journey_id: str, traveler_id: str, *, role: str = "ADMIN",
            expires_offset_minutes=None, removed: bool = False) -> str:
    ident = str(uuid.uuid4())
    session.add(JourneyMember(id=ident, journey_id=journey_id, traveler_id=traveler_id,
                              role=role, invited_by="owner-device", created_at=_now(),
                              updated_at=_now(), joined_at=_now(),
                              expires_at=_then(expires_offset_minutes)
                              if expires_offset_minutes is not None else None,
                              removed_at=_now() if removed else None))
    return ident


def _proposal(session, ids: dict[str, str], *, diff: dict | None = None) -> str:
    """A candidate a member can still answer: PRESENTED, on the active base, with a live trigger."""
    event_id = str(uuid.uuid4())
    session.add(Event(id=event_id, journey_id=ids["journey"], provider_key="guardian-simulated",
                      provenance="SIMULATED", event_type="WEATHER", severity="MINOR",
                      status="DETECTED", occurred_at=_now(), detected_at=_now(),
                      payload_json="{}", created_at=_now()))
    ident = str(uuid.uuid4())
    session.add(ReplanProposal(id=ident, journey_id=ids["journey"], trigger_event_id=event_id,
                               base_plan_version_id=ids["base"],
                               proposed_plan_version_id=ids["candidate"], status="PRESENTED",
                               hard_constraints_passed=True, locked_commitments_preserved=True,
                               utility_score=0.6, score_breakdown_json="{}",
                               diff_json=json.dumps(diff or {}), explanation_json="{}",
                               created_at=_now()))
    ids["event"] = event_id
    return ident


@pytest.fixture()
def seeded():
    """The 连城 three: an organiser, 小雨, 阿哲 -- all ADMIN, plus a read-only and a withdrawn seat.

    Rows come from the ORM, not from `db/schema.sql`. The DDL's CHECK vocabularies are read where a
    test claims a word is legal, and `db/schema.sql` is opened by
    `test_the_words_this_door_leaves_are_words_the_shipped_ddl_allows` rather than trusted.
    """
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ids: dict[str, str] = {}
    with factory() as session:
        for role, capability in CAPABILITIES:
            session.add(JourneyRoleCapability(role=role, capability=capability,
                                              scope_message_key="member.scope." + capability.lower(),
                                              created_at=_now()))
        ids["organiser"] = _traveler(session, "组织者")
        ids["xiaoyu"] = _traveler(session, "小雨")
        ids["azhe"] = _traveler(session, "阿哲")
        ids["viewer"] = _traveler(session, "围观")
        ids["withdrawn"] = _traveler(session, "已退出")
        ids["stranger"] = _traveler(session, "陌生人")
        ids["journey"] = str(uuid.uuid4())
        ids["base"] = _plan(session, ids["journey"], number=1, status="ACTIVE", mint=str(uuid.uuid4()))
        ids["candidate"] = _plan(session, ids["journey"], number=2, status="CANDIDATE",
                                 mint=str(uuid.uuid4()))
        _journey(session, ids["journey"], ids["organiser"], active_plan_id=ids["base"])
        _member(session, ids["journey"], ids["organiser"], role="OWNER")
        _member(session, ids["journey"], ids["xiaoyu"], role="ADMIN")
        _member(session, ids["journey"], ids["azhe"], role="ADMIN")
        _member(session, ids["journey"], ids["viewer"], role="COLLABORATOR")
        _member(session, ids["journey"], ids["withdrawn"], role="ADMIN", removed=True)
        ids["proposal"] = _proposal(session, ids)

        # A second journey whose whole roster lacks the mutation capability, for the refusal arm.
        ids["lonely_journey"] = str(uuid.uuid4())
        ids["lonely_base"] = _plan(session, ids["lonely_journey"], number=1, status="ACTIVE",
                                   mint=str(uuid.uuid4()))
        ids["lonely_candidate"] = _plan(session, ids["lonely_journey"], number=2, status="CANDIDATE",
                                        mint=str(uuid.uuid4()))
        _journey(session, ids["lonely_journey"], ids["stranger"],
                 active_plan_id=ids["lonely_base"])
        # Deliberately no `journey_members` row here: this is the journey whose owner never invited
        # anyone, including themselves -- the shape `seat_of` answers with SEAT_OWNER.
        ids["lonely_proposal"] = _proposal(
            session,
            {**ids, "journey": ids["lonely_journey"], "base": ids["lonely_base"],
             "candidate": ids["lonely_candidate"]},
        )
        session.commit()
    return SimpleNamespace(engine=engine, factory=factory, ids=ids)


def _app(seeded, monkeypatch):
    monkeypatch.setattr(traveler_principal, "settings",
                        replace(settings, traveler_auth_secret=SECRET))
    from app import main as main_module

    app = FastAPI()
    app.include_router(collective_consent.router)
    app.add_exception_handler(StarletteHTTPException, main_module.http_error)

    def override_session():
        with seeded.factory() as inner:
            yield inner

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _header(traveler_id: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(traveler_id)}


def _press(client, ids, traveler_id: str, decision: str, key: str):
    return client.post(CONSENT.format(ids["journey"], ids["proposal"]),
                       headers={**_header(traveler_id), "Idempotency-Key": key},
                       json={"decision": decision})


def _status(client, ids, traveler_id: str):
    return client.get(CONSENT.format(ids["journey"], ids["proposal"]),
                      headers=_header(traveler_id))


def _rows(seeded, model):
    with seeded.factory() as session:
        return list(session.scalars(select(model)).all())


def _plan_rows(seeded) -> dict[str, str]:
    with seeded.factory() as session:
        return {
            str(row.id): str(row.status) for row in session.scalars(select(PlanVersion)).all()
        }


def test_the_first_two_presses_leave_the_shared_plan_exactly_where_it_was(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    required = sorted([ids["organiser"], ids["xiaoyu"], ids["azhe"]])

    first = _press(client, ids, ids["organiser"], "APPROVE", "consent-1")
    second = _press(client, ids, ids["xiaoyu"], "APPROVE", "consent-2")
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    answer = second.json()

    assert answer["required_traveler_ids"] == required, answer["required_traveler_ids"]
    assert answer["counts"] == {"required": 3, "approved": 2, "rejected": 0, "outstanding": 1}, \
        answer["counts"]
    assert answer["fulfilled"] is False, answer
    assert answer["outstanding_traveler_ids"] == [ids["azhe"]], answer["outstanding_traveler_ids"]
    assert answer["receipt"] is None, answer["receipt"]
    # Two of three is not a plan transition: no apply attempt, and every row left where it was.
    assert answer["plan_apply"] == {"attempted": False, "applied": False}, answer["plan_apply"]
    assert answer["shared_plan"]["shared_plan_updated"] is False, answer["shared_plan"]
    assert _plan_rows(seeded)[ids["base"]] == "ACTIVE"
    assert _plan_rows(seeded)[ids["candidate"]] == "CANDIDATE"


def test_the_third_press_fulfils_the_rule_and_asks_the_plan_door(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    for key, traveler in (("consent-1", ids["organiser"]), ("consent-2", ids["xiaoyu"])):
        assert _press(client, ids, traveler, "APPROVE", key).status_code == 200

    third = _press(client, ids, ids["azhe"], "APPROVE", "consent-3")
    assert third.status_code == 200, third.text
    answer = third.json()

    assert answer["fulfilled"] is True, answer
    assert answer["counts"]["approved"] == 3, answer["counts"]
    assert answer["outstanding_traveler_ids"] == [], answer["outstanding_traveler_ids"]
    receipt = answer["receipt"]
    assert receipt is not None and receipt["authority_mode"] == collective_consent.AUTHORITY_MODE
    assert receipt["required_traveler_ids"] == sorted(
        [ids["organiser"], ids["xiaoyu"], ids["azhe"]]
    ), receipt
    assert len(receipt["principal_actor_ids"]) == 3, receipt
    assert len(receipt["response_audit_ids"]) == 3, receipt
    assert len(receipt["decision_epoch"]) == 64, receipt["decision_epoch"]
    # The plan itself is only ever moved by the door that validates it. Here that door refuses for
    # its own reason, and the refusal is reported beside the fulfilled rule instead of erasing it.
    assert answer["plan_apply"]["attempted"] is True, answer["plan_apply"]
    assert answer["plan_apply"]["applied"] is False, answer["plan_apply"]
    assert answer["plan_apply"]["refusal_status"] == 409, answer["plan_apply"]
    assert SHIPPED_EVIDENCE_REFUSAL in answer["plan_apply"]["refusal_detail"], answer["plan_apply"]
    assert answer["plan_apply"]["reason_code"] == collective_consent.REASON_APPLY_REFUSED
    assert answer["shared_plan"]["shared_plan_updated"] is False, answer["shared_plan"]
    assert _plan_rows(seeded)[ids["candidate"]] == "CANDIDATE"


def test_the_organiser_cannot_confirm_for_xiaoyu(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    before = _status(client, ids, ids["organiser"]).json()["counts"]

    refused = client.post(
        CONSENT.format(ids["journey"], ids["proposal"]),
        headers={**_header(ids["organiser"]), "Idempotency-Key": "delegate-1"},
        json={"decision": "APPROVE", "traveler_id": ids["xiaoyu"]},
    )
    assert refused.status_code == 422, refused.text
    body = refused.json()["error"]
    assert body["reason_code"] == collective_consent.REASON_DELEGATION, body
    detail = body["details"]
    assert detail["refused_fields"] == ["traveler_id"], detail
    assert detail["pressing_traveler_id"] == ids["organiser"], detail

    # A refusal that recorded nothing: the round still shows no answers at all.
    after = _status(client, ids, ids["organiser"]).json()
    assert after["counts"] == before, (after["counts"], before)
    assert after["answers"] == [], after["answers"]


def test_an_answer_binds_to_the_credential_that_pressed_it(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    assert _press(client, ids, ids["xiaoyu"], "APPROVE", "own-1").status_code == 200

    as_organiser = _status(client, ids, ids["organiser"]).json()
    assert [item["traveler_id"] for item in as_organiser["answers"]] == [ids["xiaoyu"]], \
        as_organiser["answers"]
    assert as_organiser["answers"][0]["decision"] == "APPROVE", as_organiser["answers"]

    # A second press by the same traveller revises rather than adds, and says what it replaced.
    revised = _press(client, ids, ids["xiaoyu"], "REJECT", "own-2")
    assert revised.status_code == 200, revised.text
    entry = revised.json()["answers"][0]
    assert entry["decision"] == "REJECT", entry
    assert entry["revised_from"]["decision"] == "APPROVE", entry
    assert entry["revised_from"]["audit_id"] != entry["audit_id"], entry
    assert revised.json()["counts"]["approved"] == 0, revised.json()["counts"]
    assert revised.json()["counts"]["rejected"] == 1, revised.json()["counts"]


def test_a_read_only_seat_answers_without_binding_the_plan(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    pressed = _press(client, ids, ids["viewer"], "APPROVE", "viewer-1")
    assert pressed.status_code == 200, pressed.text
    answer = pressed.json()

    assert answer["counts_toward_fulfillment"] is False, answer
    assert answer["required_traveler_ids"] != [], answer["required_traveler_ids"]
    assert ids["viewer"] not in answer["required_traveler_ids"], answer
    assert answer["counts"]["approved"] == 0, answer["counts"]
    assert answer["fulfilled"] is False, answer["fulfilled"]
    # The roster still reports what that member did, and why it does not count.
    row = next(item for item in answer["roster"] if item["traveler_id"] == ids["viewer"])
    assert row["decision"] == "APPROVE", row
    assert row["can_authorize_mutation"] is False, row


def test_a_withdrawn_member_is_not_required_and_cannot_press(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    answer = _status(client, ids, ids["organiser"]).json()
    assert ids["withdrawn"] not in answer["required_traveler_ids"], answer["required_traveler_ids"]

    refused = _press(client, ids, ids["withdrawn"], "APPROVE", "gone-1")
    assert refused.status_code == 403, refused.text
    body = refused.json()["error"]
    assert body["reason_code"] == departure_read.REASON_MEMBER_REQUIRED, body
    detail = body["details"]
    assert detail["seat"]["member_state"] == "MEMBER_WITHDRAWN", detail
    assert len(_rows(seeded, AuditLog)) == 0, "a refused press left a consent row"


def test_the_journey_owner_with_no_member_row_of_their_own_still_forms_a_round(seeded, monkeypatch):
    """A journey nobody was invited to is still somebody's journey.

    `seat_of` treats `journeys.traveler_id` as a seat in force; a round that read only member rows
    would tell that person to invite themselves before they could answer for their own trip. The
    capability is still asked of `journey_role_capabilities` for the OWNER role, never assumed.
    """
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    path = CONSENT.format(ids["lonely_journey"], ids["lonely_proposal"])

    answer = client.get(path, headers=_header(ids["stranger"])).json()
    assert answer["required_traveler_ids"] == [ids["stranger"]], answer["required_traveler_ids"]
    assert len(answer["roster"]) == 1, answer["roster"]
    assert answer["roster"][0]["member_id"] is None, answer["roster"][0]
    assert answer["roster"][0]["role"] == collective_consent.OWNER_ROLE, answer["roster"][0]
    assert answer["counts"] == {"required": 1, "approved": 0, "rejected": 0, "outstanding": 1}, \
        answer["counts"]

    pressed = client.post(path, headers={**_header(ids["stranger"]),
                                         "Idempotency-Key": "owner-alone"},
                          json={"decision": "APPROVE"})
    assert pressed.status_code == 200, pressed.text
    body = pressed.json()
    assert body["fulfilled"] is True, body
    assert body["receipt"]["principal_actor_ids"] == [ids["stranger"]], body["receipt"]
    # A complete rule still does not decide the plan: the plan door is asked, and refuses.
    assert body["plan_apply"]["attempted"] is True, body["plan_apply"]
    assert SHIPPED_EVIDENCE_REFUSAL in body["plan_apply"]["refusal_detail"], body["plan_apply"]
    assert _plan_rows(seeded)[ids["lonely_candidate"]] == "CANDIDATE"


def test_the_round_follows_the_capability_table_whenever_operations_narrows_it(seeded, monkeypatch):
    """No role list of its own: take JOURNEY_UPDATE out of the table and the round empties out."""
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    from sqlalchemy import delete

    assert _status(client, ids, ids["organiser"]).json()["required_traveler_ids"] != []
    with seeded.factory() as session:
        session.execute(delete(JourneyRoleCapability).where(
            JourneyRoleCapability.capability == collective_consent.REQUIRED_CAPABILITY))
        session.commit()

    refused = _press(client, ids, ids["organiser"], "APPROVE", "nobody-1")
    assert refused.status_code == 409, refused.text
    body = refused.json()["error"]
    assert body["reason_code"] == collective_consent.REASON_NO_AUTHORITY, body
    detail = body["details"]
    assert detail["required_capability"] == collective_consent.REQUIRED_CAPABILITY, detail
    assert detail["roles_in_roster"] == ["ADMIN", "COLLABORATOR", "OWNER"], detail

    answer = _status(client, ids, ids["organiser"]).json()
    assert answer["required_traveler_ids"] == [], answer["required_traveler_ids"]
    assert answer["fulfilled"] is False, answer
    assert answer["blocking_code"] == collective_consent.REASON_NO_AUTHORITY, answer
    assert all(not item["can_authorize_mutation"] for item in answer["roster"]), answer["roster"]


def test_a_reject_takes_back_an_issued_round_and_a_later_approve_mints_a_new_one(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    for key, traveler in (("consent-1", ids["organiser"]), ("consent-2", ids["xiaoyu"]),
                          ("consent-3", ids["azhe"])):
        assert _press(client, ids, traveler, "APPROVE", key).status_code == 200
    issued = _status(client, ids, ids["organiser"]).json()["receipt"]
    assert issued is not None, issued

    withdrawn = _press(client, ids, ids["azhe"], "REJECT", "consent-4")
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["fulfilled"] is False, withdrawn.json()
    assert withdrawn.json()["receipt"] is None, withdrawn.json()["receipt"]
    assert withdrawn.json()["receipt_invalidated"]["receipt_id"] == issued["receipt_id"], \
        withdrawn.json()["receipt_invalidated"]
    assert withdrawn.json()["receipt_invalidated"]["invalidation_code"] == \
        collective_consent.INVALIDATED_BY_REJECT, withdrawn.json()["receipt_invalidated"]

    back = _press(client, ids, ids["azhe"], "APPROVE", "consent-5")
    assert back.status_code == 200, back.text
    fresh = back.json()["receipt"]
    assert fresh is not None and fresh["receipt_id"] != issued["receipt_id"], fresh
    rows = _rows(seeded, CollectiveAuthorityReceipt)
    assert len(rows) == 2, [row.id for row in rows]
    assert {row.invalidated_at is None for row in rows} == {True, False}, rows


def test_the_status_read_runs_only_reads(seeded, monkeypatch):
    """A consent round asked about must not write: not a snapshot, not a receipt, not an audit row."""
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    spoken: list[str] = []

    @event.listens_for(seeded.engine, "before_cursor_execute")
    def capture(conn, cursor, statement, parameters, context, executemany):
        del conn, cursor, parameters, context, executemany
        head = statement.strip().split()[0].upper()
        spoken.append(head)

    before = _rows(seeded, AuditLog)
    receipts = _rows(seeded, CollectiveAuthorityReceipt)
    snapshots_before = _rows(seeded, TravelerTwinSnapshot)

    answer = _status(client, ids, ids["organiser"])
    assert answer.status_code == 200, answer.text
    assert spoken, "the listener never saw a statement"
    assert set(spoken) <= {"SELECT", "BEGIN", "COMMIT", "ROLLBACK", "PRAGMA"}, sorted(set(spoken))
    assert len(_rows(seeded, AuditLog)) == len(before), "a status read wrote an audit row"
    assert len(_rows(seeded, CollectiveAuthorityReceipt)) == len(receipts)
    assert len(_rows(seeded, TravelerTwinSnapshot)) == len(snapshots_before), \
        "a status read refreshed a twin snapshot"

def test_the_shipped_projection_names_the_same_roster_and_spends_a_snapshot_row(seeded):
    """Why this door reads the two predicates and not the shipped projection -- measured, not asserted.

    On this line `active_journey_members_with_capabilities` works, and it works out to the same
    answer: the same in-force travellers, the same `can_authorize_mutation` per role, the same
    `authority_basis` naming `JourneyRoleCapability`. So the two readers are pinned against each
    other here rather than against a column list, and the door is not free to drift.

    What the projection does in addition is what keeps the door off it: `app/main.py:8046` calls
    `refresh_snapshot` inside its member loop, so a screen that only wanted to know who has
    answered stages one `traveler_twin_snapshots` row per in-force member in the caller's
    transaction -- measured below as 0 rows before the call and one per member after. That is the
    same shape this project already calls a defect for `GET /experience`: a status read that spends
    storage. The arm goes red on the day the projection stops writing, which is the day the door
    should call the projection instead of the two predicates.
    """
    ids = seeded.ids
    from app.main import active_journey_members_with_capabilities

    with seeded.factory() as session:
        mine, roster = collective_consent.required_authority(
            session, session.get(Journey, ids["journey"])
        )
    assert len(mine) == 3, mine
    assert len(roster) == 5, roster

    with seeded.factory() as session:
        before = len(session.scalars(select(TravelerTwinSnapshot)).all())
        projected = active_journey_members_with_capabilities(
            session, session.get(Journey, ids["journey"]))
        after = len(session.scalars(select(TravelerTwinSnapshot)).all())
        session.rollback()
    assert before == 0, before
    assert after == before + projected["member_count"], (before, after, projected["member_count"])

    in_force = sorted(str(row["traveler_id"]) for row in roster
                      if row["member_state"] == "MEMBER_IN_FORCE")
    assert sorted(str(row["traveler_id"]) for row in projected["members"]) == in_force, (
        projected["members"], in_force)
    assert projected["authority_basis"] == "JourneyRoleCapability", projected["authority_basis"]
    assert sorted(str(row["traveler_id"]) for row in projected["members"]
                  if row["can_authorize_mutation"]) == mine, projected["members"]


def test_the_required_set_is_the_two_shipped_predicates_over_the_same_rows(seeded):
    """The door's roster is `_member_state` plus `_role_capabilities`, not a role list of its own."""
    ids = seeded.ids
    from app.main import _member_state, _role_capabilities

    with seeded.factory() as session:
        journey = session.get(Journey, ids["journey"])
        mine, _ = collective_consent.required_authority(session, journey)
        expected = sorted(
            str(member.traveler_id) for member in session.scalars(
                select(JourneyMember).where(JourneyMember.journey_id == journey.id)
            ).all()
            if _member_state(member, datetime.now(timezone.utc)) == "MEMBER_IN_FORCE"
            and collective_consent.REQUIRED_CAPABILITY in _role_capabilities(session, member.role)
        )
    assert mine == expected, (mine, expected)
    assert ids["viewer"] not in mine, mine
    assert ids["withdrawn"] not in mine, mine


def test_a_mission_round_names_the_classification_instead_of_this_door_deciding_it(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    assert _status(client, ids, ids["organiser"]).json()["classification"] is None

    from app.db.models import JourneyMission

    with seeded.factory() as session:
        session.add(JourneyMission(
            id=str(uuid.uuid4()), journey_id=ids["journey"], traveler_id=ids["organiser"],
            user_text="换个方案", created_at=_now(),
            resolved_intent_json=json.dumps({"collective_mediation": {
                "kind": "DISAGREEMENT_MEDIATION",
                "classification": "HUMAN_TRADEOFF_REQUIRED",
                "selected_proposal_id": ids["proposal"],
            }}),
        ))
        session.commit()

    answer = _status(client, ids, ids["organiser"]).json()
    assert answer["classification"] == "HUMAN_TRADEOFF_REQUIRED", answer["classification"]

    # A mission that names a different proposal does not lend its word to this one.
    with seeded.factory() as session:
        session.add(JourneyMission(
            id=str(uuid.uuid4()), journey_id=ids["journey"], traveler_id=ids["organiser"],
            user_text="另一轮", created_at=_now(),
            resolved_intent_json=json.dumps({"collective_mediation": {
                "kind": "DISAGREEMENT_MEDIATION", "classification": "UNANIMOUS_DOMINANCE",
                "selected_proposal_id": str(uuid.uuid4())}}),
        ))
        session.commit()
    assert _status(client, ids, ids["organiser"]).json()["classification"] == \
        "HUMAN_TRADEOFF_REQUIRED"


def test_one_press_one_row_under_a_retried_key(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    first = _press(client, ids, ids["organiser"], "APPROVE", "same-key")
    again = _press(client, ids, ids["organiser"], "APPROVE", "same-key")

    assert "idempotency_replay" not in first.json(), first.json()
    assert again.json()["idempotency_replay"] is True, again.json()
    presses = [row for row in _rows(seeded, AuditLog)
               if row.action == collective_consent.ACTION_RECORDED]
    assert len(presses) == 1, len(presses)
    assert _status(client, ids, ids["organiser"]).json()["counts"]["approved"] == 1

    # A key reused for a different answer is a conflict, not a second opinion.
    other = client.post(CONSENT.format(ids["journey"], ids["proposal"]),
                        headers={**_header(ids["xiaoyu"]), "Idempotency-Key": "same-key"},
                        json={"decision": "REJECT"})
    assert other.status_code == 409, other.text
    assert other.json()["error"]["reason_code"] == collective_consent.REASON_KEY_CONFLICT


def test_the_door_refuses_the_words_and_the_fields_it_should(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids

    unknown_word = _press(client, ids, ids["organiser"], "MAYBE", "w-1")
    assert unknown_word.status_code == 422, unknown_word.text
    assert unknown_word.json()["error"]["reason_code"] == collective_consent.REASON_DECISION_WORD

    extra = client.post(CONSENT.format(ids["journey"], ids["proposal"]),
                        headers={**_header(ids["organiser"]), "Idempotency-Key": "w-2"},
                        json={"decision": "APPROVE", "place_name": "冠豸山"})
    assert extra.status_code == 422, extra.text
    assert extra.json()["error"]["reason_code"] == collective_consent.REASON_BODY, extra.json()

    no_key = client.post(CONSENT.format(ids["journey"], ids["proposal"]),
                         headers=_header(ids["organiser"]), json={"decision": "APPROVE"})
    assert no_key.status_code == 422, no_key.text
    assert no_key.json()["error"]["reason_code"] == collective_consent.REASON_KEY_REQUIRED

    stranger = client.get(CONSENT.format(ids["journey"], ids["proposal"]),
                          headers=_header(ids["stranger"]))
    assert stranger.status_code == 403, stranger.text

    # A seat on one journey is not a window onto another journey's proposal: the caller holds a seat
    # here, and the answer is still 404 rather than anything about the proposal's own contents.
    foreign = client.get(CONSENT.format(ids["journey"], ids["lonely_proposal"]),
                         headers=_header(ids["organiser"]))
    assert foreign.status_code == 404, foreign.text
    assert foreign.json()["error"]["reason_code"] == collective_consent.REASON_PROPOSAL_NOT_IN_JOURNEY


def test_a_decided_proposal_is_no_longer_answerable(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    with seeded.factory() as session:
        proposal = session.get(ReplanProposal, ids["proposal"])
        proposal.status = "ACCEPTED"
        session.commit()

    refused = _press(client, ids, ids["organiser"], "APPROVE", "late-1")
    assert refused.status_code == 409, refused.text
    body = refused.json()["error"]
    assert body["reason_code"] == collective_consent.REASON_PROPOSAL_NOT_ACTIONABLE, body
    detail = body["details"]
    assert detail["proposal_status"] == "ACCEPTED", detail


def test_the_words_this_door_leaves_are_words_the_shipped_ddl_allows(seeded, monkeypatch):
    """Nothing this round writes may step outside the vocabularies the package schema states."""
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    ddl = Path("db/schema.sql").read_text(encoding="utf-8")

    def allowed(table: str, column: str) -> list[str]:
        """The words the shipped DDL lists for one column, taken by string position.

        Written without regex escapes on purpose: this repo's write door has twice turned a single
        backslash in a pattern into two, and a tool that silently mis-parses the DDL is the kind of
        instrument that swallows its own verdict.
        """
        start = ddl.index("CREATE TABLE IF NOT EXISTS " + table + " (")
        block = ddl[start:ddl.index(chr(10) + ");", start)]
        marker = column + " IN ("
        at = block.index(marker) + len(marker)
        listed = block[at:block.index(")", at)]
        words = [item.strip().strip("'") for item in listed.split(",")]
        assert words, (table, column)
        return words

    proposal_words = allowed("replan_proposals", "status")
    plan_words = allowed("plan_versions", "status")
    member_words = allowed("journey_members", "role")
    capability_words = allowed("journey_role_capabilities", "capability")
    assert collective_consent.ACTIONABLE_STATUSES == tuple(
        word for word in proposal_words if word in collective_consent.ACTIONABLE_STATUSES
    ), proposal_words
    assert collective_consent.REQUIRED_CAPABILITY in capability_words, capability_words
    assert {row.role for row in _rows(seeded, JourneyMember)} <= set(member_words)
    assert {row.capability for row in _rows(seeded, JourneyRoleCapability)} <= set(capability_words)

    for key, traveler in (("consent-1", ids["organiser"]), ("consent-2", ids["xiaoyu"]),
                          ("consent-3", ids["azhe"])):
        assert _press(client, ids, traveler, "APPROVE", key).status_code == 200
    assert _rows(seeded, ReplanProposal)[0].status in proposal_words
    assert {row.status for row in _rows(seeded, PlanVersion)} <= set(plan_words)


def test_no_provider_client_is_reachable_from_the_consent_module():
    """A consent round is a ledger act: it cannot ask a provider, so it cannot spend quota."""
    tree = ast.parse(
        Path("app/collective_consent.py").read_text(encoding="utf-8"), filename="consent"
    )
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(str(alias.name).split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(str(node.module).split(".")[0])
            modules.add(str(node.module))
    network = {"http", "httpx", "requests", "aiohttp", "urllib", "socket", "ssl", "urllib3"}
    assert modules.isdisjoint(network), sorted(modules & network)
    assert "app" in modules, sorted(modules)
    pressed = {str(node.func.attr) for node in ast.walk(tree)
               if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
               and isinstance(node.func.value, ast.Name) and node.func.value.id == "client"}
    assert pressed == set(), pressed


def test_the_receipt_columns_this_door_writes_are_the_ones_the_model_declares(seeded, monkeypatch):
    """Three json columns existed with no writer; this door is that writer, and the shapes are checked."""
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    for key, traveler in (("consent-1", ids["organiser"]), ("consent-2", ids["xiaoyu"]),
                          ("consent-3", ids["azhe"])):
        assert _press(client, ids, traveler, "APPROVE", key).status_code == 200

    row = _rows(seeded, CollectiveAuthorityReceipt)[0]
    assert row.authority_mode == collective_consent.AUTHORITY_MODE, row.authority_mode
    assert row.proposal_id == ids["proposal"] and row.plan_version_id == ids["candidate"], row.id
    required = json.loads(row.required_member_ids_json)
    principals = json.loads(row.principal_actor_ids_json)
    audit_ids = json.loads(row.response_audit_ids_json)
    assert required == sorted(principals), (required, principals)
    assert len(audit_ids) == 3, audit_ids
    presses = [item.id for item in _rows(seeded, AuditLog)
               if item.action == collective_consent.ACTION_RECORDED]
    assert sorted(audit_ids) == sorted(presses), (audit_ids, presses)
    world = json.loads(row.material_world_epoch)
    assert sorted(world) == ["base_plan_version_id", "hard_constraints_passed",
                             "locked_commitments_preserved", "proposed_plan_version_id"], world
    assert world["proposed_plan_version_id"] == ids["candidate"], world
    assert row.decision_epoch != row.material_world_epoch, row.decision_epoch
    assert row.recovery_epoch_id is None, row.recovery_epoch_id
    ledger = [item.action for item in _rows(seeded, AuditLog)]
    assert ledger.count(collective_consent.ACTION_RECEIPT_ISSUED) == 1, ledger
