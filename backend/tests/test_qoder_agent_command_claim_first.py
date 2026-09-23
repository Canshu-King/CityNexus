"""ORD-0253 · **claim-first** 之后的常驻门：占了键却没回填时，谁都不许再写 mission。

形制说明（G5，先看这条再引用任何绿）：本文件**全部是单进程**（TestClient 与测试同进程，
`server_pid == os.getpid()`）。进程内那把 `journey_write_lock` 会把两线程串起来，所以
"两线程同键"在这里**永远**绿——它证明的是"没有回归"，不是"跨进程已闭"。跨进程那一格
（faces=2）归 verifier（仲裁 `5793495820` §3）。

我不再"赌一次 race"：把冲突做成**已落库的前置状态**（占位行 / 已填行 / 签名不符行），
于是每一格都是确定性的，并且判**在行上**（`journey_missions` 的行数），不判在状态码上。
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.commerce.idempotency import canonical_request_signature
from app.db.models import IdempotencyKey, JourneyMission
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)
TZ = timezone(timedelta(hours=8))
CMD_A = "我护照丢了，请告诉我怎么办。"
CMD_B = "帮我把今晚的安排换成室内活动，节奏慢一点。"

#: **门内自带的字面副本**（G4：不 import 产品常量——import 之后它就永远和自己相等，测不到漂移）。
#: 两句都是产品里已有的话，本次改动一个字都不新增。
SENT_DIFFERENT_REQUEST = "same idempotency key used for a different request"
SENT_INCOMPLETE_RECEIPT = "agent idempotency record is incomplete"


def _setup_journey() -> str:
    traveler = client.post("/api/v1/travelers",
                           json={"display_name": "claimfirst", "timezone": "Asia/Shanghai"})
    assert traveler.status_code == 201, traveler.text
    start = datetime(2026, 9, 26, 8, 0, tzinfo=TZ)
    journey = client.post("/api/v1/journeys", json={
        "traveler_id": traveler.json()["id"], "title": f"claimfirst-{uuid.uuid4().hex[:8]}",
        "city_code": "CNX-DEMO", "timezone": "Asia/Shanghai", "start_at": start.isoformat(),
        "end_at": (start + timedelta(days=1, hours=8)).isoformat(),
        "budget": {"amount_minor": 20000, "currency": "CNY"}, "planning_mode": "balanced"})
    assert journey.status_code == 201, journey.text
    return str(journey.json()["id"])


def _signature(jid: str, command: str = CMD_A, autonomy: str = "PLAN_ONLY") -> str:
    return canonical_request_signature({"journey_id": jid, "command": command,
                                        "requested_autonomy": autonomy})


def _post_key(jid: str, key: str, command: str = CMD_A, autonomy: str = "PLAN_ONLY"):
    return client.post(f"/api/v1/journeys/{jid}/agent/commands",
                       json={"command": command, "requested_autonomy": autonomy},
                       headers={"Idempotency-Key": key})


def _put_receipt(scoped_key: str, signature: str, *, body: dict | None) -> None:
    """把"别人已经占了这把键"做成**已落库**的前置状态，而不是赌一次时序。"""
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        session.add(IdempotencyKey(
            key=scoped_key, operation="agent.command", request_hash=signature,
            response_status=200 if body is not None else None,
            response_json=json.dumps(body, sort_keys=True) if body is not None else None,
            created_at=now.isoformat(), expires_at=(now + timedelta(days=7)).isoformat()))
        session.commit()


def _mission_rows(jid: str) -> list[str]:
    with SessionLocal() as session:
        return sorted(session.scalars(select(JourneyMission.id)
                                      .where(JourneyMission.journey_id == jid)).all())


def _receipt_rows(scoped_key: str) -> list[IdempotencyKey]:
    with SessionLocal() as session:
        return list(session.scalars(select(IdempotencyKey).where(IdempotencyKey.key == scoped_key)))


def _message_of(response) -> str:
    """信封里那句**服务器原话**。比较一律用 `==`，不用 `in` —— 理由见最后一格。"""
    return str(response.json()["error"]["message"])


def _message_equals(response, expected: str) -> bool:
    try:
        return _message_of(response) == expected
    except Exception:
        return False


# -------------------------------------------------------------------------------- G1

def test_1_an_unfilled_claim_blocks_the_write_and_is_answered_with_the_existing_409() -> None:
    """owner=G1：有人占了键却没回填 ⇒ 我不进 impl、库里 0 行、答案是现成那句 409。"""
    jid = _setup_journey()
    key = f"cf-unfilled-{uuid.uuid4().hex[:8]}"
    _put_receipt(f"agent.command:{key}", _signature(jid), body=None)

    response = _post_key(jid, key)
    assert response.status_code == 409, f"G1：实际 {response.status_code} {response.text[:220]}"
    assert _message_equals(response, SENT_INCOMPLETE_RECEIPT), (
        f"G1：必须逐字沿用现成那句（不新造词），实际 {_message_of(response)[:200]!r}")
    assert _mission_rows(jid) == [], (
        f"G1：占了键的那发不能替我建 mission ⇒ 这正是 GHOST_MISSION_ROW 的形状，"
        f"实际 {len(_mission_rows(jid))} 行")


# -------------------------------------------------------------------------------- G2

def test_2_a_filled_claim_is_replayed_without_building_a_second_mission() -> None:
    """owner=G2：键已被填好 ⇒ 回赢家那份正文，且**一行都不许多**。"""
    jid = _setup_journey()
    key = f"cf-filled-{uuid.uuid4().hex[:8]}"
    winner_mission = {"mission": {"id": str(uuid.uuid4()), "journey_id": jid}, "replayed": True}
    _put_receipt(f"agent.command:{key}", _signature(jid), body=winner_mission)

    response = _post_key(jid, key)
    assert response.status_code == 200, f"G2：实际 {response.status_code} {response.text[:200]}"
    assert response.json()["mission"]["id"] == winner_mission["mission"]["id"], (
        "G2：回放必须回**那一枚** mission，而不是另起一枚")
    assert _mission_rows(jid) == [], (
        f"G2：回放的一发不该建行，实际 {len(_mission_rows(jid))} 行")
    assert len(_receipt_rows(f"agent.command:{key}")) == 1, "G2：收据行也只能有一枚（唯一索引在，不该多插）"


# -------------------------------------------------------------------------------- G3

def test_3_same_key_different_intent_is_still_the_canonical_mismatch_409() -> None:
    """owner=G3：同键换意图 ⇒ 现成那句 mismatch，不许被新语义顶掉。"""
    jid = _setup_journey()
    key = f"cf-mismatch-{uuid.uuid4().hex[:8]}"
    _put_receipt(f"agent.command:{key}", _signature(jid), body={"mission": {"id": str(uuid.uuid4())}})

    response = _post_key(jid, key, command=CMD_B)
    assert response.status_code == 409, f"G3：实际 {response.status_code}"
    assert _message_equals(response, SENT_DIFFERENT_REQUEST), (
        f"G3：mismatch 那句话必须逐字原样，实际 {_message_of(response)[:200]!r}")
    assert _mission_rows(jid) == [], "G3：被拒的一发不许先建行再报错"


# -------------------------------------------------------------------------------- G4

def test_4_the_happy_path_still_creates_exactly_one_mission_and_fills_the_claim() -> None:
    """owner=G4：没人占键时一切照旧——1 行 mission，且收据行被**回填**（不是留个空壳）。"""
    jid = _setup_journey()
    key = f"cf-happy-{uuid.uuid4().hex[:8]}"
    first = _post_key(jid, key)
    assert first.status_code == 200, first.text
    assert len(_mission_rows(jid)) == 1, f"G4：实际 {len(_mission_rows(jid))} 行"
    rows = _receipt_rows(f"agent.command:{key}")
    assert len(rows) == 1, f"G4：收据应 1 行，实际 {len(rows)}"
    assert rows[0].response_json and json.loads(rows[0].response_json)["mission"]["id"] \
        == first.json()["mission"]["id"], (
        "G4：占位行必须被回填成「这一发的答案」，否则下一位只会拿到 409")
    assert rows[0].response_status == 200, rows[0].response_status


def test_5_two_threads_one_key_in_one_process_stay_at_one_row() -> None:
    """owner=G5(回归面)：两线程同键 ⇒ 仍只 1 行。**这一格证明不了跨进程**（见文件头）。"""
    jid = _setup_journey()
    key = f"cf-threads-{uuid.uuid4().hex[:8]}"
    barrier = threading.Barrier(2)
    out: list[int] = []

    def fire() -> None:
        barrier.wait(timeout=30)
        out.append(_post_key(jid, key).status_code)

    threads = [threading.Thread(target=fire) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert len(out) == 2 and all(code == 200 for code in out), f"G5：读数 {out}"
    assert len(_mission_rows(jid)) == 1, f"G5：实际 {len(_mission_rows(jid))} 行"


# -------------------------------------------------------------------------------- G4 的字面等值自证

def test_6_the_two_sentences_are_compared_literally_and_the_door_would_notice_drift() -> None:
    """owner=G4：证明"比字面"这一手是咬着的——差一个标点就该红。

    不 import 产品常量：那样它永远等于自己，测不到漂移（这是我自己踩过的坑）。
    """
    assert SENT_INCOMPLETE_RECEIPT == "agent idempotency record is incomplete"
    assert SENT_DIFFERENT_REQUEST == "same idempotency key used for a different request"

    class _Resp:
        def __init__(self, message: str) -> None:
            self._message = message

        def json(self) -> dict:
            return {"error": {"message": self._message}}

    # 漂移样本：加标点、加后缀、截断、加尾空格 —— **逐字**比较必须全都不认。
    # （我上一版用 `in`，前两种会被读成"匹配"，于是门会一边红一边假称"沿用了现成那句"）
    for drifted in ("agent idempotency record is incomplete.",
                    "agent idempotency record is incomplete (stale claim)",
                    "agent idempotency record",
                    "same idempotency key used for a different request "):
        assert not _message_equals(_Resp(drifted), SENT_INCOMPLETE_RECEIPT), (
            f"G4：漂移被读成同一条 ⇒ 比较不咬字：{drifted!r}")
        assert not _message_equals(_Resp(drifted), SENT_DIFFERENT_REQUEST), (
            f"G4：漂移被读成同一条 ⇒ 比较不咬字：{drifted!r}")

    # 反面对照：完全相同的那句必须认。少了它，上面那一串"全都不认"可能只是比较坏了。
    assert _message_equals(_Resp(SENT_INCOMPLETE_RECEIPT), SENT_INCOMPLETE_RECEIPT), (
        "G4：连等值都不认 ⇒ 这一手是坏的，不是严的")
