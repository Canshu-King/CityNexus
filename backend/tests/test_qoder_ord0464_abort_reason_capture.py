"""ORD-0464 - a trip that gets binned carries the reason the traveller gave, in one of three named states.

First measured at the authoritative tip `45513fc7957214dc385b4dffea9a662a0d8b1d1c`, and re-measured on each
base this branch has been rebased onto.  The door moved from `:2984` to `:3006` under the first rebase, so the
citations below are pinned to a commit rather than to a bare line number the next landing would move.
`DELETE /api/v1/journeys/{journey_id}` (`4037cb331ea00b83124316d40329762fa1131689:backend/app/main.py:3006`) took no request body at all
(`contracts/openapi.yaml` declared `'204'/'404'/'409'` and nothing else), wrote no
`journey_outcome_events` row - only `record_audit(action="journey.deleted")` - and the vocabulary that
door *could* have used, `OutcomeEventCreate.event_type` (`backend/app/schemas.py:620-628`), had no
journey-terminal token in it.  So the bin had a bottom but no lid and no record of why anything was in
it, and `journeys.status` carried a `CANCELLED` value that no route on this tree ever writes
(grep `journey.status =` over `backend/app`: four assignment sites, `"PLANNED"` / `"ACTIVE"` /
`"COMPLETED"` only).

What is pinned here:

* one tap, one transaction, one row.  The reason rides on the same door as the delete because two calls
  can fail independently, and a half-recorded cause is worse than none.  A malformed reason refuses the
  whole tap: the trip stays out of the bin and `journey_outcome_events` gains zero rows for it;
* the three states are distinct and none of them is a default.  `DECLARED`, `SKIPPED_BY_TRAVELER` (the
  traveller was asked and declined), `NOT_ASKED` (no reason object arrived - every client that predates
  this order).  `answered` is a required field, so a caller cannot file `NOT_ASKED` in a payload; this is
  the `stay_budget_declared` rule of ORD-0355 (`backend/app/schemas.py` + `backend/app/db/session.py:825`)
  applied to a question asked once per trip;
* skipping is legal but not free of shape: declining while also naming reasons is refused, because the
  row would then claim both;
* `JOURNEY_DELETED` is produced by this door only.  The generic outcomes door refuses it, so no client
  can record a deletion - or a reason for one - without deleting anything;
* the enum lives in the contract and in the generated client, and every token asserted below is read
  out of `typing.get_args` at run time, not typed by hand, so a code added to the Literal without a
  contract entry (or vice versa) is a red test rather than a drift nobody noticed.

Deliberately out of scope: no recycle-bin column for the reason, no analytics, no `status` rewrite, and
no second table.  The row lands in the store the order named.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import get_args
from uuid import uuid4

import yaml
from fastapi.testclient import TestClient

from app.db.models import Traveler
from app.main import app
from app.schemas import ABORT_NOTE_MAX_LENGTH, JourneyAbortCode, JourneyAbortRequest

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "openapi.yaml"
GENERATED = ROOT / "frontend" / "src" / "generated" / "api.ts"
TZ = timezone(timedelta(hours=8))
START = datetime(2027, 3, 4, 9, 0, tzinfo=TZ)

CODES = list(get_args(JourneyAbortCode))


def _store_path() -> Path:
    from conftest import RESOLVED_TEST_DATABASE

    return Path(RESOLVED_TEST_DATABASE.replace("sqlite:///", "", 1)).expanduser().resolve()


def _traveler() -> str:
    traveler_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="ORD-0464 probe",
                email=None,
                locale="zh-CN",
                timezone="Asia/Shanghai",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return traveler_id


def _journey(title: str) -> str:
    created = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": _traveler(),
            "title": title,
            "city_code": "CNX-DEMO",
            "timezone": "Asia/Shanghai",
            "start_at": START.isoformat(),
            "end_at": (START + timedelta(days=2)).isoformat(),
            "budget": {"amount_minor": 90000, "currency": "CNY"},
            "planning_mode": "balanced",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _abort_rows(journey_id: str) -> list[sqlite3.Row]:
    """The rows this door is allowed to leave behind, read raw from the file this process opened."""

    with sqlite3.connect(_store_path()) as connection:
        connection.row_factory = sqlite3.Row
        return list(
            connection.execute(
                "SELECT rowid, id, event_type, actor_type, activity_id, source, occurred_at_actual,"
                " payload_json FROM journey_outcome_events"
                " WHERE journey_id = ? AND event_type = 'JOURNEY_DELETED' ORDER BY rowid",
                (journey_id,),
            ).fetchall()
        )


def _journey_row(journey_id: str) -> sqlite3.Row:
    with sqlite3.connect(_store_path()) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT rowid, id, status, deleted_at FROM journeys WHERE id = ?", (journey_id,)
        ).fetchone()
    assert row is not None, f"no journeys row for id={journey_id} in {_store_path()}"
    return row


def _error_types(answer) -> list[str]:
    assert answer.status_code == 422, f"{answer.status_code} {answer.text}"
    body = answer.json()
    assert body["error"]["code"] == "VALIDATION_ERROR", body
    return [str(item.get("type")) for item in body["error"]["details"]["errors"]]


# ---------------------------------------------------------------- R1: the three states


def test_r1_declared_reason_lands_one_row_naming_the_codes_the_traveller_gave():
    jid = _journey("ORD-0464 R1 declared")
    answer = client.request(
        "DELETE",
        f"/api/v1/journeys/{jid}",
        json={"answered": True, "codes": ["BUDGET_DOES_NOT_FIT", "OTHER"], "note": "住的那晚超了"},
    )
    assert answer.status_code == 204, answer.text
    assert answer.content == b"", answer.content

    rows = _abort_rows(jid)
    assert len(rows) == 1, f"一次成功的丢弃该留一枚事实行，实读={len(rows)}"
    payload = json.loads(rows[0]["payload_json"])
    assert payload["reason_state"] == "DECLARED", payload
    assert payload["codes"] == ["BUDGET_DOES_NOT_FIT", "OTHER"], (
        "顺序是旅客自己的顺序，不该被服务端重排"
    )
    assert payload["note"] == "住的那晚超了", payload
    assert rows[0]["activity_id"] is None, dict(rows[0])
    assert rows[0]["actor_type"] == "USER", dict(rows[0])
    assert rows[0]["source"] == "DOMAIN", dict(rows[0])

    stored = _journey_row(jid)
    assert stored["deleted_at"] is not None, stored["deleted_at"]
    assert rows[0]["occurred_at_actual"] == stored["deleted_at"], (
        "丢弃时刻与事实行的时刻必须是同一个，否则一屏会说出两个时间"
    )
    assert stored["status"] != "CANCELLED", (
        "这一刀不碰 status：回收站这件事由 deleted_at 说，封闭 CHECK 里没有为它造词的余地"
    )


def test_r2_declining_the_question_is_a_legal_answer_not_a_blank():
    jid = _journey("ORD-0464 R2 skipped")
    answer = client.request(
        "DELETE", f"/api/v1/journeys/{jid}", json={"answered": False, "codes": [], "note": None}
    )
    assert answer.status_code == 204, answer.text
    rows = _abort_rows(jid)
    assert len(rows) == 1, len(rows)
    payload = json.loads(rows[0]["payload_json"])
    assert payload["reason_state"] == "SKIPPED_BY_TRAVELER", payload
    assert payload["codes"] == [], payload
    assert payload["note"] is None, payload


def test_r3_a_client_that_never_asked_is_not_recorded_as_a_traveller_who_declined():
    """The fabrication this order exists to prevent, pinned as an inequality, not as a count."""

    skipped = _journey("ORD-0464 R3 skipped")
    silent = _journey("ORD-0464 R3 never asked")
    assert client.request(
        "DELETE", f"/api/v1/journeys/{skipped}", json={"answered": False}
    ).status_code == 204
    assert client.request("DELETE", f"/api/v1/journeys/{silent}").status_code == 204

    got = json.loads(_abort_rows(skipped)[0]["payload_json"])
    left = json.loads(_abort_rows(silent)[0]["payload_json"])
    assert got["reason_state"] == "SKIPPED_BY_TRAVELER", got
    assert left["reason_state"] == "NOT_ASKED", (
        f"没有请求体不等于旅客说「不想说」，实读={left}"
    )
    assert left != got, "两格必须落进同一张表的两枚不同状态，而不是同一句默认话"


def test_r4_a_pre_existing_trip_migration_reads_never_asked_not_declined():
    """A row written before this order could ask has no `reason_state` at all.

    The door cannot retro-ask, so the honest outward reading is `NOT_ASKED`.  This arm pins the
    reader's rule rather than the writer's: an absent state must not be rendered as the traveller's
    silence, which is how ORD-0355's `stay_budget_declared IS NULL` case behaved on the other side.
    """

    jid = _journey("ORD-0464 R4 legacy row")
    assert client.request("DELETE", f"/api/v1/journeys/{jid}").status_code == 204
    with sqlite3.connect(_store_path()) as connection:
        connection.execute(
            "UPDATE journey_outcome_events SET payload_json = '{}' "
            "WHERE journey_id = ? AND event_type = 'JOURNEY_DELETED'",
            (jid,),
        )
        connection.commit()
    raw = json.loads(_abort_rows(jid)[0]["payload_json"])
    assert raw == {}, raw
    read = client.get(f"/api/v1/journeys/{jid}/outcomes")
    assert read.status_code == 200, read.text
    events = [e for e in read.json()["events"] if e["event_type"] == "JOURNEY_DELETED"]
    assert len(events) == 1, events
    assert "reason_state" not in events[0]["payload"], (
        "读门把存的东西原样带出来：没有状态就是没有状态，不是屏幕自己补一枚「跳过」"
    )


# ---------------------------------------------------------------- R5..R9: refusals


def test_r5_answering_without_naming_anything_is_refused_and_the_trip_stays():
    jid = _journey("ORD-0464 R5 empty answer")
    answer = client.request("DELETE", f"/api/v1/journeys/{jid}", json={"answered": True, "codes": []})
    assert "abort_answer_without_codes" in _error_types(answer), _error_types(answer)
    assert "ABORT_ANSWER_WITHOUT_CODES" in answer.text, answer.text
    assert _journey_row(jid)["deleted_at"] is None, "被拒的一tap 不许把行程丢进回收站"
    assert _abort_rows(jid) == [], f"被拒的一tap 不许留下理由行：{len(_abort_rows(jid))}"


def test_r6_declining_while_naming_reasons_is_refused_as_a_contradiction():
    jid = _journey("ORD-0464 R6 both at once")
    answer = client.request(
        "DELETE", f"/api/v1/journeys/{jid}", json={"answered": False, "codes": ["OTHER"]}
    )
    assert "abort_skip_with_codes" in _error_types(answer), _error_types(answer)
    assert _journey_row(jid)["deleted_at"] is None, answer.text
    assert _abort_rows(jid) == []


def test_r7_a_code_outside_the_vocabulary_is_refused_and_points_at_its_slot():
    """Measured, not assumed: this server does not echo the rejected value back.

    The 422 item carries `loc = ["body","codes",0]`, the closed list in `msg`, and the dictionary key
    `validation.not_an_option` - the `safe_errors` filter at `4037cb331ea00b83124316d40329762fa1131689:backend/app/main.py:613-623` keeps
    `loc`/`msg`/`type`/`message_key` and drops the input, so the screen marks *which* line is wrong and
    says the same sentence for any traveller.  Pinning the slot is what a screen can act on; pinning an
    echoed value would pin a behaviour this server deliberately does not have.
    """

    jid = _journey("ORD-0464 R7 invented code")
    answer = client.request(
        "DELETE",
        f"/api/v1/journeys/{jid}",
        json={"answered": True, "codes": ["OTHER", "SUPPLIER_KEPT_MY_BAGGAGE"]},
    )
    body = answer.json()["error"]
    assert body["code"] == "VALIDATION_ERROR", body
    item = body["details"]["errors"][0]
    assert list(item["loc"]) == ["body", "codes", 1], item
    assert item["type"] == "literal_error", item
    assert item["message_key"] == "validation.not_an_option", item
    assert "SUPPLIER_KEPT_MY_BAGGAGE" not in answer.text, (
        "被拒的那一枚词面不该被服务端回吐：这一格钉的是现有设计，不是我的偏好"
    )
    for token in CODES:
        assert token in item["msg"], f"拒绝要把词表摆出来，旅客才看得见自己那枚为什么不在里面：缺 {token}"
    assert _journey_row(jid)["deleted_at"] is None
    assert _abort_rows(jid) == []


def test_r8_note_cap_and_unknown_property_are_both_refused():
    too_long = _journey("ORD-0464 R8 note too long")
    long_note = "预算" * (ABORT_NOTE_MAX_LENGTH // 2 + 1)
    assert len(long_note) > ABORT_NOTE_MAX_LENGTH, len(long_note)
    answer = client.request(
        "DELETE", f"/api/v1/journeys/{too_long}", json={"answered": True, "codes": ["OTHER"], "note": long_note}
    )
    assert _error_types(answer), answer.text
    assert _journey_row(too_long)["deleted_at"] is None

    unknown = _journey("ORD-0464 R8 unknown field")
    answer = client.request(
        "DELETE", f"/api/v1/journeys/{unknown}", json={"answered": True, "codes": ["OTHER"], "because": 3}
    )
    assert "extra_forbidden" in _error_types(answer), _error_types(answer)
    assert _journey_row(unknown)["deleted_at"] is None

    edge = _journey("ORD-0464 R8 note at the cap")
    cap_note = "价" * ABORT_NOTE_MAX_LENGTH
    assert len(cap_note) == ABORT_NOTE_MAX_LENGTH, len(cap_note)
    assert client.request(
        "DELETE", f"/api/v1/journeys/{edge}", json={"answered": True, "codes": ["OTHER"], "note": cap_note}
    ).status_code == 204
    assert json.loads(_abort_rows(edge)[0]["payload_json"])["note"] == cap_note


def test_r9_a_second_tap_refused_leaves_no_second_reason_row():
    jid = _journey("ORD-0464 R9 double tap")
    assert client.request(
        "DELETE", f"/api/v1/journeys/{jid}", json={"answered": True, "codes": ["OTHER"]}
    ).status_code == 204
    again = client.request(
        "DELETE", f"/api/v1/journeys/{jid}", json={"answered": True, "codes": ["BUDGET_DOES_NOT_FIT"]}
    )
    assert again.status_code == 409, again.text
    assert again.json()["error"]["reason_code"] == "JOURNEY_ALREADY_DELETED", again.text
    rows = _abort_rows(jid)
    assert len(rows) == 1, f"被拒的第二tap 不该再留一枚理由行：{len(rows)}"
    assert json.loads(rows[0]["payload_json"])["codes"] == ["OTHER"], rows[0]["payload_json"]


# ---------------------------------------------------------------- R10: the write guard


def test_r10_the_generic_outcomes_door_cannot_file_a_deletion():
    """`JOURNEY_DELETED` belongs to the delete door alone."""

    jid = _journey("ORD-0464 R10 forged fact")
    answer = client.post(
        f"/api/v1/journeys/{jid}/outcomes",
        json={"event_type": "JOURNEY_DELETED", "payload": {"reason_state": "DECLARED", "codes": ["OTHER"]}},
    )
    assert answer.status_code == 422, answer.text
    assert _abort_rows(jid) == [], "被拒的伪造行不许落库"
    assert _journey_row(jid)["deleted_at"] is None, "走 outcomes 门造不出丢弃这件事"

    legal = client.post(
        f"/api/v1/journeys/{jid}/outcomes", json={"event_type": "USER_ACCEPTED", "payload": {}}
    )
    assert legal.status_code == 201, legal.text
    assert _abort_rows(jid) == [], "合法的那一枚不该被算成丢弃行"


# ---------------------------------------------------------------- R11: dedupe, and the contract


def test_r11_a_reason_tapped_twice_counts_once():
    jid = _journey("ORD-0464 R11 repeats")
    assert client.request(
        "DELETE",
        f"/api/v1/journeys/{jid}",
        json={"answered": True, "codes": ["OTHER", "OTHER", "BUDGET_DOES_NOT_FIT", "OTHER"]},
    ).status_code == 204
    payload = json.loads(_abort_rows(jid)[0]["payload_json"])
    assert payload["codes"] == ["OTHER", "BUDGET_DOES_NOT_FIT"], (
        f"重复勾选不该数成两条理由，实读={payload['codes']}"
    )


def test_r12_every_vocabulary_token_is_declared_in_the_contract_and_the_client():
    """The enum is one list read three ways: pydantic, the hand-written contract, the generated client."""

    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    declared = spec["components"]["schemas"]["JourneyAbortCode"]["enum"]
    assert sorted(declared) == sorted(CODES), (
        f"契约与 Literal 不再是同一枚词表：契约={sorted(declared)} 代码={sorted(CODES)}"
    )
    assert len(declared) == len(set(declared)), declared

    request_schema = spec["components"]["schemas"]["JourneyAbortRequest"]
    assert request_schema["additionalProperties"] is False, request_schema
    assert request_schema["required"] == ["answered"], request_schema
    assert request_schema["properties"]["note"]["maxLength"] == ABORT_NOTE_MAX_LENGTH, request_schema
    state = spec["components"]["schemas"]["JourneyAbortState"]["enum"]
    assert state == ["DECLARED", "SKIPPED_BY_TRAVELER", "NOT_ASKED"], state

    operation = spec["paths"]["/journeys/{journey_id}"]["delete"]
    assert (
        operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/JourneyAbortRequest"
    ), operation
    assert operation["requestBody"]["required"] is False, (
        "这扇门必须继续接受不带理由的旧客户端，但不能把它们记成「旅客说不想答」"
    )
    assert "422" in operation["responses"], sorted(operation["responses"])

    generated = GENERATED.read_text(encoding="utf-8")
    for token in CODES + state:
        assert token in generated, f"{token} 在契约里有、在生成的客户端类型里没有"
    assert "JourneyAbortRequest" in generated, "生成的客户端必须带得起来自契约的请求形状"


def test_r13_the_request_model_itself_refuses_the_two_collapsed_shapes():
    """The refusals are a property of the model, not of one route's branch.

    Anything else that later takes this survey - a batch tool, an import - gets the same three states.
    """

    assert JourneyAbortRequest(answered=False).answered is False
    try:
        JourneyAbortRequest(answered=True, codes=[])
    except Exception as caught:  # pydantic ValidationError, named by its type below
        assert "ABORT_ANSWER_WITHOUT_CODES" in str(caught), str(caught)
    else:
        raise AssertionError("answered=true 而不点名任何理由应当被拒")
    try:
        JourneyAbortRequest(answered=False, codes=["OTHER"])
    except Exception as caught:
        assert "ABORT_SKIP_WITH_CODES" in str(caught), str(caught)
    else:
        raise AssertionError("一边跳过一边点名应当被拒")
