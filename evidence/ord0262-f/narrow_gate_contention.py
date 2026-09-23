"""ORD-0262-NARROW 常驻门：**受控写冲突必须给出机器可读的理由**（不发明第二套词汇）。

四格各只问自己那一条问题（一臂红三条 ≠ 三份证据），owner 标在名字与断言消息里：

  ① 已具名的碰撞（`traveler_agent_policies.traveler_id` 唯一索引）必须落进产品自己的信封
  ② 端到端：真排一次 race，不许出现裸 500；**判在行上**（拿 503 的那发不能留下 mission）
  ③ **名单外**的失败必须仍然是 500 —— 用另一张表的唯一冲突当正控，绝不拿 ① 那一枚冒充
  ④ `retry_after_ms` 只能由操作自己的阶梯给出，不再抄第四份字面量；
     同时钉住"现有 3 处 raise 点的常数 == 阶梯下限"——**不一致就红，这一格今晚就是红的**（commander 明令只钉不改）

护栏（commander 点名、仲裁 §3 同句）：本门**只声明这一格**。它不把 19 B/21 B 变成漂亮 JSON 就
宣称 ORD-0262 的原子性或完整性已闭 —— 孤儿 `CREATED` mission 与未落库的 `plan_version` 是各留各门的独立义务。
"""
from __future__ import annotations

import re
import sqlite3
import threading
from uuid import uuid4
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.db.models import TravelerAgentPolicy
from app.db.session import SessionLocal, engine
from app.main import (
    CONTENTION_UNIQUE_ROWS,
    _contention_of,
    _contention_response,
    _contention_retry_after_ms,
    app,
)
from app.stay_generation_operations import QUEUED
from app.stay_generation_operations import retry_after_ms as generation_retry_after_ms

TZ = timezone(timedelta(hours=8))
MAIN_PY = Path(__file__).resolve().parents[1] / "app" / "main.py"
POLICY_CLAIM = "traveler_agent_policies.traveler_id"

CMD_A = "帮我看看今晚有什么值得去的室内地方。"
CMD_B = "把今晚的安排换成节奏慢一点的室内活动。"

# 与产品内两处 raise 点**逐字相同**的那句话（不 import 产品常量：门要比字面，抄常量就测不到漂移）
BUSY_MESSAGE = "Another generation is writing right now; this one was not recorded. Try again."


def _make_traveler(client: TestClient) -> str:
    r = client.post("/api/v1/travelers",
                    json={"display_name": "ord0262", "timezone": "Asia/Shanghai"})
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _make_journey(client: TestClient, traveler_id: str, title: str) -> str:
    start = datetime(2026, 9, 26, 8, 0, tzinfo=TZ)
    r = client.post("/api/v1/journeys", json={
        "traveler_id": traveler_id, "title": title, "city_code": "CNX-DEMO",
        "timezone": "Asia/Shanghai", "start_at": start.isoformat(),
        "end_at": (start + timedelta(days=1, hours=8)).isoformat(),
        "budget": {"amount_minor": 20000, "currency": "CNY"}, "planning_mode": "balanced"})
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _real_policy_claim_collision(traveler_id: str) -> IntegrityError:
    """造一次**真的**唯一索引冲突（两次独立提交插同一枚 traveler_id），返回真实的异常对象。"""
    def insert() -> None:
        with SessionLocal() as session:
            session.add(TravelerAgentPolicy(traveler_id=traveler_id, mode="ADVISORY",
                                            auto_accept_replan=False,
                                            max_auto_replan_cost_delta_minor=0,
                                            max_auto_loss_minor=0, max_auto_schedule_drift_min=0,
                                            allowed_activity_types_json="[]",
                                            allowed_booking_types_json="[]",
                                            protected_commitment_levels_json="[]",
                                            allow_auto_commitment_management=False,
                                            allow_auto_when_provider_degraded=False,
                                            allow_auto_on_critical_event=False,
                                            version=1, created_at="x", updated_at="x"))
            session.commit()

    insert()
    try:
        insert()
    except IntegrityError as exc:
        with SessionLocal() as cleanup:      # 清掉我自己造的那行，别给后面的格子留脏
            cleanup.query(TravelerAgentPolicy).filter_by(traveler_id=traveler_id).delete()
            cleanup.commit()
        return exc
    raise AssertionError("SETUP：唯一索引没咬住 ⇒ 这一格什么都没测到（先修造数据，别改判据）")


def _missions_of(journey_id: str) -> list[str]:
    with SessionLocal() as session:
        return [row[0] for row in session.execute(
            text("SELECT id FROM journey_missions WHERE journey_id=:j"), {"j": journey_id})]


# ------------------------------------------------------------------ ① 已具名碰撞 ⇒ 落进产品信封

