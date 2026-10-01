"""ORD-0505 - the trip's other half: an abort that the record can carry, not only the screen.

Measured at the base this order names (`f707e1b3908c9ff4371e4a013242880b7e36045d`): the CHECK on
`journeys.status` has offered `CANCELLED` since the first schema, and the only journey-status writes
on that tree are `main.py:6463` (`PLANNED`), `main.py:7836` (`ACTIVE`) and `main.py:8002` /
`main.py:8086` (`COMPLETED`).  The four `.status = "CANCELLED"` assignments in `backend/app` are an
activity, a booking, a commitment and a transport reservation -- none is a journey.  So a traveller
could throw a trip away and could not stop one.

Each arm below pays for one requirement of the order, and refusals are checked by their named
`error.reason_code` with the `http_status=` they answer at:

* the why is stored, not painted -- `cancelled_reason` and `cancelled_at` land in the row and are
  read back off `GET /api/v1/journeys/{id}` with nothing kept by the client;
* 中止 is not 丢弃 -- `deleted_at` is untouched, the trip still appears in `GET /api/v1/journeys`,
  and the live door `GET .../experience` refuses it by name;
* the three refusals are the three the order asked for: not-there, not-yours, already-stopped.
"""

from __future__ import annotations

from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app

client = TestClient(raise_server_exceptions=False, app=app)
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "openapi.yaml"