def test_1_named_policy_claim_collision_answers_inside_the_existing_envelope() -> None:
    """owner=①：碰撞被认出并翻译成一族现成码 + reason_code 指名，字段一格不缺。"""
    traveler_id = _traveler_id()
    exc = _real_policy_claim_collision(traveler_id)
    assert POLICY_CLAIM in str(getattr(exc, "orig", exc)), (
        f"SETUP：拿到的不是那一枚唯一索引的冲突，实测 {str(exc)[:160]}")
    reason = _contention_of(exc)
    assert reason == f"unique_row_already_claimed:{POLICY_CLAIM}", (
        f"①：名单内的碰撞必须被具名，实际 {reason!r}")

    response = _contention_response(reason)
    body = response.body.decode("utf-8") if isinstance(response.body, bytes) else str(response.body)
    import json as _json
    payload = _json.loads(body)["error"]
    assert response.status_code == 503, f"①：状态码须 503，实际 {response.status_code}"
    assert payload["code"] == "GENERATION_STORE_BUSY", payload   # 不新增第四枚码（commander (a)）
    assert payload["message"] == BUSY_MESSAGE, "①：同一条件同一句话，不许按端点各造一份措辞"
    assert payload["message_key"] == "generation.store_busy", payload
    assert payload.get("reason_code") == reason, f"①：reason_code 没指名，实际 {payload!r}"
    assert payload.get("trace_id"), "①：信封没有 trace_id ⇒ 事后无法回溯是哪一发"
    assert isinstance(payload["details"]["retry_after_ms"], int), payload["details"]
    assert payload["details"]["contention"] == reason, payload["details"]
    assert POLICY_CLAIM in CONTENTION_UNIQUE_ROWS


_UNIT_CLIENT = TestClient(app)


def _traveler_id() -> str:
    """用产品自己的端点建 traveler：直接 ORM 插会撞 NOT NULL(`locale`)，那是仪器的错不是被测事实。"""
    r = _UNIT_CLIENT.post("/api/v1/travelers",
                          json={"display_name": "ord0262-unit", "timezone": "Asia/Shanghai"})
    assert r.status_code == 201, f"SETUP：建 traveler 失败 {r.status_code} {r.text[:160]}"
    return str(r.json()["id"])


# --------------------------------------------------------------------- ② 端到端：不许裸 500

def test_2_a_held_write_lock_answers_in_the_envelope_not_as_a_bare_500() -> None:
    """owner=②：另一个人**真的**占着写锁时，这一发必须落在信封里，而不是屏上一句自造原因。

    进程内两线程撞不出 `traveler_agent_policies` 那一格（同步路由被同一个事件循环串起来，
    get-or-create 的窗口不重叠）—— 那是跨进程形制，归 verifier（仲裁 §3）。所以我改成
    用真连接真的占住 SQLite 写锁：这样拿到的 `database is locked` 不是造的，
    而且必须等满产品的 busy_timeout 才失败 —— 等待时长本身也钉住，免得"绕过锁"读成"修好了"。
    """
    client = TestClient(app)
    traveler_id = _make_traveler(client)
    jid = _make_journey(client, traveler_id, f"lock-held-{uuid4().hex[:8]}")
    db_path = Path(engine.url.database).resolve()
    assert db_path.is_file(), f"SETUP：解析到的库文件不在（{db_path}）⇒ 归属不对，不测"

    holder = sqlite3.connect(db_path, timeout=0, isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")            # 真实占用写者锁
    started = time.monotonic()
    try:
        response = client.post(f"/api/v1/journeys/{jid}/agent/commands",
                               json={"command": CMD_A, "requested_autonomy": "PLAN_ONLY"})
    finally:
        holder.execute("ROLLBACK")
        holder.close()
    waited = time.monotonic() - started
    assert waited >= 25, (
        f"②：只等了 {waited:.1f}s 就返回 ⇒ 没走到 busy_timeout，这一格什么都没测到（别放宽，去确认锁真占住了）")
    assert response.status_code == 503, (
        f"②：写锁占用中的答案必须 503，实际 {response.status_code}：{response.text[:220]}")
    payload = response.json()["error"]
    assert payload["code"] == "GENERATION_STORE_BUSY", payload
    assert payload.get("reason_code") == "sqlite_write_lock_busy", payload
    assert payload.get("message_key") == "generation.store_busy", payload
    assert isinstance(payload["details"]["retry_after_ms"], int) and payload["details"]["retry_after_ms"] > 0
    assert isinstance(payload.get("trace_id"), str) and payload["trace_id"], payload
    assert len(_missions_of(jid)) == 0, "②：被拒的这一发不该留下 mission 行"


# ------------------------------------------------------------- ③ 名单外必须仍然是 500（不洗白）

def test_3_an_unlisted_integrity_error_keeps_its_500_and_is_not_laundered() -> None:
    """owner=③：**名单外**的唯一冲突不是受控原因 ⇒ 原样再抛、保留 500。

    正控故意不用 `traveler_agent_policies`（那是 ① 的具名原因），否则等于拿已知的东西冒充未知。
    """
    traveler_id = _traveler_id()
    dup = IntegrityError("INSERT INTO travelers", {}, Exception(
        "UNIQUE constraint failed: travelers.id"))
    assert _contention_of(dup) is None, (
        "③：名单外的表被判成受控冲突 ⇒ 契约成了洗白机（`travelers.id` 不在名单里）")
    real = _real_policy_claim_collision(traveler_id)
    assert _contention_of(real) is not None       # 对照：名单内的确实认得出
    registered = [key for key in app.exception_handlers if isinstance(key, type)]
    assert IntegrityError in registered, (
        f"③：处理器没注册 ⇒ 名单形同虚设。实际 {[k.__name__ for k in registered]}")
    assert OperationalError in registered, (
        f"③：写锁那一半没注册。实际 {[k.__name__ for k in registered]}")


def test_4_a_non_lock_operational_error_is_not_called_contention() -> None:
    """owner=③'：sqlite 报的不是锁（语法错等）⇒ 不许冒充"忙"，更不许给重试资格。"""
    with engine.connect() as conn:
        try:
            conn.exec_driver_sql("SELECT * FROM a_table_that_does_not_exist")
        except OperationalError as exc:
            assert _contention_of(exc) is None, (
                f"③'：把非锁错误判成了写锁忙 ⇒ 会给不该重试的请求发 retry 提示：{exc}")
        else:
            raise AssertionError("SETUP：这条 SQL 没报错 ⇒ 拿不到真异常，这一格空转")
    real_lock = OperationalError("BEGIN IMMEDIATE", {},
                                 sqlite3.OperationalError("database is locked"))
    assert _contention_of(real_lock) == "sqlite_write_lock_busy"


# ------------------------------------------------- ④ retry 提示归阶梯；三处旧常数只钉不改

def test_5_the_retry_hint_comes_from_the_operation_ladder_not_a_fourth_literal() -> None:
    """owner=④：新契约的数值必须 == 阶梯对「刚排队的非终态作业」给的下限；并钉住现有 3 处常数。"""
    floor = generation_retry_after_ms(
        SimpleNamespace(status=QUEUED, queued_at=datetime.now(timezone.utc).isoformat()))
    assert _contention_retry_after_ms() == floor, (
        f"④：契约给的等值 ≠ 阶梯下限（{floor}）⇒ 有人在 raise 点又抄了一份数")
    literals = [int(m) for m in re.findall(
        r"details=\{[^{}]*\"retry_after_ms\":\s*([0-9]+)\}", MAIN_PY.read_text(encoding="utf-8"))]
    assert len(literals) >= 3, f"④：没找到那 3 处常数，实际 {literals}"
    assert set(literals) == {floor}, (
        f"FINDING_OPEN：三处 raise 点写的是 {sorted(set(literals))}ms，而操作自己的阶梯下限是 "
        f"{floor}ms ⇒ 同一件「忙」对用户承诺了两套等待。commander 明令今晚只钉不改，"
        f"要改的是把常数收口进阶梯（两枚 retry_after_ms(row) 之一），不是把断言放宽")


SHEET = Path(__file__).resolve().parents[2] / "frontend/src/features/planning/PlanWithAiSheet.tsx"


def test_6_the_surface_that_calls_this_route_still_reads_the_envelope_message() -> None:
    """owner=⑤（两侧都有份）：卡片的回落链里必须还有一格读 `body?.error?.message`。

    少了这一格，我给的具名答案会在屏上退化成客户端自造的 `HTTP <status>` —— 那正是 commander
    点名的失败形制。链子被谁拆了，这一格当场红，并说是哪一侧坏。
    """
    assert SHEET.is_file(), f"SETUP：读不到 {SHEET} ⇒ 前端耦合无从判定，不许当通过"
    text = SHEET.read_text(encoding="utf-8")
    assert "/agent/commands" in text, "⑤：这个组件不再调本门覆盖的路由 ⇒ 先确认归属再谈红绿"
    lines = text.splitlines()
    at = next((i for i, ln in enumerate(lines)
               if re.match(r"^\s*failureReason:\s*$", ln)), None)
    assert at is not None, (
        "SETUP：找不到「值为一条回落链」的 failureReason（类型声明里也有同名字段，不算）"
        " ⇒ 前端改了形制，这一格要重读而不是放宽")
    body = "\n".join(lines[at:at + 5])          # 链体就是紧随其后的那几行，不靠括号配对
    assert "body?.error?.message" in body, (
        f"⑤ **前端侧坏**：回落链不再读 `error.message` ⇒ 服务器的话上不了屏，用户只剩自造的 "
        f"HTTP <status>。实测链体：{body[:260]}")
    rungs = [i for i, key in enumerate(("body?.detail", "body?.error?.message",
                                        "`HTTP ${response.status}`")) if key in body]
    assert rungs == [0, 1, 2], (
        f"⑤：三档缺一或顺序变了（detail → error.message → 自造 HTTP）⇒ 需重新判定谁在造原因：{body[:260]}")
    assert re.search(r'^\s+"message": message,$', MAIN_PY.read_text(encoding="utf-8"), re.M), (
        "⑤ **服务端侧坏**：信封正文不再组装 `message` 那一格 ⇒ 前端无从显示服务器的话")