def _traveller(name: str) -> str:
    response = client.post(
        "/api/v1/travelers",
        json={"display_name": name, "locale": "zh-CN", "timezone": "Asia/Shanghai"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _journey(traveller_id: str, title: str) -> str:
    start = datetime.now(timezone.utc) + timedelta(days=3)
    response = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": traveller_id,
            "title": title,
            "city_code": "CN-TIANJIN",
            "timezone": "Asia/Shanghai",
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(days=2)).isoformat(),
            "budget": {"amount_minor": 300000, "currency": "CNY"},
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _abort(journey_id: str, requested_by: str, reason: str):
    return client.post(
        f"/api/v1/journeys/{journey_id}/abort",
        json={"reason": reason, "requested_by": requested_by},
    )


def _reason_code(response) -> str:
    return str(response.json().get("error", {}).get("reason_code") or "")


def test_ord0505_abort_stores_the_why_and_reads_it_back_off_the_server() -> None:
    traveller = _traveller(f"ord0505-owner-{uuid4()}")
    journey = _journey(traveller, "ORD-0505 中止链路")

    response = _abort(journey, traveller, "同行的人改期了")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "CANCELLED", body
    assert body["cancelled_reason"] == "同行的人改期了", body
    assert body["cancelled_at"], "the server must record its own moment"

    # Read it back through an ordinary GET: nothing above this line may be the only copy.
    reread = client.get(f"/api/v1/journeys/{journey}")
    assert reread.status_code == 200, reread.text
    assert reread.json()["status"] == "CANCELLED", reread.json()
    assert reread.json()["cancelled_reason"] == "同行的人改期了", reread.json()
    assert reread.json()["cancelled_at"] == body["cancelled_at"], reread.json()


def test_ord0505_abort_is_not_the_bin_and_the_trip_stays_in_the_list() -> None:
    traveller = _traveller(f"ord0505-list-{uuid4()}")
    journey = _journey(traveller, "ORD-0505 中止不等于丢弃")

    row = _row(journey)
    assert row["deleted_at"] is None, row
    response = _abort(journey, traveller, "计划取消")
    assert response.status_code == 200, response.text

    after = _row(journey)
    assert after["rowid"] == row["rowid"], "the same row, not a replacement"
    assert after["deleted_at"] is None, f"中止 must not touch the bin column: {after}"
    assert after["status"] == "CANCELLED", after
    assert after["cancelled_reason"] == "计划取消", after

    listed = client.get("/api/v1/journeys")
    assert listed.status_code == 200, listed.text
    assert journey in [str(item["id"]) for item in listed.json()], (
        "an aborted trip disappeared from the list, which is the bin door's behaviour, not this one"
    )


def _row(journey_id: str) -> dict:
    session = SessionLocal()
    try:
        raw = session.execute(
            text(
                "SELECT rowid, status, deleted_at, cancelled_at, cancelled_reason "
                "FROM journeys WHERE id = :i"
            ),
            {"i": journey_id},
        ).first()
    finally:
        session.close()
    assert raw is not None, f"no journeys row for {journey_id}"
    return {
        "rowid": raw[0],
        "status": raw[1],
        "deleted_at": raw[2],
        "cancelled_at": raw[3],
        "cancelled_reason": raw[4],
    }


def test_ord0505_live_door_refuses_an_aborted_trip_by_name() -> None:
    traveller = _traveller(f"ord0505-live-{uuid4()}")
    journey = _journey(traveller, "ORD-0505 实时屏")

    live = client.get(f"/api/v1/journeys/{journey}/experience")
    assert live.status_code == 200, live.text

    assert _abort(journey, traveller, "这趟不走了").status_code == 200
    refused = client.get(f"/api/v1/journeys/{journey}/experience")
    assert refused.status_code == 409, refused.text
    assert _reason_code(refused) == "JOURNEY_ABORTED_NOT_LIVE", refused.text


def test_ord0505_three_refusals_each_answer_with_their_own_name() -> None:
    traveller = _traveller(f"ord0505-refusal-{uuid4()}")

    missing = _abort(str(uuid4()), traveller, "不存在也要有名")
    assert missing.status_code == 404, missing.text
    assert _reason_code(missing) == "JOURNEY_NOT_FOUND", missing.text

    journey = _journey(traveller, "ORD-0505 拒绝形")
    stranger = _traveller(f"ord0505-stranger-{uuid4()}")
    forbidden = _abort(journey, stranger, "不该由别人中止")
    assert forbidden.status_code == 403, forbidden.text
    assert _reason_code(forbidden) == "JOURNEY_ABORT_NOT_AUTHORISED", forbidden.text
    assert _row(journey)["status"] != "CANCELLED", "a refused tap must not have written the state"

    assert _abort(journey, traveller, "第一次中止").status_code == 200
    again = _abort(journey, traveller, "第二次不该覆盖第一次")
    assert again.status_code == 409, again.text
    assert _reason_code(again) == "JOURNEY_ABORT_ALREADY_CANCELLED", again.text
    assert _row(journey)["cancelled_reason"] == "第一次中止", (
        "the refused second tap overwrote the reason the record already held"
    )


def test_ord0505_blank_reason_is_refused_rather_than_stored_as_nothing() -> None:
    traveller = _traveller(f"ord0505-blank-{uuid4()}")
    journey = _journey(traveller, "ORD-0505 空原因")
    response = _abort(journey, traveller, "   ")
    assert response.status_code == 422, response.text
    assert _row(journey)["status"] != "CANCELLED", "a refused tap wrote the state anyway"
    assert _row(journey)["status"] != "CANCELLED", response.text


def test_ord0505_audit_records_the_abort_as_its_own_action() -> None:
    traveller = _traveller(f"ord0505-audit-{uuid4()}")
    journey = _journey(traveller, "ORD-0505 审计")
    assert _abort(journey, traveller, "同行者退出").status_code == 200

    session = SessionLocal()
    try:
        rows = session.execute(
            text("SELECT action FROM audit_logs WHERE entity_id = :i ORDER BY rowid"),
            {"i": journey},
        ).fetchall()
    finally:
        session.close()
    actions = [str(row[0]) for row in rows]
    assert "journey.aborted" in actions, actions
    assert "journey.deleted" not in actions, f"中止 wrote a bin action: {actions}"


def test_ord0505_contract_declares_the_door_and_the_generated_client_carries_it() -> None:
    import yaml

    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    path = spec["paths"]["/journeys/{journey_id}/abort"]
    assert "post" in path, sorted(path)
    post = path["post"]
    assert "JourneyAbortRequest" in str(post["requestBody"]), post["requestBody"]
    codes = str(post["responses"])
    for name in (
        "JOURNEY_NOT_FOUND",
        "JOURNEY_ABORT_NOT_AUTHORISED",
        "JOURNEY_ABORT_ALREADY_CANCELLED",
    ):
        assert name in codes, f"{name} is not named in the contract: {codes[:400]}"

    runtime = {
        (route.path, method)
        for route in app.routes
        for method in (getattr(route, "methods", None) or set())
    }
    assert ("/api/v1/journeys/{journey_id}/abort", "POST") in runtime, (
        "the contract declares a door the app does not serve"
    )

    generated = (ROOT / "frontend" / "src" / "generated" / "api.ts").read_text(encoding="utf-8")
    assert "/journeys/{journey_id}/abort" in generated, (
        "frontend/src/generated/api.ts was not regenerated from the synced contract"
    )
    assert "JourneyAbortRequest" in generated, generated[:400]

def test_ord0505_screen_words_carry_both_facts_in_both_language_arms() -> None:
    """The order asks for a screen that says what happens and whether it can be taken back.

    That is checkable off the browser: the copy table is one file, both arms must carry every key,
    and the two sentences must state the two facts -- leaving the live screen while staying in the
    list, and the absence of an un-abort door in this build.  A key missing from one arm would print
    a raw key name on the phone, which is the failure `t(key)` already has a history of here.
    """

    text = (ROOT / "frontend" / "src" / "features" / "abort" / "journeyAbortCopy.ts").read_text(
        encoding="utf-8"
    )
    zh = text.split("  zh: {", 1)[1].split("  },", 1)[0]
    en = text.split("  en: {", 1)[1].split("  },", 1)[0]
    keys = [
        "title", "reasonLabel", "reasonHint", "submit", "after", "back",
        "storedReason", "noReasonYet", "done", "refusedAuthorised",
        "refusedNotFound", "refusedAlready", "refusedOther",
    ]
    for arm, body in (("zh", zh), ("en", en)):
        missing = [key for key in keys if f"{key}:" not in body]
        assert not missing, f"the {arm} arm is missing {missing}; a screen would print the key itself"
    assert "实时屏" in zh and "行程列表" in zh, zh
    assert "不可逆" in zh, "the Chinese sentence must say there is no un-abort door"
    assert "live screen" in en and "trip list" in en, en
    assert "no un-abort door" in en, en
    assert "{reason}" in zh and "{moment}" in zh, "the stored reason must read back from the row"
